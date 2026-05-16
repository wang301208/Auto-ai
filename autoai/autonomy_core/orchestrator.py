"""自主编排器: 跨模块reflect->decide闭环,连接所有改造模块的反思输出到统一认知循环。"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Optional
from enum import Enum

from .cognitive_loop import CognitiveLoop, CognitiveState, CognitivePhase
from .reasoning_decider import ReasoningDecider, DecisionContext
from .learnable_params import ParamSpace, ParamLearner, LearnableParam, UpdateRule

logger = logging.getLogger(__name__)


class ModuleRole(Enum):
    GOAL = "goal"
    DECISION = "decision"
    ADAPTATION = "adaptation"
    REFLECTION = "reflection"
    EXECUTION = "execution"
    PROTECTION = "protection"


@dataclass
class ModuleReflector:
    """模块反射器: 包装一个模块的反思接口。"""
    module_path: str
    role: ModuleRole
    reflect_fn: Optional[Callable] = None
    get_actions_fn: Optional[Callable] = None
    enable_fn: Optional[Callable] = None
    last_reflection: Optional[Any] = None
    last_actions: list = field(default_factory=list)
    cycle_count: int = 0


@dataclass
class OrchestrationCycle:
    """编排循环记录。"""
    cycle_id: int
    timestamp: float
    modules_reflected: int
    actions_collected: int
    decisions_made: int
    duration_ms: float
    errors: list[str] = field(default_factory=list)


class AutonomyOrchestrator:
    """自主编排器: 统一认知循环,跨模块reflect->decide闭环。

    工作流:
    1. observe: 收集所有模块状态
    2. assess: 通过CognitiveLoop评估当前自主度
    3. decide: ReasoningDecider决策下一步行动
    4. act: 将决策分发到各模块enable/adjust接口
    5. reflect: 收集所有模块反思,反馈到ParamLearner
    """

    def __init__(self, use_orchestration: bool = False):
        self.use_orchestration = use_orchestration
        self._modules: dict[str, ModuleReflector] = {}
        self._cognitive_loop = CognitiveLoop()
        self._decider = ReasoningDecider()
        self._param_space = ParamSpace()
        self._param_learner = ParamLearner(self._param_space)
        self._cycles: list[OrchestrationCycle] = []
        self._running = False
        self._cycle_count = 0
        self._init_params()

    def _init_params(self):
        self._param_space.declare("reflection_weight", 0.5, min_val=0.0, max_val=1.0, lr=0.05)
        self._param_space.declare("action_threshold", 0.3, min_val=0.1, max_val=0.9, lr=0.03)
        self._param_space.declare("cross_module_influence", 0.2, min_val=0.0, max_val=0.8, lr=0.02)
        self._param_space.declare("cycle_interval_ms", 1000.0, min_val=100.0, max_val=10000.0, lr=0.01)

    def enable_orchestration(self):
        self.use_orchestration = True
        logger.info("自主编排已启用")

    def register_module(
        self,
        module_path: str,
        role: ModuleRole,
        reflect_fn: Optional[Callable] = None,
        get_actions_fn: Optional[Callable] = None,
        enable_fn: Optional[Callable] = None,
    ) -> ModuleReflector:
        reflector = ModuleReflector(
            module_path=module_path,
            role=role,
            reflect_fn=reflect_fn,
            get_actions_fn=get_actions_fn,
            enable_fn=enable_fn,
        )
        self._modules[module_path] = reflector
        logger.debug(f"注册模块: {module_path} (角色={role.value})")
        return reflector

    def unregister_module(self, module_path: str) -> bool:
        if module_path in self._modules:
            del self._modules[module_path]
            return True
        return False

    def run_cycle(self) -> OrchestrationCycle:
        start = time.time()
        self._cycle_count += 1
        cycle = OrchestrationCycle(
            cycle_id=self._cycle_count,
            timestamp=start,
            modules_reflected=0,
            actions_collected=0,
            decisions_made=0,
            duration_ms=0,
        )
        if not self.use_orchestration:
            cycle.duration_ms = (time.time() - start) * 1000
            self._cycles.append(cycle)
            return cycle
        try:
            observations = self._observe()
            assessment = self._assess(observations)
            decisions = self._decide(assessment)
            self._act(decisions)
            self._reflect()
            cycle.modules_reflected = len([m for m in self._modules.values() if m.last_reflection is not None])
            cycle.actions_collected = sum(len(m.last_actions) for m in self._modules.values())
            cycle.decisions_made = len(decisions)
        except Exception as e:
            cycle.errors.append(str(e))
            logger.error(f"编排循环{self._cycle_count}错误: {e}")
        cycle.duration_ms = (time.time() - start) * 1000
        self._cycles.append(cycle)
        return cycle

    def _observe(self) -> dict[str, Any]:
        observations = {}
        for path, module in self._modules.items():
            state = {
                "role": module.role.value,
                "cycle_count": module.cycle_count,
                "has_reflection": module.last_reflection is not None,
                "action_count": len(module.last_actions),
            }
            if module.reflect_fn:
                try:
                    module.last_reflection = module.reflect_fn()
                    module.cycle_count += 1
                    state["reflection_success"] = True
                except Exception as e:
                    state["reflection_success"] = False
                    state["reflection_error"] = str(e)
            observations[path] = state
        return observations

    def _assess(self, observations: dict[str, Any]) -> dict[str, Any]:
        active_modules = sum(1 for o in observations.values() if o.get("reflection_success", False))
        total_modules = max(len(observations), 1)
        coverage = active_modules / total_modules
        avg_actions = sum(o.get("action_count", 0) for o in observations.values()) / total_modules
        assessment = {
            "module_coverage": coverage,
            "avg_actions_per_module": avg_actions,
            "total_modules": total_modules,
            "active_modules": active_modules,
            "param_reflection_weight": self._param_space.get("reflection_weight"),
            "param_action_threshold": self._param_space.get("action_threshold"),
        }
        try:
            obs = self._cognitive_loop.observe("orchestrator", observations)
            asm = self._cognitive_loop.assess(obs)
            assessment["cognitive_assessment"] = asm.interpretation if asm else "unknown"
        except Exception as e:
            assessment["cognitive_assessment"] = f"error: {e}"
        return assessment

    def _decide(self, assessment: dict[str, Any]) -> list[dict[str, Any]]:
        decisions = []
        coverage = assessment.get("module_coverage", 0)
        threshold = self._param_space.get("action_threshold")
        if coverage < threshold:
            decisions.append({
                "action": "increase_coverage",
                "reason": f"模块覆盖{coverage:.0%}低于阈值{threshold:.0%}",
                "priority": 1.0 - coverage,
            })
        for path, module in self._modules.items():
            if not module.last_reflection and module.cycle_count > 3:
                decisions.append({
                    "action": "retry_reflection",
                    "target": path,
                    "reason": f"模块{path}连续{module.cycle_count}轮无反思",
                    "priority": 0.5,
                })
        try:
            ctx = DecisionContext(
                gate_type="orchestration",
                fitness=coverage,
                safety_score=1.0 - (1.0 - coverage),
                risk=1.0 - coverage,
                evidence_count=assessment.get("active_modules", 0),
            )
            outcome = self._decider.decide(ctx)
            if outcome and outcome.verdict:
                for d in decisions:
                    d["confidence"] = outcome.confidence
        except Exception:
            pass
        return decisions

    def _act(self, decisions: list[dict[str, Any]]):
        for decision in decisions:
            action = decision.get("action")
            if action == "increase_coverage":
                for path, module in self._modules.items():
                    if module.enable_fn and not module.last_reflection:
                        try:
                            module.enable_fn()
                            logger.info(f"编排器启用模块: {path}")
                        except Exception as e:
                            logger.warning(f"启用{path}失败: {e}")
            elif action == "retry_reflection":
                target = decision.get("target")
                if target and target in self._modules:
                    module = self._modules[target]
                    if module.reflect_fn:
                        try:
                            module.last_reflection = module.reflect_fn()
                            if module.get_actions_fn:
                                module.last_actions = module.get_actions_fn() or []
                        except Exception as e:
                            logger.warning(f"重试反思{target}失败: {e}")

    def _reflect(self):
        reflection_weight = self._param_space.get("reflection_weight")
        influence = self._param_space.get("cross_module_influence")
        total_score = 0
        count = 0
        for module in self._modules.values():
            if module.last_reflection:
                score = 1.0
                if isinstance(module.last_reflection, dict):
                    score = module.last_reflection.get("score", module.last_reflection.get("quality", 1.0))
                elif isinstance(module.last_reflection, (int, float)):
                    score = float(module.last_reflection)
                total_score += score
                count += 1
        if count > 0:
            avg_score = total_score / count
            gradient = (avg_score - 0.5) * reflection_weight * influence
            self._param_learner.receive_feedback(avg_score, {"reflection_weight": gradient})
            self._param_space.get_param("reflection_weight").gradient_update(gradient)
            self._param_space.get_param("cross_module_influence").gradient_update(gradient * 0.5)
        try:
            self._cognitive_loop.reflect()
        except Exception:
            pass

    @property
    def modules(self) -> dict[str, ModuleReflector]:
        return dict(self._modules)

    @property
    def cycle_history(self) -> list[OrchestrationCycle]:
        return list(self._cycles)

    @property
    def last_cycle(self) -> Optional[OrchestrationCycle]:
        return self._cycles[-1] if self._cycles else None

    @property
    def stats(self) -> dict[str, Any]:
        return {
            "total_modules": len(self._modules),
            "total_cycles": self._cycle_count,
            "running": self._running,
            "use_orchestration": self.use_orchestration,
            "param_reflection_weight": self._param_space.get("reflection_weight"),
            "param_action_threshold": self._param_space.get("action_threshold"),
            "param_cross_influence": self._param_space.get("cross_module_influence"),
            "decider_decisions": self._decider._decision_count if hasattr(self._decider, '_decision_count') else 0,
        }

    def get_module_status(self, module_path: str) -> Optional[dict[str, Any]]:
        module = self._modules.get(module_path)
        if not module:
            return None
        return {
            "path": module.module_path,
            "role": module.role.value,
            "cycle_count": module.cycle_count,
            "has_reflection": module.last_reflection is not None,
            "action_count": len(module.last_actions),
            "has_enable": module.enable_fn is not None,
        }
