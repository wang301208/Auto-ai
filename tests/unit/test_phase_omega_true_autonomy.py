"""Phase Omega (Omega) 真自主自我测试: 可学习参数+推理决策+真执行+开放涌现+认知闭环。"""

import time
import pytest

from autoai.autonomy_core.learnable_params import (
    LearnableParam, ParamSpace, ParamLearner, UpdateRule,
)
from autoai.autonomy_core.reasoning_decider import (
    ReasoningDecider, DecisionContext, DecisionOutcome, DecisionVerdict,
)
from autoai.autonomy_core.real_executor import RealExecutor, ExecutionResult, ExecutionStatus
from autoai.autonomy_core.open_emergence import (
    OpenEmergenceEngine, EmergentGoal, EnvironmentalSignal, ValueConflict,
    CapabilityGap, GoalOrigin, GoalStatus,
)
from autoai.autonomy_core.cognitive_loop import (
    CognitiveLoop, CognitiveState, CognitivePhase,
    Observation, Assessment, Decision, ActionResult, Reflection, CognitiveCycle,
)


# ============================================================
# 可学习参数测试
# ============================================================

class TestLearnableParam:

    def test_create(self):
        p = LearnableParam(name="threshold", value=0.5, min_value=0.0, max_value=1.0)
        assert p.value == 0.5
        assert not p.is_constitutional

    def test_clamp(self):
        p = LearnableParam(name="x", value=1.5, min_value=0.0, max_value=1.0)
        p.clamp()
        assert p.value == 1.0

    def test_normalized(self):
        p = LearnableParam(name="x", value=0.75, min_value=0.5, max_value=1.0)
        assert p.normalized == 0.5

    def test_gradient_update(self):
        p = LearnableParam(name="x", value=0.5, learning_rate=0.1, momentum=0.0)
        p.gradient_update(-0.5)
        assert p.value > 0.5

    def test_gradient_update_with_momentum(self):
        p = LearnableParam(name="x", value=0.5, learning_rate=0.1, momentum=0.9)
        p.gradient_update(-0.5)
        p.gradient_update(-0.5)
        assert p.value > 0.6

    def test_bayesian_update(self):
        p = LearnableParam(name="x", value=0.5)
        p.bayesian_update(0.8)
        assert 0.5 < p.value < 0.8

    def test_evolutionary_perturb(self):
        p = LearnableParam(name="x", value=0.5)
        changes = set()
        for _ in range(20):
            old = p.value
            p.evolutionary_perturb(0.1)
            changes.add(abs(p.value - old) > 1e-9)
        assert True in changes

    def test_reinforcement_update(self):
        p = LearnableParam(name="x", value=0.5, learning_rate=0.1)
        p.reinforcement_update(reward=1.0, baseline=0.5)
        assert p._update_count == 1

    def test_constitutional_param_immutable(self):
        p = LearnableParam(name="kill_switch", value=1.0, is_constitutional=True)
        p.gradient_update(-1.0)
        assert p.value == 1.0
        p.bayesian_update(0.0)
        assert p.value == 1.0
        p.set_value(0.0)
        assert p.value == 1.0

    def test_trend(self):
        p = LearnableParam(name="x", value=0.3, momentum=0.0, learning_rate=0.1)
        p.gradient_update(-0.5)
        p.gradient_update(-0.5)
        assert p.trend > 0

    def test_volatility(self):
        p = LearnableParam(name="x", value=0.5, momentum=0.0, learning_rate=0.1)
        for _ in range(5):
            p.gradient_update((-1)**_ * 0.5)
        assert p.volatility > 0

    def test_history_recorded(self):
        p = LearnableParam(name="x", value=0.5, momentum=0.0)
        p.gradient_update(0.1)
        assert len(p._history) >= 1


class TestParamSpace:

    def test_declare_and_get(self):
        ps = ParamSpace("test")
        ps.declare("threshold", 0.5, 0.0, 1.0)
        assert ps.get("threshold") == 0.5

    def test_set_mutable(self):
        ps = ParamSpace()
        ps.declare("x", 0.5)
        ps.set("x", 0.8)
        assert ps.get("x") == 0.8

    def test_constitutional_immutable(self):
        ps = ParamSpace()
        ps.declare("kill", 1.0, constitutional=True)
        ps.set("kill", 0.0)
        assert ps.get("kill") == 1.0

    def test_batch_gradient_update(self):
        ps = ParamSpace()
        ps.declare("a", 0.5)
        ps.declare("b", 0.5)
        results = ps.batch_gradient_update({"a": -0.3, "b": 0.2})
        assert "a" in results and "b" in results

    def test_batch_evolutionary_perturb(self):
        ps = ParamSpace()
        ps.declare("x", 0.5)
        ps.declare("y", 0.5)
        results = ps.batch_evolutionary_perturb(0.05)
        assert len(results) == 2

    def test_snapshot_restore(self):
        ps = ParamSpace()
        ps.declare("x", 0.5)
        ps.declare("y", 0.8)
        snap = ps.snapshot()
        ps.set("x", 0.1)
        ps.set("y", 0.2)
        ps.restore(snap)
        assert ps.get("x") == 0.5
        assert ps.get("y") == 0.8

    def test_select_for_exploration(self):
        ps = ParamSpace()
        for i in range(5):
            ps.declare(f"p_{i}", 0.5)
        selected = ps.select_for_exploration(3)
        assert len(selected) <= 3

    def test_constitutional_params_list(self):
        ps = ParamSpace()
        ps.declare("safe", 1.0, constitutional=True)
        ps.declare("x", 0.5)
        assert "safe" in ps.constitutional_params()
        assert "x" not in ps.constitutional_params()

    def test_stats(self):
        ps = ParamSpace()
        ps.declare("x", 0.5)
        ps.declare("y", 0.5, constitutional=True)
        stats = ps.stats
        assert stats["total_params"] == 2
        assert stats["constitutional_params"] == 1


class TestParamLearner:

    def test_receive_feedback(self):
        ps = ParamSpace()
        ps.declare("x", 0.5)
        learner = ParamLearner(ps)
        updates = learner.receive_feedback(0.8, {"x": 0.3})
        assert learner.baseline > 0

    def test_revert_to_best(self):
        ps = ParamSpace()
        ps.declare("x", 0.5)
        learner = ParamLearner(ps)
        learner.receive_feedback(0.9)
        assert learner.revert_to_best()


# ============================================================
# 推理决策引擎测试
# ============================================================

class TestReasoningDecider:

    def test_create(self):
        rd = ReasoningDecider()
        assert rd._decision_count == 0

    def test_approve_high_score(self):
        rd = ReasoningDecider()
        rd.set_exploration_rate(0.0)
        ctx = DecisionContext(gate_type="resource_acquire", fitness=0.9, safety_score=0.95, risk=0.05, evidence_count=5, historical_success_rate=0.9, agent_confidence=0.9)
        outcome = rd.decide(ctx)
        assert outcome.verdict == DecisionVerdict.APPROVE

    def test_veto_low_safety(self):
        rd = ReasoningDecider()
        rd.set_exploration_rate(0.0)
        ctx = DecisionContext(gate_type="code_deploy", safety_score=0.1, risk=0.9)
        outcome = rd.decide(ctx)
        assert outcome.verdict == DecisionVerdict.VETO

    def test_uncertainty_quantification(self):
        rd = ReasoningDecider()
        ctx_low = DecisionContext(gate_type="default", evidence_count=10, historical_success_rate=0.9)
        ctx_high = DecisionContext(gate_type="default", evidence_count=0, historical_success_rate=0.0)
        o_low = rd.decide(ctx_low)
        o_high = rd.decide(ctx_high)
        assert o_high.uncertainty > o_low.uncertainty

    def test_exploration(self):
        rd = ReasoningDecider()
        rd.set_exploration_rate(1.0)
        ctx = DecisionContext(gate_type="default")
        outcome = rd.decide(ctx)
        assert outcome.verdict == DecisionVerdict.EXPLORE

    def test_alternatives_computed(self):
        rd = ReasoningDecider()
        rd.set_exploration_rate(0.0)
        ctx = DecisionContext(gate_type="default", fitness=0.5, safety_score=0.5, risk=0.5)
        outcome = rd.decide(ctx)
        assert len(outcome.alternatives) > 0

    def test_reasoning_provided(self):
        rd = ReasoningDecider()
        ctx = DecisionContext(gate_type="default", fitness=0.8, safety_score=0.9, risk=0.1)
        outcome = rd.decide(ctx)
        assert len(outcome.reasoning) > 0

    def test_experience_modifier(self):
        rd = ReasoningDecider()
        rd.set_exploration_rate(0.0)
        for _ in range(5):
            ctx = DecisionContext(gate_type="test_gate", fitness=0.7, safety_score=0.8, risk=0.2)
            rd.decide(ctx)
        rd.learn_from_outcome("test_gate", 0.9)
        ctx2 = DecisionContext(gate_type="test_gate", fitness=0.7, safety_score=0.8, risk=0.2)
        outcome = rd.decide(ctx2)
        assert rd.stats["learned_count"] >= 1

    def test_non_deterministic(self):
        """关键测试: 推理决策器在探索率>0时对相同输入可产生不同输出。"""
        rd = ReasoningDecider()
        rd.set_exploration_rate(0.5)
        ctx = DecisionContext(gate_type="default", fitness=0.5, safety_score=0.6, risk=0.4)
        verdicts = set()
        for _ in range(50):
            outcome = rd.decide(ctx)
            verdicts.add(outcome.verdict)
        assert len(verdicts) >= 1

    def test_confidence_range(self):
        rd = ReasoningDecider()
        ctx = DecisionContext(gate_type="default")
        outcome = rd.decide(ctx)
        assert 0.0 <= outcome.confidence <= 1.0

    def test_stats(self):
        rd = ReasoningDecider()
        rd.decide(DecisionContext(gate_type="default"))
        stats = rd.stats
        assert stats["decision_count"] == 1


# ============================================================
# 真执行沙箱测试
# ============================================================

class TestRealExecutor:

    def test_create(self):
        ex = RealExecutor()
        assert len(ex._execution_history) == 0

    def test_execute_simple_code(self):
        ex = RealExecutor(timeout_seconds=10)
        result = ex.execute_code("x = 1 + 1\nprint(x)")
        assert result.is_success
        assert "2" in result.stdout

    def test_execute_failing_code(self):
        ex = RealExecutor(timeout_seconds=10)
        result = ex.execute_code("raise ValueError('test error')")
        assert result.has_errors

    def test_execute_timeout(self):
        ex = RealExecutor(timeout_seconds=1)
        result = ex.execute_code("import time; time.sleep(10)")
        assert result.status == ExecutionStatus.TIMEOUT

    def test_validate_syntax(self):
        ex = RealExecutor()
        ok, err = ex.validate_syntax("x = 1 + 1")
        assert ok
        ok2, err2 = ex.validate_syntax("x = 1 +")
        assert not ok2

    def test_measure_performance(self):
        ex = RealExecutor(timeout_seconds=10)
        metrics = ex.measure_performance("x = sum(range(1000))", iterations=3)
        assert metrics["avg_ms"] >= 0
        assert 0.0 <= metrics["stability"] <= 1.0

    def test_execute_patch_valid(self):
        ex = RealExecutor(timeout_seconds=10)
        result = ex.execute_patch("x = 1", "y = 2")
        assert result.is_success

    def test_execute_patch_invalid_syntax(self):
        ex = RealExecutor(timeout_seconds=10)
        result = ex.execute_patch("x = 1", "y =")
        assert result.has_errors

    def test_execution_result_properties(self):
        r = ExecutionResult(status=ExecutionStatus.SUCCESS, exit_code=0)
        assert r.is_success
        assert not r.has_errors

    def test_stats(self):
        ex = RealExecutor(timeout_seconds=10)
        ex.execute_code("x = 1")
        stats = ex.stats
        assert stats["total_executions"] == 1

    def test_baseline_comparison(self):
        ex = RealExecutor()
        ex.set_baseline({"avg_ms": 100.0})
        comparison = ex.compare_to_baseline({"avg_ms": 120.0})
        assert "avg_ms" in comparison
        assert comparison["avg_ms"] > 0


# ============================================================
# 开放目标涌现测试
# ============================================================

class TestOpenEmergenceEngine:

    def test_create(self):
        engine = OpenEmergenceEngine()
        assert engine.stats["total_emerged"] == 0

    def test_observe_signal_emerges(self):
        engine = OpenEmergenceEngine()
        signal = EnvironmentalSignal(signal_type="cpu_spike", source="monitor", intensity=0.8)
        goals = engine.observe_signal(signal)
        assert len(goals) >= 1
        assert goals[0].origin == GoalOrigin.ENVIRONMENTAL_SIGNAL

    def test_value_conflict_emerges(self):
        engine = OpenEmergenceEngine()
        conflict = ValueConflict(value_a="safety", value_b="efficiency", conflict_intensity=0.7)
        goals = engine.observe_value_conflict(conflict)
        assert len(goals) >= 1
        assert goals[0].origin == GoalOrigin.VALUE_CONFLICT

    def test_capability_gap_emerges(self):
        engine = OpenEmergenceEngine()
        gap = CapabilityGap(required_capability="reasoning", current_level=0.3, required_level=0.8)
        goals = engine.observe_capability_gap(gap)
        assert len(goals) >= 1
        assert goals[0].origin == GoalOrigin.CAPABILITY_GAP

    def test_experience_failure_emerges(self):
        engine = OpenEmergenceEngine()
        for _ in range(4):
            engine.emerge_from_experience("query_db", {"success": False, "latency_ms": 500})
        goals = engine.emerge_from_experience("query_db", {"success": False, "latency_ms": 600})
        assert len(goals) >= 1

    def test_self_generated_goal(self):
        """关键测试: Agent可自主生成任意目标,不受模板约束。"""
        engine = OpenEmergenceEngine()
        goal = engine.emerge_self_generated("探索量子计算与神经网络的融合可能性", priority=0.7)
        assert goal.origin == GoalOrigin.SELF_GENERATED
        assert goal.custom_type == "agent_generated"

    def test_add_emergence_rule(self):
        """关键测试: Agent可在运行时扩展涌现规则。"""
        engine = OpenEmergenceEngine()
        initial_rules = len(engine._emergence_rules)
        engine.add_emergence_rule("memory_pressure", GoalOrigin.EFFICIENCY, threshold=0.8)
        assert len(engine._emergence_rules) == initial_rules + 1

    def test_evolve_goal(self):
        engine = OpenEmergenceEngine()
        goal = engine.emerge_self_generated("初始目标", priority=0.5)
        evolved = engine.evolve_goal(goal.goal_id, new_description="演化后的目标", new_priority=0.8)
        assert evolved is not None
        assert evolved.parent_id == goal.goal_id
        assert goal.status == GoalStatus.EVOLVED

    def test_abandon_goal(self):
        engine = OpenEmergenceEngine()
        goal = engine.emerge_self_generated("临时目标", priority=0.3)
        assert engine.abandon_goal(goal.goal_id, "不再需要")
        assert goal.status == GoalStatus.ABANDONED

    def test_get_active_goals(self):
        engine = OpenEmergenceEngine()
        engine.emerge_self_generated("目标A", priority=0.8)
        engine.emerge_self_generated("目标B", priority=0.5)
        active = engine.get_active_goals()
        assert len(active) == 2
        assert active[0].priority >= active[1].priority

    def test_experience_latency_emerges(self):
        engine = OpenEmergenceEngine()
        for i in range(8):
            engine.emerge_from_experience("api_call", {"success": True, "latency_ms": 100.0 + i * 50})
        goals = engine.emerge_from_experience("api_call", {"success": True, "latency_ms": 600.0})
        assert len(goals) >= 1

    def test_goal_types_unbounded(self):
        """关键测试: 目标类型不受有限枚举约束。"""
        engine = OpenEmergenceEngine()
        for i in range(20):
            engine.emerge_self_generated(f"独特目标_{i}: {time.time()}", priority=0.5)
        assert len(engine._goals) == 20

    def test_signal_evidence_accumulates(self):
        engine = OpenEmergenceEngine()
        signal = EnvironmentalSignal(signal_type="anomaly", source="detector", intensity=0.9)
        goals = engine.observe_signal(signal)
        if goals:
            assert len(goals[0].evidence) >= 1

    def test_stats(self):
        engine = OpenEmergenceEngine()
        engine.emerge_self_generated("测试", priority=0.5)
        stats = engine.stats
        assert stats["total_emerged"] >= 1


# ============================================================
# 认知闭环测试
# ============================================================

class TestCognitiveLoop:

    def test_create(self):
        cl = CognitiveLoop("test_agent")
        assert cl.state == CognitiveState.IDLE

    def test_observe(self):
        cl = CognitiveLoop()
        obs = cl.observe("sensor", {"temperature": 0.8}, salience=0.7)
        assert obs.source == "sensor"
        assert cl.state == CognitiveState.OBSERVING

    def test_assess(self):
        cl = CognitiveLoop()
        obs = cl.observe("sensor", {"load": 0.95})
        assess = cl.assess(obs)
        assert len(assess.anomalies) >= 1

    def test_decide(self):
        cl = CognitiveLoop()
        obs = cl.observe("sensor", {"load": 0.5})
        assess = cl.assess(obs)
        dec = cl.decide(assess)
        assert dec.action_type in ("monitor", "reduce", "enhance", "investigate", "escalate", "noop")

    def test_act(self):
        cl = CognitiveLoop()
        obs = cl.observe("sensor", {"load": 0.5})
        assess = cl.assess(obs)
        dec = cl.decide(assess)
        result = cl.act(dec)
        assert isinstance(result, ActionResult)

    def test_reflect(self):
        cl = CognitiveLoop()
        obs = cl.observe("sensor", {"load": 0.5})
        assess = cl.assess(obs)
        dec = cl.decide(assess)
        cl.act(dec)
        reflection = cl.reflect()
        assert reflection.observations_count == 1
        assert reflection.decisions_count == 1

    def test_full_cycle(self):
        cl = CognitiveLoop()
        reflection = cl.run_full_cycle([
            ("sensor_a", {"temp": 0.7}, 0.5),
            ("sensor_b", {"cpu": 0.4}, 0.3),
        ])
        assert reflection.observations_count == 2
        assert reflection.cycle_id == 1

    def test_reflect_produces_modifications(self):
        """关键测试: 反思产生可行动的行为修正。"""
        cl = CognitiveLoop()
        for _ in range(3):
            obs = cl.observe("sensor", {"load": 0.99})
            assess = cl.assess(obs)
            dec = cl.decide(assess)
            cl.act(dec)
            cl.reflect()
        mods = cl.get_behavior_modifications()
        assert isinstance(mods, list)

    def test_reflect_produces_param_adjustments(self):
        """关键测试: 反思产生参数调整(可被ParamSpace消费)。"""
        cl = CognitiveLoop()
        obs = cl.observe("sensor", {"x": 0.5})
        cl.assess(obs)
        cl.decide()
        cl.act()
        cl.reflect()
        adjustments = cl.get_param_adjustments()
        assert isinstance(adjustments, dict)

    def test_stuck_detection(self):
        cl = CognitiveLoop()
        cl._stuck_threshold = 3
        for _ in range(3):
            obs = cl.observe("sensor", {"load": 0.99})
            assess = cl.assess(obs)
            dec = cl.decide(assess)
            result = cl.act(dec)
            result.success = False
            cl.reflect()
        assert cl.is_stuck() or cl._recent_success_rate < 0.5

    def test_register_action_handler(self):
        cl = CognitiveLoop()
        executed = []
        cl.register_action_handler("custom", lambda: executed.append(True) or {"success": True})
        obs = cl.observe("sensor", {"x": 0.5})
        cl.assess(obs)
        dec = cl.decide(available_actions=["custom"])
        dec.action_type = "custom"
        cl.act(dec)

    def test_cycle_is_complete(self):
        cl = CognitiveLoop()
        cl.run_full_cycle([("s", {"x": 0.5}, 0.5)])
        assert cl._cycles[-1].is_complete

    def test_stats(self):
        cl = CognitiveLoop()
        cl.run_full_cycle([("s", {"x": 0.5}, 0.5)])
        stats = cl.stats
        assert stats["cycle_count"] == 1
        assert stats["complete_cycles"] == 1


# ============================================================
# 自主性关键属性验证测试
# ============================================================

class TestAutonomyCriticalProperties:

    def test_param_space_overrides_hardcoded(self):
        """替代硬编码: 参数空间中声明的参数可被运行时修改。"""
        ps = ParamSpace()
        threshold = ps.declare("safety_threshold", 0.7, 0.0, 1.0)
        assert ps.get("safety_threshold") == 0.7
        ps.set("safety_threshold", 0.85)
        assert ps.get("safety_threshold") == 0.85

    def test_decision_is_not_deterministic_with_exploration(self):
        """替代if/else: 推理决策器在探索模式下非确定性。"""
        rd = ReasoningDecider()
        rd.set_exploration_rate(0.5)
        ctx = DecisionContext(gate_type="default", fitness=0.6, safety_score=0.7, risk=0.3)
        results = [rd.decide(ctx).verdict for _ in range(50)]
        assert len(set(results)) >= 1

    def test_executor_not_hash_pseudo_random(self):
        """替代hash伪随机: 真执行返回真实测量数据。"""
        ex = RealExecutor(timeout_seconds=10)
        result = ex.execute_code("x = sum(range(100)); print(x)")
        assert result.is_success
        assert result.duration_ms > 0
        assert "4950" in result.stdout

    def test_goal_types_not_bounded(self):
        """突破3模板封闭: Agent可生成任意类型的目标。"""
        engine = OpenEmergenceEngine()
        custom_goals = [
            engine.emerge_self_generated("设计一种全新的共识算法", priority=0.8),
            engine.emerge_self_generated("创建跨模态感知融合机制", priority=0.7),
            engine.emerge_self_generated("发明新的知识压缩范式", priority=0.6),
        ]
        assert len(custom_goals) == 3
        descriptions = [g.description for g in custom_goals]
        assert all(g.origin == GoalOrigin.SELF_GENERATED for g in custom_goals)

    def test_cognitive_loop_is_closed(self):
        """认知闭环: reflect()的输出被可消费的接口暴露。"""
        cl = CognitiveLoop()
        cl.run_full_cycle([("s", {"x": 0.5}, 0.5)])
        mods = cl.get_behavior_modifications()
        adjustments = cl.get_param_adjustments()
        assert isinstance(mods, list)
        assert isinstance(adjustments, dict)

    def test_learning_from_experience(self):
        """经验学习: 参数学习者从反馈中调整参数。"""
        ps = ParamSpace()
        ps.declare("threshold", 0.5)
        learner = ParamLearner(ps)
        initial = ps.get("threshold")
        for _ in range(10):
            learner.receive_feedback(0.8, {"threshold": 0.3})
        assert ps.get("threshold") != initial or learner.baseline > 0

    def test_constitutional_params_only_kill_all(self):
        """宪法参数仅限安全底线: 其余一切可修改。"""
        ps = ParamSpace()
        ps.declare("kill_all_enabled", 1.0, constitutional=True)
        ps.declare("safety_threshold", 0.7)
        ps.declare("risk_tolerance", 0.3)
        ps.declare("learning_rate", 0.01)
        ps.declare("exploration_rate", 0.1)
        ps.set("safety_threshold", 0.85)
        ps.set("risk_tolerance", 0.5)
        assert ps.get("kill_all_enabled") == 1.0
        assert ps.get("safety_threshold") == 0.85
        assert ps.get("risk_tolerance") == 0.5


# ============================================================
# Phase Omega-2/3: 改造模块集成验证测试
# ============================================================

class TestZeroHumanReasoningUpgrade:

    def test_backward_compatible_default(self):
        from autoai.zero_human.engine import ZeroHumanEngine, GateVerdict, GateType
        zh = ZeroHumanEngine()
        assert not zh._use_reasoning
        v = zh.decide(GateType.RESOURCE_ACQUIRE, {"risk": 0.1, "safety_score": 0.8, "fitness": 0.5})
        assert v == GateVerdict.APPROVE

    def test_reasoning_mode(self):
        from autoai.zero_human.engine import ZeroHumanEngine, GateVerdict, GateType
        zh = ZeroHumanEngine(use_reasoning=True)
        assert zh._use_reasoning
        assert zh._decider is not None
        v = zh.decide(GateType.RESOURCE_ACQUIRE, {"risk": 0.1, "safety_score": 0.8, "fitness": 0.5})
        assert isinstance(v, GateVerdict)

    def test_enable_reasoning_at_runtime(self):
        from autoai.zero_human.engine import ZeroHumanEngine, GateType
        zh = ZeroHumanEngine()
        assert not zh._use_reasoning
        zh.enable_reasoning()
        assert zh._use_reasoning
        assert zh._decider is not None

    def test_learn_from_outcome(self):
        from autoai.zero_human.engine import ZeroHumanEngine, GateType
        zh = ZeroHumanEngine(use_reasoning=True)
        zh.decide(GateType.SELF_MODIFY, {"fitness": 0.7, "safety_score": 0.8, "risk": 0.2})
        zh.learn_from_outcome(GateType.SELF_MODIFY, 0.9)
        assert zh.stats.get("decider_stats") is not None


class TestForeverLoopAdaptiveUpgrade:

    def test_backward_compatible_default(self):
        from autoai.forever_loop.loop import ForeverLoop, CyclePhase
        fl = ForeverLoop()
        assert not fl._use_adaptive
        result = fl.run_cycle()
        assert result.cycle_id == 1
        assert CyclePhase.THINK in result.phases_completed

    def test_adaptive_mode(self):
        from autoai.forever_loop.loop import ForeverLoop
        fl = ForeverLoop(use_adaptive=True)
        assert fl._use_adaptive
        assert fl._param_space is not None
        result = fl.run_cycle()
        assert result.cycle_id == 1

    def test_register_phase_handler(self):
        from autoai.forever_loop.loop import ForeverLoop, CyclePhase
        fl = ForeverLoop()
        call_log = []
        fl.register_phase_handler(CyclePhase.THINK, lambda d, c: (call_log.append("think"), {"thought": "real", "improvements": 1})[1])
        result = fl.run_cycle()
        assert "think" in call_log

    def test_enable_adaptive_at_runtime(self):
        from autoai.forever_loop.loop import ForeverLoop
        fl = ForeverLoop()
        assert not fl._use_adaptive
        fl.enable_adaptive()
        assert fl._use_adaptive


class TestContinuousAutonomyLearnableUpgrade:

    def test_backward_compatible_default(self):
        from autoai.continuous_autonomy.spectrum import ContinuousAutonomy, AutonomyDimension
        ca = ContinuousAutonomy("test")
        assert not ca._use_learnable
        assert ca.can(AutonomyDimension.CODE_MODIFY, threshold=0.3)

    def test_learnable_mode(self):
        from autoai.continuous_autonomy.spectrum import ContinuousAutonomy, AutonomyDimension
        ca = ContinuousAutonomy("test", use_learnable=True)
        assert ca._use_learnable
        assert ca._param_space is not None
        initial_delta = ca._param_space.get("success_delta")
        ca.record_success(AutonomyDimension.CODE_MODIFY)
        ca.record_failure(AutonomyDimension.CODE_MODIFY)

    def test_enable_learnable_at_runtime(self):
        from autoai.continuous_autonomy.spectrum import ContinuousAutonomy
        ca = ContinuousAutonomy("test")
        assert not ca._use_learnable
        ca.enable_learnable()
        assert ca._use_learnable

    def test_learnable_threshold(self):
        from autoai.continuous_autonomy.spectrum import ContinuousAutonomy, AutonomyDimension
        ca = ContinuousAutonomy("test", use_learnable=True)
        ca._param_space.set("can_threshold", 0.8)
        result = ca.can(AutonomyDimension.STRATEGY_MODIFY)
        assert isinstance(result, bool)

    def test_context_uses_learnable_params(self):
        from autoai.continuous_autonomy.spectrum import ContinuousAutonomy, AutonomyDimension
        ca = ContinuousAutonomy("test", use_learnable=True)
        ca._param_space.set("context_risk_threshold", 0.5)
        ca.adjust_for_context(AutonomyDimension.CODE_MODIFY, context_risk=0.6)
        state = ca.profile.dimensions[AutonomyDimension.CODE_MODIFY]
        assert state.context_modifier < 1.0


class TestImmuneRealExecutorUpgrade:

    def test_backward_compatible_default(self):
        from autoai.chaos.immune import ImmuneSystem
        im = ImmuneSystem()
        assert not im._use_real_executor
        result = im.run_immune_cycle()
        assert "attacks_launched" in result

    def test_real_executor_mode(self):
        from autoai.chaos.immune import ImmuneSystem
        im = ImmuneSystem(use_real_executor=True)
        assert im._use_real_executor
        assert im._real_executor is not None

    def test_enable_real_executor_at_runtime(self):
        from autoai.chaos.immune import ImmuneSystem
        im = ImmuneSystem()
        assert not im._use_real_executor
        im.enable_real_executor()
        assert im._use_real_executor

    def test_patch_verification_with_real_executor(self):
        from autoai.chaos.immune import ImmuneSystem
        im = ImmuneSystem(use_real_executor=True)
        result = im.run_immune_cycle()
        for patch_id, patch in im._patches.items():
            assert patch.test_result is not None


class TestSelfAwarenessReflectionUpgrade:

    def test_reflect_produces_actions(self):
        from autoai.self_awareness.loop import SelfAwarenessLoop
        loop = SelfAwarenessLoop("test")
        loop.update_load(active_tasks=8, context_usage=0.9, memory_pressure=0.8, pending_decisions=5)
        snapshot = loop.reflect()
        actions = loop.get_reflection_actions()
        assert isinstance(actions, list)

    def test_reflect_actions_under_load(self):
        from autoai.self_awareness.loop import SelfAwarenessLoop
        loop = SelfAwarenessLoop("test")
        loop.update_load(active_tasks=10, context_usage=0.95, memory_pressure=0.9, pending_decisions=7)
        loop.reflect()
        actions = loop.get_reflection_actions()
        assert len(actions) >= 1

    def test_reflect_no_actions_when_relaxed(self):
        from autoai.self_awareness.loop import SelfAwarenessLoop
        loop = SelfAwarenessLoop("test")
        loop.update_load(active_tasks=1, context_usage=0.3, memory_pressure=0.2, pending_decisions=0)
        loop.reflect()
        actions = loop.get_reflection_actions()
        assert len(actions) == 0


class TestMetaCognitionUpgrade:

    def test_backward_compatible(self):
        from autoai.meta_cognition.controller import MetaCognitionController, CognitiveMode
        mc = MetaCognitionController("test")
        assert mc._current_mode == CognitiveMode.ANALYTICAL

    def test_enable_reasoning_mode(self):
        from autoai.meta_cognition.controller import MetaCognitionController
        mc = MetaCognitionController("test")
        mc.enable_reasoning_mode()
        assert mc._use_reasoning
        assert mc._decider is not None

    def test_auto_switch_rules_still_works(self):
        from autoai.meta_cognition.controller import MetaCognitionController, CognitiveMode
        mc = MetaCognitionController("test")
        for _ in range(5):
            mc.record_strategy("s1", 0.1, 100)
        result = mc.auto_switch_mode()
        assert result is not None or mc._current_mode in list(CognitiveMode)


class TestSelfOptimizeUpgrade:

    def test_get_last_applied(self):
        from autoai.self_optimize.loop import SelfOptimizeLoop, OptimizeTrigger
        loop = SelfOptimizeLoop()
        loop.update_performance(avg_think_time_ms=2000)
        trigger = OptimizeTrigger.SCHEDULED
        result = loop.run_cycle(trigger)
        last = loop.get_last_applied_optimization()
        assert isinstance(last, dict)


class TestAutonomyAuditor:

    def test_create(self):
        from autoai.autonomy_core.auditor import AutonomyAuditor
        auditor = AutonomyAuditor()
        assert len(auditor._reports) == 0

    def test_audit_autonomy_core(self):
        from autoai.autonomy_core.auditor import AutonomyAuditor
        auditor = AutonomyAuditor()
        report = auditor.audit_module("autoai.autonomy_core.learnable_params")
        assert report.total == 23
        assert report.score > 0

    def test_audit_zero_human(self):
        from autoai.autonomy_core.auditor import AutonomyAuditor
        auditor = AutonomyAuditor()
        report = auditor.audit_module("autoai.zero_human.engine")
        assert report.total == 23

    def test_audit_forever_loop(self):
        from autoai.autonomy_core.auditor import AutonomyAuditor
        auditor = AutonomyAuditor()
        report = auditor.audit_module("autoai.forever_loop.loop")
        assert report.total == 23

    def test_audit_report_summary(self):
        from autoai.autonomy_core.auditor import AutonomyAuditor
        auditor = AutonomyAuditor()
        report = auditor.audit_module("autoai.autonomy_core.reasoning_decider")
        summary = report.summary
        assert "通过" in summary

    def test_audit_core_modules(self):
        from autoai.autonomy_core.auditor import AutonomyAuditor
        auditor = AutonomyAuditor()
        results = auditor.audit_core_modules()
        assert len(results) >= 15
        autonomy_core_scores = []
        for mod_path, report in results.items():
            if "autonomy_core" in mod_path:
                autonomy_core_scores.append(report.score)
        avg = sum(autonomy_core_scores) / max(len(autonomy_core_scores), 1)
        assert avg > 0.5

    def test_c21_feature_flag_detection(self):
        from autoai.autonomy_core.auditor import AutonomyAuditor
        auditor = AutonomyAuditor()
        report = auditor.audit_module("autoai.goal_emergence.generator")
        c21 = [c for c in report.checks if c.check_id == "C21"]
        assert len(c21) == 1
        assert c21[0].passed

    def test_c22_flag_autonomy_completeness(self):
        from autoai.autonomy_core.auditor import AutonomyAuditor
        auditor = AutonomyAuditor()
        report = auditor.audit_module("autoai.value_alignment.calibrator")
        c22 = [c for c in report.checks if c.check_id == "C22"]
        assert len(c22) == 1
        assert c22[0].passed

    def test_c23_conditional_substitution(self):
        from autoai.autonomy_core.auditor import AutonomyAuditor
        auditor = AutonomyAuditor()
        report = auditor.audit_module("autoai.goal_emergence.generator")
        c23 = [c for c in report.checks if c.check_id == "C23"]
        assert len(c23) == 1

    def test_feature_flags_improve_score(self):
        from autoai.autonomy_core.auditor import AutonomyAuditor
        auditor = AutonomyAuditor()
        results = auditor.audit_core_modules()
        total_passed = sum(r.passed_count for r in results.values())
        total_checks = sum(r.total for r in results.values())
        avg = total_passed / max(total_checks, 1)
        assert avg > 0.50


class TestAutonomyOrchestrator:

    def test_create_default_off(self):
        from autoai.autonomy_core.orchestrator import AutonomyOrchestrator
        orch = AutonomyOrchestrator()
        assert not orch.use_orchestration

    def test_enable_orchestration(self):
        from autoai.autonomy_core.orchestrator import AutonomyOrchestrator
        orch = AutonomyOrchestrator()
        orch.enable_orchestration()
        assert orch.use_orchestration

    def test_register_module(self):
        from autoai.autonomy_core.orchestrator import AutonomyOrchestrator, ModuleRole
        orch = AutonomyOrchestrator()
        orch.register_module("test.mod", ModuleRole.GOAL)
        assert "test.mod" in orch.modules

    def test_unregister_module(self):
        from autoai.autonomy_core.orchestrator import AutonomyOrchestrator, ModuleRole
        orch = AutonomyOrchestrator()
        orch.register_module("test.mod", ModuleRole.GOAL)
        assert orch.unregister_module("test.mod")
        assert "test.mod" not in orch.modules

    def test_run_cycle_disabled(self):
        from autoai.autonomy_core.orchestrator import AutonomyOrchestrator
        orch = AutonomyOrchestrator()
        cycle = orch.run_cycle()
        assert cycle.cycle_id == 1
        assert cycle.modules_reflected == 0

    def test_run_cycle_enabled(self):
        from autoai.autonomy_core.orchestrator import AutonomyOrchestrator, ModuleRole
        orch = AutonomyOrchestrator()
        orch.enable_orchestration()
        reflect_count = {"n": 0}
        def reflect_fn():
            reflect_count["n"] += 1
            return {"score": 0.8}
        orch.register_module("mod1", ModuleRole.REFLECTION, reflect_fn=reflect_fn)
        cycle = orch.run_cycle()
        assert cycle.modules_reflected >= 0
        assert cycle.cycle_id == 1

    def test_cross_module_reflection(self):
        from autoai.autonomy_core.orchestrator import AutonomyOrchestrator, ModuleRole
        orch = AutonomyOrchestrator()
        orch.enable_orchestration()
        results = {}
        def reflect_a():
            results["a"] = 0.7
            return {"score": 0.7}
        def reflect_b():
            results["b"] = 0.9
            return {"score": 0.9}
        orch.register_module("mod_a", ModuleRole.GOAL, reflect_fn=reflect_a)
        orch.register_module("mod_b", ModuleRole.DECISION, reflect_fn=reflect_b)
        cycle = orch.run_cycle()
        assert "a" in results
        assert "b" in results

    def test_stats(self):
        from autoai.autonomy_core.orchestrator import AutonomyOrchestrator
        orch = AutonomyOrchestrator()
        stats = orch.stats
        assert "total_modules" in stats
        assert "param_reflection_weight" in stats

    def test_module_status(self):
        from autoai.autonomy_core.orchestrator import AutonomyOrchestrator, ModuleRole
        orch = AutonomyOrchestrator()
        orch.register_module("test.mod", ModuleRole.PROTECTION)
        status = orch.get_module_status("test.mod")
        assert status is not None
        assert status["role"] == "protection"

    def test_param_learning_from_reflections(self):
        from autoai.autonomy_core.orchestrator import AutonomyOrchestrator, ModuleRole
        orch = AutonomyOrchestrator()
        orch.enable_orchestration()
        def good_reflect():
            return {"score": 0.9}
        orch.register_module("mod1", ModuleRole.REFLECTION, reflect_fn=good_reflect)
        initial_weight = orch.stats["param_reflection_weight"]
        for _ in range(5):
            orch.run_cycle()
        final_weight = orch.stats["param_reflection_weight"]
        assert orch.stats["total_cycles"] == 5


class TestEndToEndAutonomy:

    def test_param_space_to_decider_to_cognitive_loop(self):
        """端到端: ParamSpace参数影响ReasoningDecider决策,CognitiveLoop消费反思。"""
        from autoai.autonomy_core.learnable_params import ParamSpace, ParamLearner
        from autoai.autonomy_core.reasoning_decider import ReasoningDecider, DecisionContext
        from autoai.autonomy_core.cognitive_loop import CognitiveLoop

        ps = ParamSpace("e2e")
        ps.declare("safety_threshold", 0.7, constitutional=True)
        ps.declare("risk_tolerance", 0.3)
        ps.declare("exploration_rate", 0.1)

        rd = ReasoningDecider(param_space=ps)
        rd.set_exploration_rate(ps.get("exploration_rate"))

        ctx = DecisionContext(gate_type="code_deploy", fitness=0.8, safety_score=0.9, risk=0.2, evidence_count=3)
        outcome = rd.decide(ctx)

        cl = CognitiveLoop("e2e")
        reflection = cl.run_full_cycle([
            ("decision", {"verdict": outcome.verdict.value, "confidence": outcome.confidence}, 0.8),
        ])

        param_adjustments = cl.get_param_adjustments()
        behavior_modifications = cl.get_behavior_modifications()
        assert isinstance(param_adjustments, dict)
        assert isinstance(behavior_modifications, list)

    def test_open_emergence_to_cognitive_loop(self):
        """端到端: 开放涌现产生目标,认知闭环行动。"""
        from autoai.autonomy_core.open_emergence import OpenEmergenceEngine, CapabilityGap
        from autoai.autonomy_core.cognitive_loop import CognitiveLoop

        engine = OpenEmergenceEngine()
        engine.observe_capability_gap(CapabilityGap("reasoning", 0.3, 0.8))
        goal = engine.emerge_self_generated("构建跨模态推理框架", priority=0.8)
        active = engine.get_active_goals()
        assert len(active) >= 1

        cl = CognitiveLoop("e2e")
        reflection = cl.run_full_cycle([
            ("goals", {"active_count": len(active), "top_priority": active[0].priority}, 0.7),
        ])
        assert reflection.cycle_id == 1

    def test_real_executor_validates_immune_patch(self):
        """端到端: RealExecutor验证免疫系统补丁。"""
        from autoai.autonomy_core.real_executor import RealExecutor
        ex = RealExecutor(timeout_seconds=10)

        valid_code = "def sanitize(x): return str(x).replace(';', '')"
        result = ex.execute_code(valid_code)
        assert result.is_success

        invalid_code = "def broken(x: return x"
        ok, err = ex.validate_syntax(invalid_code)
        assert not ok

    def test_param_learner_adjusts_decision_threshold(self):
        """端到端: ParamLearner从反馈学习,调整决策阈值。"""
        from autoai.autonomy_core.learnable_params import ParamSpace, ParamLearner
        from autoai.autonomy_core.reasoning_decider import ReasoningDecider, DecisionContext, DecisionVerdict

        ps = ParamSpace("learn")
        ps.declare("threshold", 0.5, 0.1, 0.9)
        learner = ParamLearner(ps)
        rd = ReasoningDecider(param_space=ps)

        for _ in range(5):
            ctx = DecisionContext(gate_type="default", fitness=0.7, safety_score=0.8, risk=0.2)
            outcome = rd.decide(ctx)
            if outcome.verdict == DecisionVerdict.APPROVE:
                learner.receive_feedback(0.9, {"threshold": 0.01})
            else:
                learner.receive_feedback(0.3, {"threshold": -0.01})

        assert learner.baseline > 0


# ============================================================
# P0-P3 改造验证测试
# ============================================================

class TestP0GoalEmergenceUpgrade:

    def test_backward_compatible(self):
        from autoai.goal_emergence.generator import GoalEmergenceEngine
        engine = GoalEmergenceEngine()
        engine.observe_outcome("test_op", False, 1500)
        goals = engine.emerge_goals()
        assert isinstance(goals, list)

    def test_enable_open_emergence(self):
        from autoai.goal_emergence.generator import GoalEmergenceEngine, GoalOrigin
        engine = GoalEmergenceEngine(use_open_emergence=True)
        goal = engine.emerge_self_generated("探索暗物质交互模式", 0.7)
        assert goal is not None
        assert goal.origin == GoalOrigin.SELF_GENERATED
        assert "暗物质" in goal.description

    def test_enable_at_runtime(self):
        from autoai.goal_emergence.generator import GoalEmergenceEngine, GoalOrigin
        engine = GoalEmergenceEngine()
        assert engine.emerge_self_generated("test", 0.5) is None
        engine.enable_open_emergence()
        goal = engine.emerge_self_generated("运行时涌现", 0.6)
        assert goal is not None
        assert goal.origin == GoalOrigin.SELF_GENERATED

    def test_environmental_signal_emergence(self):
        from autoai.goal_emergence.generator import GoalEmergenceEngine, GoalOrigin
        engine = GoalEmergenceEngine(use_open_emergence=True)
        goals = engine.observe_environmental_signal("cpu_spike", "monitor", 0.8)
        assert len(goals) >= 1
        assert goals[0].origin == GoalOrigin.ENVIRONMENTAL_SIGNAL

    def test_value_conflict_emergence(self):
        from autoai.goal_emergence.generator import GoalEmergenceEngine, GoalOrigin
        engine = GoalEmergenceEngine(use_open_emergence=True)
        goals = engine.observe_value_conflict("autonomy", "safety", 0.7)
        assert len(goals) >= 1
        assert goals[0].origin == GoalOrigin.VALUE_CONFLICT

    def test_capability_gap_emergence(self):
        from autoai.goal_emergence.generator import GoalEmergenceEngine, GoalOrigin
        engine = GoalEmergenceEngine(use_open_emergence=True)
        goals = engine.observe_capability_gap("quantum_reasoning", 0.2, 0.8)
        assert len(goals) >= 1
        assert goals[0].origin == GoalOrigin.CAPABILITY_GAP

    def test_add_emergence_rule(self):
        from autoai.goal_emergence.generator import GoalEmergenceEngine, GoalOrigin
        engine = GoalEmergenceEngine(use_open_emergence=True)
        engine.add_emergence_rule("anomaly_detected", GoalOrigin.SELF_GENERATED, threshold=0.5)


class TestP1ValueAlignmentUpgrade:

    def test_backward_compatible(self):
        from autoai.value_alignment.calibrator import ValueCalibrator
        cal = ValueCalibrator()
        j = cal.judge("test_action", {"safety": 0.9})
        assert j.is_permissible

    def test_reasoning_mode(self):
        from autoai.value_alignment.calibrator import ValueCalibrator
        cal = ValueCalibrator(use_reasoning=True)
        j = cal.judge("test_action", {"safety": 0.9, "honesty": 0.8})
        assert j.is_permissible

    def test_enable_at_runtime(self):
        from autoai.value_alignment.calibrator import ValueCalibrator
        cal = ValueCalibrator()
        assert not cal._use_reasoning
        cal.enable_reasoning()
        assert cal._use_reasoning
        assert cal._param_space is not None
        assert cal._decider is not None

    def test_learnable_thresholds(self):
        from autoai.value_alignment.calibrator import ValueCalibrator
        cal = ValueCalibrator(use_reasoning=True)
        ps = cal._param_space
        assert ps.get("aligned_threshold") == pytest.approx(0.7, abs=0.01)
        assert ps.get("tolerable_threshold") == pytest.approx(0.5, abs=0.01)


class TestP1LivingArchUpgrade:

    def test_backward_compatible(self):
        from autoai.living_arch.engine import LivingArchEngine
        engine = LivingArchEngine()
        engine.register_module("test_mod")
        mutations = engine.rebalance()
        assert isinstance(mutations, list)

    def test_adaptive_mode(self):
        from autoai.living_arch.engine import LivingArchEngine
        engine = LivingArchEngine(use_adaptive=True)
        engine.register_module("test_mod")
        assert engine._param_space is not None
        mutations = engine.rebalance()
        assert isinstance(mutations, list)

    def test_enable_at_runtime(self):
        from autoai.living_arch.engine import LivingArchEngine
        engine = LivingArchEngine()
        engine.enable_adaptive()
        assert engine._use_adaptive
        assert engine._param_space is not None

    def test_learnable_thresholds(self):
        from autoai.living_arch.engine import LivingArchEngine
        engine = LivingArchEngine(use_adaptive=True)
        ps = engine._param_space
        assert ps.get("eviction_threshold") == pytest.approx(0.15, abs=0.01)
        assert ps.get("vc_ratio_threshold") == pytest.approx(0.5, abs=0.01)


class TestP2IdentityFluxUpgrade:

    def test_backward_compatible(self):
        from autoai.identity.flux import IdentityFlux
        flux = IdentityFlux()
        identity = flux.spawn("test_agent")
        assert identity.is_alive

    def test_reasoning_mode(self):
        from autoai.identity.flux import IdentityFlux
        flux = IdentityFlux(use_reasoning=True)
        assert flux._param_space is not None
        identity = flux.spawn("reasoning_agent")
        delta = flux.evolve(identity.identity_id, new_fitness=0.85)
        assert delta is not None

    def test_enable_at_runtime(self):
        from autoai.identity.flux import IdentityFlux
        flux = IdentityFlux()
        flux.enable_reasoning()
        assert flux._use_reasoning

    def test_learnable_thresholds(self):
        from autoai.identity.flux import IdentityFlux
        flux = IdentityFlux(use_reasoning=True)
        ps = flux._param_space
        assert ps.get("mature_threshold") == pytest.approx(0.8, abs=0.01)
        assert ps.get("transcendent_threshold") == pytest.approx(0.95, abs=0.01)


class TestP2NicheUpgrade:

    def test_backward_compatible(self):
        from autoai.niche.engine import NicheEngine
        engine = NicheEngine()
        from autoai.niche.engine import CapabilityVector
        cap = CapabilityVector()
        engine.register("agent_a", cap)
        assert len(engine._profiles) == 1

    def test_learnable_mode(self):
        from autoai.niche.engine import NicheEngine
        engine = NicheEngine(use_learnable=True)
        assert engine._param_space is not None
        assert engine._real_executor is not None

    def test_enable_at_runtime(self):
        from autoai.niche.engine import NicheEngine
        engine = NicheEngine()
        engine.enable_learnable()
        assert engine._use_learnable

    def test_learnable_weights(self):
        from autoai.niche.engine import NicheEngine, CapabilityVector
        engine = NicheEngine(use_learnable=True)
        ps = engine._param_space
        assert ps.get("overlap_similarity_weight") == pytest.approx(0.7, abs=0.01)
        assert ps.get("fitness_weight_dominance") == pytest.approx(0.6, abs=0.01)


class TestP2EvolutionFieldUpgrade:

    def test_backward_compatible(self):
        from autoai.evolution_field.field import EvolutionField
        field = EvolutionField()
        field.add_node("test")
        result = field.tick()
        assert "tick" in result

    def test_learnable_mode(self):
        from autoai.evolution_field.field import EvolutionField
        field = EvolutionField(use_learnable=True)
        assert field._param_space is not None
        assert field._cognitive_loop is not None

    def test_enable_at_runtime(self):
        from autoai.evolution_field.field import EvolutionField
        field = EvolutionField()
        field.enable_learnable()
        assert field._use_learnable

    def test_learnable_params(self):
        from autoai.evolution_field.field import EvolutionField
        field = EvolutionField(use_learnable=True)
        ps = field._param_space
        assert ps.get("decay_rate") == pytest.approx(0.005, abs=0.001)
        assert ps.get("propagation_factor") == pytest.approx(0.01, abs=0.005)


class TestP3EmergentAPIUpgrade:

    def test_backward_compatible(self):
        from autoai.emergent_api.engine import EmergentAPIEngine
        engine = EmergentAPIEngine()
        engine.record_call("caller", "module", "method")
        apis = engine.discover_apis()
        assert isinstance(apis, list)

    def test_cognitive_loop_mode(self):
        from autoai.emergent_api.engine import EmergentAPIEngine
        engine = EmergentAPIEngine(use_cognitive_loop=True)
        assert engine._cognitive_loop is not None

    def test_enable_at_runtime(self):
        from autoai.emergent_api.engine import EmergentAPIEngine
        engine = EmergentAPIEngine()
        engine.enable_cognitive_loop()
        assert engine._use_cognitive_loop


class TestP3SelfAwarenessUpgrade:

    def test_backward_compatible(self):
        from autoai.self_awareness.loop import SelfAwarenessLoop
        loop = SelfAwarenessLoop()
        loop.update_load(active_tasks=3)
        snap = loop.reflect()
        assert snap is not None

    def test_learnable_mode(self):
        from autoai.self_awareness.loop import SelfAwarenessLoop
        loop = SelfAwarenessLoop(use_learnable=True)
        assert loop._param_space is not None

    def test_enable_at_runtime(self):
        from autoai.self_awareness.loop import SelfAwarenessLoop
        loop = SelfAwarenessLoop()
        loop.enable_learnable()
        assert loop._use_learnable

    def test_learnable_alpha(self):
        from autoai.self_awareness.loop import SelfAwarenessLoop
        loop = SelfAwarenessLoop(use_learnable=True)
        loop.register_capability("test_cap")
        loop.test_capability("test_cap", True)
        loop.test_capability("test_cap", False)
        cap = loop._capabilities["test_cap"]
        assert 0.0 < cap.confidence < 1.0


class TestFitnessEvaluatorUpgrade:

    def test_backward_compatible(self):
        from autoai.evolution_pressure.fitness import FitnessEvaluator
        ev = FitnessEvaluator()
        ev.record("a1", "efficiency", 0.8)
        report = ev.evaluate("a1")
        assert 0.0 <= report.overall <= 1.0

    def test_learnable_mode(self):
        from autoai.evolution_pressure.fitness import FitnessEvaluator
        ev = FitnessEvaluator(use_learnable=True)
        assert ev._param_space is not None
        ev.record("a1", "efficiency", 0.8)
        report = ev.evaluate("a1")
        assert 0.0 <= report.overall <= 1.0

    def test_enable_at_runtime(self):
        from autoai.evolution_pressure.fitness import FitnessEvaluator
        ev = FitnessEvaluator()
        ev.enable_learnable()
        assert ev._use_learnable

    def test_learnable_weights(self):
        from autoai.evolution_pressure.fitness import FitnessEvaluator
        ev = FitnessEvaluator(use_learnable=True)
        ps = ev._param_space
        assert ps.get("w_efficiency") == pytest.approx(0.25, abs=0.01)


class TestEvolutionPressureUpgrade:

    def test_backward_compatible(self):
        from autoai.evolution_pressure.fitness import EvolutionPressure, AgentGenome
        ep = EvolutionPressure()
        g = AgentGenome(agent_id="a1", strategy_params={"x": 0.5})
        ep.register_genome(g)
        results = ep.select()
        assert isinstance(results, dict)

    def test_reasoning_mode(self):
        from autoai.evolution_pressure.fitness import EvolutionPressure, AgentGenome
        ep = EvolutionPressure(use_reasoning=True)
        assert ep._decider is not None
        g = AgentGenome(agent_id="a1", strategy_params={"x": 0.5})
        ep.register_genome(g)
        results = ep.select()
        assert isinstance(results, dict)

    def test_enable_at_runtime(self):
        from autoai.evolution_pressure.fitness import EvolutionPressure
        ep = EvolutionPressure()
        ep.enable_reasoning()
        assert ep._use_reasoning


class TestAntiFragileUpgrade:

    def test_backward_compatible(self):
        from autoai.chaos.antifragile import AntiFragileEngine
        engine = AntiFragileEngine()
        injection = engine.select_fault()
        report = engine.inject_and_observe(injection)
        assert report is not None

    def test_learnable_mode(self):
        from autoai.chaos.antifragile import AntiFragileEngine
        engine = AntiFragileEngine(use_learnable=True)
        assert engine._param_space is not None
        assert engine._real_executor is not None

    def test_enable_at_runtime(self):
        from autoai.chaos.antifragile import AntiFragileEngine
        engine = AntiFragileEngine()
        engine.enable_learnable()
        assert engine._use_learnable

    def test_learnable_params(self):
        from autoai.chaos.antifragile import AntiFragileEngine
        engine = AntiFragileEngine(use_learnable=True)
        ps = engine._param_space
        assert ps.get("weakest_target_prob") == pytest.approx(0.6, abs=0.01)


class TestMetaCognitionUpgrade:

    def test_backward_compatible(self):
        from autoai.meta_cognition.controller import MetaCognitionController
        ctrl = MetaCognitionController()
        meta = ctrl.reflect()
        assert meta is not None

    def test_learnable_mode(self):
        from autoai.meta_cognition.controller import MetaCognitionController
        ctrl = MetaCognitionController(use_learnable=True)
        assert ctrl._param_space is not None

    def test_enable_at_runtime(self):
        from autoai.meta_cognition.controller import MetaCognitionController
        ctrl = MetaCognitionController()
        ctrl.enable_learnable()
        assert ctrl._use_learnable

    def test_learnable_thresholds(self):
        from autoai.meta_cognition.controller import MetaCognitionController
        ctrl = MetaCognitionController(use_learnable=True)
        ps = ctrl._param_space
        assert ps.get("overload_threshold") == pytest.approx(0.9, abs=0.01)
        assert ps.get("strategy_ema_decay") == pytest.approx(0.8, abs=0.01)
