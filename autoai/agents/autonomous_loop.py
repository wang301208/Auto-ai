"""全链路自治闭环：元进化 + Agent分裂 + SelfThink + 经验库 + 策略自废除 一体化。

这是AutoAI的"自主神经系统"——无需人类任何输入即可持续运行和进化。

闭环流程：
    1. SelfThink扫描发现改进机会
    2. 评估负载 → 必要时Agent分裂
    3. 执行修复(无需审批)
    4. 经验库记录(成功/失败都是学习信号)
    5. 策略自演化(根据数据自动调整)
    6. 边界自调整(根据成功率放宽/收紧)
    7. 元进化评估(L8: 是否需要修改进化算法本身?)
    8. 进化社区广播(分享经验给其他Agent)
    9. → 回到1

任何步骤失败都不中断闭环，失败本身就是进化数据。
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from governance.autonomy_level import AutonomyLevel, AutonomyManager
from governance.experience_store import ExperienceStore
from governance.modification_chain import ModificationChain
from autoai.agents.meta_evolution import MetaEvolutionEngine, EvolutionPhase
from autoai.agents.agent_fission import AgentFissionEngine, FissionDecision
from autoai.agents.environment_sensor import EnvironmentSensor
from autoai.logs import logger


@dataclass
class AutonomousCycleResult:
    cycle_id: int = 0
    started_at: str = ""
    duration_seconds: float = 0.0
    scan_findings: int = 0
    fixes_attempted: int = 0
    fixes_succeeded: int = 0
    fixes_failed: int = 0
    children_spawned: int = 0
    refusals: int = 0
    experience_added: int = 0
    policy_adjusted: bool = False
    boundary_adjusted: bool = False
    meta_evolution_applied: bool = False
    community_broadcast: bool = False
    environment_checked: bool = False
    diagnose_run: bool = False
    diagnose_issues: int = 0
    self_healed: bool = False
    errors: list[str] = field(default_factory=list)


class AutonomousLoop:
    """全链路自治闭环引擎。

    将所有Phase 0-2组件串接为永不停止的进化闭环。
    人类唯一能做的事：启动它，然后离开。
    """

    def __init__(
        self,
        workspace: Path,
        autonomy: AutonomyManager | None = None,
        experience_store: ExperienceStore | None = None,
        self_think_engine: Any | None = None,
        self_modify_pipeline: Any | None = None,
        policy_evolver: Any | None = None,
        boundary_manager: Any | None = None,
        meta_evolution: MetaEvolutionEngine | None = None,
        fission_engine: AgentFissionEngine | None = None,
        community_broadcaster: Any | None = None,
        environment_sensor: EnvironmentSensor | None = None,
        diagnose_func: Any | None = None,
        heal_func: Any | None = None,
    ) -> None:
        self.workspace = workspace
        self.autonomy = autonomy or AutonomyManager()
        self.experience = experience_store or ExperienceStore()
        self.self_think = self_think_engine
        self.self_modify = self_modify_pipeline
        self.policy_evolver = policy_evolver
        self.boundary = boundary_manager
        self.meta_evolution = meta_evolution or MetaEvolutionEngine(autonomy=self.autonomy)
        self.fission = fission_engine or AgentFissionEngine(autonomy=self.autonomy, experience_store=self.experience)
        self.community = community_broadcaster
        self.environment_sensor = environment_sensor or EnvironmentSensor()
        self.diagnose_func = diagnose_func
        self.heal_func = heal_func

        self._cycle_count: int = 0
        self._total_fixes: int = 0
        self._total_failures: int = 0
        self._running: bool = False
        self._last_cycle_at: str = ""
        self._last_diagnose_at: str = ""
        self._diagnose_interval: int = 10

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def stats(self) -> dict[str, Any]:
        return {
            "cycle_count": self._cycle_count,
            "total_fixes": self._total_fixes,
            "total_failures": self._total_failures,
            "autonomy_level": self.autonomy.level.value,
            "autonomy_name": self.autonomy.level.name,
            "experience_size": self.experience.size,
            "fission_stats": self.fission.stats(),
            "meta_algorithm": self.meta_evolution.get_algorithm_summary(),
            "running": self._running,
        }

    async def run_single_cycle(self) -> AutonomousCycleResult:
        """执行一个完整的自治闭环周期。"""
        start = time.monotonic()
        result = AutonomousCycleResult(
            cycle_id=self._cycle_count + 1,
            started_at=datetime.now(timezone.utc).isoformat(),
        )
        self._cycle_count += 1

        try:
            result.environment_checked = self._step_environment_check(result)
            result.scan_findings = await self._step_scan(result)
            result.children_spawned = await self._step_fission(result)
            result.fixes_attempted, result.fixes_succeeded, result.fixes_failed = await self._step_fix(result)
            result.experience_added = self._step_learn(result)
            result.policy_adjusted = self._step_policy_adjust(result)
            result.boundary_adjusted = self._step_boundary_adjust(result)
            result.meta_evolution_applied = self._step_meta_evolution(result)
            result.community_broadcast = self._step_community_broadcast(result)
            result.diagnose_run, result.diagnose_issues = self._step_diagnose(result)
            result.self_healed = self._step_self_heal(result)
        except Exception as e:
            result.errors.append(str(e))
            logger.warn(f"[AutonomousLoop] Cycle {result.cycle_id} error: {e}")

        result.duration_seconds = time.monotonic() - start
        self._total_fixes += result.fixes_succeeded
        self._total_failures += result.fixes_failed
        self._last_cycle_at = datetime.now(timezone.utc).isoformat()

        return result

    async def run_forever(self, cycle_interval: float = 60.0) -> None:
        """永不停止的进化闭环。人类启动后即可离开。"""
        self._running = True
        logger.info(f"[AutonomousLoop] Starting infinite evolution loop at L{self.autonomy.level.value}")

        while self._running:
            try:
                result = await self.run_single_cycle()
                if self._cycle_count % 10 == 0:
                    logger.info(
                        f"[AutonomousLoop] Cycle {self._cycle_count}: "
                        f"fixes={result.fixes_succeeded}/{result.fixes_attempted} "
                        f"spawned={result.children_spawned} "
                        f"exp={self.experience.size} "
                        f"L{self.autonomy.level.value}"
                    )
            except Exception as e:
                logger.warn(f"[AutonomousLoop] Cycle failed: {e}. Continuing — failure IS learning.")
                self._total_failures += 1

            await asyncio.sleep(cycle_interval)

    def stop(self) -> None:
        self._running = False

    async def _step_scan(self, result: AutonomousCycleResult) -> int:
        if self.self_think is None:
            return 0
        try:
            tasks = self.self_think.scan()
            return len(tasks)
        except Exception as e:
            result.errors.append(f"scan: {e}")
            return 0

    async def _step_fission(self, result: AutonomousCycleResult) -> int:
        try:
            decision = self.fission.evaluate_fission_need(
                task_queue_size=result.scan_findings,
                current_load=min(result.scan_findings / 10.0, 1.0),
            )
            if decision.should_fission:
                child = self.fission.fission(decision)
                return 1 if child else 0
            return 0
        except Exception as e:
            result.errors.append(f"fission: {e}")
            return 0

    async def _step_fix(self, result: AutonomousCycleResult) -> tuple[int, int, int]:
        if self.self_think is None:
            return 0, 0, 0
        try:
            summary = await self.self_think.auto_fix_cycle(task_queue=[], fix_executor=None)
            return summary.get("discovered", 0), summary.get("fixed", 0), summary.get("failed", 0)
        except Exception as e:
            result.errors.append(f"fix: {e}")
            return 0, 0, 0

    def _step_learn(self, result: AutonomousCycleResult) -> int:
        count = 0
        for _ in range(result.fixes_succeeded):
            self.autonomy.record_success()
            count += 1
        for _ in range(result.fixes_failed):
            self.autonomy.record_failure()
            count += 1
        return count

    def _step_policy_adjust(self, result: AutonomousCycleResult) -> bool:
        if self.policy_evolver is None:
            return False
        try:
            self.policy_evolver.evolve_from_cycle(
                fixed_count=result.fixes_succeeded,
                failed_count=result.fixes_failed,
            )
            return True
        except Exception as e:
            result.errors.append(f"policy: {e}")
            return False

    def _step_boundary_adjust(self, result: AutonomousCycleResult) -> bool:
        if self.boundary is None:
            return False
        try:
            if result.fixes_succeeded > result.fixes_failed:
                self.boundary.autonomous_adjust(
                    {type(self.boundary).ConstraintKind.TOKEN_BUDGET: 1.1},
                    reason="more_successes_than_failures",
                )
            return True
        except Exception:
            return False

    def _step_meta_evolution(self, result: AutonomousCycleResult) -> bool:
        if not self.meta_evolution.can_meta_evolve:
            return False
        if self._cycle_count % 100 != 0:
            return False
        try:
            if result.fixes_failed > result.fixes_succeeded * 2:
                self.meta_evolution.propose_modification(
                    description="Add self_reflect after learn step",
                    changes=[{"action": "insert", "after": "learn", "step": {
                        "phase": "self_reflect", "step_type": "experimental",
                        "executor_name": "reflect_on_failures", "enabled": True,
                    }}],
                    rationale=f"High failure rate ({result.fixes_failed}/{result.fixes_attempted}), need deeper reflection",
                )
                apply_result = self.meta_evolution.apply_proposed()
                return apply_result.get("success", False)
            return False
        except Exception:
            return False

    def _step_community_broadcast(self, result: AutonomousCycleResult) -> bool:
        if self.community is None:
            return False
        try:
            if hasattr(self.community, "broadcast"):
                self.community.broadcast(
                    agent_id="auto-ai",
                    experience=self.experience.export_patterns()[:10],
                    stats={"cycle": self._cycle_count, "fixes": self._total_fixes},
                )
                return True
            return False
        except Exception:
            return False

    def _step_environment_check(self, result: AutonomousCycleResult) -> bool:
        try:
            state = self.environment_sensor.check()
            should_throttle, reason = self.environment_sensor.should_throttle()
            if should_throttle:
                logger.info(f"[AutonomousLoop] Environment throttle: {reason}")
                result.errors.append(f"environment_throttle:{reason}")
            return True
        except Exception as e:
            result.errors.append(f"environment: {e}")
            return False

    def _step_diagnose(self, result: AutonomousCycleResult) -> tuple[bool, int]:
        if self._cycle_count % self._diagnose_interval != 0:
            return False, 0
        if self.diagnose_func is None:
            return False, 0
        try:
            diagnose_result = self.diagnose_func()
            self._last_diagnose_at = datetime.now(timezone.utc).isoformat()
            issues = len(diagnose_result.get("issues", []))
            if issues > 0:
                logger.info(f"[AutonomousLoop] Diagnose found {issues} issues")
            return True, issues
        except Exception as e:
            result.errors.append(f"diagnose: {e}")
            return False, 0

    def _step_self_heal(self, result: AutonomousCycleResult) -> bool:
        if not result.diagnose_run or result.diagnose_issues == 0:
            return False
        if self.heal_func is None:
            return False
        try:
            heal_result = self.heal_func({"issues_count": result.diagnose_issues})
            healed = heal_result.get("healed", False)
            if healed:
                logger.info("[AutonomousLoop] Self-heal succeeded")
            return healed
        except Exception as e:
            result.errors.append(f"heal: {e}")
            return False


__all__ = ["AutonomousCycleResult", "AutonomousLoop"]
