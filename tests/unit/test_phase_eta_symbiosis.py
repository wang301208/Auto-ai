"""Phase eta: 共生能力测试 - 全息集成/时间感知/资源经济/自适应架构/量子决策"""
from __future__ import annotations

import time
import pytest

from autoai.holistic import HoloAgent, HoloStatus
from autoai.temporal import TemporalEngine, TemporalEvent, Deadline, UrgencyCurve
from autoai.resource_economics import ResourceMarket, Resource, Bid, Allocation
from autoai.adaptive_arch import AdaptiveArchitecture, Component, Topology
from autoai.quantum_decision import QuantumDecider, DecisionPath, Superposition


# === 全息集成 ===

class TestHoloAgent:
    def test_initialize(self):
        agent = HoloAgent(agent_id="test-holo")
        status = agent.initialize()
        assert status.initialized
        assert status.module_count >= 10

    def test_think(self):
        agent = HoloAgent(agent_id="test-think")
        agent.initialize()
        result = agent.think("analyze code")
        assert "content" in result

    def test_act(self):
        agent = HoloAgent(agent_id="test-act")
        agent.initialize()
        result = agent.act("read_file")
        assert "action" in result
        assert "allowed" in result

    def test_evolve(self):
        agent = HoloAgent(agent_id="test-evolve")
        agent.initialize()
        result = agent.evolve()
        assert isinstance(result, dict)

    def test_full_status(self):
        agent = HoloAgent(agent_id="test-status")
        agent.initialize()
        status = agent.get_full_status()
        assert "agent_id" in status
        assert "initialized" in status

    def test_module_access(self):
        agent = HoloAgent(agent_id="test-mod")
        agent.initialize()
        assert agent.goals is not None
        assert agent.awareness is not None
        assert agent.values is not None

    def test_alias_access(self):
        agent = HoloAgent(agent_id="test-alias")
        agent.initialize()
        assert agent.memory is not None or agent.layered_memory is not None

    def test_double_init(self):
        agent = HoloAgent(agent_id="test-dbl")
        s1 = agent.initialize()
        s2 = agent.initialize()
        assert s1.timestamp == s2.timestamp


# === 时间感知 ===

class TestTemporal:
    def test_event_recording(self):
        te = TemporalEngine()
        event = te.record_event()
        assert event.event_id.startswith("te-")

    def test_temporal_ordering(self):
        te = TemporalEngine()
        e1 = te.record_event(timestamp=100.0)
        e2 = te.record_event(timestamp=200.0)
        assert e1.is_before(e2)

    def test_event_overlap(self):
        e1 = TemporalEvent(event_id="a", timestamp=100.0, duration=150.0)
        e2 = TemporalEvent(event_id="b", timestamp=150.0, duration=50.0)
        assert e1.overlaps(e2)

    def test_deadline_urgency(self):
        te = TemporalEngine()
        dl = te.add_deadline("task1", deadline_time=time.time() + 10)
        assert dl.urgency > 0

    def test_expired_deadline(self):
        te = TemporalEngine()
        dl = te.add_deadline("task1", deadline_time=time.time() - 1)
        assert dl.is_expired
        assert dl.penalty > 0

    def test_prioritize_by_deadline(self):
        te = TemporalEngine()
        te.add_deadline("urgent", deadline_time=time.time() + 10)
        te.add_deadline("relaxed", deadline_time=time.time() + 3600)
        ranked = te.prioritize_by_deadline()
        assert len(ranked) == 2
        assert ranked[0][0] == "urgent"

    def test_forecast(self):
        te = TemporalEngine()
        te.record_event(timestamp=time.time() + 100)
        forecast = te.forecast(horizon_seconds=3600)
        assert len(forecast) >= 1

    def test_urgency_curve(self):
        uc = UrgencyCurve()
        u1 = uc.urgency_at(0)
        u2 = uc.urgency_at(3600)
        assert u1 > u2

    def test_conflict_detection(self):
        te = TemporalEngine()
        te.record_event(timestamp=100.0, duration=200.0)
        te.record_event(timestamp=150.0, duration=100.0)
        conflicts = te.detect_temporal_conflicts()
        assert len(conflicts) >= 1


# === 资源经济 ===

class TestResourceEconomics:
    def test_resource_scarcity(self):
        r = Resource(resource_type=Resource.TOKENS if hasattr(Resource, 'TOKENS') else __import__("autoai.resource_economics.market", fromlist=["ResourceType"]).ResourceType.TOKENS, total_supply=100, allocated=80)
        assert r.scarcity == pytest.approx(0.8)

    def test_allocate_and_release(self):
        from autoai.resource_economics.market import ResourceType
        market = ResourceMarket()
        bid = Bid(bidder="task1", resource_type=ResourceType.TOKENS, amount=50, max_price=10)
        alloc = market.submit_bid(bid)
        assert alloc.success
        market.release("task1", ResourceType.TOKENS, 50)

    def test_price_dynamics(self):
        from autoai.resource_economics.market import ResourceType
        r = Resource(resource_type=ResourceType.TOKENS, total_supply=100)
        for _ in range(9):
            r.allocate(10)
        assert r.price > 1.0

    def test_budget_constraint(self):
        from autoai.resource_economics.market import ResourceType
        market = ResourceMarket()
        market.set_budget("poor_task", budget=5)
        bid = Bid(bidder="poor_task", resource_type=ResourceType.TOKENS, amount=100, max_price=1)
        alloc = market.submit_bid(bid)
        assert alloc.amount <= 5

    def test_market_status(self):
        market = ResourceMarket()
        status = market.get_market_status()
        assert "tokens" in status


# === 自适应架构 ===

class TestAdaptiveArchitecture:
    def test_register_and_load(self):
        arch = AdaptiveArchitecture(memory_limit_mb=512)
        arch.register_component("memory", priority=0.8, memory_mb=50)
        assert arch.load("memory")

    def test_unload_non_critical(self):
        arch = AdaptiveArchitecture(memory_limit_mb=512)
        arch.register_component("optional", priority=0.3, memory_mb=50)
        arch.load("optional")
        assert arch.unload("optional")

    def test_cannot_unload_critical(self):
        arch = AdaptiveArchitecture(memory_limit_mb=512)
        arch.register_component("core", priority=0.9, memory_mb=50)
        arch.load("core")
        assert not arch.unload("core")

    def test_memory_pressure_unload(self):
        arch = AdaptiveArchitecture(memory_limit_mb=100)
        arch.register_component("low_pri", priority=0.2, memory_mb=60)
        arch.register_component("high_pri", priority=0.8, memory_mb=60)
        arch.load("low_pri")
        assert arch.load("high_pri")

    def test_graceful_degrade(self):
        arch = AdaptiveArchitecture(memory_limit_mb=512)
        arch.register_component("opt1", priority=0.3, memory_mb=50)
        arch.register_component("opt2", priority=0.6, memory_mb=50)
        arch.load("opt1")
        arch.load("opt2")
        unloaded = arch.degrade()
        assert len(unloaded) >= 1

    def test_topology(self):
        topo = Topology()
        topo.connect("A", "B")
        topo.connect("A", "C")
        assert topo.get_downstream("A") == ["B", "C"]
        assert "A" in topo.get_upstream("B")


# === 量子决策 ===

class TestQuantumDecision:
    def test_superposition_creation(self):
        qd = QuantumDecider()
        sp = qd.create_superposition([
            {"action": "A", "expected_value": 0.8},
            {"action": "B", "expected_value": 0.5},
        ])
        assert len(sp.paths) == 2
        assert sp.is_normalized

    def test_collapse(self):
        qd = QuantumDecider()
        result = qd.decide([
            {"action": "go_left", "expected_value": 0.6, "risk": 0.3},
            {"action": "go_right", "expected_value": 0.5, "risk": 0.2},
        ])
        assert result is not None
        assert result.state.value == "collapsed"

    def test_interference(self):
        sp = Superposition(paths=[
            DecisionPath(action="A", amplitude=0.7, phase=0.0),
            DecisionPath(action="B", amplitude=0.7, phase=0.1),
        ])
        sp.normalize()
        sp.interfere()
        assert sp.is_normalized

    def test_ev_risk_analysis(self):
        qd = QuantumDecider()
        results = qd.evaluate_ev_risk([
            {"action": "safe", "expected_value": 0.5, "risk": 0.1},
            {"action": "risky", "expected_value": 0.3, "risk": 0.7},
        ])
        assert results[0]["action"] == "safe"

    def test_path_probability(self):
        dp = DecisionPath(action="test", amplitude=0.5)
        assert dp.probability == pytest.approx(0.25)

    def test_entanglement(self):
        qd = QuantumDecider()
        qd.apply_entanglement("speed", "cost", 0.5)
        assert len(qd._entanglements) == 1
