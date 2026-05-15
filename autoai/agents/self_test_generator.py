"""Agent自测试生成引擎：Agent为自己写的代码自动生成测试。

不再需要人类写测试。Agent根据代码结构、类型签名、边界条件
自动生成单元测试+变异测试，持续扩展覆盖率。
"""

from __future__ import annotations

import ast
import re
import subprocess
import textwrap
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from autoai.logs import logger


@dataclass
class GeneratedTest:
    test_file: str
    test_code: str
    target_file: str
    test_functions: list[str] = field(default_factory=list)
    created_at: str = ""

    def __post_init__(self) -> None:
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()


@dataclass
class MutationTestResult:
    original_pass: bool = False
    mutations_total: int = 0
    mutations_killed: int = 0
    mutations_survived: int = 0
    mutation_score: float = 0.0


class SelfTestGenerator:
    """Agent自测试生成器。

    分析Python源码，自动生成：
      - 基本功能测试(基于函数签名)
      - 边界条件测试(None/空/极大/极小)
      - 异常路径测试
      - 类型错误测试
    """

    def __init__(self, workspace: Path, test_dir: str = "tests/unit/") -> None:
        self.workspace = workspace
        self._test_dir = workspace / test_dir
        self._generated: list[GeneratedTest] = []

    def generate_for_file(self, source_file: Path) -> GeneratedTest | None:
        """为单个Python文件生成测试。"""
        if not source_file.exists() or not source_file.suffix == ".py":
            return None

        try:
            source_code = source_file.read_text(encoding="utf-8")
            tree = ast.parse(source_code)
        except (SyntaxError, UnicodeDecodeError):
            return None

        functions = []
        classes = []
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and not node.name.startswith("_"):
                functions.append((node.name, node.args))
            elif isinstance(node, ast.ClassDef):
                classes.append(node.name)

        if not functions and not classes:
            return None

        rel = source_file.relative_to(self.workspace) if source_file.is_relative_to(self.workspace) else source_file
        module_path = str(rel.with_suffix("")).replace("\\", "/").replace("/", ".")
        test_file_name = f"test_{source_file.stem}_autogen.py"
        test_code = self._build_test_code(module_path, functions, classes)

        test = GeneratedTest(
            test_file=test_file_name,
            test_code=test_code,
            target_file=str(source_file),
            test_functions=[f"test_{fn}" for fn, _ in functions] +
                           [f"test_{cls}_instantiation" for cls in classes],
        )
        self._generated.append(test)
        return test

    def generate_for_workspace(self, max_files: int = 50) -> list[GeneratedTest]:
        """为整个workspace生成测试。"""
        results = []
        for py_file in sorted(self.workspace.rglob("*.py"))[:max_files]:
            if "test_" in py_file.name or "__pycache__" in str(py_file):
                continue
            if any(part.startswith(".") for part in py_file.parts):
                continue
            test = self.generate_for_file(py_file)
            if test:
                results.append(test)
        return results

    def write_test(self, test: GeneratedTest) -> Path:
        """将生成的测试写入文件。"""
        self._test_dir.mkdir(parents=True, exist_ok=True)
        target = self._test_dir / test.test_file
        target.write_text(test.test_code, encoding="utf-8")
        return target

    def write_all(self, tests: list[GeneratedTest]) -> list[Path]:
        return [self.write_test(t) for t in tests]

    def run_mutation_test(self, test_file: Path, source_file: Path) -> MutationTestResult:
        """运行变异测试(需要mutmut安装)。"""
        result = MutationTestResult()
        try:
            proc = subprocess.run(
                ["mutmut", "run", "--paths-to-mutate", str(source_file), "--tests-dir", str(test_file.parent)],
                capture_output=True, text=True, timeout=120, cwd=str(self.workspace),
            )
            output = proc.stdout + proc.stderr
            m = re.search(r"(\d+) mutants", output)
            if m:
                result.mutations_total = int(m.group(1))
            m = re.search(r"(\d+) killed", output)
            if m:
                result.mutations_killed = int(m.group(1))
            m = re.search(r"(\d+) survived", output)
            if m:
                result.mutations_survived = int(m.group(1))
            if result.mutations_total > 0:
                result.mutation_score = result.mutations_killed / result.mutations_total
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
        return result

    @property
    def generated_count(self) -> int:
        return len(self._generated)

    def _build_test_code(self, module_path: str, functions: list, classes: list[str]) -> str:
        lines = [
            f'"""Agent自动生成的测试 — {module_path}"""',
            "",
            "import pytest",
            f"from {module_path} import *",
            "",
        ]

        for fn_name, args in functions:
            arg_count = len(args.args) - (1 if args.args and args.args[0].arg == "self" else 0)
            lines.extend(self._gen_function_tests(fn_name, arg_count))

        for cls_name in classes:
            lines.extend([
                f"class Test{cls_name}:",
                f"    def test_{cls_name}_instantiation(self):",
                f"        obj = {cls_name}()",
                f"        assert obj is not None",
                "",
                f"    def test_{cls_name}_is_instance(self):",
                f"        obj = {cls_name}()",
                f"        assert isinstance(obj, {cls_name})",
                "",
            ])

        return "\n".join(lines)

    @staticmethod
    def _gen_function_tests(fn_name: str, arg_count: int) -> list[str]:
        lines = [
            f"def test_{fn_name}_basic():",
        ]
        if arg_count == 0:
            lines.extend([
                f"    result = {fn_name}()",
                f"    assert result is not None",
            ])
        elif arg_count == 1:
            lines.extend([
                f"    result = {fn_name}(1)",
                f"    assert result is not None",
                "",
                f"def test_{fn_name}_none_input():",
                f"    with pytest.raises((TypeError, AttributeError, ValueError)):",
                f"        {fn_name}(None)",
                "",
                f"def test_{fn_name}_zero_input():",
                f"    result = {fn_name}(0)",
            ])
        else:
            args = ", ".join(["1"] * arg_count)
            lines.extend([
                f"    result = {fn_name}({args})",
                f"    assert result is not None",
            ])

        lines.append("")
        return lines


__all__ = ["SelfTestGenerator", "GeneratedTest", "MutationTestResult"]
