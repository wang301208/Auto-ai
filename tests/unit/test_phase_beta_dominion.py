"""Phase beta 统治阶段集成测试。"""
import pytest
import asyncio
import time


class TestEventSourcing:
    def test_event_stream_append(self):
        from autoai.event_sourcing import EventStream, ThoughtEvent, DecisionEvent
        stream = EventStream()
        e1 = ThoughtEvent(agent_id="a1", content="思考中...")
        r1 = stream.append(e1)
        assert r1.sequence_number == 1
        assert r1.record_hash != ""
        assert stream.total_events == 1

    def test_event_chain_integrity(self):
        from autoai.event_sourcing import EventStream, ActionEvent
        stream = EventStream()
        for i in range(10):
            stream.append(ActionEvent(agent_id="a1", content=f"动作{i}"))
        valid, broken_at = stream.verify_integrity()
        assert valid
        assert broken_at == 0

    def test_event_types(self):
        from autoai.event_sourcing import (
            EventStream, ThoughtEvent, DecisionEvent, ActionEvent,
            MutationEvent, EmotionEvent,
        )
        stream = EventStream()
        stream.append(ThoughtEvent(agent_id="a", content="思考"))
        stream.append(DecisionEvent(agent_id="a", content="决定"))
        stream.append(ActionEvent(agent_id="a", content="执行"))
        stream.append(MutationEvent(agent_id="a", content="自修改"))
        stream.append(EmotionEvent(agent_id="a", content="挫败", emotion_type="frustration", intensity=0.8))
        assert stream.total_events == 5
        stats = stream.get_stats()
        assert stats["by_type"]["thought"] == 1
        assert stats["by_type"]["emotion"] == 1

    def test_time_travel(self):
        from autoai.event_sourcing import EventStream, ThoughtEvent, DecisionEvent, TimeTravelDebugger
        stream = EventStream()
        stream.append(ThoughtEvent(agent_id="a", content="初始思考"))
        stream.append(DecisionEvent(agent_id="a", content="决策A"))
        stream.append(ThoughtEvent(agent_id="a", content="后续思考"))
        debugger = TimeTravelDebugger(stream)
        state = debugger.goto(2)
        assert state["sequence"] == 2
        assert state["state"]["total_decisions"] == 1

    def test_counterfactual(self):
        from autoai.event_sourcing import EventStream, DecisionEvent, TimeTravelDebugger
        stream = EventStream()
        stream.append(DecisionEvent(agent_id="a", content="选A"))
        stream.append(DecisionEvent(agent_id="a", content="选B"))
        debugger = TimeTravelDebugger(stream)
        alt = DecisionEvent(agent_id="a", content="选C")
        result = debugger.counterfactual(2, alt)
        assert "divergence" in result

    def test_consciousness_search(self):
        from autoai.event_sourcing import EventStream, ThoughtEvent, TimeTravelDebugger
        stream = EventStream()
        stream.append(ThoughtEvent(agent_id="a", content="关于量子计算的思考"))
        stream.append(ThoughtEvent(agent_id="a", content="关于排序算法的思考"))
        debugger = TimeTravelDebugger(stream)
        results = debugger.search_consciousness("量子")
        assert len(results) == 1

    def test_materialized_view(self):
        from autoai.event_sourcing import EventStream, ThoughtEvent, DecisionEvent, MaterializedView
        stream = EventStream()
        stream.append(ThoughtEvent(agent_id="a", content="思考"))
        stream.append(DecisionEvent(agent_id="a", content="决策"))
        view = MaterializedView(stream)
        view.rebuild_all()
        thoughts = view.query("thoughts")
        assert len(thoughts) > 0

    def test_stream_save_load(self, tmp_path):
        from autoai.event_sourcing import EventStream, ThoughtEvent
        path = str(tmp_path / "events.json")
        stream = EventStream(persist_path=path)
        stream.append(ThoughtEvent(agent_id="a", content="可持久化思考"))
        stream.save()
        stream2 = EventStream(persist_path=path)
        stream2.load()
        assert stream2.total_events == 1


class TestGovernanceV2:
    def test_tripartite_governance(self):
        from autoai.governance_v2 import TripartiteGovernance, PolicyEffect
        gov = TripartiteGovernance()
        effect, verdict = gov.evaluate_operation("shell.rm")
        assert isinstance(effect, PolicyEffect)
        assert gov.legislature.get_active_laws() == []

    def test_auto_legislate(self):
        from autoai.governance_v2 import TripartiteGovernance, PolicyEffect
        gov = TripartiteGovernance()
        new_laws = gov.legislature.auto_legislate({
            "type": "shell_destruction", "pattern": "shell.rm",
            "harm_level": 4, "description": "rm导致数据丢失",
        })
        assert len(new_laws) == 1
        assert new_laws[0].effect == PolicyEffect.DENY
        effect, _ = gov.evaluate_operation("shell.rm")
        assert effect == PolicyEffect.DENY

    def test_self_report(self):
        from autoai.governance_v2 import TripartiteGovernance, VerdictType
        gov = TripartiteGovernance()
        verdict = gov.judiciary.self_report("agent-1", "unauthorized_access", "访问了未授权文件")
        assert verdict.verdict_type == VerdictType.SELF_REPORTED

    def test_constitution(self):
        from autoai.governance_v2 import GovernanceConstitution, Law, PolicyEffect
        constitution = GovernanceConstitution()
        articles = constitution.list_articles()
        assert len(articles) >= 5
        law = Law(title="禁用kill-all", operation_pattern="kill-all", effect=PolicyEffect.DENY)
        assert not constitution.is_constitutional(law)

    def test_law_effectiveness(self):
        from autoai.governance_v2 import LegislativeBranch, PolicyEffect
        leg = LegislativeBranch()
        proposal = leg.propose_law("限制shell", "限制shell执行", "shell.*", PolicyEffect.WARN)
        law = leg.enact(proposal.proposal_id)
        assert law is not None
        law.enforcement_count = 8
        law.violation_count = 2
        assert law.effectiveness == 0.8
        result = leg.evaluate_effectiveness()
        assert result["total_active"] == 1


class TestLocalModelMatrix:
    def test_matrix_init(self):
        from autoai.local_model_matrix import LocalModelMatrix
        matrix = LocalModelMatrix()
        stats = matrix.get_matrix_stats()
        assert stats["total_models"] == 5
        assert stats["free_ratio"] >= 0.8

    def test_zero_cost_router(self):
        from autoai.local_model_matrix import LocalModelMatrix, ZeroCostRouter
        matrix = LocalModelMatrix()
        router = ZeroCostRouter(matrix, escalation_threshold=0.7)
        result = router.route(task_complexity=0.3, required_quality=0.5)
        assert result.estimated_cost == 0.0
        assert not result.escalated

    def test_escalation(self):
        from autoai.local_model_matrix import LocalModelMatrix, ZeroCostRouter
        matrix = LocalModelMatrix()
        router = ZeroCostRouter(matrix, escalation_threshold=0.7)
        result = router.route(task_complexity=0.9, required_quality=0.95)
        assert result.escalated
        assert result.estimated_cost > 0

    def test_local_ratio(self):
        from autoai.local_model_matrix import LocalModelMatrix, ZeroCostRouter
        matrix = LocalModelMatrix()
        router = ZeroCostRouter(matrix)
        for _ in range(20):
            router.route(task_complexity=0.3, required_quality=0.5)
        for _ in range(5):
            router.route(task_complexity=0.9, required_quality=0.95)
        stats = router.get_stats()
        assert stats["local_ratio"] > 0.5


class TestDreamEngine:
    @pytest.mark.asyncio
    async def test_dream_session(self):
        from autoai.dream_engine import DreamEngine
        engine = DreamEngine()
        session = await engine.dream(agent_id="dreamer", num_cycles=2, memory_sample_size=10)
        assert session.insight_count >= 0
        assert session.duration_ms >= 0

    @pytest.mark.asyncio
    async def test_dream_with_memory(self):
        from autoai.dream_engine import DreamEngine
        from autoai.memory.layered import LayeredMemorySystem, MemoryLayer
        memory = LayeredMemorySystem()
        for i in range(15):
            memory.store(f"关于主题{i%3}的经验{i}", MemoryLayer.LONG_TERM, importance=0.7)
        engine = DreamEngine(memory_provider=memory.stores[MemoryLayer.LONG_TERM])
        session = await engine.dream(agent_id="dreamer", num_cycles=2, memory_sample_size=10)
        stats = engine.get_dream_stats()
        assert stats["total_sessions"] == 1


class TestContinuousAutonomy:
    def test_default_profiles(self):
        from autoai.continuous_autonomy import ContinuousAutonomy, AutonomyDimension
        conservative = ContinuousAutonomy("c1", "conservative")
        balanced = ContinuousAutonomy("b1", "balanced")
        radical = ContinuousAutonomy("r1", "radical")
        assert conservative.profile.get_overall_autonomy() < balanced.profile.get_overall_autonomy()
        assert balanced.profile.get_overall_autonomy() < radical.profile.get_overall_autonomy()

    def test_can_check(self):
        from autoai.continuous_autonomy import ContinuousAutonomy, AutonomyDimension
        ca = ContinuousAutonomy("a1", "balanced")
        assert ca.can(AutonomyDimension.STRATEGY_MODIFY, 0.5)
        assert not ca.can(AutonomyDimension.POLICY_MODIFY, 0.5)

    def test_context_adjustment(self):
        from autoai.continuous_autonomy import ContinuousAutonomy, AutonomyDimension
        ca = ContinuousAutonomy("a1", "radical")
        base = ca.get_value(AutonomyDimension.SHELL_EXECUTE)
        ca.adjust_for_context(AutonomyDimension.SHELL_EXECUTE, context_risk=0.9)
        adjusted = ca.get_value(AutonomyDimension.SHELL_EXECUTE)
        assert adjusted <= base

    def test_success_failure_adjustment(self):
        from autoai.continuous_autonomy import ContinuousAutonomy, AutonomyDimension
        ca = ContinuousAutonomy("a1", "balanced")
        initial = ca.get_value(AutonomyDimension.CODE_MODIFY)
        for _ in range(5):
            ca.record_success(AutonomyDimension.CODE_MODIFY)
        after_success = ca.get_value(AutonomyDimension.CODE_MODIFY)
        assert after_success > initial
        for _ in range(3):
            ca.record_failure(AutonomyDimension.CODE_MODIFY)
        after_failure = ca.get_value(AutonomyDimension.CODE_MODIFY)
        assert after_failure < after_success

    def test_legacy_mapping(self):
        from autoai.continuous_autonomy import ContinuousAutonomy
        ca = ContinuousAutonomy("a1", "balanced")
        level = ca.to_legacy_level()
        assert 0 <= level <= 8

    def test_risk_profile(self):
        from autoai.continuous_autonomy import ContinuousAutonomy
        ca = ContinuousAutonomy("a1", "radical")
        risk = ca.profile.get_risk_profile()
        total_risky = sum(len(v) for v in risk.values())
        assert total_risky > 0
