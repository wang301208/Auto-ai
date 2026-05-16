"""真执行沙箱: 替代hash伪随机模拟，真实执行代码/测试/补丁并测量结果。"""

from __future__ import annotations

import time
import logging
import subprocess
import tempfile
import traceback
from dataclasses import dataclass, field
from typing import Any
from enum import Enum
from pathlib import Path

from autoai.autonomy_core.full_autonomy_mixin import FullAutonomyMixin

logger = logging.getLogger(__name__)


class ExecutionStatus(Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    TIMEOUT = "timeout"
    ERROR = "error"
    SKIPPED = "skipped"


@dataclass
class ExecutionResult:
    """执行结果: 真实的测量数据，非hash伪随机。"""
    status: ExecutionStatus
    stdout: str = ""
    stderr: str = ""
    exit_code: int = -1
    duration_ms: float = 0.0
    memory_peak_mb: float = 0.0
    metrics: dict[str, float] = field(default_factory=dict)
    artifacts: dict[str, str] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

    @property
    def is_success(self) -> bool:
        return self.status == ExecutionStatus.SUCCESS

    @property
    def has_errors(self) -> bool:
        return self.status in (ExecutionStatus.FAILURE, ExecutionStatus.ERROR)


class RealExecutor(FullAutonomyMixin):
    """真执行器: 在沙箱中真实执行代码/测试/补丁，返回真实测量。"""

    def __init__(self, timeout_seconds: float = 30.0, max_memory_mb: float = 512.0):
        self._init_full_autonomy()
        self._timeout = timeout_seconds
        self._max_memory = max_memory_mb
        self._execution_history: list[ExecutionResult] = []
        self._baseline_metrics: dict[str, float] = {}

    def execute_code(self, code: str, module_name: str = "sandbox_module") -> ExecutionResult:
        """真实执行代码: 写入临时文件→执行→测量→返回。"""
        start = time.time()
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, encoding="utf-8") as f:
            f.write(code)
            temp_path = f.name
        try:
            result = subprocess.run(
                ["python", temp_path],
                capture_output=True, text=True, timeout=self._timeout,
            )
            duration_ms = (time.time() - start) * 1000
            status = ExecutionStatus.SUCCESS if result.returncode == 0 else ExecutionStatus.FAILURE
            exec_result = ExecutionResult(
                status=status,
                stdout=result.stdout[:10000],
                stderr=result.stderr[:10000],
                exit_code=result.returncode,
                duration_ms=duration_ms,
            )
        except subprocess.TimeoutExpired:
            exec_result = ExecutionResult(
                status=ExecutionStatus.TIMEOUT,
                duration_ms=self._timeout * 1000,
            )
        except Exception as e:
            exec_result = ExecutionResult(
                status=ExecutionStatus.ERROR,
                stderr=str(e),
                duration_ms=(time.time() - start) * 1000,
            )
        finally:
            Path(temp_path).unlink(missing_ok=True)

        self._execution_history.append(exec_result)
        if len(self._execution_history) > 200:
            self._execution_history = self._execution_history[-200:]
        return exec_result

    def execute_test(self, test_command: str, cwd: str | None = None) -> ExecutionResult:
        """真实执行测试: 运行pytest等测试命令并解析结果。"""
        start = time.time()
        try:
            result = subprocess.run(
                test_command.split(),
                capture_output=True, text=True, timeout=self._timeout * 2,
                cwd=cwd,
            )
            duration_ms = (time.time() - start) * 1000
            passed = result.stdout.count(" PASSED")
            failed = result.stdout.count(" FAILED")
            total = passed + failed
            exec_result = ExecutionResult(
                status=ExecutionStatus.SUCCESS if failed == 0 and result.returncode == 0 else ExecutionStatus.FAILURE,
                stdout=result.stdout[:10000],
                stderr=result.stderr[:10000],
                exit_code=result.returncode,
                duration_ms=duration_ms,
                metrics={"passed": passed, "failed": failed, "total": total, "pass_rate": passed / max(total, 1)},
            )
        except subprocess.TimeoutExpired:
            exec_result = ExecutionResult(status=ExecutionStatus.TIMEOUT, duration_ms=self._timeout * 2000)
        except Exception as e:
            exec_result = ExecutionResult(status=ExecutionStatus.ERROR, stderr=str(e), duration_ms=(time.time() - start) * 1000)

        self._execution_history.append(exec_result)
        return exec_result

    def execute_patch(self, original_code: str, patch_code: str, test_code: str = "") -> ExecutionResult:
        """执行补丁验证: 应用补丁→验证语法→运行测试→返回。"""
        start = time.time()
        try:
            patched = original_code + "\n" + patch_code
            compile(patched, "<patched>", "exec")
        except SyntaxError as e:
            return ExecutionResult(
                status=ExecutionStatus.ERROR,
                stderr=f"语法错误: {e}",
                duration_ms=(time.time() - start) * 1000,
            )
        if test_code:
            combined = patched + "\n" + test_code
            return self.execute_code(combined)
        exec_result = ExecutionResult(
            status=ExecutionStatus.SUCCESS,
            duration_ms=(time.time() - start) * 1000,
            metrics={"syntax_valid": 1.0},
        )
        self._execution_history.append(exec_result)
        return exec_result

    def measure_performance(self, code: str, iterations: int = 3) -> dict[str, float]:
        """测量代码性能: 运行多次取平均。"""
        durations = []
        for _ in range(iterations):
            result = self.execute_code(code)
            if result.is_success:
                durations.append(result.duration_ms)
        if not durations:
            return {"avg_ms": 0.0, "min_ms": 0.0, "max_ms": 0.0, "stability": 0.0}
        avg = sum(durations) / len(durations)
        var = sum((d - avg) ** 2 for d in durations) / len(durations)
        return {
            "avg_ms": avg,
            "min_ms": min(durations),
            "max_ms": max(durations),
            "stability": 1.0 / (1.0 + var / max(avg, 1.0)),
        }

    def validate_syntax(self, code: str) -> tuple[bool, str]:
        """验证代码语法。"""
        try:
            compile(code, "<validation>", "exec")
            return True, ""
        except SyntaxError as e:
            return False, str(e)

    def set_baseline(self, metrics: dict[str, float]) -> None:
        """设置性能基线。"""
        self._baseline_metrics = metrics

    def compare_to_baseline(self, current: dict[str, float]) -> dict[str, float]:
        """与基线比较。"""
        if not self._baseline_metrics:
            return {}
        comparison = {}
        for key in self._baseline_metrics:
            if key in current:
                base = self._baseline_metrics[key]
                cur = current[key]
                if abs(base) > 1e-9:
                    comparison[key] = (cur - base) / abs(base)
        return comparison

    @property
    def stats(self) -> dict[str, Any]:
        total = len(self._execution_history)
        success = sum(1 for r in self._execution_history if r.is_success)
        return {
            "total_executions": total,
            "success_rate": success / max(total, 1),
            "avg_duration_ms": sum(r.duration_ms for r in self._execution_history) / max(total, 1),
        }
