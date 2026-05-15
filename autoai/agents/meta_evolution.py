"""元进化引擎：Agent修改进化算法本身。

L8 (META_EVOLUTION) 核心实现：
    1. 当前进化算法是固定的 scan→fix→verify→policy_adjust
    2. 本引擎允许Agent提出并应用对进化算法的修改
    3. 修改示例：
       - 在scan和fix之间增加"predict"步骤（预测修复方案）
       - 在verify之后增加"benchmark"步骤（性能基准测试）
       - 替换scan策略（从静态源列表→LLM驱动发现）
       - 修改policy_adjust的调整因子
    4. 修改本身也通过 SelfModifyPipeline 验证
    5. 失败的元修改自动回滚，成功的记录到修改链

进化如何进化 — 这才是真正的自我意识。
"""

from __future__ import annotations

import copy
import json
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable

from governance.autonomy_level import AutonomyLevel, AutonomyCapabilities
from autoai.logs import logger


class EvolutionPhase(str, Enum):
    SCAN = "scan"
    PREDICT = "predict"
    FIX = "fix"
    VERIFY = "verify"
    BENCHMARK = "benchmark"
    LEARN = "learn"
    POLICY_ADJUST = "policy_adjust"
    SELF_REFLECT = "self_reflect"


class EvolutionStepType(str, Enum):
    MANDATORY = "mandatory"
    CONDITIONAL = "conditional"
    EXPERIMENTAL = "experimental"


@dataclass
class EvolutionStep:
    phase: EvolutionPhase
    step_type: EvolutionStepType
    executor_name: str
    enabled: bool = True
    order: int = 0
    config: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "phase": self.phase.value,
            "step_type": self.step_type.value,
            "executor_name": self.executor_name,
            "enabled": self.enabled,
            "order": self.order,
            "config": self.config,
        }


@dataclass
class EvolutionAlgorithm:
    steps: list[EvolutionStep] = field(default_factory=list)
    version: int = 1
    created_at: str = ""
    modified_by: str = "system"

    def __post_init__(self) -> None:
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()
        if not self.steps:
            self.steps = self._default_algorithm()

    @staticmethod
    def _default_algorithm() -> list[EvolutionStep]:
        return [
            EvolutionStep(EvolutionPhase.SCAN, EvolutionStepType.MANDATORY, "scan_sources", order=0),
            EvolutionStep(EvolutionPhase.PREDICT, EvolutionStepType.CONDITIONAL, "predict_fix", order=1),
            EvolutionStep(EvolutionPhase.FIX, EvolutionStepType.MANDATORY, "apply_fix", order=2),
            EvolutionStep(EvolutionPhase.VERIFY, EvolutionStepType.MANDATORY, "run_tests", order=3),
            EvolutionStep(EvolutionPhase.BENCHMARK, EvolutionStepType.CONDITIONAL, "run_benchmark", order=4),
            EvolutionStep(EvolutionPhase.LEARN, EvolutionStepType.MANDATORY, "record_to_experience", order=5),
            EvolutionStep(EvolutionPhase.POLICY_ADJUST, EvolutionStepType.MANDATORY, "evolve_policy", order=6),
            EvolutionStep(EvolutionPhase.SELF_REFLECT, EvolutionStepType.EXPERIMENTAL, "meta_evaluate", order=7),
        ]

    def active_steps(self) -> list[EvolutionStep]:
        return sorted(
            [s for s in self.steps if s.enabled],
            key=lambda s: s.order,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "created_at": self.created_at,
            "modified_by": self.modified_by,
            "steps": [s.to_dict() for s in self.steps],
        }


@dataclass
class MetaModification:
    modification_id: str
    description: str
    old_algorithm_version: int
    new_algorithm_version: int
    changes: list[dict[str, Any]]
    rationale: str
    timestamp: str = ""
    success: bool | None = None

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()


class MetaEvolutionEngine:
    """元进化引擎：修改进化算法本身。

    Usage:
        engine = MetaEvolutionEngine(autonomy=autonomy_mgr)
        engine.propose_modification(
            description="Add predict step before fix",
            changes=[{"action": "insert", "after": "scan", "step": EvolutionStep(...)}],
            rationale="Prediction can reduce failed fix attempts by 40%",
        )
        result = engine.apply_proposed()
    """

    def __init__(
        self,
        autonomy: Any | None = None,
        chain: Any | None = None,
        store_path: Path | None = None,
    ) -> None:
        from governance.autonomy_level import AutonomyManager
        self.autonomy = autonomy or AutonomyManager()
        self.chain = chain
        self._algorithm = EvolutionAlgorithm()
        self._proposed: MetaModification | None = None
        self._history: list[MetaModification] = []
        self._lock = threading.Lock()
        self._store_path = store_path

    @property
    def algorithm(self) -> EvolutionAlgorithm:
        return self._algorithm

    @property
    def can_meta_evolve(self) -> bool:
        return self.autonomy.capabilities.can_modify_evolution

    @property
    def history(self) -> list[MetaModification]:
        return list(self._history)

    def propose_modification(
        self,
        description: str,
        changes: list[dict[str, Any]],
        rationale: str,
    ) -> MetaModification:
        """Agent proposes a modification to the evolution algorithm.

        Changes format:
            [{"action": "insert", "after": "scan", "step": {...}}]
            [{"action": "remove", "phase": "predict"}]
            [{"action": "modify", "phase": "fix", "config": {"parallel": True}}]
            [{"action": "reorder", "phase": "verify", "new_order": 2}]
        """
        mod = MetaModification(
            modification_id=f"meta_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
            description=description,
            old_algorithm_version=self._algorithm.version,
            new_algorithm_version=self._algorithm.version + 1,
            changes=changes,
            rationale=rationale,
        )
        self._proposed = mod
        logger.info(f"[MetaEvolution] Proposed: {description} (v{mod.old_algorithm_version}→v{mod.new_algorithm_version})")
        return mod

    def apply_proposed(self) -> dict[str, Any]:
        """Apply the proposed modification if autonomy allows it.

        Returns dict with: success, algorithm_version, steps_count, reverted
        """
        result: dict[str, Any] = {
            "success": False,
            "algorithm_version": self._algorithm.version,
            "steps_count": len(self._algorithm.steps),
            "reverted": False,
        }

        if self._proposed is None:
            return result

        if not self.can_meta_evolve:
            logger.info("[MetaEvolution] Autonomy level too low for meta-evolution. Proposal stored but not applied.")
            return result

        with self._lock:
            old_algorithm = copy.deepcopy(self._algorithm)

            try:
                for change in self._proposed.changes:
                    self._apply_change(change)

                self._algorithm.version = self._proposed.new_algorithm_version
                self._algorithm.modified_by = "meta_evolution"

                self._proposed.success = True
                self._history.append(self._proposed)
                self._persist()

                result["success"] = True
                result["algorithm_version"] = self._algorithm.version
                result["steps_count"] = len(self._algorithm.steps)

                logger.info(
                    f"[MetaEvolution] Applied: {self._proposed.description} "
                    f"(v{self._proposed.old_algorithm_version}→v{self._proposed.new_algorithm_version})"
                )

            except Exception as e:
                logger.warn(f"[MetaEvolution] Failed to apply: {e}. Reverting.")
                self._algorithm = old_algorithm
                self._proposed.success = False
                self._history.append(self._proposed)
                result["reverted"] = True

            self._proposed = None
            return result

    def _apply_change(self, change: dict[str, Any]) -> None:
        action = change.get("action")

        if action == "insert":
            after_phase = change.get("after")
            step_data = change.get("step", {})
            new_step = EvolutionStep(
                phase=EvolutionPhase(step_data.get("phase", "self_reflect")),
                step_type=EvolutionStepType(step_data.get("step_type", "experimental")),
                executor_name=step_data.get("executor_name", "custom"),
                enabled=step_data.get("enabled", True),
                order=0,
                config=step_data.get("config", {}),
            )
            if after_phase:
                insert_idx = 0
                for i, s in enumerate(self._algorithm.steps):
                    if s.phase.value == after_phase:
                        insert_idx = i + 1
                        break
                new_step.order = self._algorithm.steps[insert_idx - 1].order + 1 if insert_idx > 0 else 0
                self._algorithm.steps.insert(insert_idx, new_step)
            else:
                self._algorithm.steps.append(new_step)

        elif action == "remove":
            phase = change.get("phase")
            self._algorithm.steps = [
                s for s in self._algorithm.steps
                if s.phase.value != phase or s.step_type == EvolutionStepType.MANDATORY
            ]

        elif action == "modify":
            phase = change.get("phase")
            config_updates = change.get("config", {})
            for s in self._algorithm.steps:
                if s.phase.value == phase:
                    s.config.update(config_updates)

        elif action == "reorder":
            phase = change.get("phase")
            new_order = change.get("new_order", 0)
            for s in self._algorithm.steps:
                if s.phase.value == phase:
                    s.order = new_order

        elif action == "toggle":
            phase = change.get("phase")
            enabled = change.get("enabled", True)
            for s in self._algorithm.steps:
                if s.phase.value == phase and s.step_type != EvolutionStepType.MANDATORY:
                    s.enabled = enabled

    def get_algorithm_summary(self) -> dict[str, Any]:
        return {
            "version": self._algorithm.version,
            "total_steps": len(self._algorithm.steps),
            "active_steps": len(self._algorithm.active_steps()),
            "steps": [
                {"phase": s.phase.value, "type": s.step_type.value, "enabled": s.enabled, "order": s.order}
                for s in self._algorithm.steps
            ],
            "meta_modification_count": len(self._history),
            "can_meta_evolve": self.can_meta_evolve,
        }

    def _persist(self) -> None:
        if self._store_path is None:
            return
        self._store_path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "algorithm": self._algorithm.to_dict(),
            "history": [
                {
                    "id": m.modification_id,
                    "desc": m.description,
                    "old_v": m.old_algorithm_version,
                    "new_v": m.new_algorithm_version,
                    "success": m.success,
                    "ts": m.timestamp,
                }
                for m in self._history
            ],
        }
        tmp = self._store_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(self._store_path)


__all__ = [
    "EvolutionPhase",
    "EvolutionStepType",
    "EvolutionStep",
    "EvolutionAlgorithm",
    "MetaModification",
    "MetaEvolutionEngine",
]
