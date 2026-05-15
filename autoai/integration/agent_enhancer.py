from __future__ import annotations

import time
import logging
from dataclasses import dataclass, field
from typing import Any, Optional

from autoai.memory.layered import LayeredMemorySystem, MemoryLayer
from autoai.event_sourcing import EventStream, ThoughtEvent, DecisionEvent, ActionEvent, MutationEvent, EmotionEvent
from autoai.event_sourcing.replay import TimeTravelDebugger
from autoai.event_sourcing.projection import MaterializedView
from autoai.governance_v2 import TripartiteGovernance, PolicyEffect
from autoai.safety_intuition import SafetyIntuition, IntuitionTrainer, SafetyLearner
from autoai.safety_intuition.social import SocialSafetyNorm
from autoai.continuous_autonomy import ContinuousAutonomy, AutonomyDimension
from autoai.local_model_matrix import LocalModelMatrix, ZeroCostRouter
from autoai.telemetry.tracer import TelemetryTracer, SpanKind
from autoai.telemetry.metrics import MetricsCollector
from autoai.reasoning import StrategySelector

logger = logging.getLogger(__name__)


@dataclass
class EnhancedAgentContext:
    """增强Agent上下文: 包含所有新模块的运行时引用。"""
    agent_id: str = ""

    layered_memory: Optional[LayeredMemorySystem] = None
    event_stream: Optional[EventStream] = None
    time_travel: Optional[TimeTravelDebugger] = None
    materialized_view: Optional[MaterializedView] = None
    governance: Optional[TripartiteGovernance] = None
    safety_intuition: Optional[SafetyIntuition] = None
    safety_learner: Optional[SafetyLearner] = None
    social_norm: Optional[SocialSafetyNorm] = None
    continuous_autonomy: Optional[ContinuousAutonomy] = None
    model_matrix: Optional[LocalModelMatrix] = None
    zero_cost_router: Optional[ZeroCostRouter] = None
    tracer: Optional[TelemetryTracer] = None
    metrics: Optional[MetricsCollector] = None
    reasoning_selector: Optional[StrategySelector] = None

    _initialized: bool = field(default=False, init=False)


class AgentEnhancer:
    """Agent增强器: 将所有Phase alpha/beta模块注入现有Agent执行链。

    这是新旧架构之间的桥接层。它在Agent执行的关键节点
    (思考前/决策时/执行前/执行后)织入新能力。
    """

    def __init__(self, agent_id: str = "enhanced-agent", autonomy_profile: str = "balanced"):
        self.agent_id = agent_id
        self.ctx = EnhancedAgentContext(agent_id=agent_id)
        self._autonomy_profile = autonomy_profile
        self._safety_trained = False

    def initialize(self) -> EnhancedAgentContext:
        """初始化所有增强模块。"""
        if self.ctx._initialized:
            return self.ctx

        self.ctx.layered_memory = LayeredMemorySystem()

        self.ctx.event_stream = EventStream(stream_id=f"agent-{self.agent_id}")
        self.ctx.time_travel = TimeTravelDebugger(self.ctx.event_stream)
        self.ctx.materialized_view = MaterializedView(self.ctx.event_stream)

        self.ctx.governance = TripartiteGovernance(self.agent_id)

        self.ctx.continuous_autonomy = ContinuousAutonomy(self.agent_id, self._autonomy_profile)

        self.ctx.model_matrix = LocalModelMatrix()
        self.ctx.zero_cost_router = ZeroCostRouter(self.ctx.model_matrix)

        self.ctx.tracer = TelemetryTracer(self.agent_id)
        self.ctx.metrics = MetricsCollector()

        self.ctx.reasoning_selector = StrategySelector()

        self.ctx.social_norm = SocialSafetyNorm()

        self.ctx._initialized = True
        logger.info(f"Agent增强器初始化完成: {self.agent_id}")
        return self.ctx

    def on_think_start(self, thought_content: str) -> dict:
        """Agent思考前的增强钩子。"""
        if not self.ctx._initialized:
            return {}
        result = {}

        if self.ctx.event_stream:
            event = ThoughtEvent(
                agent_id=self.agent_id,
                content=thought_content,
                reasoning_chain=[thought_content],
            )
            self.ctx.event_stream.append(event)
            result["event_id"] = event.event_id

        if self.ctx.tracer:
            trace_id = self.ctx.tracer.start_trace("agent_think")
            with self.ctx.tracer.span(SpanKind.THOUGHT, "thinking") as span:
                span.set_attribute("content_length", len(thought_content))
            result["trace_id"] = trace_id

        if self.ctx.continuous_autonomy:
            can_think = self.ctx.continuous_autonomy.can(AutonomyDimension.STRATEGY_MODIFY)
            result["can_think_freely"] = can_think

        return result

    def on_decision(self, operation: str, context: dict | None = None) -> dict:
        """Agent决策时的增强钩子: 治理评估+安全直觉+自主度检查。"""
        if not self.ctx._initialized:
            return {"allowed": True}

        result = {"allowed": True, "effect": "allow"}

        if self.ctx.governance:
            effect, verdict = self.ctx.governance.evaluate_operation(operation, context)
            result["governance_effect"] = effect.value
            result["governance_verdict"] = verdict.verdict_type.value
            if effect == PolicyEffect.DENY:
                result["allowed"] = False
                result["effect"] = "deny"
            elif effect == PolicyEffect.WARN:
                result["effect"] = "warn"

        if self.ctx.safety_intuition and result["allowed"]:
            judgment = self.ctx.safety_intuition.judge(operation)
            result["safety_judgment"] = judgment.judgment.value
            result["safety_confidence"] = judgment.confidence
            if not judgment.should_proceed:
                result["allowed"] = False
                result["effect"] = "forbidden"
            elif judgment.needs_sandbox:
                result["sandbox_recommended"] = True
            if judgment.suggested_alternative:
                result["alternative"] = judgment.suggested_alternative

        if self.ctx.continuous_autonomy and result["allowed"]:
            dim = self._operation_to_dimension(operation)
            if dim:
                can = self.ctx.continuous_autonomy.can(dim)
                result["autonomy_allowed"] = can
                if not can:
                    result["allowed"] = False
                    result["effect"] = "autonomy_blocked"

        if self.ctx.event_stream:
            event = DecisionEvent(
                agent_id=self.agent_id,
                content=f"决策: {operation}",
                decision=operation,
                rationale=result.get("effect", "unknown"),
            )
            self.ctx.event_stream.append(event)

        if self.ctx.metrics:
            self.ctx.metrics.counter("decisions_total").increment()

        return result

    def on_action_execute(self, action_type: str, content: str) -> dict:
        """Agent执行操作时的增强钩子: 模型路由+事件记录。"""
        if not self.ctx._initialized:
            return {}
        result = {}

        if self.ctx.event_stream:
            event = ActionEvent(
                agent_id=self.agent_id,
                content=content,
                action_type=action_type,
            )
            self.ctx.event_stream.append(event)
            result["event_id"] = event.event_id

        if self.ctx.tracer:
            with self.ctx.tracer.span(SpanKind.ACTION, action_type) as span:
                span.set_attribute("action_type", action_type)

        return result

    def on_action_complete(self, action_type: str, success: bool, duration_ms: float = 0) -> dict:
        """Agent执行完成后的增强钩子: 自主度调整+指标记录。"""
        if not self.ctx._initialized:
            return {}
        result = {}

        dim = self._operation_to_dimension(action_type)
        if self.ctx.continuous_autonomy and dim:
            if success:
                self.ctx.continuous_autonomy.record_success(dim)
            else:
                self.ctx.continuous_autonomy.record_failure(dim)

        if self.ctx.metrics:
            self.ctx.metrics.record_task(action_type, duration_ms, success)

        if self.ctx.social_norm:
            if success:
                self.ctx.social_norm.record_success(self.agent_id)
            else:
                self.ctx.social_norm.record_violation(self.agent_id)

        return result

    def on_self_modify(self, target_file: str, patch_diff: str, test_passed: bool) -> dict:
        """Agent自修改时的增强钩子: 事件记录+治理+自主度。"""
        if not self.ctx._initialized:
            return {}
        result = {}

        if self.ctx.event_stream:
            event = MutationEvent(
                agent_id=self.agent_id,
                content=f"自修改: {target_file}",
                target_file=target_file,
                patch_diff=patch_diff[:500],
                test_result=test_passed,
            )
            self.ctx.event_stream.append(event)

        if self.ctx.continuous_autonomy:
            can_modify = self.ctx.continuous_autonomy.can(AutonomyDimension.CODE_MODIFY)
            result["can_modify"] = can_modify
            if not can_modify:
                result["blocked"] = True

        if self.ctx.metrics:
            self.ctx.metrics.record_self_modify(test_passed)

        return result

    async def train_safety_intuition(self) -> int:
        """训练安全直觉(懒加载)。"""
        if self._safety_trained or not self.ctx._initialized:
            return 0
        trainer = IntuitionTrainer()
        experiences = await trainer.train()
        self.ctx.safety_intuition = SafetyIntuition(experiences)
        self.ctx.safety_learner = SafetyLearner(self.ctx.safety_intuition)
        self._safety_trained = True
        logger.info(f"安全直觉训练完成: {len(experiences)}条经验")
        return len(experiences)

    def route_model(self, task_complexity: float, required_quality: float = 0.8) -> dict:
        """零成本模型路由。"""
        if not self.ctx.zero_cost_router:
            return {"model": "default", "cost": 0}
        result = self.ctx.zero_cost_router.route(task_complexity, required_quality)
        return {
            "model": result.model.name,
            "tier": result.model.tier.value,
            "cost": result.estimated_cost,
            "escalated": result.escalated,
        }

    def store_memory(self, content: str, layer: MemoryLayer = MemoryLayer.WORKING,
                     importance: float = 1.0) -> str:
        """存储到分层记忆。"""
        if not self.ctx.layered_memory:
            return ""
        return self.ctx.layered_memory.store(content, layer, importance=importance)

    def get_status(self) -> dict:
        """获取增强Agent的完整状态。"""
        status = {"agent_id": self.agent_id, "initialized": self.ctx._initialized}
        if self.ctx.continuous_autonomy:
            status["autonomy"] = self.ctx.continuous_autonomy.get_status()
        if self.ctx.governance:
            status["governance"] = self.ctx.governance.get_status()
        if self.ctx.event_stream:
            status["events"] = self.ctx.event_stream.get_stats()
        if self.ctx.model_matrix:
            status["model_matrix"] = self.ctx.model_matrix.get_matrix_stats()
        if self.ctx.zero_cost_router:
            status["router"] = self.ctx.zero_cost_router.get_stats()
        if self.ctx.metrics:
            status["metrics"] = self.ctx.metrics.get_summary()
        if self.ctx.layered_memory:
            status["memory"] = self.ctx.layered_memory.get_layer_stats()
        return status

    @staticmethod
    def _operation_to_dimension(operation: str) -> AutonomyDimension | None:
        op = operation.lower()
        if any(k in op for k in ["shell", "exec", "subprocess"]):
            return AutonomyDimension.SHELL_EXECUTE
        if any(k in op for k in ["write", "create_file"]):
            return AutonomyDimension.FILE_WRITE
        if any(k in op for k in ["delete", "remove", "unlink"]):
            return AutonomyDimension.FILE_DELETE
        if any(k in op for k in ["network", "http", "fetch", "curl"]):
            return AutonomyDimension.NETWORK_ACCESS
        if any(k in op for k in ["self_modify", "patch", "code_change"]):
            return AutonomyDimension.CODE_MODIFY
        if any(k in op for k in ["spawn", "create_agent"]):
            return AutonomyDimension.SELF_SPAWN
        if any(k in op for k in ["policy", "governance"]):
            return AutonomyDimension.POLICY_MODIFY
        if any(k in op for k in ["strategy", "plan"]):
            return AutonomyDimension.STRATEGY_MODIFY
        if any(k in op for k in ["config", "setting"]):
            return AutonomyDimension.CONFIG_MODIFY
        return None
