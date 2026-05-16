"""自测试引擎: Agent自主生成和运行测试。"""

from __future__ import annotations

import time
import logging
from dataclasses import dataclass, field
from typing import Any
from enum import Enum

logger = logging.getLogger(__name__)


class TestStatus(Enum):
    PENDING = "pending"
    GENERATING = "generating"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    ERROR = "error"


class TestPriority(Enum):
    SMOKE = "smoke"
    REGRESSION = "regression"
    INVARIANT = "invariant"
    EDGE_CASE = "edge_case"
    PROPERTY = "property"


@dataclass
class TestSpec:
    """测试规格: Agent生成的测试蓝图。"""
    spec_id: str
    target_module: str
    target_function: str
    priority: TestPriority = TestPriority.SMOKE
    description: str = ""
    test_code: str = ""
    inputs: list[Any] = field(default_factory=list)
    expected_behavior: str = ""
    created_at: float = field(default_factory=time.time)

    @property
    def is_complete(self) -> bool:
        return len(self.test_code) > 0


@dataclass
class TestRun:
    """测试运行: 一次测试执行的结果。"""
    run_id: str
    spec_id: str
    status: TestStatus = TestStatus.PENDING
    execution_time_ms: float = 0.0
    error_message: str = ""
    coverage_hit: bool = False
    timestamp: float = field(default_factory=time.time)

    @property
    def passed(self) -> bool:
        return self.status == TestStatus.PASSED


class SelfTestEngine:
    """自测试引擎: Agent自主测试自己。"""

    def __init__(self, agent_id: str = "default"):
        self._agent_id = agent_id
        self._specs: dict[str, TestSpec] = {}
        self._runs: list[TestRun] = []
        self._total_generated: int = 0
        self._total_run: int = 0
        self._total_passed: int = 0
        self._total_failed: int = 0

    def generate_test(
        self,
        target_module: str,
        target_function: str,
        priority: TestPriority = TestPriority.SMOKE,
        description: str = "",
    ) -> TestSpec:
        """生成测试规格。"""
        self._total_generated += 1
        spec_id = f"tspec_{self._total_generated}"
        spec = TestSpec(
            spec_id=spec_id,
            target_module=target_module,
            target_function=target_function,
            priority=priority,
            description=description or f"测试 {target_module}.{target_function}",
        )
        spec.test_code = self._generate_code(spec)
        spec.inputs = self._generate_inputs(spec)
        spec.expected_behavior = self._infer_behavior(spec)
        self._specs[spec_id] = spec
        return spec

    def _generate_code(self, spec: TestSpec) -> str:
        return (
            f"def test_{spec.target_function}():\n"
            f"    from {spec.target_module} import {spec.target_function}\n"
            f"    result = {spec.target_function}()\n"
            f"    assert result is not None\n"
        )

    def _generate_inputs(self, spec: TestSpec) -> list[Any]:
        if spec.priority == TestPriority.EDGE_CASE:
            return [None, 0, -1, "", [], {}]
        elif spec.priority == TestPriority.PROPERTY:
            return [1, 10, 100]
        return [None]

    def _infer_behavior(self, spec: TestSpec) -> str:
        return f"{spec.target_function} should return valid result for given inputs"

    def run_test(self, spec: TestSpec) -> TestRun:
        """运行测试。"""
        self._total_run += 1
        run_id = f"trun_{self._total_run}"
        run = TestRun(run_id=run_id, spec_id=spec.spec_id, status=TestStatus.RUNNING)
        start = time.time()
        try:
            passed = self._simulate_execution(spec)
            run.status = TestStatus.PASSED if passed else TestStatus.FAILED
            run.coverage_hit = True
        except Exception as e:
            run.status = TestStatus.ERROR
            run.error_message = str(e)
        run.execution_time_ms = (time.time() - start) * 1000
        if run.passed:
            self._total_passed += 1
        else:
            self._total_failed += 1
        self._runs.append(run)
        return run

    def _simulate_execution(self, spec: TestSpec) -> bool:
        roll = hash(f"{spec.spec_id}:{spec.target_function}") % 10
        return roll < 8

    def run_all_tests(self) -> dict[str, Any]:
        """运行所有生成的测试。"""
        results = []
        for spec in self._specs.values():
            run = self.run_test(spec)
            results.append(run)
        return {
            "total": len(results),
            "passed": sum(1 for r in results if r.passed),
            "failed": sum(1 for r in results if not r.passed),
            "pass_rate": (
                sum(1 for r in results if r.passed) / len(results)
                if results else 0.0
            ),
        }

    def generate_module_tests(self, module_name: str, functions: list[str]) -> list[TestSpec]:
        """为模块生成全套测试。"""
        specs = []
        for func in functions:
            for priority in (TestPriority.SMOKE, TestPriority.EDGE_CASE):
                spec = self.generate_test(module_name, func, priority)
                specs.append(spec)
        return specs

    def get_failing_tests(self) -> list[TestRun]:
        return [r for r in self._runs if not r.passed]

    @property
    def stats(self) -> dict[str, Any]:
        pass_rate = self._total_passed / self._total_run if self._total_run > 0 else 0.0
        return {
            "agent_id": self._agent_id,
            "specs_generated": self._total_generated,
            "total_runs": self._total_run,
            "passed": self._total_passed,
            "failed": self._total_failed,
            "pass_rate": pass_rate,
        }
