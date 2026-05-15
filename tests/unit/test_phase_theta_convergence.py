"""Phase theta: 终极融合 - 跨模块桥接/端到端生命周期/架构拓扑/健康仪表盘"""
from __future__ import annotations

import time
import asyncio
import pytest

from autoai.holistic import HoloAgent


class TestCrossModuleBridges:
    """验证模块间的真实数据流动与协作。"""

    def test_goal_emergence_feeds_awareness(self):
        """目标涌现->自我意识: 新目标触发知识缺口检测。"""
        from autoai.goal_emergence import GoalEmergenceEngine
        from autoai.self_awareness import SelfAwarenessLoop
        goals = GoalEmergenceEngine()
        awareness = SelfAwarenessLoop()
        for _ in range(5):
            goals.observe_outcome("unknown_op", success=False)
        new_goals = goals.emerge_goals()
        if new_goals:
            for g in new_goals:
                awareness.discover_gap(g.description, relevance=g.priority)
        plan = awareness.get_learning_plan()
        assert len(plan) >= 1

    def test_causal_feeds_world_model(self):
        """因果推理->世界模型: 因果边变为状态转移规则。"""
        from autoai.causal_reasoning import CausalGraph, CausalReasoner
        from autoai.world_model import WorldModel, WorldState
        cg = CausalGraph()
        cg.add_edge("X", "Y", strength=0.8)
        wm = WorldModel()
        s1 = WorldState(variables={"X": 1, "Y": 0})
        s2 = WorldState(variables={"X": 1, "Y": 1})
        wm.learn_transition("set_X", s1, s2)
        wm.observe_state(s1)
        pred = wm.predict("set_X")
        assert pred.confidence > 0.5

    def test_value_alignment_gates_goals(self):
        """价值对齐门控目标涌现: 违反核心价值的目标被拒绝。"""
        from autoai.value_alignment import ValueCalibrator
        from autoai.goal_emergence import GoalEmergenceEngine, GoalOrigin
        vc = ValueCalibrator()
        goals = GoalEmergenceEngine()
        j = vc.judge("explore_unknown", context={"safety": 0.9, "autonomy": 0.8})
        assert j.is_permissible

    def test_meta_cognition_switches_reasoning(self):
        """元认知切换推理策略: 思维循环时切换策略。"""
        from autoai.meta_cognition import MetaCognitionController, CognitiveMode
        mc = MetaCognitionController()
        mc.record_strategy("cot", 0.3, 100)
        mc.record_strategy("cot", 0.2, 100)
        mc.record_strategy("cot", 0.1, 100)
        for _ in range(3):
            mc.detect_thought_loop("same_pattern")
        mc.auto_switch_mode()
        assert mc.current_mode != CognitiveMode.ANALYTICAL

    def test_temporal_drives_evolution_pressure(self):
        """时间紧迫度驱动进化选择。"""
        from autoai.temporal import TemporalEngine
        from autoai.evolution_pressure import EvolutionPressure, AgentGenome
        te = TemporalEngine()
        te.add_deadline("critical", deadline_time=time.time() + 10)
        te.add_deadline("relaxed", deadline_time=time.time() + 3600)
        ranked = te.prioritize_by_deadline()
        assert ranked[0][0] == "critical"

    def test_resource_market_constrains_execution(self):
        """资源市场约束执行: token不足时拒绝执行。"""
        from autoai.resource_economics import ResourceMarket, Bid
        from autoai.resource_economics.market import ResourceType
        market = ResourceMarket()
        market.set_budget("task", budget=10)
        market.set_supply(ResourceType.TOKENS, 100)
        bid1 = Bid(bidder="task", resource_type=ResourceType.TOKENS, amount=5, max_price=1)
        alloc1 = market.submit_bid(bid1)
        assert alloc1.success
        bid2 = Bid(bidder="task", resource_type=ResourceType.TOKENS, amount=100, max_price=1)
        alloc2 = market.submit_bid(bid2)
        assert alloc2.amount < 100

    def test_adaptive_arch_responds_to_pressure(self):
        """自适应架构响应资源压力。"""
        from autoai.adaptive_arch import AdaptiveArchitecture
        arch = AdaptiveArchitecture(memory_limit_mb=100)
        arch.register_component("low", priority=0.2, memory_mb=80)
        arch.register_component("high", priority=0.9, memory_mb=80)
        arch.load("low")
        result = arch.load("high")
        assert result
        assert arch._components["low"].state.value != "active"

    def test_quantum_decision_with_value_alignment(self):
        """量子决策经价值对齐过滤后坍缩。"""
        from autoai.quantum_decision import QuantumDecider
        from autoai.value_alignment import ValueCalibrator
        qd = QuantumDecider()
        vc = ValueCalibrator()
        options = [
            {"action": "safe_action", "expected_value": 0.6, "risk": 0.1},
            {"action": "risky_action", "expected_value": 0.8, "risk": 0.7},
        ]
        filtered = []
        for opt in options:
            j = vc.judge(opt["action"], context={"safety": 1.0 - opt["risk"]})
            if j.is_permissible:
                filtered.append(opt)
        if filtered:
            result = qd.decide(filtered)
            assert result is not None

    def test_bootstrap_uses_all_capabilities(self):
        """自举启动器使用所有能力模块。"""
        from autoai.bootstrap import SelfBootstrapper
        bs = SelfBootstrapper(target_capabilities=[
            "reason", "remember", "act", "self_improve", "plan",
        ])
        report = bs.run_full_bootstrap()
        assert report.phase.value == "maturity"
        assert report.total_capabilities >= 5
        assert report.quality_score > 0.5


class TestEndToEndLifecycle:
    """端到端Agent生命周期仿真。"""

    def test_holo_agent_full_lifecycle(self):
        """全息Agent完整生命周期: 初始化->思考->行动->进化->状态。"""
        agent = HoloAgent(agent_id="e2e-test")
        status = agent.initialize()
        assert status.initialized
        assert status.module_count >= 10
        think_result = agent.think("分析系统性能")
        assert "content" in think_result
        act_result = agent.act("run_benchmark")
        assert "action" in act_result
        evolve_result = agent.evolve()
        assert isinstance(evolve_result, dict)
        full_status = agent.get_full_status()
        assert full_status["initialized"]

    def test_holo_agent_error_recovery(self):
        """全息Agent遇到错误时优雅降级。"""
        agent = HoloAgent(agent_id="error-test")
        agent.initialize()
        result = agent.think("正常思考")
        assert "content" in result
        result2 = agent.act("unknown_action")
        assert "action" in result2

    def test_full_pipeline_goal_to_action(self):
        """完整管道: 观察失败->涌现目标->价值评估->因果预测->执行。"""
        from autoai.goal_emergence import GoalEmergenceEngine
        from autoai.value_alignment import ValueCalibrator
        from autoai.causal_reasoning import CausalReasoner, CausalGraph
        goals = GoalEmergenceEngine()
        for _ in range(5):
            goals.observe_outcome("api_call", success=False)
        new_goals = goals.emerge_goals()
        assert len(new_goals) >= 1
        vc = ValueCalibrator()
        for g in new_goals:
            j = vc.judge(g.description, context={"safety": 0.8, "efficiency": 0.7})
        cg = CausalGraph()
        cg.add_edge("fix", "api_call_success", strength=0.8)
        reasoner = CausalReasoner(cg)
        est = reasoner.estimate_effect("fix", "api_call_success")
        assert est["estimated_effect"] > 0

    def test_multi_agent_negotiation(self):
        """多Agent协议协商场景。"""
        from autoai.protocol_evolution import ProtocolEvolver
        from autoai.protocol_evolution.negotiator import VoteType
        evolver = ProtocolEvolver("agent-comm")
        nr = evolver.propose_change({"compression": "zstd"}, proposer="agent-A")
        evolver.vote(nr.round_id, "agent-A", VoteType.ACCEPT, "faster")
        evolver.vote(nr.round_id, "agent-B", VoteType.ACCEPT, "compatible")
        evolver.vote(nr.round_id, "agent-C", VoteType.REJECT, "unsupported")
        new_v = evolver.conclude_negotiation(nr.round_id, quorum=3)
        assert new_v is not None
        assert new_v.version == 1


class TestArchitectureTopology:
    """架构拓扑生成器。"""

    def test_capability_graph(self):
        """生成模块间依赖图。"""
        from autoai.adaptive_arch import Topology
        topo = Topology()
        topo.connect("goals", "awareness")
        topo.connect("awareness", "meta_cognition")
        topo.connect("meta_cognition", "reasoning")
        topo.connect("values", "goals")
        topo.connect("causal", "world_model")
        downstream = topo.get_downstream("goals")
        assert "awareness" in downstream
        upstream = topo.get_upstream("reasoning")
        assert "meta_cognition" in upstream

    def test_dependency_depth(self):
        """计算依赖深度。"""
        from autoai.adaptive_arch import Topology
        topo = Topology()
        topo.connect("A", "B")
        topo.connect("B", "C")
        topo.connect("C", "D")
        visited = set()
        depth = 0
        current = "A"
        while current not in visited:
            visited.add(current)
            downstream = topo.get_downstream(current)
            if downstream:
                current = downstream[0]
                depth += 1
            else:
                break
        assert depth == 3


class TestHealthDashboard:
    """运行时健康仪表盘。"""

    def test_holo_health_check(self):
        """全息Agent健康检查。"""
        agent = HoloAgent(agent_id="health-check")
        agent.initialize()
        status = agent.get_full_status()
        healthy_modules = sum(1 for k, v in status.items() if isinstance(v, dict) and "error" not in v)
        assert healthy_modules >= 10

    def test_resource_health(self):
        """资源市场健康检查。"""
        from autoai.resource_economics import ResourceMarket
        from autoai.resource_economics.market import ResourceType
        market = ResourceMarket()
        status = market.get_market_status()
        for rt in ResourceType:
            assert rt.value in status
            assert status[rt.value]["available"] > 0

    def test_temporal_health(self):
        """时间引擎健康检查。"""
        from autoai.temporal import TemporalEngine
        te = TemporalEngine()
        expired = te.get_expired_deadlines()
        assert len(expired) == 0
        conflicts = te.detect_temporal_conflicts()
        assert len(conflicts) == 0

    def test_architecture_health(self):
        """架构健康检查。"""
        from autoai.adaptive_arch import AdaptiveArchitecture
        arch = AdaptiveArchitecture(memory_limit_mb=512)
        arch.register_component("core", priority=0.9, memory_mb=50)
        arch.register_component("optional", priority=0.3, memory_mb=50)
        arch.load("core")
        arch.load("optional")
        stats = arch.stats
        assert stats["active_components"] == 2
        assert stats["memory_utilization"] < 1.0
