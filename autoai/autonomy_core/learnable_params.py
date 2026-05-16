"""可学习参数系统: 替代所有硬编码阈值/权重，参数可被Agent自身在运行时调整。"""

from __future__ import annotations

import math
import time
import logging
import random
from dataclasses import dataclass, field
from typing import Any
from enum import Enum

from autoai.autonomy_core.full_autonomy_mixin import FullAutonomyMixin

logger = logging.getLogger(__name__)


class UpdateRule(Enum):
    GRADIENT = "gradient"
    BAYESIAN = "bayesian"
    EVOLUTIONARY = "evolutionary"
    REINFORCEMENT = "reinforcement"


@dataclass
class LearnableParam:
    """可学习参数: 有初始值、范围、学习率、历史轨迹。"""
    name: str
    value: float
    min_value: float = 0.0
    max_value: float = 1.0
    learning_rate: float = 0.01
    momentum: float = 0.9
    _velocity: float = field(default=0.0, repr=False)
    _history: list[tuple[float, float]] = field(default_factory=list, repr=False)
    _gradient_accumulator: float = field(default=0.0, repr=False)
    _update_count: int = field(default=0, repr=False)
    is_constitutional: bool = False

    @property
    def normalized(self) -> float:
        span = self.max_value - self.min_value
        if span < 1e-9:
            return 0.5
        return (self.value - self.min_value) / span

    def clamp(self) -> None:
        self.value = max(self.min_value, min(self.max_value, self.value))

    def gradient_update(self, gradient: float, lr_override: float | None = None) -> float:
        """梯度下降+动量: Agent从反馈信号中学习调整参数。"""
        if self.is_constitutional:
            return self.value
        lr = lr_override or self.learning_rate
        self._velocity = self.momentum * self._velocity - lr * gradient
        old = self.value
        self.value += self._velocity
        self.clamp()
        self._gradient_accumulator += gradient
        self._update_count += 1
        self._record(old)
        return self.value

    def bayesian_update(self, observation: float, uncertainty: float = 0.1) -> float:
        """贝叶斯更新: 参数作为高斯分布的均值，从观测中更新。"""
        if self.is_constitutional:
            return self.value
        prior_var = uncertainty * uncertainty
        likelihood_var = 0.05
        posterior_var = 1.0 / (1.0 / prior_var + 1.0 / likelihood_var)
        posterior_mean = posterior_var * (self.value / prior_var + observation / likelihood_var)
        old = self.value
        self.value = posterior_mean
        self.clamp()
        self._update_count += 1
        self._record(old)
        return self.value

    def evolutionary_perturb(self, sigma: float = 0.05) -> float:
        """进化扰动: 用于无需显式梯度的参数搜索。"""
        if self.is_constitutional:
            return self.value
        perturbation = random.gauss(0, sigma)
        old = self.value
        self.value += perturbation
        self.clamp()
        self._update_count += 1
        self._record(old)
        return self.value

    def reinforcement_update(self, reward: float, baseline: float = 0.0) -> float:
        """强化更新: REINFORCE风格，奖励信号驱动参数向高奖励方向移动。"""
        if self.is_constitutional:
            return self.value
        advantage = reward - baseline
        gradient = advantage * (self.value - self.min_value) / max(self.max_value - self.min_value, 1e-9)
        return self.gradient_update(-gradient)

    def set_value(self, new_value: float) -> float:
        """直接设定(仅在非宪法参数上允许)。"""
        if self.is_constitutional:
            logger.warning(f"拒绝修改宪法参数: {self.name}")
            return self.value
        old = self.value
        self.value = max(self.min_value, min(self.max_value, new_value))
        self._record(old)
        return self.value

    def _record(self, old: float) -> None:
        self._history.append((time.time(), self.value))
        if len(self._history) > 1000:
            self._history = self._history[-1000:]

    @property
    def trend(self) -> float:
        """参数变化趋势: 正=上升, 负=下降, 0=稳定。"""
        if len(self._history) < 2:
            return 0.0
        recent = [v for _, v in self._history[-10:]]
        if len(recent) < 2:
            return 0.0
        return recent[-1] - recent[0]

    @property
    def volatility(self) -> float:
        """参数波动率: 衡量参数的稳定程度。"""
        if len(self._history) < 3:
            return 0.0
        recent = [v for _, v in self._history[-20:]]
        mean = sum(recent) / len(recent)
        var = sum((v - mean) ** 2 for v in recent) / len(recent)
        return math.sqrt(var)


class ParamSpace(FullAutonomyMixin):
    """参数空间: 管理一组可学习参数，提供批量更新和优化。"""

    def __init__(self, space_id: str = "default"):
        self._init_full_autonomy()
        self._space_id = space_id
        self._params: dict[str, LearnableParam] = {}
        self._update_rule: UpdateRule = UpdateRule.GRADIENT
        self._total_updates: int = 0

    def declare(
        self, name: str, default: float, min_val: float = 0.0, max_val: float = 1.0,
        lr: float = 0.01, constitutional: bool = False,
    ) -> LearnableParam:
        """声明一个可学习参数。"""
        param = LearnableParam(
            name=name, value=default, min_value=min_val, max_value=max_val,
            learning_rate=lr, is_constitutional=constitutional,
        )
        self._params[name] = param
        return param

    def get(self, name: str) -> float:
        """获取参数当前值。"""
        param = self._params.get(name)
        if param is None:
            raise KeyError(f"参数'{name}'未声明")
        return param.value

    def get_param(self, name: str) -> LearnableParam:
        return self._params[name]

    def set(self, name: str, value: float) -> float:
        """设置参数值(非宪法参数)。"""
        return self._params[name].set_value(value)

    def batch_gradient_update(self, gradients: dict[str, float]) -> dict[str, float]:
        """批量梯度更新。"""
        results = {}
        for name, grad in gradients.items():
            if name in self._params:
                results[name] = self._params[name].gradient_update(grad)
                self._total_updates += 1
        return results

    def batch_evolutionary_perturb(self, sigma: float = 0.05) -> dict[str, float]:
        """批量进化扰动。"""
        results = {}
        for name, param in self._params.items():
            if not param.is_constitutional:
                results[name] = param.evolutionary_perturb(sigma)
                self._total_updates += 1
        return results

    def batch_reinforcement_update(self, rewards: dict[str, float], baseline: float = 0.0) -> dict[str, float]:
        """批量强化更新。"""
        results = {}
        for name, reward in rewards.items():
            if name in self._params:
                results[name] = self._params[name].reinforcement_update(reward, baseline)
                self._total_updates += 1
        return results

    def select_for_exploration(self, n: int = 3) -> list[str]:
        """选择最值得探索的参数: 高波动率或长未更新。"""
        scored = []
        for name, param in self._params.items():
            if param.is_constitutional:
                continue
            exploration_score = param.volatility * 2.0 + (1.0 / max(param._update_count, 1))
            scored.append((name, exploration_score))
        scored.sort(key=lambda x: x[1], reverse=True)
        return [name for name, _ in scored[:n]]

    def snapshot(self) -> dict[str, float]:
        """当前参数快照。"""
        return {name: p.value for name, p in self._params.items()}

    def restore(self, snapshot: dict[str, float]) -> None:
        """从快照恢复(非宪法参数)。"""
        for name, value in snapshot.items():
            if name in self._params:
                self._params[name].set_value(value)

    def constitutional_params(self) -> dict[str, float]:
        """列出所有宪法参数(不可修改)。"""
        return {name: p.value for name, p in self._params.items() if p.is_constitutional}

    def mutable_params(self) -> dict[str, float]:
        """列出所有可变参数。"""
        return {name: p.value for name, p in self._params.items() if not p.is_constitutional}

    @property
    def stats(self) -> dict[str, Any]:
        total = len(self._params)
        constitutional = sum(1 for p in self._params.values() if p.is_constitutional)
        return {
            "space_id": self._space_id,
            "total_params": total,
            "constitutional_params": constitutional,
            "mutable_params": total - constitutional,
            "total_updates": self._total_updates,
            "avg_volatility": sum(p.volatility for p in self._params.values()) / max(total, 1),
        }


class ParamLearner:
    """参数学习器: 根据环境反馈自动调整参数空间的参数。"""

    def __init__(self, param_space: ParamSpace):
        self._space = param_space
        self._reward_history: list[float] = []
        self._baseline: float = 0.0
        self._best_snapshot: dict[str, float] | None = None
        self._best_reward: float = float("-inf")

    def receive_feedback(self, reward: float, context: dict[str, float] | None = None) -> dict[str, float]:
        """接收环境反馈，调整参数。"""
        self._reward_history.append(reward)
        if len(self._reward_history) > 100:
            self._reward_history = self._reward_history[-100:]
        self._baseline = sum(self._reward_history) / len(self._reward_history)
        if reward > self._best_reward:
            self._best_reward = reward
            self._best_snapshot = self._space.snapshot()
        updates = {}
        if context:
            for name, signal in context.items():
                if name in self._space._params:
                    gradient = -signal * (reward - self._baseline)
                    updates[name] = self._space._params[name].gradient_update(gradient)
        else:
            updates = self._space.batch_evolutionary_perturb(sigma=0.02)
        return updates

    def revert_to_best(self) -> bool:
        """回退到历史最佳参数。"""
        if self._best_snapshot is None:
            return False
        self._space.restore(self._best_snapshot)
        return True

    @property
    def baseline(self) -> float:
        return self._baseline

    @property
    def best_reward(self) -> float:
        return self._best_reward
