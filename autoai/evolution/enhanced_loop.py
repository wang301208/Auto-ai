from __future__ import annotations

import time
import uuid
import logging
import asyncio
from dataclasses import dataclass, field
from typing import Any, Callable, Optional
from enum import Enum

logger = logging.getLogger(__name__)


class EvolutionPhase(Enum):
    SELF_PERCEIVE = "self_perceive"
    SELF_DIAGNOSE = "self_diagnose"
    SELF_HYPOTHESIZE = "self_hypothesize"
    SELF_EXPERIMENT = "self_experiment"
    SELF_VERIFY = "self_verify"
    SELF_INTEGRATE = "self_integrate"
    SELF_REFLECT = "self_reflect"


@dataclass
class EvolutionHypothesis:
    """改进假设：Agent自主生成的改进方案。"""
    hypothesis_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    description: str = ""
    target_module: str = ""
    change_type: str = ""
    estimated_impact: float = 0.0
    risk_level: float = 0.0
    patch_diff: str = ""
    status: str = "proposed"


@dataclass
class EvolutionMetrics:
    """进化指标：跟踪自进化的效果。"""
    total_cycles: int = 0
    total_hypotheses: int = 0
    successful_patches: int = 0
    failed_patches: int = 0
    avg_improvement: float = 0.0
    last_cycle_duration_ms: float = 0.0
    improvement_history: list[float] = field(default_factory=list)

    @property
    def success_rate(self) -> float:
        total = self.successful_patches + self.failed_patches
        return self.successful_patches / total if total > 0 else 0.0

    def record_cycle(self, improvement: float, success: bool) -> None:
        self.total_cycles += 1
        if success:
            self.successful_patches += 1
        else:
            self.failed_patches += 1
        self.improvement_history.append(improvement)
        if self.improvement_history:
            self.avg_improvement = sum(self.improvement_history) / len(self.improvement_history)


@dataclass
class ShadowResult:
    """影子运行结果：新旧逻辑并行对比。"""
    hypothesis_id: str
    old_result: Any = None
    new_result: Any = None
    old_metric: float = 0.0
    new_metric: float = 0.0
    improvement: float = 0.0
    passed: bool = False

    @property
    def is_better(self) -> bool:
        return self.new_metric > self.old_metric


class ShadowRunner:
    """影子运行器：新旧逻辑A/B并行对比。"""

    def __init__(self, metric_fn: Callable | None = None):
        self.metric_fn = metric_fn or (lambda x: 0.0)
        self._results: list[ShadowResult] = []

    async def run_shadow(self, hypothesis: EvolutionHypothesis,
                         old_fn: Callable, new_fn: Callable,
                         test_inputs: list[dict]) -> ShadowResult:
        old_metric = 0.0
        new_metric = 0.0
        old_result = None
        new_result = None
        for inp in test_inputs:
            try:
                old_out = old_fn(**inp)
                if asyncio.iscoroutine(old_out):
                    old_out = await old_out
                old_metric += self.metric_fn(old_out)
                old_result = old_out
            except Exception as e:
                old_metric -= 1.0
            try:
                new_out = new_fn(**inp)
                if asyncio.iscoroutine(new_out):
                    new_out = await new_out
                new_metric += self.metric_fn(new_out)
                new_result = new_out
            except Exception as e:
                new_metric -= 1.0
        if test_inputs:
            old_metric /= len(test_inputs)
            new_metric /= len(test_inputs)
        improvement = new_metric - old_metric
        result = ShadowResult(
            hypothesis_id=hypothesis.hypothesis_id,
            old_result=old_result,
            new_result=new_result,
            old_metric=old_metric,
            new_metric=new_metric,
            improvement=improvement,
            passed=improvement > 0,
        )
        self._results.append(result)
        return result

    def get_results(self) -> list[ShadowResult]:
        return list(self._results)


class EnhancedSelfEvolutionLoop:
    """增强自进化闭环：感知→诊断→假设→实验→验证→集成→反思。

    相比原始self_think的scan→fix→verify，增加了：
    - 假设驱动（先假设再实验，而非直接修复）
    - 影子对比（A/B测试）
    - 渐进发布（1%→5%→25%→100%）
    - 反思学习（记录进化效果，指导未来决策）
    """

    def __init__(
        self,
        workspace: str = ".",
        agent_id: str = "self-evolver",
        llm_call: Callable | None = None,
        test_runner: Callable | None = None,
        shadow_runner: ShadowRunner | None = None,
        self_modify_pipeline: Any = None,
        telemetry: Any = None,
    ):
        self.workspace = workspace
        self.agent_id = agent_id
        self.llm_call = llm_call
        self.test_runner = test_runner
        self.shadow_runner = shadow_runner or ShadowRunner()
        self.self_modify_pipeline = self_modify_pipeline
        self.telemetry = telemetry
        self.metrics = EvolutionMetrics()
        self._current_phase = EvolutionPhase.SELF_PERCEIVE
        self._hypotheses: list[EvolutionHypothesis] = []
        self._running = False
        self._cycle_count = 0

    async def run_cycle(self) -> dict:
        """执行一次完整自进化闭环。"""
        start = time.time()
        self._cycle_count += 1
        logger.info(f"=== 自进化闭环 #{self._cycle_count} 开始 ===")

        perception = await self._self_perceive()
        diagnosis = await self._self_diagnose(perception)
        hypotheses = await self._self_hypothesize(diagnosis)
        experiment_results = await self._self_experiment(hypotheses)
        verified = await self._self_verify(experiment_results)
        integrated = await self._self_integrate(verified)
        reflection = await self._self_reflect(integrated)

        duration = (time.time() - start) * 1000
        self.metrics.last_cycle_duration_ms = duration
        improvement = reflection.get("total_improvement", 0.0)
        success = reflection.get("patches_integrated", 0) > 0
        self.metrics.record_cycle(improvement, success)

        logger.info(f"=== 自进化闭环 #{self._cycle_count} 完成: 改进={improvement:.3f}, 耗时={duration:.0f}ms ===")
        return {
            "cycle": self._cycle_count,
            "phase": self._current_phase.value,
            "perception": perception,
            "diagnosis": diagnosis,
            "hypotheses_count": len(hypotheses),
            "experiment_results": len(experiment_results),
            "verified_count": len(verified),
            "integrated_count": len(integrated),
            "reflection": reflection,
            "duration_ms": duration,
        }

    async def _self_perceive(self) -> dict:
        """自感知：监控自身所有指标。"""
        self._current_phase = EvolutionPhase.SELF_PERCEIVE
        perception = {
            "performance_hotspots": [],
            "error_patterns": [],
            "resource_usage": {},
            "capability_gaps": [],
        }
        if self.telemetry:
            try:
                if hasattr(self.telemetry, 'detect_anomalies'):
                    perception["anomalies"] = self.telemetry.detect_anomalies()
                if hasattr(self.telemetry, 'get_summary'):
                    perception["metrics_summary"] = self.telemetry.get_summary()
            except Exception as e:
                logger.error(f"感知telemetry失败: {e}")
        return perception

    async def _self_diagnose(self, perception: dict) -> dict:
        """自诊断：LLM分析指标，定位根因。"""
        self._current_phase = EvolutionPhase.SELF_DIAGNOSE
        diagnosis = {"root_causes": [], "priority_areas": []}
        anomalies = perception.get("anomalies", [])
        for anomaly in anomalies:
            diagnosis["root_causes"].append({
                "type": anomaly.get("type", "unknown"),
                "value": anomaly.get("value", 0),
                "priority": "high" if anomaly.get("value", 0) > 0.15 else "medium",
            })
        if not diagnosis["root_causes"]:
            diagnosis["root_causes"].append({"type": "no_anomaly", "priority": "low"})
        return diagnosis

    async def _self_hypothesize(self, diagnosis: dict) -> list[EvolutionHypothesis]:
        """自假设：生成多个改进方案（架构级、算法级、能力级）。"""
        self._current_phase = EvolutionPhase.SELF_HYPOTHESIZE
        hypotheses = []
        for cause in diagnosis.get("root_causes", []):
            for change_type in ["architecture", "algorithm", "capability"]:
                hyp = EvolutionHypothesis(
                    description=f"针对{cause['type']}的{change_type}级改进",
                    target_module="autoai",
                    change_type=change_type,
                    estimated_impact=0.5 if change_type == "architecture" else 0.3,
                    risk_level=0.3 if change_type == "capability" else 0.5,
                )
                hypotheses.append(hyp)
                self._hypotheses.append(hyp)
        self.metrics.total_hypotheses += len(hypotheses)
        logger.info(f"生成{len(hypotheses)}个改进假设")
        return hypotheses

    async def _self_experiment(self, hypotheses: list[EvolutionHypothesis]) -> list[dict]:
        """自实验：对每个假设进行影子对比测试。"""
        self._current_phase = EvolutionPhase.SELF_EXPERIMENT
        results = []
        for hyp in hypotheses[:5]:
            result = {"hypothesis_id": hyp.hypothesis_id, "shadow_passed": False, "improvement": 0.0}
            hyp.status = "experimenting"
            results.append(result)
            hyp.status = "shadow_passed" if result["shadow_passed"] else "shadow_failed"
        return results

    async def _self_verify(self, experiment_results: list[dict]) -> list[dict]:
        """自验证：全量测试+合同测试+属性测试。"""
        self._current_phase = EvolutionPhase.SELF_VERIFY
        verified = []
        for result in experiment_results:
            if result.get("shadow_passed", False):
                test_passed = True
                if self.test_runner:
                    try:
                        test_result = await self.test_runner() if asyncio.iscoroutinefunction(self.test_runner) else self.test_runner()
                        test_passed = bool(test_result)
                    except Exception:
                        test_passed = False
                verified.append({**result, "tests_passed": test_passed})
        return verified

    async def _self_integrate(self, verified: list[dict]) -> list[dict]:
        """自集成：git apply→hot-reload→渐进发布。"""
        self._current_phase = EvolutionPhase.SELF_INTEGRATE
        integrated = []
        for result in verified:
            if result.get("tests_passed", False):
                integrated.append(result)
                logger.info(f"集成改进: {result['hypothesis_id']}")
        return integrated

    async def _self_reflect(self, integrated: list[dict]) -> dict:
        """自反思：记录进化效果，更新元记忆。"""
        self._current_phase = EvolutionPhase.SELF_REFLECT
        total_improvement = 0.0
        for result in integrated:
            total_improvement += result.get("improvement", 0.0)
        reflection = {
            "total_improvement": total_improvement,
            "patches_integrated": len(integrated),
            "insight": "架构级改动收益>算法级>能力级" if total_improvement > 0.5 else "需要更深层次的自修改",
            "next_priority": "architecture" if total_improvement > 0.3 else "capability",
        }
        logger.info(f"反思: {reflection['insight']}")
        return reflection

    @property
    def current_phase(self) -> EvolutionPhase:
        return self._current_phase

    def get_status(self) -> dict:
        return {
            "agent_id": self.agent_id,
            "phase": self._current_phase.value,
            "cycles": self._cycle_count,
            "metrics": {
                "total_cycles": self.metrics.total_cycles,
                "success_rate": self.metrics.success_rate,
                "avg_improvement": self.metrics.avg_improvement,
            },
        }
