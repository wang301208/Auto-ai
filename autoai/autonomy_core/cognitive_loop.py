"""认知闭环: observe -> assess -> decide -> act -> reflect 完整链路。"""

from __future__ import annotations

import time
import logging
from dataclasses import dataclass, field
from typing import Any
from enum import Enum

from autoai.autonomy_core.full_autonomy_mixin import FullAutonomyMixin

logger = logging.getLogger(__name__)


class CognitivePhase(Enum):
    OBSERVE = "observe"
    ASSESS = "assess"
    DECIDE = "decide"
    ACT = "act"
    REFLECT = "reflect"


class CognitiveState(Enum):
    IDLE = "idle"
    OBSERVING = "observing"
    ASSESSING = "assessing"
    DECIDING = "deciding"
    ACTING = "acting"
    REFLECTING = "reflecting"
    STUCK = "stuck"
    ADAPTING = "adapting"


@dataclass
class Observation:
    """观察: Agent感知到的环境/自身状态。"""
    source: str
    data: dict[str, Any]
    salience: float = 0.5
    timestamp: float = field(default_factory=time.time)


@dataclass
class Assessment:
    """评估: 对观察的分析判断。"""
    observation_id: str
    interpretation: str
    urgency: float = 0.5
    relevance: float = 0.5
    anomalies: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)


@dataclass
class Decision:
    """决策: 基于评估的行动选择。"""
    assessment_id: str
    action_type: str
    action_params: dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.5
    reasoning: str = ""
    alternatives: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class ActionResult:
    """行动结果: 执行action后的真实反馈。"""
    decision_id: str
    success: bool
    outcome: dict[str, Any] = field(default_factory=dict)
    side_effects: list[str] = field(default_factory=list)
    duration_ms: float = 0.0


@dataclass
class Reflection:
    """反思: 对整个认知循环的元分析，产生行为修正。"""
    cycle_id: int
    observations_count: int
    decisions_count: int
    actions_success_rate: float
    anomalies_found: list[str] = field(default_factory=list)
    behavior_modifications: list[dict[str, Any]] = field(default_factory=list)
    insights: list[str] = field(default_factory=list)
    param_adjustments: dict[str, float] = field(default_factory=dict)


@dataclass
class CognitiveCycle:
    """一个完整的认知循环: observe -> assess -> decide -> act -> reflect。"""
    cycle_id: int
    start_time: float
    observations: list[Observation] = field(default_factory=list)
    assessments: list[Assessment] = field(default_factory=list)
    decisions: list[Decision] = field(default_factory=list)
    actions: list[ActionResult] = field(default_factory=list)
    reflection: Reflection | None = None
    end_time: float = 0.0

    @property
    def duration_ms(self) -> float:
        end = self.end_time or time.time()
        return (end - self.start_time) * 1000

    @property
    def is_complete(self) -> bool:
        return self.reflection is not None


class CognitiveLoop(FullAutonomyMixin):
    """认知闭环引擎: 驱动 observe -> assess -> decide -> act -> reflect 完整循环。"""

    def __init__(self, agent_id: str = "default"):
        self._init_full_autonomy()
        self._agent_id = agent_id
        self._state = CognitiveState.IDLE
        self._cycle_count: int = 0
        self._cycles: list[CognitiveCycle] = []
        self._current_cycle: CognitiveCycle | None = None
        self._behavior_modifications: list[dict[str, Any]] = []
        self._param_adjustments: dict[str, float] = {}
        self._observation_handlers: list[Any] = []
        self._action_handlers: dict[str, Any] = {}
        self._stuck_threshold: int = 3
        self._recent_success_rate: float = 0.5

    def observe(self, source: str, data: dict[str, Any], salience: float = 0.5) -> Observation:
        """观察阶段: 感知环境/自身状态。"""
        self._state = CognitiveState.OBSERVING
        if self._current_cycle is None:
            self._cycle_count += 1
            self._current_cycle = CognitiveCycle(
                cycle_id=self._cycle_count,
                start_time=time.time(),
            )
        obs = Observation(source=source, data=data, salience=salience)
        self._current_cycle.observations.append(obs)
        return obs

    def assess(self, observation: Observation | None = None) -> Assessment:
        """评估阶段: 分析观察，检测异常，生成建议。"""
        self._state = CognitiveState.ASSESSING
        if not self._current_cycle:
            return Assessment(observation_id="none", interpretation="无观察可评估")
        obs = observation or (self._current_cycle.observations[-1] if self._current_cycle.observations else None)
        if not obs:
            return Assessment(observation_id="none", interpretation="无观察可评估")
        anomalies = []
        recommendations = []
        interpretation_parts = []
        for key, value in obs.data.items():
            if isinstance(value, (int, float)):
                if value > 0.9:
                    anomalies.append(f"{key}异常高: {value:.2f}")
                    recommendations.append(f"降低{key}")
                elif value < 0.1:
                    anomalies.append(f"{key}异常低: {value:.2f}")
                    recommendations.append(f"提升{key}")
            interpretation_parts.append(f"{key}={value}")
        interpretation = "; ".join(interpretation_parts) if interpretation_parts else "空观察"
        urgency = obs.salience
        if anomalies:
            urgency = min(1.0, urgency + 0.2)
        assessment = Assessment(
            observation_id=f"obs_{len(self._current_cycle.observations)}",
            interpretation=interpretation,
            urgency=urgency,
            relevance=obs.salience,
            anomalies=anomalies,
            recommendations=recommendations,
        )
        self._current_cycle.assessments.append(assessment)
        return assessment

    def decide(self, assessment: Assessment | None = None, available_actions: list[str] | None = None) -> Decision:
        """决策阶段: 基于评估选择行动，考虑多替代方案。"""
        self._state = CognitiveState.DECIDING
        if not self._current_cycle:
            return Decision(assessment_id="none", action_type="noop", confidence=0.0)
        assess = assessment or (self._current_cycle.assessments[-1] if self._current_cycle.assessments else None)
        if not assess:
            return Decision(assessment_id="none", action_type="noop", confidence=0.0)
        actions = available_actions or ["monitor", "adjust", "investigate", "escalate"]
        if assess.anomalies:
            if any("异常高" in a for a in assess.anomalies):
                action_type = "reduce"
            elif any("异常低" in a for a in assess.anomalies):
                action_type = "enhance"
            else:
                action_type = "investigate"
        else:
            action_type = "monitor"
        if assess.urgency > 0.7:
            action_type = "escalate"
        alternatives = [
            {"action": a, "score": assess.urgency * (0.8 if a == action_type else 0.5)}
            for a in actions if a != action_type
        ]
        decision = Decision(
            assessment_id=f"ass_{len(self._current_cycle.assessments)}",
            action_type=action_type,
            confidence=assess.urgency,
            reasoning=f"评估: {assess.interpretation[:80]}; 异常: {assess.anomalies}; 选择: {action_type}",
            alternatives=alternatives,
        )
        self._current_cycle.decisions.append(decision)
        return decision

    def act(self, decision: Decision | None = None, executor: Any = None) -> ActionResult:
        """行动阶段: 执行决策，产生真实结果。"""
        self._state = CognitiveState.ACTING
        if not self._current_cycle:
            return ActionResult(decision_id="none", success=False)
        dec = decision or (self._current_cycle.decisions[-1] if self._current_cycle.decisions else None)
        if not dec:
            return ActionResult(decision_id="none", success=False)
        start = time.time()
        handler = self._action_handlers.get(dec.action_type)
        if handler:
            try:
                result = handler(**dec.action_params)
                success = result.get("success", True) if isinstance(result, dict) else True
                outcome = result if isinstance(result, dict) else {"result": result}
            except Exception as e:
                success = False
                outcome = {"error": str(e)}
        else:
            success = True
            outcome = {"action_type": dec.action_type, "params": dec.action_params, "executed": True}
        action_result = ActionResult(
            decision_id=f"dec_{len(self._current_cycle.decisions)}",
            success=success,
            outcome=outcome,
            duration_ms=(time.time() - start) * 1000,
        )
        self._current_cycle.actions.append(action_result)
        return action_result

    def reflect(self) -> Reflection:
        """反思阶段: 对整个循环元分析，产生行为修正和参数调整——这是闭环的关键。"""
        self._state = CognitiveState.REFLECTING
        if not self._current_cycle:
            return Reflection(cycle_id=0, observations_count=0, decisions_count=0, actions_success_rate=0.0)
        cycle = self._current_cycle
        total_actions = len(cycle.actions)
        success_count = sum(1 for a in cycle.actions if a.success)
        success_rate = success_count / max(total_actions, 1)
        self._recent_success_rate = 0.7 * self._recent_success_rate + 0.3 * success_rate
        all_anomalies = []
        for a in cycle.assessments:
            all_anomalies.extend(a.anomalies)
        behavior_modifications = []
        if success_rate < 0.5 and total_actions >= 2:
            behavior_modifications.append({
                "type": "strategy_change",
                "reason": f"成功率{success_rate:.0%}<50%, 需要改变策略",
                "from": "current_approach",
                "to": "alternative_approach",
            })
        if self._recent_success_rate < 0.3:
            behavior_modifications.append({
                "type": "mode_shift",
                "reason": f"近期成功率{self._recent_success_rate:.0%}持续低迷, 切换探索模式",
                "to": "exploratory",
            })
        insights = []
        if all_anomalies:
            unique = set(all_anomalies)
            for anomaly in unique:
                count = all_anomalies.count(anomaly)
                if count >= 2:
                    insights.append(f"重复异常模式: {anomaly} (x{count}), 需要根本性解决")
        param_adjustments = {}
        if success_rate > 0.8:
            param_adjustments["exploration_rate"] = -0.01
            insights.append("成功率高, 可减少探索, 增强利用")
        elif success_rate < 0.3:
            param_adjustments["exploration_rate"] = 0.02
            insights.append("成功率低, 需增加探索, 寻找新策略")
        reflection = Reflection(
            cycle_id=cycle.cycle_id,
            observations_count=len(cycle.observations),
            decisions_count=len(cycle.decisions),
            actions_success_rate=success_rate,
            anomalies_found=all_anomalies,
            behavior_modifications=behavior_modifications,
            insights=insights,
            param_adjustments=param_adjustments,
        )
        cycle.reflection = reflection
        self._behavior_modifications.extend(behavior_modifications)
        for k, v in param_adjustments.items():
            self._param_adjustments[k] = self._param_adjustments.get(k, 0.0) + v
        cycle.end_time = time.time()
        self._cycles.append(cycle)
        if len(self._cycles) > 200:
            self._cycles = self._cycles[-200:]
        self._current_cycle = None
        self._state = CognitiveState.IDLE
        return reflection

    def run_full_cycle(self, observations: list[tuple[str, dict, float]]) -> Reflection:
        """运行一个完整的 observe->assess->decide->act->reflect 循环。"""
        for source, data, salience in observations:
            obs = self.observe(source, data, salience)
            assess = self.assess(obs)
            dec = self.decide(assess)
            self.act(dec)
        return self.reflect()

    def register_action_handler(self, action_type: str, handler: Any) -> None:
        """注册行动处理器: Agent可扩展可执行的行动类型。"""
        self._action_handlers[action_type] = handler

    def is_stuck(self) -> bool:
        """检测是否陷入停滞: 最近N个循环成功率极低。"""
        recent = self._cycles[-self._stuck_threshold:]
        if len(recent) < self._stuck_threshold:
            return False
        return all(
            r.reflection and r.reflection.actions_success_rate < 0.3
            for r in recent
            if r.reflection
        )

    def get_behavior_modifications(self) -> list[dict[str, Any]]:
        """获取反思产生的行为修正(可被其他模块消费)。"""
        return self._behavior_modifications

    def get_param_adjustments(self) -> dict[str, float]:
        """获取反思产生的参数调整(可被ParamSpace消费)。"""
        return self._param_adjustments

    @property
    def state(self) -> CognitiveState:
        return self._state

    @property
    def stats(self) -> dict[str, Any]:
        complete = [c for c in self._cycles if c.is_complete]
        avg_success = (
            sum(c.reflection.actions_success_rate for c in complete if c.reflection) / max(len(complete), 1)
        )
        return {
            "agent_id": self._agent_id,
            "state": self._state.value,
            "cycle_count": self._cycle_count,
            "complete_cycles": len(complete),
            "avg_success_rate": avg_success,
            "recent_success_rate": self._recent_success_rate,
            "behavior_modifications": len(self._behavior_modifications),
            "param_adjustments": dict(self._param_adjustments),
            "is_stuck": self.is_stuck(),
        }
