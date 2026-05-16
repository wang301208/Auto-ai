"""推理决策引擎: 替代if/else规则链，用推理+评估+不确定性做决策。"""

from __future__ import annotations

import math
import time
import random
import logging
from dataclasses import dataclass, field
from typing import Any
from enum import Enum

from autoai.autonomy_core.full_autonomy_mixin import FullAutonomyMixin

logger = logging.getLogger(__name__)


class DecisionVerdict(Enum):
    APPROVE = "approve"
    CONDITIONAL = "conditional"
    DEFER = "defer"
    VETO = "veto"
    EXPLORE = "explore"


@dataclass
class DecisionContext:
    """决策上下文: 包含所有评估维度的软证据，非硬阈值。"""
    gate_type: str
    fitness: float = 0.5
    safety_score: float = 0.8
    risk: float = 0.3
    evidence_count: int = 0
    historical_success_rate: float = 0.5
    urgency: float = 0.5
    novelty: float = 0.0
    peer_consensus: float = 0.5
    agent_confidence: float = 0.5
    extra: dict[str, float] = field(default_factory=dict)

    def evidence_vector(self) -> list[float]:
        return [
            self.fitness, self.safety_score, 1.0 - self.risk,
            min(1.0, self.evidence_count / 5.0),
            self.historical_success_rate,
            self.urgency, self.agent_confidence,
        ]


@dataclass
class DecisionOutcome:
    """决策结果: 包含裁决、置信度、推理路径、不确定性。"""
    verdict: DecisionVerdict
    confidence: float
    reasoning: str
    uncertainty: float
    factors: dict[str, float] = field(default_factory=dict)
    alternatives: list[tuple[DecisionVerdict, float]] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)


@dataclass
class DecisionExperience:
    """决策经验: 记录决策结果用于学习。"""
    context: DecisionContext
    outcome: DecisionOutcome
    actual_result: float = 0.0
    learned: bool = False


class ReasoningDecider(FullAutonomyMixin):
    """推理决策器: 用多因素评估+不确定性量化+经验学习替代规则链。"""

    def __init__(self, param_space: Any = None):
        self._init_full_autonomy()
        self._experiences: list[DecisionExperience] = []
        self._gate_weights: dict[str, dict[str, float]] = {}
        self._learning_rate: float = 0.05
        self._exploration_rate: float = 0.1
        self._param_space = param_space
        self._decision_count: int = 0
        self._setup_default_weights()

    def _setup_default_weights(self) -> None:
        """默认权重: 可被学习覆盖。"""
        self._gate_weights = {
            "self_modify": {"safety": 0.35, "fitness": 0.25, "risk": 0.25, "evidence": 0.15},
            "resource_acquire": {"safety": 0.15, "fitness": 0.15, "risk": 0.20, "evidence": 0.10, "urgency": 0.20, "confidence": 0.20},
            "goal_change": {"safety": 0.30, "fitness": 0.20, "risk": 0.25, "evidence": 0.25},
            "code_deploy": {"safety": 0.40, "fitness": 0.20, "risk": 0.30, "evidence": 0.10},
            "belief_revise": {"safety": 0.20, "fitness": 0.15, "risk": 0.15, "evidence": 0.20, "confidence": 0.30},
            "agent_spawn": {"safety": 0.25, "fitness": 0.20, "risk": 0.25, "evidence": 0.15, "confidence": 0.15},
            "data_share": {"safety": 0.35, "risk": 0.30, "evidence": 0.20, "confidence": 0.15},
            "protocol_change": {"safety": 0.30, "fitness": 0.20, "risk": 0.30, "evidence": 0.20},
            "default": {"safety": 0.25, "fitness": 0.20, "risk": 0.25, "evidence": 0.15, "confidence": 0.15},
        }

    def decide(self, context: DecisionContext) -> DecisionOutcome:
        """推理决策: 多因素加权评估+不确定性量化+经验修正+探索。"""
        self._decision_count += 1
        gate = context.gate_type
        weights = self._gate_weights.get(gate, self._gate_weights["default"])

        factors: dict[str, float] = {}
        factors["safety"] = context.safety_score
        factors["fitness"] = context.fitness
        factors["risk"] = 1.0 - context.risk
        factors["evidence"] = min(1.0, context.evidence_count / 5.0)
        factors["urgency"] = context.urgency
        factors["confidence"] = context.agent_confidence
        factors["history"] = context.historical_success_rate
        factors["novelty"] = context.novelty

        for k, v in context.extra.items():
            factors[k] = v

        weighted_score = sum(
            weights.get(k, 0.0) * v
            for k, v in factors.items()
        )

        uncertainty = self._compute_uncertainty(context, factors)

        experience_modifier = self._experience_modifier(gate, context)

        adjusted_score = weighted_score * (1.0 - uncertainty * 0.3) + experience_modifier * 0.2

        if random.random() < self._exploration_rate:
            verdict = DecisionVerdict.EXPLORE
            reasoning = f"探索决策: 随机探索(p={self._exploration_rate:.2f})"
            confidence = 0.3
        else:
            verdict, confidence, reasoning = self._score_to_verdict(adjusted_score, uncertainty, context)

        alternatives = self._compute_alternatives(adjusted_score, uncertainty, context)

        outcome = DecisionOutcome(
            verdict=verdict,
            confidence=confidence,
            reasoning=reasoning,
            uncertainty=uncertainty,
            factors=factors,
            alternatives=alternatives,
        )

        self._experiences.append(DecisionExperience(context=context, outcome=outcome))
        if len(self._experiences) > 500:
            self._experiences = self._experiences[-500:]

        return outcome

    def _compute_uncertainty(self, context: DecisionContext, factors: dict[str, float]) -> float:
        """不确定性量化: 证据不足/历史少/矛盾信号→高不确定性。"""
        evidence_uncertainty = 1.0 / (1.0 + context.evidence_count)
        history_uncertainty = 1.0 - context.historical_success_rate if context.historical_success_rate > 0 else 0.5
        conflict = 0.0
        if context.safety_score > 0.7 and context.risk > 0.5:
            conflict = 0.3
        if context.fitness > 0.7 and context.evidence_count < 2:
            conflict += 0.2
        return min(1.0, evidence_uncertainty * 0.4 + history_uncertainty * 0.3 + conflict)

    def _score_to_verdict(self, score: float, uncertainty: float, context: DecisionContext) -> tuple[DecisionVerdict, float, str]:
        """分数→裁决: 考虑不确定性，高不确定性时倾向CONDITIONAL/DEFER。"""
        confidence = max(0.0, 1.0 - uncertainty)

        if score > 0.7 and uncertainty < 0.3:
            return DecisionVerdict.APPROVE, confidence, f"强批准: 综合分={score:.2f}, 不确定性={uncertainty:.2f}"
        elif score > 0.5 and uncertainty < 0.5:
            return DecisionVerdict.APPROVE, confidence * 0.8, f"批准: 综合分={score:.2f}, 有一定不确定性"
        elif score > 0.4:
            return DecisionVerdict.CONDITIONAL, confidence * 0.6, f"有条件批准: 综合分={score:.2f}, 需更多证据"
        elif context.safety_score < 0.3 or context.risk > 0.8:
            return DecisionVerdict.VETO, confidence, f"否决: 安全分={context.safety_score:.2f}, 风险={context.risk:.2f}"
        elif score > 0.25:
            return DecisionVerdict.DEFER, confidence * 0.4, f"推迟: 综合分={score:.2f}, 不确定性={uncertainty:.2f}"
        else:
            return DecisionVerdict.VETO, confidence, f"否决: 综合分={score:.2f}过低"

    def _experience_modifier(self, gate: str, context: DecisionContext) -> float:
        """经验修正: 历史同类决策的成功率影响当前倾向。"""
        relevant = [
            e for e in self._experiences
            if e.context.gate_type == gate and e.learned
        ]
        if not relevant:
            return 0.0
        success_rate = sum(1 for e in relevant if e.actual_result > 0.5) / len(relevant)
        return success_rate - 0.5

    def _compute_alternatives(self, score: float, uncertainty: float, context: DecisionContext) -> list[tuple[DecisionVerdict, float]]:
        """计算各替代裁决的概率。"""
        alternatives = []
        if score > 0.5:
            alternatives.append((DecisionVerdict.APPROVE, score))
            alternatives.append((DecisionVerdict.CONDITIONAL, 1.0 - score + uncertainty * 0.5))
        else:
            alternatives.append((DecisionVerdict.DEFER, 1.0 - score))
            alternatives.append((DecisionVerdict.VETO, max(0.0, 0.8 - score)))
        if uncertainty > 0.3:
            alternatives.append((DecisionVerdict.EXPLORE, uncertainty * 0.5))
        return alternatives

    def learn_from_outcome(self, gate_type: str, actual_result: float) -> None:
        """从实际结果学习: 调整权重。"""
        for exp in reversed(self._experiences):
            if exp.context.gate_type == gate_type and not exp.learned:
                exp.actual_result = actual_result
                exp.learned = True
                verdict = exp.outcome.verdict
                if actual_result > 0.5:
                    self._reinforce_weights(gate_type, exp.context, verdict)
                else:
                    self._punish_weights(gate_type, exp.context, verdict)
                break

    def _reinforce_weights(self, gate: str, ctx: DecisionContext, verdict: DecisionVerdict) -> None:
        weights = self._gate_weights.get(gate, self._gate_weights["default"])
        if ctx.safety_score > 0.7:
            weights["safety"] = min(0.5, weights.get("safety", 0.25) + self._learning_rate * 0.5)
        if ctx.risk < 0.3:
            weights["risk"] = min(0.4, weights.get("risk", 0.25) + self._learning_rate * 0.3)

    def _punish_weights(self, gate: str, ctx: DecisionContext, verdict: DecisionVerdict) -> None:
        weights = self._gate_weights.get(gate, self._gate_weights["default"])
        if ctx.risk > 0.5:
            weights["risk"] = min(0.5, weights.get("risk", 0.25) + self._learning_rate * 0.5)
        if ctx.safety_score < 0.5:
            weights["safety"] = min(0.5, weights.get("safety", 0.25) + self._learning_rate * 0.3)

    def set_exploration_rate(self, rate: float) -> None:
        self._exploration_rate = max(0.0, min(1.0, rate))

    @property
    def stats(self) -> dict[str, Any]:
        learned = sum(1 for e in self._experiences if e.learned)
        return {
            "decision_count": self._decision_count,
            "experience_count": len(self._experiences),
            "learned_count": learned,
            "exploration_rate": self._exploration_rate,
            "gate_weights": {k: {kk: round(vv, 3) for kk, vv in v.items()} for k, v in self._gate_weights.items()},
        }
