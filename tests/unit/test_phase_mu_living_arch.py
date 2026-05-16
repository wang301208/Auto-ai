"""Phase mu: 活架构+身份流变+语义路由+永不停歇 测试。"""

import time
import pytest
from autoai.living_arch.engine import (
    LivingArchEngine, ModuleVitals, ModuleState, ModuleRole, ArchSnapshot, ArchMutation,
)
from autoai.identity.flux import (
    IdentityFlux, AgentIdentity, IdentityState, FusionResult, IdentityDelta,
)
from autoai.semantic_router.router import (
    SemanticRouter, CapabilityAd, RouteResult, AdStatus,
)
from autoai.forever_loop.loop import (
    ForeverLoop, CycleResult, CyclePhase, PhaseResult, LoopState,
)


# ======================================================================
# 活架构测试
# ======================================================================

class TestLivingArchEngine:
    def test_register_module(self):
        engine = LivingArchEngine("test")
        vitals = engine.register_module("test_mod", ModuleRole.COGNITIVE, 0.5, 20.0, 0.7)
        assert vitals.module_name == "test_mod"
        assert vitals.state == ModuleState.ACTIVE

    def test_register_default_modules(self):
        engine = LivingArchEngine("test")
        engine.register_default_modules()
        assert len(engine._modules) >= 30

    def test_rebalance_evict_low_importance(self):
        engine = LivingArchEngine("test")
        engine.register_module("important", ModuleRole.CORE, 0.3, 10.0, 0.9)
        low = engine.register_module("low_value", ModuleRole.EXPERIMENTAL, 0.1, 5.0, 0.1)
        low.access_frequency = 0.0
        low.last_access = time.time() - 86400 * 30
        mutations = engine.rebalance()
        assert low.state in (ModuleState.ACTIVE, ModuleState.DORMANT)

    def test_rebalance_core_always_active(self):
        engine = LivingArchEngine("test")
        core = engine.register_module("safety", ModuleRole.CORE, 0.3, 10.0, 0.9)
        core.state = ModuleState.DORMANT
        engine.rebalance()
        assert core.state == ModuleState.ACTIVE

    def test_rebalance_memory_pressure(self):
        engine = LivingArchEngine("test")
        engine._memory_budget_mb = 30.0
        for i in range(10):
            m = engine.register_module(f"mod_{i}", ModuleRole.EXPERIMENTAL, 0.5, 20.0, 0.1)
            m.access_frequency = 0.01
            m.last_access = time.time() - 86400 * 7
        mutations = engine.rebalance()
        active = sum(1 for m in engine._modules.values() if m.state == ModuleState.ACTIVE)
        assert active < 10

    def test_fuse_modules(self):
        engine = LivingArchEngine("test")
        engine.register_module("a", ModuleRole.COGNITIVE, 0.5, 10.0, 0.7)
        engine.register_module("b", ModuleRole.COGNITIVE, 0.5, 10.0, 0.7)
        mutation = engine.fuse_modules("a", "b", "ab_fused")
        assert mutation is not None
        assert engine._modules["a"].state == ModuleState.FUSED
        assert "ab_fused" in engine._modules

    def test_fuse_core_forbidden(self):
        engine = LivingArchEngine("test")
        engine.register_module("core_a", ModuleRole.CORE, 0.3, 10.0, 0.9)
        engine.register_module("b", ModuleRole.COGNITIVE, 0.5, 10.0, 0.7)
        result = engine.fuse_modules("core_a", "b", "fused")
        assert result is None

    def test_split_module(self):
        engine = LivingArchEngine("test")
        engine.register_module("big", ModuleRole.COGNITIVE, 1.0, 40.0, 0.7)
        mutations = engine.split_module("big", ["big_a", "big_b"])
        assert len(mutations) == 2
        assert "big_a" in engine._modules
        assert "big_b" in engine._modules

    def test_snapshot(self):
        engine = LivingArchEngine("test")
        engine.register_default_modules()
        snap = engine.snapshot()
        assert len(snap.active_modules) > 0
        assert snap.efficiency > 0

    def test_module_vitals(self):
        v = ModuleVitals(module_name="test", fitness_score=0.8, access_frequency=5.0)
        assert v.importance > 0.3
        assert v.should_exist

    def test_stats(self):
        engine = LivingArchEngine("test")
        engine.register_default_modules()
        engine.rebalance()
        s = engine.stats
        assert s["total_modules"] >= 30


# ======================================================================
# 身份流变测试
# ======================================================================

class TestIdentityFlux:
    def test_spawn(self):
        flux = IdentityFlux()
        identity = flux.spawn("agent_a", {"reasoning", "knowledge"})
        assert identity.is_alive
        assert identity.state == IdentityState.AWAKENING
        assert "reasoning" in identity.capabilities

    def test_evolve(self):
        flux = IdentityFlux()
        identity = flux.spawn("agent_a", {"reasoning"})
        delta = flux.evolve(identity.identity_id, new_capabilities={"reasoning", "analysis"}, new_fitness=0.9)
        assert delta is not None
        assert identity.fitness == 0.9
        assert "analysis" in identity.capabilities

    def test_evolve_to_mature(self):
        flux = IdentityFlux()
        identity = flux.spawn("agent_a", {"reasoning"})
        flux.evolve(identity.identity_id, new_fitness=0.85)
        assert identity.state == IdentityState.MATURE

    def test_evolve_to_transcendent(self):
        flux = IdentityFlux()
        identity = flux.spawn("agent_a", {"reasoning"})
        flux.evolve(identity.identity_id, new_fitness=0.85)
        assert identity.state == IdentityState.MATURE
        flux.evolve(identity.identity_id, new_fitness=0.96)
        assert identity.state == IdentityState.TRANSCENDENT

    def test_fuse(self):
        flux = IdentityFlux()
        a = flux.spawn("agent_a", {"reasoning", "analysis"})
        b = flux.spawn("agent_b", {"monitoring", "alerting"})
        result = flux.fuse(a.identity_id, b.identity_id)
        assert result is not None
        assert len(result.merged_capabilities) == 4
        assert not a.is_alive
        assert not b.is_alive

    def test_fuse_synergy(self):
        flux = IdentityFlux()
        a = flux.spawn("agent_a", {"reasoning", "analysis"})
        b = flux.spawn("agent_b", {"reasoning", "monitoring"})
        result = flux.fuse(a.identity_id, b.identity_id)
        assert result.redundancy_eliminated >= 1

    def test_dissolve(self):
        flux = IdentityFlux()
        identity = flux.spawn("temp_agent", {"cleanup"})
        dissolved = flux.dissolve(identity.identity_id)
        assert dissolved
        assert not identity.is_alive
        assert identity.state == IdentityState.DISSOLVED

    def test_dissolve_blocked_by_children(self):
        flux = IdentityFlux()
        a = flux.spawn("parent", {"reasoning"})
        b = flux.spawn("child", {"monitoring"})
        result = flux.fuse(a.identity_id, b.identity_id)
        c = flux.get_identity(result.super_id)
        dissolved = flux.dissolve(a.identity_id)
        assert not dissolved

    def test_fingerprint_changes(self):
        flux = IdentityFlux()
        identity = flux.spawn("agent", {"cap_a"})
        fp1 = identity.fingerprint()
        flux.evolve(identity.identity_id, new_capabilities={"cap_b"})
        fp2 = identity.fingerprint()
        assert fp1 != fp2

    def test_active_identities(self):
        flux = IdentityFlux()
        flux.spawn("a", {"reasoning"})
        flux.spawn("b", {"analysis"})
        assert len(flux.get_active_identities()) == 2

    def test_stats(self):
        flux = IdentityFlux()
        flux.spawn("a", {"reasoning"})
        flux.spawn("b", {"analysis"})
        s = flux.stats
        assert s["active"] == 2
        assert s["total_identities"] == 2


# ======================================================================
# 语义路由测试
# ======================================================================

class TestSemanticRouter:
    def test_advertise(self):
        router = SemanticRouter()
        ad = CapabilityAd("agent_a", "data_analysis", "数据分析能力", 0.8, 0.3, 50.0)
        router.advertise(ad)
        assert router.stats["active_ads"] == 1

    def test_route_exact(self):
        router = SemanticRouter()
        router.advertise(CapabilityAd("agent_a", "data_analysis", quality=0.9, cost=0.3))
        router.advertise(CapabilityAd("agent_b", "data_analysis", quality=0.7, cost=0.5))
        result = router.route("data_analysis")
        assert result.found
        assert result.best_agent == "agent_a"

    def test_route_with_constraints(self):
        router = SemanticRouter()
        router.advertise(CapabilityAd("cheap", "compute", quality=0.5, cost=0.1))
        router.advertise(CapabilityAd("expensive", "compute", quality=0.9, cost=1.0))
        result = router.route("compute", max_cost=0.5)
        assert result.found
        assert result.best_agent == "cheap"

    def test_route_semantic_fallback(self):
        router = SemanticRouter()
        router.advertise(CapabilityAd("agent_a", "data_analysis", quality=0.8))
        result = router.route("data_processing")
        assert result.found

    def test_revoke(self):
        router = SemanticRouter()
        router.advertise(CapabilityAd("agent_a", "compute", quality=0.8))
        count = router.revoke("agent_a", "compute")
        assert count == 1

    def test_discover_capabilities(self):
        router = SemanticRouter()
        router.advertise(CapabilityAd("a", "compute", quality=0.8))
        router.advertise(CapabilityAd("b", "storage", quality=0.7))
        caps = router.discover_capabilities()
        assert "compute" in caps
        assert "storage" in caps

    def test_agent_capabilities(self):
        router = SemanticRouter()
        router.advertise(CapabilityAd("a", "compute", quality=0.8))
        router.advertise(CapabilityAd("a", "storage", quality=0.7))
        caps = router.agent_capabilities("a")
        assert len(caps) == 2

    def test_expired_ads(self):
        router = SemanticRouter()
        ad = CapabilityAd("a", "compute", quality=0.8, ttl_seconds=0.001)
        ad.advertised_at = time.time() - 1.0
        router.advertise(ad)
        result = router.route("compute")
        assert not result.found

    def test_value_score(self):
        ad = CapabilityAd("a", "compute", quality=0.9, cost=0.1, latency_ms=50.0)
        assert ad.value_score > 1.0

    def test_stats(self):
        router = SemanticRouter()
        router.advertise(CapabilityAd("a", "compute", quality=0.8))
        s = router.stats
        assert s["active_ads"] == 1
        assert s["capability_types"] == 1


# ======================================================================
# 永不停歇主循环测试
# ======================================================================

class TestForeverLoop:
    def test_run_cycle(self):
        loop = ForeverLoop("test")
        result = loop.run_cycle()
        assert result.cycle_id == 1
        assert len(result.phases_completed) > 0

    def test_all_phases_present(self):
        loop = ForeverLoop("test")
        result = loop.run_cycle()
        assert CyclePhase.THINK in result.phases_completed
        assert CyclePhase.ACT in result.phases_completed
        assert CyclePhase.EVOLVE in result.phases_completed
        assert CyclePhase.REFLECT in result.phases_completed

    def test_conditional_phases(self):
        loop = ForeverLoop("test")
        result = loop.run_cycle()
        assert CyclePhase.IMMUNE in result.phases_completed
        assert CyclePhase.CHAOS in result.phases_completed
        assert CyclePhase.DREAM in result.phases_completed

    def test_cycle_interval(self):
        loop = ForeverLoop("test")
        r1 = loop.run_cycle()
        assert CyclePhase.IMMUNE in r1.phases_completed
        for _ in range(8):
            loop.run_cycle()
        r10 = loop.run_cycle()
        assert CyclePhase.IMMUNE in r10.phases_completed

    def test_success_rate(self):
        loop = ForeverLoop("test")
        result = loop.run_cycle()
        assert result.success_rate > 0.5

    def test_multiple_cycles(self):
        loop = ForeverLoop("test")
        for _ in range(10):
            loop.run_cycle()
        assert loop.state.cycle_count == 10
        assert loop.state.is_healthy

    def test_stop(self):
        loop = ForeverLoop("test")
        loop.run_cycle()
        loop.stop()
        assert not loop.state.running

    def test_uptime(self):
        loop = ForeverLoop("test")
        loop.run_cycle()
        assert loop.state.uptime_seconds >= 0

    def test_stats(self):
        loop = ForeverLoop("test")
        loop.run_cycle()
        s = loop.stats
        assert s["cycle_count"] == 1
        assert s["running"] is True

    def test_loop_state_healthy(self):
        state = LoopState()
        assert state.is_healthy
        state.consecutive_errors = 15
        assert not state.is_healthy
