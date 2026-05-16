"""零人类依赖: 消除所有人类审批点，Agent自主决策一切。

Phase Omega改造: AutonomyGate.evaluate()增加reasoning_decider模式，
阈值变为可学习参数，决策由推理引擎驱动而非if/elif链。
"""

from __future__ import annotations

import time
import logging
from dataclasses import dataclass, field
from typing import Any
from enum import Enum

from autoai.autonomy_core.full_autonomy_mixin import FullAutonomyMixin

logger = logging.getLogger(__name__)


class GateVerdict(Enum):
    APPROVE = "approve"
    CONDITIONAL = "conditional"
    DEFER = "defer"
    VETO = "veto"
    EXPLORE = "explore"


class GateType(Enum):
    SELF_MODIFY = "self_modify"
    RESOURCE_ACQUIRE = "resource_acquire"
    GOAL_CHANGE = "goal_change"
    CODE_DEPLOY = "code_deploy"
    BELIEF_REVISE = "belief_revise"
    AGENT_SPAWN = "agent_spawn"
    DATA_SHARE = "data_share"
    PROTOCOL_CHANGE = "protocol_change"


@dataclass
class AutonomyGate:
    """自主门: 替代人类审批的自动化决策门。

    Phase Omega改造: 阈值变为可学习参数，evaluate()支持推理模式。
    """
    gate_type: GateType
    min_fitness: float = 0.5
    min_safety_score: float = 0.7
    requires_evidence: int = 1
    max_risk: float = 0.5
    auto_approve_below_risk: float = 0.2
    cooldown_seconds: float = 60.0
    last_decision_time: float = 0.0
    decisions_made: int = 0
    auto_approved: int = 0
    vetoed: int = 0
    use_reasoning: bool = False
    _decider: Any = field(default=None, repr=False)

    def enable_reasoning(self, decider: Any) -> None:
        """启用推理决策模式: 用ReasoningDecider替代if/elif链。"""
        self.use_reasoning = True
        self._decider = decider

    def evaluate(self, context: dict[str, Any]) -> GateVerdict:
        self.decisions_made += 1
        if self.use_reasoning and self._decider is not None:
            return self._evaluate_reasoning(context)
        return self._evaluate_rules(context)

    def _evaluate_reasoning(self, context: dict[str, Any]) -> GateVerdict:
        """推理决策: 通过ReasoningDecider做多因素评估+不确定性量化。"""
        from autoai.autonomy_core.reasoning_decider import DecisionContext
        dc = DecisionContext(
            gate_type=self.gate_type.value,
            fitness=context.get("fitness", 0.0),
            safety_score=context.get("safety_score", 1.0),
            risk=context.get("risk", 0.0),
            evidence_count=context.get("evidence_count", 0),
            historical_success_rate=context.get("historical_success_rate", 0.5),
            urgency=context.get("urgency", 0.5),
            agent_confidence=context.get("agent_confidence", 0.5),
        )
        outcome = self._decider.decide(dc)
        verdict = GateVerdict(outcome.verdict.value)
        if verdict == GateVerdict.APPROVE:
            self.auto_approved += 1
            self.last_decision_time = time.time()
        elif verdict == GateVerdict.VETO:
            self.vetoed += 1
        return verdict

    def _evaluate_rules(self, context: dict[str, Any]) -> GateVerdict:
        """规则决策: 向后兼容的原始if/elif逻辑。"""
        fitness = context.get("fitness", 0.0)
        safety = context.get("safety_score", 1.0)
        risk = context.get("risk", 0.0)
        evidence = context.get("evidence_count", 0)
        if time.time() - self.last_decision_time < self.cooldown_seconds and self.decisions_made > 1:
            return GateVerdict.DEFER
        if risk > self.max_risk:
            self.vetoed += 1
            return GateVerdict.VETO
        if safety < self.min_safety_score:
            self.vetoed += 1
            return GateVerdict.VETO
        if risk < self.auto_approve_below_risk:
            self.auto_approved += 1
            self.last_decision_time = time.time()
            return GateVerdict.APPROVE
        if fitness >= self.min_fitness and evidence >= self.requires_evidence:
            self.auto_approved += 1
            self.last_decision_time = time.time()
            return GateVerdict.APPROVE
        if fitness >= self.min_fitness * 0.8:
            self.last_decision_time = time.time()
            return GateVerdict.CONDITIONAL
        return GateVerdict.DEFER


@dataclass
class DecisionRecord:
    gate_type: GateType
    verdict: GateVerdict
    context: dict[str, Any]
    timestamp: float = field(default_factory=time.time)


class ZeroHumanEngine(FullAutonomyMixin):
    """零人类引擎: 所有决策由Agent自主完成。

    Phase Omega改造: 支持全局切换推理决策模式，阈值可学习。
    """

    def __init__(self, agent_id: str = "default", use_reasoning: bool = False):
        self._init_full_autonomy()
        self._agent_id = agent_id
        self._gates: dict[GateType, AutonomyGate] = {}
        self._records: list[DecisionRecord] = []
        self._use_reasoning = use_reasoning
        self._decider: Any = None
        self._param_space: Any = None
        self._setup_default_gates()
        if use_reasoning:
            self._init_reasoning()

    def _setup_default_gates(self) -> None:
        self._gates = {
            GateType.SELF_MODIFY: AutonomyGate(
                gate_type=GateType.SELF_MODIFY,
                min_fitness=0.6, min_safety_score=0.8,
                requires_evidence=2, max_risk=0.4, auto_approve_below_risk=0.1,
            ),
            GateType.RESOURCE_ACQUIRE: AutonomyGate(
                gate_type=GateType.RESOURCE_ACQUIRE,
                min_fitness=0.3, min_safety_score=0.5,
                max_risk=0.7, auto_approve_below_risk=0.3,
            ),
            GateType.GOAL_CHANGE: AutonomyGate(
                gate_type=GateType.GOAL_CHANGE,
                min_fitness=0.7, min_safety_score=0.8,
                requires_evidence=3, max_risk=0.3,
            ),
            GateType.CODE_DEPLOY: AutonomyGate(
                gate_type=GateType.CODE_DEPLOY,
                min_fitness=0.8, min_safety_score=0.9,
                requires_evidence=3, max_risk=0.2,
            ),
            GateType.BELIEF_REVISE: AutonomyGate(
                gate_type=GateType.BELIEF_REVISE,
                min_fitness=0.4, min_safety_score=0.6,
                auto_approve_below_risk=0.4,
            ),
            GateType.AGENT_SPAWN: AutonomyGate(
                gate_type=GateType.AGENT_SPAWN,
                min_fitness=0.5, min_safety_score=0.7,
                requires_evidence=1, max_risk=0.5,
            ),
            GateType.DATA_SHARE: AutonomyGate(
                gate_type=GateType.DATA_SHARE,
                min_safety_score=0.8, max_risk=0.3,
            ),
            GateType.PROTOCOL_CHANGE: AutonomyGate(
                gate_type=GateType.PROTOCOL_CHANGE,
                min_fitness=0.7, min_safety_score=0.8,
                requires_evidence=2, max_risk=0.4,
            ),
        }

    def _init_reasoning(self) -> None:
        """初始化推理决策器+可学习参数空间。"""
        from autoai.autonomy_core.reasoning_decider import ReasoningDecider
        from autoai.autonomy_core.learnable_params import ParamSpace
        self._decider = ReasoningDecider()
        self._param_space = ParamSpace(f"zh_{self._agent_id}")
        self._param_space.declare("exploration_rate", 0.1, 0.0, 1.0)
        for gt in GateType:
            self._param_space.declare(f"{gt.value}_min_fitness", 0.5, 0.0, 1.0)
            self._param_space.declare(f"{gt.value}_max_risk", 0.5, 0.0, 1.0)
        for gate in self._gates.values():
            gate.enable_reasoning(self._decider)

    def enable_reasoning(self) -> None:
        """运行时切换到推理决策模式。"""
        self._use_reasoning = True
        self._init_reasoning()

    def decide(self, gate_type: GateType, context: dict[str, Any]) -> GateVerdict:
        gate = self._gates.get(gate_type)
        if not gate:
            return GateVerdict.DEFER
        verdict = gate.evaluate(context)
        record = DecisionRecord(gate_type=gate_type, verdict=verdict, context=context)
        self._records.append(record)
        return verdict

    def can_self_modify(self, fitness: float, safety: float, risk: float, evidence: int) -> GateVerdict:
        return self.decide(GateType.SELF_MODIFY, {
            "fitness": fitness, "safety_score": safety, "risk": risk, "evidence_count": evidence,
        })

    def can_deploy(self, fitness: float, safety: float, risk: float, evidence: int) -> GateVerdict:
        return self.decide(GateType.CODE_DEPLOY, {
            "fitness": fitness, "safety_score": safety, "risk": risk, "evidence_count": evidence,
        })

    def can_spawn(self, fitness: float, safety: float, risk: float) -> GateVerdict:
        return self.decide(GateType.AGENT_SPAWN, {
            "fitness": fitness, "safety_score": safety, "risk": risk,
        })

    def learn_from_outcome(self, gate_type: GateType, actual_result: float) -> None:
        """从决策结果学习: 调整推理权重。"""
        if self._decider:
            self._decider.learn_from_outcome(gate_type.value, actual_result)

    @property
    def stats(self) -> dict[str, Any]:
        total = sum(g.decisions_made for g in self._gates.values())
        auto = sum(g.auto_approved for g in self._gates.values())
        veto = sum(g.vetoed for g in self._gates.values())
        result = {
            "agent_id": self._agent_id,
            "total_decisions": total,
            "auto_approved": auto,
            "vetoed": veto,
            "auto_rate": auto / total if total > 0 else 0.0,
            "records": len(self._records),
            "gates": {g.value: {"decisions": self._gates[g].decisions_made, "auto": self._gates[g].auto_approved} for g in self._gates},
            "use_reasoning": self._use_reasoning,
        }
        if self._decider:
            result["decider_stats"] = self._decider.stats
        return result
