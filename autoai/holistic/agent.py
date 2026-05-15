from __future__ import annotations

import time
import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class HoloStatus:
    initialized: bool = False
    modules_loaded: list[str] = field(default_factory=list)
    agent_id: str = ""
    timestamp: float = field(default_factory=time.time)

    @property
    def module_count(self) -> int:
        return len(self.modules_loaded)


class HoloAgent:
    """全息Agent: 一个实例，所有能力。

    统一入口整合:
    - 分层记忆 (layered_memory)
    - Agent Mesh (mesh)
    - MCP协议 (mcp)
    - 自进化闭环 (evolution)
    - 安全直觉 (safety)
    - 事件溯源 (event_sourcing)
    - 治理三权分立 (governance)
    - 连续自主度 (autonomy)
    - 模型矩阵 (model_matrix)
    - 遥测 (telemetry)
    - 推理策略 (reasoning)
    - 目标涌现 (goals)
    - 自我意识 (awareness)
    - 因果推理 (causal)
    - 进化压力 (evolution_pressure)
    - 工具创造 (tool_creation)
    - 元认知 (meta_cognition)
    - 协议进化 (protocol_evolution)
    - 价值对齐 (value_alignment)
    - 世界模型 (world_model)
    - 自举 (bootstrap)
    - 知识涌现 (knowledge)
    """

    def __init__(self, agent_id: str = "holo", autonomy_profile: str = "balanced"):
        self.agent_id = agent_id
        self._autonomy_profile = autonomy_profile
        self._modules: dict[str, Any] = {}
        self._status = HoloStatus(agent_id=agent_id)
        self._initialized = False

    def initialize(self) -> HoloStatus:
        if self._initialized:
            return self._status
        modules_to_load = [
            ("layered_memory", "autoai.memory.layered", "LayeredMemorySystem"),
            ("event_sourcing", "autoai.event_sourcing", "EventStream"),
            ("governance", "autoai.governance_v2", "TripartiteGovernance"),
            ("safety", "autoai.safety_intuition", "SafetyIntuition"),
            ("autonomy", "autoai.continuous_autonomy", "ContinuousAutonomy"),
            ("model_matrix", "autoai.local_model_matrix", "LocalModelMatrix"),
            ("telemetry_tracer", "autoai.telemetry.tracer", "TelemetryTracer"),
            ("telemetry_metrics", "autoai.telemetry.metrics", "MetricsCollector"),
            ("reasoning", "autoai.reasoning", "StrategySelector"),
            ("goals", "autoai.goal_emergence", "GoalEmergenceEngine"),
            ("desires", "autoai.goal_emergence.desire", "DesireSystem"),
            ("awareness", "autoai.self_awareness", "SelfAwarenessLoop"),
            ("causal", "autoai.causal_reasoning", "CausalReasoner"),
            ("evolution_pressure", "autoai.evolution_pressure", "EvolutionPressure"),
            ("tool_creation", "autoai.tool_creation", "ToolCreator"),
            ("meta_cognition", "autoai.meta_cognition", "MetaCognitionController"),
            ("protocol_evolution", "autoai.protocol_evolution", "ProtocolEvolver"),
            ("value_alignment", "autoai.value_alignment", "ValueCalibrator"),
            ("world_model", "autoai.world_model", "WorldModel"),
            ("bootstrap", "autoai.bootstrap", "SelfBootstrapper"),
            ("knowledge_graph", "autoai.knowledge.graph", "KnowledgeGraph"),
            ("semantic_compressor", "autoai.knowledge.compressor", "SemanticCompressor"),
            ("cross_domain", "autoai.knowledge.transfer", "CrossDomainTransfer"),
            ("belief_system", "autoai.knowledge.belief", "BeliefSystem"),
        ]
        loaded = []
        for name, module_path, class_name in modules_to_load:
            try:
                mod = __import__(module_path, fromlist=[class_name])
                cls = getattr(mod, class_name)
                if name in ("governance", "meta_cognition", "protocol_evolution"):
                    instance = cls(self.agent_id)
                elif name == "event_sourcing":
                    instance = cls(stream_id=f"holo-{self.agent_id}")
                elif name == "autonomy":
                    instance = cls(self.agent_id, self._autonomy_profile)
                elif name == "telemetry_tracer":
                    instance = cls(self.agent_id)
                else:
                    instance = cls()
                self._modules[name] = instance
                loaded.append(name)
            except Exception as e:
                logger.debug(f"全息集成: 模块{name}加载失败(非致命): {e}")
        self._status = HoloStatus(
            initialized=True,
            modules_loaded=loaded,
            agent_id=self.agent_id,
        )
        self._initialized = True
        logger.info(f"全息Agent初始化: {len(loaded)}/{len(modules_to_load)}模块加载")
        return self._status

    def __getattr__(self, name: str) -> Any:
        if name.startswith("_") or name in ("agent_id", "initialize"):
            raise AttributeError(name)
        if name in self._modules:
            return self._modules[name]
        aliases = {
            "memory": "layered_memory",
            "events": "event_sourcing",
            "gov": "governance",
            "safety_int": "safety",
            "auto": "autonomy",
            "models": "model_matrix",
            "tracer": "telemetry_tracer",
            "metrics": "telemetry_metrics",
            "reason": "reasoning",
            "goal_eng": "goals",
            "desire_sys": "desires",
            "aware": "awareness",
            "cause": "causal",
            "evo_p": "evolution_pressure",
            "tool_cr": "tool_creation",
            "meta": "meta_cognition",
            "proto": "protocol_evolution",
            "values": "value_alignment",
            "world": "world_model",
            "boot": "bootstrap",
            "kgraph": "knowledge_graph",
            "compress": "semantic_compressor",
            "xfer": "cross_domain",
            "belief": "belief_system",
        }
        if name in aliases and aliases[name] in self._modules:
            return self._modules[aliases[name]]
        raise AttributeError(f"模块'{name}'未加载。可用: {list(self._modules.keys())}")

    def think(self, content: str) -> dict:
        """统一思考入口: 元认知+安全+治理+价值对齐。"""
        result = {"content": content}
        if "meta_cognition" in self._modules:
            mc = self._modules["meta_cognition"]
            mc.record_strategy("think", 0.5, 10)
            result["cognitive_mode"] = mc.current_mode.value
        if "safety" in self._modules:
            try:
                judgment = self._modules["safety"].judge(content)
                result["safety"] = judgment.judgment.value
            except Exception:
                pass
        if "value_alignment" in self._modules:
            judgment = self._modules["value_alignment"].judge(content)
            result["alignment"] = judgment.level.value
        if "awareness" in self._modules:
            snap = self._modules["awareness"].reflect()
            result["self_awareness"] = snap.overall_self_awareness
        return result

    def act(self, action: str, context: dict | None = None) -> dict:
        """统一行动入口: 治理审批+因果预测+执行+学习。"""
        result = {"action": action, "allowed": True}
        if "governance" in self._modules:
            try:
                from autoai.governance_v2 import PolicyEffect
                effect, _ = self._modules["governance"].evaluate_operation(action, context)
                if effect == PolicyEffect.DENY:
                    result["allowed"] = False
                    result["reason"] = "governance_deny"
            except Exception:
                pass
        if "world_model" in self._modules and result["allowed"]:
            pred = self._modules["world_model"].predict(action)
            result["predicted_confidence"] = pred.confidence
        if "goals" in self._modules:
            self._modules["goals"].observe_outcome(action, result["allowed"])
        return result

    def evolve(self) -> dict:
        """统一进化入口: 目标涌现+自举+进化压力。"""
        result = {}
        if "goals" in self._modules:
            result["emerged_goals"] = self._modules["goals"].emerge_goals()
        if "evolution_pressure" in self._modules:
            result["evolution_stats"] = self._modules["evolution_pressure"].stats
        if "awareness" in self._modules:
            snap = self._modules["awareness"].reflect()
            result["self_awareness"] = snap.overall_self_awareness
            result["learning_plan"] = [
                {"domain": g.domain, "priority": g.priority}
                for g in self._modules["awareness"].get_learning_plan()
            ]
        return result

    @property
    def status(self) -> HoloStatus:
        return self._status

    def get_full_status(self) -> dict[str, Any]:
        """获取所有模块的状态。"""
        full = {"agent_id": self.agent_id, "initialized": self._initialized}
        for name, module in self._modules.items():
            try:
                if hasattr(module, "stats"):
                    full[name] = module.stats
                elif hasattr(module, "get_status"):
                    full[name] = module.get_status()
            except Exception:
                full[name] = {"error": "status_unavailable"}
        return full
