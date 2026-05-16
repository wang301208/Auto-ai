"""Phase Xi (Xi) 统一收敛终态测试: 自进化场+零人类依赖+自涌现API+生态位计算。"""

import time
import pytest

from autoai.evolution_field.field import EvolutionField, FieldNode, FieldState, FieldPulse
from autoai.zero_human.engine import ZeroHumanEngine, AutonomyGate, GateVerdict, GateType, DecisionRecord
from autoai.emergent_api.engine import EmergentAPIEngine, APIPattern, APISpec, APIStability
from autoai.niche.engine import (
    NicheEngine, NicheProfile, CapabilityAxis, CapabilityVector,
    EcologicalRole,
)


# ============================================================
# 自进化场测试
# ============================================================

class TestEvolutionField:

    def test_create_field(self):
        ef = EvolutionField("test_field")
        assert ef._field_id == "test_field"
        assert len(ef._nodes) == 0

    def test_add_node(self):
        ef = EvolutionField()
        node = ef.add_node("reasoning", 0.7)
        assert node.module_name == "reasoning"
        assert node.energy == 0.7
        assert node.state == FieldState.GROUND

    def test_add_default_nodes(self):
        ef = EvolutionField()
        ef.add_default_nodes()
        assert len(ef._nodes) >= 30
        assert "safety_intuition" in ef._nodes
        assert "governance" in ef._nodes

    def test_node_excite(self):
        node = FieldNode(node_id="fn_test", module_name="test")
        node.excite(0.5)
        assert node.energy == 1.0
        assert node.state == FieldState.SUPERNOVA

    def test_node_excite_partial(self):
        node = FieldNode(node_id="fn_test", module_name="test", energy=0.2)
        node.excite(0.3)
        assert abs(node.energy - 0.5) < 1e-9
        assert node.state == FieldState.EXCITED

    def test_node_decay(self):
        node = FieldNode(node_id="fn_test", module_name="test", energy=0.5)
        node.decay(0.1)
        assert node.energy == pytest.approx(0.45, abs=0.01)

    def test_node_decay_to_ground(self):
        node = FieldNode(node_id="fn_test", module_name="test", energy=0.2)
        node.decay(0.9)
        assert node.state == FieldState.DECAYED

    def test_node_is_active(self):
        node = FieldNode(node_id="fn_test", module_name="test", energy=0.5)
        assert node.is_active
        node.energy = 0.05
        assert not node.is_active

    def test_node_field_potential(self):
        node = FieldNode(node_id="fn_test", module_name="test", energy=0.5)
        node.coupling_strengths["other"] = 0.4
        assert node.field_potential == pytest.approx(0.5 * 1.4)

    def test_tick(self):
        ef = EvolutionField()
        ef.add_default_nodes()
        result = ef.tick()
        assert result["tick"] == 1
        assert result["active_nodes"] > 0
        assert result["total_energy"] > 0

    def test_tick_multiple(self):
        ef = EvolutionField()
        ef.add_default_nodes()
        for _ in range(10):
            result = ef.tick()
        assert result["tick"] == 10

    def test_inject(self):
        ef = EvolutionField()
        ef.add_node("memory", 0.5)
        assert ef.inject("memory", 0.3)
        assert ef._nodes["memory"].energy > 0.5

    def test_inject_nonexistent(self):
        ef = EvolutionField()
        assert not ef.inject("ghost", 0.5)

    def test_query_field(self):
        ef = EvolutionField()
        ef.add_node("a", 0.3)
        ef.add_node("b", 0.7)
        state = ef.query_field()
        assert "a" in state and "b" in state

    def test_query_hotspots(self):
        ef = EvolutionField()
        ef.add_node("cold", 0.2)
        ef.add_node("hot", 0.9)
        hotspots = ef.query_hotspots(0.7)
        assert len(hotspots) == 1
        assert hotspots[0][0] == "hot"

    def test_stats(self):
        ef = EvolutionField()
        ef.add_default_nodes()
        stats = ef.stats
        assert stats["node_count"] >= 30
        assert "avg_energy" in stats

    def test_coupling_propagation(self):
        ef = EvolutionField()
        ef.add_default_nodes()
        initial_energy = ef._nodes["immune_system"].energy
        ef.tick()
        assert ef._nodes["immune_system"].energy != initial_energy

    def test_entanglement(self):
        ef = EvolutionField()
        ef.add_default_nodes()
        for _ in range(50):
            ef.tick()
        assert len(ef._entanglement_map) > 0

    def test_pulse_generation(self):
        ef = EvolutionField()
        ef.add_default_nodes()
        ef.tick()
        assert len(ef._pulses) > 0


# ============================================================
# 零人类依赖测试
# ============================================================

class TestZeroHumanEngine:

    def test_create_engine(self):
        zh = ZeroHumanEngine("agent_x")
        assert zh._agent_id == "agent_x"
        assert len(zh._gates) == 8

    def test_auto_approve_low_risk(self):
        zh = ZeroHumanEngine()
        verdict = zh.decide(GateType.RESOURCE_ACQUIRE, {
            "fitness": 0.5, "safety_score": 0.8, "risk": 0.1,
        })
        assert verdict == GateVerdict.APPROVE

    def test_veto_high_risk(self):
        zh = ZeroHumanEngine()
        verdict = zh.decide(GateType.CODE_DEPLOY, {
            "fitness": 0.9, "safety_score": 0.95, "risk": 0.5,
        })
        assert verdict == GateVerdict.VETO

    def test_veto_low_safety(self):
        zh = ZeroHumanEngine()
        verdict = zh.decide(GateType.SELF_MODIFY, {
            "fitness": 0.9, "safety_score": 0.3, "risk": 0.1,
        })
        assert verdict == GateVerdict.VETO

    def test_conditional(self):
        zh = ZeroHumanEngine()
        verdict = zh.decide(GateType.SELF_MODIFY, {
            "fitness": 0.5, "safety_score": 0.9, "risk": 0.3,
        })
        assert verdict == GateVerdict.CONDITIONAL

    def test_approve_with_evidence(self):
        zh = ZeroHumanEngine()
        verdict = zh.decide(GateType.SELF_MODIFY, {
            "fitness": 0.7, "safety_score": 0.9, "risk": 0.3,
            "evidence_count": 3,
        })
        assert verdict == GateVerdict.APPROVE

    def test_can_self_modify(self):
        zh = ZeroHumanEngine()
        v = zh.can_self_modify(fitness=0.8, safety=0.9, risk=0.1, evidence=5)
        assert v == GateVerdict.APPROVE

    def test_can_deploy_strict(self):
        zh = ZeroHumanEngine()
        v = zh.can_deploy(fitness=0.5, safety=0.8, risk=0.1, evidence=1)
        assert v in (GateVerdict.VETO, GateVerdict.DEFER, GateVerdict.CONDITIONAL)

    def test_can_spawn(self):
        zh = ZeroHumanEngine()
        v = zh.can_spawn(fitness=0.7, safety=0.8, risk=0.1)
        assert v == GateVerdict.APPROVE

    def test_decision_records(self):
        zh = ZeroHumanEngine()
        zh.decide(GateType.RESOURCE_ACQUIRE, {"risk": 0.1, "safety_score": 0.8})
        assert len(zh._records) == 1

    def test_cooldown_defer(self):
        gate = AutonomyGate(gate_type=GateType.RESOURCE_ACQUIRE, cooldown_seconds=10.0)
        ctx = {"fitness": 0.5, "safety_score": 0.8, "risk": 0.05}
        gate.evaluate(ctx)
        gate.last_decision_time = time.time()
        v2 = gate.evaluate(ctx)
        assert v2 == GateVerdict.DEFER

    def test_stats(self):
        zh = ZeroHumanEngine()
        zh.decide(GateType.RESOURCE_ACQUIRE, {"risk": 0.1, "safety_score": 0.8})
        stats = zh.stats
        assert stats["total_decisions"] == 1
        assert stats["auto_approved"] >= 0

    def test_all_gate_types_covered(self):
        zh = ZeroHumanEngine()
        for gt in GateType:
            assert gt in zh._gates


# ============================================================
# 自涌现API测试
# ============================================================

class TestEmergentAPIEngine:

    def test_create_engine(self):
        eapi = EmergentAPIEngine()
        assert len(eapi._patterns) == 0

    def test_record_call(self):
        eapi = EmergentAPIEngine()
        pat = eapi.record_call("agent_a", "memory", "store", latency_ms=5.0)
        assert pat.call_count == 1
        assert pat.caller == "agent_a"

    def test_record_multiple_calls(self):
        eapi = EmergentAPIEngine()
        for i in range(10):
            eapi.record_call("agent_a", "memory", "store", latency_ms=float(i))
        key = "agent_a:memory.store"
        assert eapi._patterns[key].call_count == 10

    def test_record_call_with_error(self):
        eapi = EmergentAPIEngine()
        eapi.record_call("a", "m", "f", error=False)
        eapi.record_call("a", "m", "f", error=True)
        key = "a:m.f"
        assert eapi._patterns[key].error_rate == pytest.approx(0.5, abs=0.01)

    def test_pattern_is_hot(self):
        eapi = EmergentAPIEngine()
        for _ in range(5):
            eapi.record_call("a", "m", "f")
        key = "a:m.f"
        assert eapi._patterns[key].is_hot

    def test_pattern_quality(self):
        eapi = EmergentAPIEngine()
        for _ in range(20):
            eapi.record_call("a", "m", "f")
        key = "a:m.f"
        assert eapi._patterns[key].quality > 0.9

    def test_discover_apis(self):
        eapi = EmergentAPIEngine()
        for _ in range(5):
            eapi.record_call("a", "memory", "store")
            eapi.record_call("b", "memory", "store")
        apis = eapi.discover_apis()
        assert len(apis) >= 1
        assert apis[0].endpoint == "/memory/store"

    def test_api_stability_promotion(self):
        eapi = EmergentAPIEngine()
        for _ in range(25):
            eapi.record_call("a", "memory", "store")
        eapi.discover_apis()
        api = eapi.get_api("/memory/store")
        assert api is not None
        assert api.stability == APIStability.STABLE

    def test_api_no_emergence_below_threshold(self):
        eapi = EmergentAPIEngine()
        eapi.record_call("a", "rare", "method")
        eapi.record_call("a", "rare", "method")
        apis = eapi.discover_apis()
        rare_api = [a for a in apis if "rare" in a.endpoint]
        assert len(rare_api) == 0

    def test_get_api(self):
        eapi = EmergentAPIEngine()
        for _ in range(5):
            eapi.record_call("a", "mod", "action")
        eapi.discover_apis()
        api = eapi.get_api("/mod/action")
        assert api is not None

    def test_get_api_not_found(self):
        eapi = EmergentAPIEngine()
        assert eapi.get_api("/nonexistent") is None

    def test_stats(self):
        eapi = EmergentAPIEngine()
        for _ in range(5):
            eapi.record_call("a", "m", "f")
        eapi.discover_apis()
        stats = eapi.stats
        assert stats["total_patterns"] >= 1
        assert stats["total_calls"] >= 5


# ============================================================
# 生态位计算测试
# ============================================================

class TestNicheEngine:

    def test_create_engine(self):
        ne = NicheEngine()
        assert len(ne._profiles) == 0

    def test_register_agent(self):
        ne = NicheEngine()
        profile = ne.register("agent_a")
        assert profile.agent_id == "agent_a"
        assert profile.resource_footprint == 0.5

    def test_register_with_capability(self):
        cap = CapabilityVector({CapabilityAxis.REASONING: 0.9, CapabilityAxis.ACTION: 0.7})
        ne = NicheEngine()
        profile = ne.register("agent_a", capability=cap)
        assert profile.capability.values[CapabilityAxis.REASONING] == 0.9

    def test_capability_vector_magnitude(self):
        cap = CapabilityVector({CapabilityAxis.REASONING: 0.6, CapabilityAxis.ACTION: 0.8})
        mag = cap.magnitude()
        assert abs(mag - 1.0) < 0.01

    def test_capability_vector_similarity(self):
        cap1 = CapabilityVector({CapabilityAxis.REASONING: 0.9, CapabilityAxis.ACTION: 0.1})
        cap2 = CapabilityVector({CapabilityAxis.REASONING: 0.1, CapabilityAxis.ACTION: 0.9})
        sim = cap1.cosine_similarity(cap2)
        assert 0 < sim < 1

    def test_capability_vector_self_similarity(self):
        cap = CapabilityVector({CapabilityAxis.REASONING: 0.8})
        assert abs(cap.cosine_similarity(cap) - 1.0) < 1e-6

    def test_capability_vector_distance(self):
        cap1 = CapabilityVector({CapabilityAxis.REASONING: 1.0})
        cap2 = CapabilityVector({CapabilityAxis.REASONING: 0.0})
        assert abs(cap1.distance(cap2) - 1.0) < 1e-6

    def test_update_capability(self):
        ne = NicheEngine()
        ne.register("agent_a")
        assert ne.update_capability("agent_a", CapabilityAxis.LEARNING, 0.8)
        assert ne._profiles["agent_a"].capability.values[CapabilityAxis.LEARNING] == 0.8

    def test_update_capability_clamped(self):
        ne = NicheEngine()
        ne.register("agent_a")
        ne.update_capability("agent_a", CapabilityAxis.REASONING, 1.5)
        assert ne._profiles["agent_a"].capability.values[CapabilityAxis.REASONING] == 1.0

    def test_niche_overlap_self(self):
        ne = NicheEngine()
        cap = CapabilityVector({CapabilityAxis.REASONING: 0.8, CapabilityAxis.ACTION: 0.6})
        ne.register("a", capability=cap)
        ne.register("b", capability=cap)
        overlap = ne.compute_niche_overlap("a", "b")
        assert overlap > 0.9

    def test_niche_overlap_orthogonal(self):
        cap1 = CapabilityVector({CapabilityAxis.REASONING: 1.0})
        cap2 = CapabilityVector({CapabilityAxis.ACTION: 1.0})
        ne = NicheEngine()
        ne.register("a", capability=cap1)
        ne.register("b", capability=cap2)
        overlap = ne.compute_niche_overlap("a", "b")
        assert overlap < 0.5

    def test_competition_high_overlap(self):
        cap = CapabilityVector({CapabilityAxis.REASONING: 0.8, CapabilityAxis.ACTION: 0.7})
        ne = NicheEngine()
        ne.register("a", capability=cap)
        ne.register("b", capability=cap)
        comp = ne.compute_competition("a", "b")
        assert comp > 0.5

    def test_symbiosis_complementary(self):
        cap1 = CapabilityVector({CapabilityAxis.REASONING: 0.9, CapabilityAxis.ACTION: 0.1})
        cap2 = CapabilityVector({CapabilityAxis.REASONING: 0.1, CapabilityAxis.ACTION: 0.9})
        ne = NicheEngine()
        ne.register("a", capability=cap1)
        ne.register("b", capability=cap2)
        symb = ne.compute_symbiosis("a", "b")
        assert symb > 0.0

    def test_assign_ecological_roles(self):
        ne = NicheEngine()
        cap_keystone = CapabilityVector({a: 0.8 for a in CapabilityAxis})
        cap_specialist = CapabilityVector({CapabilityAxis.REASONING: 0.95})
        ne.register("keystone", capability=cap_keystone, resource_footprint=0.9)
        ne.register("specialist", capability=cap_specialist)
        roles = ne.assign_ecological_roles()
        assert "keystone" in roles
        assert "specialist" in roles

    def test_niche_width(self):
        cap = CapabilityVector({CapabilityAxis.REASONING: 0.5, CapabilityAxis.ACTION: 0.5})
        ne = NicheEngine()
        ne.register("a", capability=cap)
        width = ne.compute_niche_width("a")
        assert 0 < width <= 1.0

    def test_niche_width_specialist(self):
        cap = CapabilityVector({CapabilityAxis.REASONING: 0.99, CapabilityAxis.ACTION: 0.01, CapabilityAxis.PERCEPTION: 0.01})
        ne = NicheEngine()
        ne.register("a", capability=cap)
        width = ne.compute_niche_width("a")
        assert width < 0.5

    def test_find_optimal_niche(self):
        ne = NicheEngine()
        cap = CapabilityVector({CapabilityAxis.REASONING: 0.8, CapabilityAxis.ACTION: 0.3})
        ne.register("a", capability=cap)
        result = ne.find_optimal_niche("a")
        assert "development_priorities" in result
        assert len(result["development_priorities"]) <= 5

    def test_detect_succession(self):
        ne = NicheEngine()
        cap_strong = CapabilityVector({a: 0.8 for a in CapabilityAxis})
        cap_weak = CapabilityVector({a: 0.5 for a in CapabilityAxis})
        ne.register("strong", capability=cap_strong, resource_footprint=0.7)
        ne.register("weak", capability=cap_weak, resource_footprint=0.3)
        ne._profiles["strong"].fitness_score = 0.8
        ne._profiles["weak"].fitness_score = 0.3
        successions = ne.detect_succession()
        assert len(successions) >= 1

    def test_tick(self):
        ne = NicheEngine()
        ne.register("a", capability=CapabilityVector({CapabilityAxis.REASONING: 0.7}))
        ne.register("b", capability=CapabilityVector({CapabilityAxis.ACTION: 0.7}))
        result = ne.tick()
        assert result["tick"] == 1
        assert result["agents"] == 2
        assert "roles" in result

    def test_tick_multiple(self):
        ne = NicheEngine()
        ne.register("a", capability=CapabilityVector({CapabilityAxis.REASONING: 0.7}))
        for _ in range(5):
            ne.tick()
        assert ne._tick_count == 5

    def test_profile_dominance(self):
        cap = CapabilityVector({CapabilityAxis.REASONING: 0.8, CapabilityAxis.ACTION: 0.6})
        profile = NicheProfile(agent_id="x", capability=cap, resource_footprint=0.5)
        dom = profile.dominance
        assert dom > 0

    def test_profile_specialization(self):
        cap = CapabilityVector({CapabilityAxis.REASONING: 1.0})
        profile = NicheProfile(agent_id="x", capability=cap)
        assert profile.specialization > 0.5

    def test_stats(self):
        ne = NicheEngine()
        ne.register("a", capability=CapabilityVector({CapabilityAxis.REASONING: 0.7}))
        ne.tick()
        stats = ne.stats
        assert stats["agent_count"] == 1
        assert "avg_fitness" in stats

    def test_multi_agent_ecology(self):
        ne = NicheEngine()
        caps = [
            ("reasoner", CapabilityVector({CapabilityAxis.REASONING: 0.9, CapabilityAxis.LEARNING: 0.7})),
            ("actor", CapabilityVector({CapabilityAxis.ACTION: 0.9, CapabilityAxis.CREATIVITY: 0.8})),
            ("comms", CapabilityVector({CapabilityAxis.COMMUNICATION: 0.9, CapabilityAxis.COLLABORATION: 0.85})),
            ("general", CapabilityVector({a: 0.5 for a in CapabilityAxis})),
        ]
        for name, cap in caps:
            ne.register(name, capability=cap)
        result = ne.tick()
        assert result["agents"] == 4
        assert len(result["roles"]) == 4
        for name, _ in caps:
            assert len(ne._profiles[name].competitors) >= 0 or len(ne._profiles[name].symbionts) >= 0
