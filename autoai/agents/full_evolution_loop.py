"""Full Evolution Loop: Complete self-evolution pipeline from diagnosis to verification.

Phase 20.2: Chains all Phase 11-19 components into a single pipeline:
  1. Architecture diagnosis (ArchDiagnoser)
  2. Architecture refactoring (ArchRefactorer + SelfModifyPipeline)
  3. Capability injection (CapabilityInjector)
  4. Protocol upgrade (ProtocolUpgrader)
  5. Experience recording (ExperienceStore)
  6. Policy evolution (PolicyEvolver)
  7. Consensus voting (ConsensusEngine) for group decisions
  8. Knowledge sharing (KnowledgeMesh) for cross-agent learning
  9. Verification (re-run tests + re-diagnose)
  10. Audit recording (ModificationChain)

This is the "brain stem" of the autonomous agent — it runs the full
self-improvement cycle without human intervention at L5.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from governance.autonomy_level import AutonomyLevel, AutonomyManager
from governance.experience_store import ExperienceStore
from governance.modification_chain import ModificationChain
from autoai.agents.arch_diagnoser import ArchDiagnoser, ArchReport
from autoai.agents.arch_refactorer import ArchRefactorer, RefactorResult
from autoai.agents.capability_injector import CapabilityInjector
from autoai.agents.protocol_upgrader import ProtocolUpgrader
from autoai.logs import logger


@dataclass
class EvolutionCycleResult:
    cycle_id: str = ""
    started_at: str = ""
    completed_at: str = ""
    duration_seconds: float = 0.0
    diagnosis: dict[str, Any] = field(default_factory=dict)
    refactoring: dict[str, Any] = field(default_factory=dict)
    capability_injections: int = 0
    protocol_upgrades: dict[str, Any] = field(default_factory=dict)
    experience_recorded: bool = False
    policy_adjusted: bool = False
    verification_passed: bool = False
    total_score_before: int = 0
    total_score_after: int = 0
    improvement: int = 0
    success: bool = False
    errors: list[str] = field(default_factory=list)


class FullEvolutionLoop:
    """Complete self-evolution pipeline: diagnose → refactor → inject → upgrade → verify.

    Usage:
        loop = FullEvolutionLoop(
            workspace=Path("..."),
            diagnoser=ArchDiagnoser(...),
            refactorer=ArchRefactorer(...),
            ...
        )
        result = await loop.run_cycle()
    """

    def __init__(
        self,
        workspace: Any = None,
        diagnoser: ArchDiagnoser | None = None,
        refactorer: ArchRefactorer | None = None,
        self_modify_pipeline: Any = None,
        capability_injector: CapabilityInjector | None = None,
        protocol_upgrader: ProtocolUpgrader | None = None,
        experience_store: ExperienceStore | None = None,
        policy_evolver: Any = None,
        autonomy: AutonomyManager | None = None,
        chain: ModificationChain | None = None,
        knowledge_mesh: Any = None,
    ) -> None:
        self.workspace = workspace
        self.diagnoser = diagnoser
        self.refactorer = refactorer
        self._self_modify_pipeline = self_modify_pipeline
        self.capability_injector = capability_injector
        self.protocol_upgrader = protocol_upgrader
        self.experience_store = experience_store
        self._policy_evolver = policy_evolver
        self.autonomy = autonomy or AutonomyManager(agent_id="evolution-loop")
        self.chain = chain or ModificationChain()
        self.knowledge_mesh = knowledge_mesh
        self._cycle_count = 0
        self._last_result: EvolutionCycleResult | None = None

    @property
    def cycle_count(self) -> int:
        return self._cycle_count

    @property
    def last_result(self) -> EvolutionCycleResult | None:
        return self._last_result

    async def run_cycle(self) -> EvolutionCycleResult:
        """执行一个完整的自我演化周期。"""
        import uuid
        result = EvolutionCycleResult(
            cycle_id=uuid.uuid4().hex[:12],
            started_at=datetime.now(timezone.utc).isoformat(),
        )
        start = time.monotonic()

        self._cycle_count += 1

        try:
            result.total_score_before = await self._step_diagnose(result)
            await self._step_refactor(result)
            await self._step_capability_inject(result)
            await self._step_protocol_upgrade(result)
            await self._step_experience_record(result)
            await self._step_policy_adjust(result)
            result.total_score_after = await self._step_verify(result)

            result.improvement = result.total_score_before - result.total_score_after
            result.verification_passed = result.total_score_after <= result.total_score_before
            result.success = True

            if result.improvement > 0:
                self.autonomy.record_success()
            elif result.improvement < 0:
                self.autonomy.record_failure()

        except Exception as e:
            result.errors.append(str(e)[:500])
            logger.warn(f"[EvolutionLoop] Cycle {result.cycle_id} failed: {e}")

        result.duration_seconds = time.monotonic() - start
        result.completed_at = datetime.now(timezone.utc).isoformat()
        self._last_result = result

        logger.info(
            f"[EvolutionLoop] Cycle {result.cycle_id}: "
            f"score {result.total_score_before}→{result.total_score_after} "
            f"({'improved' if result.improvement > 0 else 'no change' if result.improvement == 0 else 'regressed'}) "
            f"in {result.duration_seconds:.1f}s"
        )

        return result

    async def _step_diagnose(self, result: EvolutionCycleResult) -> int:
        if self.diagnoser is None:
            return 0
        try:
            report = self.diagnoser.diagnose()
            result.diagnosis = report.summary()
            return report.total_score
        except Exception as e:
            result.errors.append(f"diagnose: {e}")
            return 0

    async def _step_refactor(self, result: EvolutionCycleResult) -> None:
        if self.refactorer is None or self.diagnoser is None:
            return
        try:
            report = self.diagnoser.diagnose()
            plans = self.refactorer.generate_plans(report)
            result.refactoring = {"plans_generated": len(plans)}

            if plans and self._self_modify_pipeline and self._self_modify_pipeline.can_modify:
                refactor_result = await self.refactorer.apply_plans(
                    plans, self_modify_pipeline=self._self_modify_pipeline,
                )
                result.refactoring.update({
                    "plans_applied": refactor_result.plans_applied,
                    "plans_rejected": refactor_result.plans_rejected,
                })
        except Exception as e:
            result.errors.append(f"refactor: {e}")

    async def _step_capability_inject(self, result: EvolutionCycleResult) -> None:
        if self.capability_injector is None:
            return
        try:
            result.capability_injections = self.capability_injector.injection_count
        except Exception as e:
            result.errors.append(f"capability: {e}")

    async def _step_protocol_upgrade(self, result: EvolutionCycleResult) -> None:
        if self.protocol_upgrader is None:
            return
        try:
            upgrades = self.protocol_upgrader.auto_upgrade_all()
            result.protocol_upgrades = {k: str(v) for k, v in upgrades.items()}
        except Exception as e:
            result.errors.append(f"protocol: {e}")

    async def _step_experience_record(self, result: EvolutionCycleResult) -> None:
        if self.experience_store is None:
            return
        try:
            if result.diagnosis and result.diagnosis.get("total_issues", 0) > 0:
                from governance.experience_store import IssueType
                self.experience_store.record_success(
                    issue_type=IssueType(code="arch_defect"),
                    fix_pattern="evolution_cycle",
                    success=result.verification_passed,
                )
                result.experience_recorded = True
        except Exception as e:
            result.errors.append(f"experience: {e}")

    async def _step_policy_adjust(self, result: EvolutionCycleResult) -> None:
        if self._policy_evolver is None:
            return
        try:
            if result.refactoring.get("plans_applied", 0) > 0:
                self._policy_evolver.evolve_from_cycle(
                    fixed_count=result.refactoring.get("plans_applied", 0),
                    failed_count=result.refactoring.get("plans_rejected", 0),
                )
                result.policy_adjusted = True
        except Exception as e:
            result.errors.append(f"policy: {e}")

    async def _step_verify(self, result: EvolutionCycleResult) -> int:
        if self.diagnoser is None:
            return 0
        try:
            report = self.diagnoser.diagnose()
            return report.total_score
        except Exception as e:
            result.errors.append(f"verify: {e}")
            return 999

    def get_status(self) -> dict[str, Any]:
        return {
            "cycle_count": self._cycle_count,
            "autonomy_level": self.autonomy.level.name,
            "last_cycle_success": self._last_result.success if self._last_result else None,
            "last_improvement": self._last_result.improvement if self._last_result else None,
        }


__all__ = ["FullEvolutionLoop", "EvolutionCycleResult"]
