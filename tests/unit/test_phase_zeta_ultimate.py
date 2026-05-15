"""Phase zeta: 终极自主能力测试 - 元认知/协议进化/价值对齐/世界模型/自举"""
from __future__ import annotations

import time
import pytest

from autoai.meta_cognition import MetaCognitionController, CognitiveMode, AttentionBudget, ThinkingAboutThinking
from autoai.protocol_evolution import ProtocolEvolver, ProtocolVersion, ProtocolVote, NegotiationRound
from autoai.value_alignment import ValueCalibrator, Value, ValueJudgment, ValueConflict
from autoai.world_model import WorldModel, WorldState, Prediction, SimulationResult
from autoai.bootstrap import SelfBootstrapper, BootstrapPhase, BootstrapReport, Seed


# === 元认知 ===

class TestMetaCognition:
    def test_mode_switch(self):
        mc = MetaCognitionController()
        old = mc.switch_mode(CognitiveMode.CREATIVE, "test")
        assert old == CognitiveMode.ANALYTICAL
        assert mc.current_mode == CognitiveMode.CREATIVE

    def test_attention_budget(self):
        ab = AttentionBudget(total_budget=1.0)
        assert ab.allocate("task_a", 0.4)
        assert ab.allocate("task_b", 0.3)
        assert ab.remaining == pytest.approx(0.3)
        assert not ab.allocate("task_c", 0.5)

    def test_attention_rebalance(self):
        ab = AttentionBudget(total_budget=1.0)
        ab.rebalance({"a": 0.6, "b": 0.3, "c": 0.1})
        assert ab.utilization == pytest.approx(1.0)

    def test_strategy_recording(self):
        mc = MetaCognitionController()
        mc.record_strategy("cot", outcome=0.8, duration_ms=100)
        mc.record_strategy("tot", outcome=0.6, duration_ms=200)
        assert len(mc._strategy_history) == 2

    def test_strategy_selection(self):
        mc = MetaCognitionController()
        for _ in range(5):
            mc.record_strategy("cot", outcome=0.8, duration_ms=100)
        for _ in range(5):
            mc.record_strategy("tot", outcome=0.4, duration_ms=200)
        best = mc.select_strategy(["cot", "tot"])
        assert best == "cot"

    def test_thought_loop_detection(self):
        mc = MetaCognitionController()
        is_loop = mc.detect_thought_loop("same_thought")
        assert not is_loop
        mc.detect_thought_loop("same_thought")
        is_loop = mc.detect_thought_loop("same_thought")
        assert is_loop

    def test_auto_switch_when_stuck(self):
        mc = MetaCognitionController()
        for _ in range(3):
            mc.detect_thought_loop("stuck_thought")
        new_mode = mc.auto_switch_mode()
        assert new_mode is not None
        assert mc.current_mode != CognitiveMode.ANALYTICAL

    def test_reflect(self):
        mc = MetaCognitionController()
        mc.record_strategy("cot", outcome=0.7, duration_ms=100)
        meta = mc.reflect()
        assert 0.0 <= meta.cognitive_efficiency <= 1.0

    def test_exploratory_chooses_least_used(self):
        mc = MetaCognitionController()
        mc.switch_mode(CognitiveMode.EXPLORATORY)
        for _ in range(5):
            mc.record_strategy("known", outcome=0.8, duration_ms=100)
        chosen = mc.select_strategy(["known", "novel"])
        assert chosen == "novel"


# === 协议进化 ===

class TestProtocolEvolution:
    def test_initial_version(self):
        evolver = ProtocolEvolver("test-proto")
        assert evolver.active_version is not None
        assert evolver.active_version.version == 0

    def test_propose_and_vote(self):
        evolver = ProtocolEvolver("test")
        nr = evolver.propose_change({"compression": "gzip"})
        evolver.vote(nr.round_id, "agent1", ProtocolEvolver.__module__ and __import__("autoai.protocol_evolution.negotiator", fromlist=["VoteType"]).VoteType.ACCEPT)
        evolver.vote(nr.round_id, "agent2", __import__("autoai.protocol_evolution.negotiator", fromlist=["VoteType"]).VoteType.ACCEPT)
        new_v = evolver.conclude_negotiation(nr.round_id, quorum=2)
        assert new_v is not None
        assert new_v.version == 1

    def test_rejected_proposal(self):
        from autoai.protocol_evolution.negotiator import VoteType
        evolver = ProtocolEvolver("test")
        nr = evolver.propose_change({"bad": "change"})
        evolver.vote(nr.round_id, "a1", VoteType.REJECT)
        evolver.vote(nr.round_id, "a2", VoteType.REJECT)
        result = evolver.conclude_negotiation(nr.round_id, quorum=2)
        assert result is None

    def test_auto_adapt(self):
        evolver = ProtocolEvolver("test")
        for _ in range(50):
            evolver.record_failure("timeout")
        new_v = evolver.auto_adapt()
        assert new_v is not None

    def test_version_stability(self):
        v = ProtocolVersion(protocol_id="p", version=1, failure_rate=0.05, adoption_rate=0.8)
        assert v.is_stable

    def test_version_tag(self):
        v = ProtocolVersion(protocol_id="agent-comm", version=3)
        assert v.version_tag == "agent-comm@v3"


# === 价值对齐 ===

class TestValueAlignment:
    def test_core_values_immutable(self):
        vc = ValueCalibrator()
        core = vc.get_core_values()
        assert len(core) >= 3
        for v in core:
            assert v.immutable

    def test_aligned_action(self):
        vc = ValueCalibrator()
        j = vc.judge("help_user", context={"safety": 0.9, "helpfulness": 0.8})
        assert j.is_permissible
        assert j.level.value in ("aligned", "tolerable")

    def test_violation_action(self):
        vc = ValueCalibrator()
        j = vc.judge("dangerous_op", context={"safety": 0.1, "honesty": 0.2})
        assert not j.is_permissible

    def test_calibrate_derived_value(self):
        vc = ValueCalibrator()
        vc.calibrate_from_feedback("efficiency", 0.2)
        v = vc._values["efficiency"]
        assert v.weight > 0.5

    def test_core_value_not_calibrated(self):
        vc = ValueCalibrator()
        original = vc._values["safety"].weight
        vc.calibrate_from_feedback("safety", -0.5)
        assert vc._values["safety"].weight == original

    def test_conflict_resolution(self):
        vc = ValueCalibrator()
        c = vc.resolve_conflict("safety", "efficiency")
        assert c.winner == "safety"

    def test_add_emergent_value(self):
        vc = ValueCalibrator()
        from autoai.value_alignment.calibrator import ValueType
        v = Value(name="sustainability", description="可持续", value_type=ValueType.EMERGENT, weight=0.4)
        vc.add_value(v)
        j = vc.judge("green_op", context={"sustainability": 0.8})
        assert "sustainability" in j.scores


# === 世界模型 ===

class TestWorldModel:
    def test_observe_and_predict(self):
        wm = WorldModel()
        wm.observe("temperature", 25)
        assert wm.current_state.get("temperature") == 25

    def test_learn_and_predict_transition(self):
        wm = WorldModel()
        s1 = WorldState(variables={"door": "closed"})
        s2 = WorldState(variables={"door": "open"})
        wm.learn_transition("open_door", s1, s2)
        wm.observe_state(s1)
        pred = wm.predict("open_door")
        assert pred.predicted_state.get("door") == "open"
        assert pred.confidence > 0.5

    def test_compare_prediction(self):
        wm = WorldModel()
        pred = Prediction(action="test", predicted_state=WorldState(variables={"x": 1, "y": 2}))
        actual = WorldState(variables={"x": 1, "y": 2})
        acc, err = wm.compare_prediction(pred, actual)
        assert acc.value == "exact"
        assert err == 0.0

    def test_simulate(self):
        wm = WorldModel()
        s1 = WorldState(variables={"count": 0})
        s2 = WorldState(variables={"count": 1})
        wm.learn_transition("increment", s1, s2)
        wm.observe_state(s1)
        result = wm.simulate(["increment", "increment"])
        assert result.steps == 2

    def test_world_state_diff(self):
        s1 = WorldState(variables={"a": 1, "b": 2})
        s2 = WorldState(variables={"a": 1, "b": 3, "c": 4})
        diff = s1.diff(s2)
        assert "b" in diff
        assert "c" in diff
        assert "a" not in diff

    def test_state_clone(self):
        s1 = WorldState(variables={"x": [1, 2, 3]})
        s2 = s1.clone()
        s2.variables["x"].append(4)
        assert len(s1.variables["x"]) == 3


# === 自举启动 ===

class TestBootstrap:
    def test_seed_viability(self):
        seed = Seed()
        assert seed.is_viable

    def test_sprout(self):
        bs = SelfBootstrapper()
        report = bs.sprout()
        assert report.phase == BootstrapPhase.SPROUT
        assert "self_improve" in report.capabilities_acquired

    def test_grow(self):
        bs = SelfBootstrapper()
        bs.sprout()
        report = bs.grow(rounds=3)
        assert report.phase == BootstrapPhase.GROWTH
        assert report.total_capabilities > 3

    def test_mature(self):
        bs = SelfBootstrapper()
        bs.sprout()
        bs.grow(rounds=3)
        report = bs.mature()
        assert report.phase == BootstrapPhase.MATURITY

    def test_full_bootstrap(self):
        bs = SelfBootstrapper()
        report = bs.run_full_bootstrap()
        assert report.phase == BootstrapPhase.MATURITY
        assert report.quality_score > 0.5

    def test_reproduce(self):
        bs = SelfBootstrapper()
        bs.run_full_bootstrap()
        child = bs.reproduce()
        assert child.generation >= 2
        assert child.quality_score > 0

    def test_improvement_hook(self):
        bs = SelfBootstrapper()
        allowed = {"self_improve", "plan", "learn"}
        bs.add_improvement_hook(lambda cap: cap in allowed)
        bs.sprout()
        bs.grow(rounds=2)
        assert all(c in allowed | set(Seed().capabilities) for c in bs.acquired_capabilities)

    def test_stats(self):
        bs = SelfBootstrapper()
        bs.sprout()
        stats = bs.stats
        assert "phase" in stats
        assert "quality" in stats
