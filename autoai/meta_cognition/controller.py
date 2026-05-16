from __future__ import annotations

import time
import logging
from dataclasses import dataclass, field
from typing import Any
from enum import Enum

from autoai.autonomy_core.learnable_params import ParamSpace, ParamLearner
from autoai.autonomy_core.full_autonomy_mixin import FullAutonomyMixin

logger = logging.getLogger(__name__)


class CognitiveMode(Enum):
    ANALYTICAL = "analytical"
    CREATIVE = "creative"
    INTUITIVE = "intuitive"
    REFLECTIVE = "reflective"
    EXPLORATORY = "exploratory"
    CONSERVATIVE = "conservative"


@dataclass
class AttentionBudget:
    """注意力预算: 有限的认知资源分配。"""
    total_budget: float = 1.0
    allocations: dict[str, float] = field(default_factory=dict)

    def allocate(self, target: str, amount: float) -> bool:
        current_used = sum(self.allocations.values())
        if current_used + amount > self.total_budget:
            return False
        self.allocations[target] = self.allocations.get(target, 0.0) + amount
        return True

    def deallocate(self, target: str) -> float:
        return self.allocations.pop(target, 0.0)

    @property
    def remaining(self) -> float:
        return self.total_budget - sum(self.allocations.values())

    @property
    def utilization(self) -> float:
        return sum(self.allocations.values()) / self.total_budget if self.total_budget > 0 else 0.0

    def rebalance(self, priorities: dict[str, float]) -> None:
        total_pri = sum(priorities.values())
        if total_pri <= 0:
            return
        self.allocations = {
            k: self.total_budget * v / total_pri
            for k, v in priorities.items()
        }


@dataclass
class StrategyRecord:
    strategy: str
    outcome: float
    duration_ms: float
    mode: CognitiveMode
    timestamp: float = field(default_factory=time.time)


@dataclass
class ThinkingAboutThinking:
    """思维关于思维的记录 - 元认知快照。"""
    current_mode: CognitiveMode = CognitiveMode.ANALYTICAL
    strategy_effectiveness: dict[str, float] = field(default_factory=dict)
    attention_utilization: float = 0.0
    thought_loops_detected: int = 0
    mode_switches: int = 0
    insight_rate: float = 0.0

    @property
    def is_stuck(self) -> bool:
        return self.thought_loops_detected >= 3 or self.insight_rate < 0.1

    @property
    def cognitive_efficiency(self) -> float:
        if not self.strategy_effectiveness:
            return 0.5
        avg_eff = sum(self.strategy_effectiveness.values()) / len(self.strategy_effectiveness)
        attention_factor = 1.0 - abs(self.attention_utilization - 0.7)
        return avg_eff * 0.7 + attention_factor * 0.3


class MetaCognitionController(FullAutonomyMixin):
    """元认知控制器: 监控和调控Agent的认知过程。"""

    def __init__(self, agent_id: str = "meta", use_learnable: bool = False):
        self._init_full_autonomy()
        self.agent_id = agent_id
        self._current_mode = CognitiveMode.ANALYTICAL
        self._attention = AttentionBudget()
        self._strategy_history: list[StrategyRecord] = []
        self._mode_history: list[tuple[CognitiveMode, float]] = [(CognitiveMode.ANALYTICAL, time.time())]
        self._thought_signatures: list[str] = []
        self._loop_detection_window = 5
        self._use_learnable = use_learnable
        self._param_space: ParamSpace | None = None
        self._param_learner: ParamLearner | None = None
        if use_learnable:
            self._init_learnable()

    def _init_learnable(self) -> None:
        self._param_space = ParamSpace("meta_cognition")
        self._param_space.declare("stuck_loop_threshold", 3.0, 1.0, 10.0, lr=0.1, constitutional=False)
        self._param_space.declare("insight_stuck_threshold", 0.1, 0.01, 0.3, lr=0.01)
        self._param_space.declare("overload_threshold", 0.9, 0.7, 0.99, lr=0.01)
        self._param_space.declare("strategy_ema_decay", 0.8, 0.5, 0.95, lr=0.01)
        self._param_learner = ParamLearner(self._param_space)

    def enable_learnable(self) -> None:
        if not self._use_learnable:
            self._use_learnable = True
            self._init_learnable()

    @property
    def current_mode(self) -> CognitiveMode:
        return self._current_mode

    def switch_mode(self, new_mode: CognitiveMode, reason: str = "") -> CognitiveMode:
        old_mode = self._current_mode
        self._current_mode = new_mode
        self._mode_history.append((new_mode, time.time()))
        if old_mode != new_mode:
            logger.info(f"认知模式切换: {old_mode.value} -> {new_mode.value} ({reason})")
        return old_mode

    def auto_switch_mode(self) -> CognitiveMode | None:
        """基于当前状态自动切换认知模式。

        Phase Omega改造: 支持推理决策模式,Agent可选择非预设转移路径。
        """
        meta = self.reflect()
        if getattr(self, '_use_reasoning', False) and hasattr(self, '_decider') and self._decider:
            return self._auto_switch_reasoning(meta)
        return self._auto_switch_rules(meta)

    def _auto_switch_reasoning(self, meta: Any) -> CognitiveMode | None:
        """推理决策模式: 用ReasoningDecider选择认知模式。"""
        from autoai.autonomy_core.reasoning_decider import DecisionContext
        modes = [CognitiveMode.ANALYTICAL, CognitiveMode.CREATIVE, CognitiveMode.REFLECTIVE,
                 CognitiveMode.EXPLORATORY, CognitiveMode.CONSERVATIVE, CognitiveMode.INTUITIVE]
        if meta.is_stuck:
            current_idx = modes.index(self._current_mode) if self._current_mode in modes else 0
            candidates = modes[:current_idx] + modes[current_idx+1:]
            if candidates:
                chosen = candidates[hash(f"{time.time()}{meta.thought_loops}") % len(candidates)]
                return self.switch_mode(chosen, f"stuck:推理切换(非固定路径)")
        if meta.attention_utilization > 0.9:
            return self.switch_mode(CognitiveMode.CONSERVATIVE, "过载:切换到保守模式")
        return None

    def _auto_switch_rules(self, meta: Any) -> CognitiveMode | None:
        """规则模式: 向后兼容的固定FSM转移。"""
        if meta.is_stuck:
            if self._current_mode == CognitiveMode.ANALYTICAL:
                return self.switch_mode(CognitiveMode.CREATIVE, "stuck:切换到创造性模式")
            elif self._current_mode == CognitiveMode.CREATIVE:
                return self.switch_mode(CognitiveMode.REFLECTIVE, "stuck:切换到反思模式")
            elif self._current_mode == CognitiveMode.REFLECTIVE:
                return self.switch_mode(CognitiveMode.EXPLORATORY, "stuck:切换到探索模式")
        overload_t = 0.9
        if self._use_learnable and self._param_space:
            overload_t = self._param_space.get("overload_threshold")
        if meta.attention_utilization > overload_t:
            return self.switch_mode(CognitiveMode.CONSERVATIVE, "过载:切换到保守模式")
        return None

    def enable_reasoning_mode(self) -> None:
        """运行时切换推理决策模式。"""
        from autoai.autonomy_core.reasoning_decider import ReasoningDecider
        self._use_reasoning = True
        self._decider = ReasoningDecider()

    def record_strategy(self, strategy: str, outcome: float, duration_ms: float) -> None:
        record = StrategyRecord(
            strategy=strategy,
            outcome=outcome,
            duration_ms=duration_ms,
            mode=self._current_mode,
        )
        self._strategy_history.append(record)
        if len(self._strategy_history) > 1000:
            self._strategy_history = self._strategy_history[-500:]

    def detect_thought_loop(self, thought_signature: str) -> bool:
        """检测思维循环: 是否在重复相同的思考。"""
        self._thought_signatures.append(thought_signature)
        if len(self._thought_signatures) > self._loop_detection_window:
            self._thought_signatures = self._thought_signatures[-self._loop_detection_window:]
        recent = self._thought_signatures[-3:]
        if len(recent) >= 3 and len(set(recent)) == 1:
            logger.warning(f"检测到思维循环: {thought_signature[:50]}")
            return True
        return False

    def select_strategy(self, available: list[str]) -> str | None:
        """基于历史效果选择最优策略。"""
        if not available:
            return None
        strategy_scores: dict[str, float] = {}
        for s in available:
            records = [r for r in self._strategy_history if r.strategy == s]
            if records:
                recent = records[-10:]
                avg_outcome = sum(r.outcome for r in recent) / len(recent)
                strategy_scores[s] = avg_outcome
            else:
                strategy_scores[s] = 0.5
        if self._current_mode == CognitiveMode.EXPLORATORY:
            min_count = min(
                len([r for r in self._strategy_history if r.strategy == s])
                for s in available
            )
            least_used = [s for s in available
                          if len([r for r in self._strategy_history if r.strategy == s]) == min_count]
            if least_used:
                return least_used[0]
        return max(strategy_scores, key=strategy_scores.get)

    def reflect(self) -> ThinkingAboutThinking:
        """元认知反思: 生成当前认知状态快照。"""
        strategy_eff: dict[str, float] = {}
        ema_decay = 0.8
        if self._use_learnable and self._param_space:
            ema_decay = self._param_space.get("strategy_ema_decay")
        for record in self._strategy_history[-50:]:
            if record.strategy not in strategy_eff:
                strategy_eff[record.strategy] = record.outcome
            else:
                old = strategy_eff[record.strategy]
                strategy_eff[record.strategy] = old * ema_decay + record.outcome * (1.0 - ema_decay)
        recent_30 = self._mode_history[-30:]
        mode_switches = len(recent_30) - 1 if len(recent_30) > 1 else 0
        recent_records = self._strategy_history[-20:]
        insight_rate = sum(1 for r in recent_records if r.outcome > 0.7) / max(1, len(recent_records))
        return ThinkingAboutThinking(
            current_mode=self._current_mode,
            strategy_effectiveness=strategy_eff,
            attention_utilization=self._attention.utilization,
            thought_loops_detected=len([1 for i in range(len(self._thought_signatures) - 2)
                                       if i >= 0 and
                                       self._thought_signatures[i] == self._thought_signatures[i+1] == self._thought_signatures[i+2]]),
            mode_switches=mode_switches,
            insight_rate=insight_rate,
        )

    @property
    def attention(self) -> AttentionBudget:
        return self._attention

    @property
    def stats(self) -> dict[str, Any]:
        meta = self.reflect()
        return {
            "current_mode": self._current_mode.value,
            "attention_utilization": self._attention.utilization,
            "attention_remaining": self._attention.remaining,
            "cognitive_efficiency": meta.cognitive_efficiency,
            "is_stuck": meta.is_stuck,
            "insight_rate": meta.insight_rate,
            "strategy_count": len(set(r.strategy for r in self._strategy_history)),
            "mode_switches": meta.mode_switches,
        }
