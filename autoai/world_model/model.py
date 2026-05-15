from __future__ import annotations

import time
import copy
import logging
from dataclasses import dataclass, field
from typing import Any
from enum import Enum

logger = logging.getLogger(__name__)


class PredictionAccuracy(Enum):
    EXACT = "exact"
    CLOSE = "close"
    APPROXIMATE = "approximate"
    WRONG = "wrong"


@dataclass
class WorldState:
    """世界状态快照。"""
    variables: dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

    def get(self, key: str, default: Any = None) -> Any:
        return self.variables.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self.variables[key] = value

    def diff(self, other: "WorldState") -> dict[str, tuple[Any, Any]]:
        changes = {}
        all_keys = set(self.variables) | set(other.variables)
        for k in all_keys:
            v1 = self.variables.get(k)
            v2 = other.variables.get(k)
            if v1 != v2:
                changes[k] = (v1, v2)
        return changes

    def clone(self) -> "WorldState":
        return WorldState(variables=copy.deepcopy(self.variables), timestamp=self.timestamp)


@dataclass
class Prediction:
    action: str
    predicted_state: WorldState = field(default_factory=WorldState)
    confidence: float = 0.5
    predicted_reward: float = 0.0
    timestamp: float = field(default_factory=time.time)

    @property
    def is_reliable(self) -> bool:
        return self.confidence >= 0.6


@dataclass
class SimulationResult:
    action_sequence: list[str]
    final_state: WorldState = field(default_factory=WorldState)
    total_reward: float = 0.0
    steps: int = 0
    predictions: list[Prediction] = field(default_factory=list)

    @property
    def avg_reward_per_step(self) -> float:
        return self.total_reward / self.steps if self.steps > 0 else 0.0


@dataclass
class ModelUpdate:
    variable: str
    prediction_error: float
    old_model_param: float
    new_model_param: float


class WorldModel:
    """世界模型: 内部预测模型用于规划和反事实推理。"""

    def __init__(self):
        self._current_state = WorldState()
        self._transition_model: dict[str, dict[str, Any]] = {}
        self._predictions: list[Prediction] = []
        self._updates: list[ModelUpdate] = []
        self._simulation_count = 0

    @property
    def current_state(self) -> WorldState:
        return self._current_state

    def observe(self, key: str, value: Any) -> None:
        self._current_state.set(key, value)

    def observe_state(self, state: WorldState) -> None:
        self._current_state = state

    def learn_transition(self, action: str, pre_state: WorldState, post_state: WorldState) -> None:
        """学习状态转移规则。"""
        changes = pre_state.diff(post_state)
        if action not in self._transition_model:
            self._transition_model[action] = {}
        for var, (old_val, new_val) in changes.items():
            self._transition_model[action][var] = {"from": old_val, "to": new_val}

    def predict(self, action: str) -> Prediction:
        """预测执行action后的世界状态。"""
        predicted = self._current_state.clone()
        confidence = 0.5
        if action in self._transition_model:
            rules = self._transition_model[action]
            match_count = 0
            for var, rule in rules.items():
                current_val = self._current_state.get(var)
                if current_val == rule.get("from"):
                    predicted.set(var, rule["to"])
                    match_count += 1
            confidence = 0.5 + 0.5 * (match_count / max(1, len(rules)))
        pred = Prediction(action=action, predicted_state=predicted, confidence=confidence)
        self._predictions.append(pred)
        return pred

    def compare_prediction(self, prediction: Prediction, actual_state: WorldState) -> tuple[PredictionAccuracy, float]:
        """对比预测与实际，返回准确度和误差。"""
        diff = prediction.predicted_state.diff(actual_state)
        if not diff:
            return PredictionAccuracy.EXACT, 0.0
        total_vars = max(1, len(set(prediction.predicted_state.variables) | set(actual_state.variables)))
        error = len(diff) / total_vars
        if error < 0.1:
            return PredictionAccuracy.CLOSE, error
        elif error < 0.3:
            return PredictionAccuracy.APPROXIMATE, error
        return PredictionAccuracy.WRONG, error

    def update_model(self, prediction: Prediction, actual_state: WorldState, learning_rate: float = 0.1) -> None:
        """根据预测误差更新模型。"""
        accuracy, error = self.compare_prediction(prediction, actual_state)
        if accuracy != PredictionAccuracy.EXACT:
            diff = prediction.predicted_state.diff(actual_state)
            for var, (pred_val, actual_val) in diff.items():
                update = ModelUpdate(
                    variable=var,
                    prediction_error=error,
                    old_model_param=0.5,
                    new_model_param=0.5 + learning_rate * (1.0 - error),
                )
                self._updates.append(update)

    def simulate(self, actions: list[str], steps: int = 0) -> SimulationResult:
        """在内部世界模型中模拟执行一系列动作。"""
        state = self._current_state.clone()
        total_reward = 0.0
        predictions = []
        for action in actions:
            pred = self.predict(action)
            state = pred.predicted_state.clone()
            total_reward += pred.predicted_reward
            predictions.append(pred)
        result = SimulationResult(
            action_sequence=actions,
            final_state=state,
            total_reward=total_reward,
            steps=len(actions),
            predictions=predictions,
        )
        self._simulation_count += 1
        return result

    def plan(self, available_actions: list[str], horizon: int = 3) -> list[str]:
        """通过模拟选择最优动作序列。"""
        if not available_actions or horizon <= 0:
            return []
        from itertools import product
        candidates = list(product(available_actions, repeat=min(horizon, len(available_actions))))
        candidates = candidates[:50]
        best_plan = []
        best_reward = float("-inf")
        for plan in candidates:
            result = self.simulate(list(plan))
            if result.total_reward > best_reward:
                best_reward = result.total_reward
                best_plan = list(plan)
        return best_plan

    @property
    def stats(self) -> dict[str, Any]:
        return {
            "variables_tracked": len(self._current_state.variables),
            "known_transitions": len(self._transition_model),
            "predictions_made": len(self._predictions),
            "model_updates": len(self._updates),
            "simulations_run": self._simulation_count,
        }
