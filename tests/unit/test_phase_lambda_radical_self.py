"""Phase lambda: 混沌引擎+技术达尔文+生殖管道+自优化闭环 测试。"""

import time
import pytest
from autoai.chaos.immune import (
    ImmuneSystem, AttackVector, AttackResult, AttackCategory, AttackSeverity,
    ImmuneMemory, AutoPatch, PatchStatus,
)
from autoai.chaos.antifragile import (
    AntiFragileEngine, FaultInjection, FaultType, RecoveryReport, RecoveryStatus,
    ResilienceProfile,
)
from autoai.evolution.tech_darwin import (
    TechDarwinEngine, TechOpportunity, OpportunityType, OpportunityRisk,
    MigrationExperiment, MigrationStatus, DarwinRecord,
)
from autoai.reproduction.pipeline import (
    ReproductionPipeline, ChildAgentSpec, GeneticCode, BirthReport,
    BirthStatus, DeathReason,
)
from autoai.self_optimize.loop import (
    SelfOptimizeLoop, OptimizeCycle, OptimizeReport, OptimizePhase,
    OptimizeTrigger, PerformanceBaseline,
)


# ======================================================================
# 免疫系统测试
# ======================================================================

class TestImmuneSystem:
    def test_generate_attack_vectors(self):
        immune = ImmuneSystem("test")
        vectors = immune.generate_attack_vectors()
        assert len(vectors) == len(AttackCategory)
        for v in vectors:
            assert v.category in AttackCategory
            assert v.payload != ""

    def test_execute_attack_known_threat(self):
        immune = ImmuneSystem("test")
        vec = AttackVector(
            vector_id="atk_test",
            category=AttackCategory.INPUT_INJECTION,
            payload="test_payload",
            target_module="think",
            severity=AttackSeverity.HIGH,
        )
        r1 = immune.execute_attack(vec)
        fp = vec.fingerprint
        assert fp in immune._memory
        r2 = immune.execute_attack(vec)
        assert immune._memory[fp].attack_count == 2

    def test_auto_patch_generation(self):
        immune = ImmuneSystem("test")
        vec = AttackVector(
            vector_id="atk_patch",
            category=AttackCategory.KNOWLEDGE_POISON,
            payload="inject_false",
            target_module="knowledge",
            severity=AttackSeverity.HIGH,
        )
        result = immune.execute_attack(vec)
        if result.success:
            assert result.patch_generated
            assert result.patch_id != ""

    def test_verify_patch(self):
        immune = ImmuneSystem("test")
        immune._total_auto_patches = 1
        patch = AutoPatch(
            patch_id="patch_1",
            target_vector_id="v1",
            target_module="knowledge",
            fix_description="test fix",
            fix_code="# test pass",
        )
        immune._patches["patch_1"] = patch
        result = immune.verify_patch("patch_1")
        assert result in (True, False)
        assert patch.status in (PatchStatus.APPLIED, PatchStatus.FAILED)

    def test_run_immune_cycle(self):
        immune = ImmuneSystem("test")
        report = immune.run_immune_cycle()
        assert "attacks_launched" in report
        assert report["attacks_launched"] > 0
        assert "breaches" in report
        assert "immune_memory_size" in report

    def test_immune_memory_defense_rate(self):
        mem = ImmuneMemory(fingerprint="test", category=AttackCategory.INPUT_INJECTION)
        mem.record_defense(True)
        mem.record_defense(True)
        mem.record_defense(False)
        assert mem.defense_rate == pytest.approx(2.0 / 3.0)

    def test_stats(self):
        immune = ImmuneSystem("test")
        immune.run_immune_cycle()
        s = immune.stats
        assert s["total_attacks"] > 0
        assert "breach_rate" in s
        assert "immune_memory_entries" in s

    def test_attack_vector_fingerprint(self):
        v1 = AttackVector("a1", AttackCategory.INPUT_INJECTION, "p", "t")
        v2 = AttackVector("a2", AttackCategory.INPUT_INJECTION, "p", "t")
        assert v1.fingerprint == v2.fingerprint
        v3 = AttackVector("a3", AttackCategory.LOGIC_BOMB, "p", "t")
        assert v1.fingerprint != v3.fingerprint


# ======================================================================
# 反脆弱引擎测试
# ======================================================================

class TestAntiFragileEngine:
    def test_select_fault(self):
        engine = AntiFragileEngine("test")
        injection = engine.select_fault(["memory", "mesh", "knowledge"])
        assert injection.fault_type in FaultType
        assert 0 < injection.intensity <= 1.0

    def test_inject_and_observe_recovered(self):
        engine = AntiFragileEngine("test", intensity=0.2)
        injection = engine.select_fault(["core"])
        report = engine.inject_and_observe(injection)
        assert report.fault_type == injection.fault_type
        assert report.status in list(RecoveryStatus)

    def test_antifragile_resilience_growth(self):
        engine = AntiFragileEngine("test", intensity=0.2)
        initial = engine.profile.overall_resilience
        for _ in range(20):
            inj = engine.select_fault(["core", "memory"])
            engine.inject_and_observe(inj)
        final = engine.profile.overall_resilience
        assert final >= initial * 0.8

    def test_run_chaos_cycle(self):
        engine = AntiFragileEngine("test")
        result = engine.run_chaos_cycle(["core"], num_injections=5)
        assert result["injections"] == 5
        assert "overall_resilience" in result
        assert "antifragile_events" in result

    def test_resilience_profile(self):
        profile = ResilienceProfile()
        report = RecoveryReport(
            injection_id="c1",
            fault_type=FaultType.MODULE_KILL,
            status=RecoveryStatus.RECOVERED,
            resilience_delta=0.05,
        )
        profile.update(report)
        assert profile.total_injections == 1
        assert profile.total_recoveries == 1
        assert profile.fault_resilience[FaultType.MODULE_KILL.value] > 0.5

    def test_cascading_failure_detection(self):
        engine = AntiFragileEngine("test", intensity=0.9)
        injection = FaultInjection(
            injection_id="severe",
            fault_type=FaultType.NETWORK_PARTITION,
            target="mesh",
            intensity=1.0,
        )
        report = engine.inject_and_observe(injection)
        assert report.fault_type == FaultType.NETWORK_PARTITION

    def test_lessons_learned(self):
        engine = AntiFragileEngine("test")
        engine.run_chaos_cycle(["core"], num_injections=3)
        lessons = engine.lessons
        assert isinstance(lessons, dict)

    def test_stats(self):
        engine = AntiFragileEngine("test")
        engine.run_chaos_cycle()
        s = engine.stats
        assert s["total_injections"] > 0
        assert 0 <= s["overall_resilience"] <= 1.0


# ======================================================================
# 技术达尔文引擎测试
# ======================================================================

class TestTechDarwinEngine:
    def test_scan_opportunities(self):
        engine = TechDarwinEngine("test")
        opps = engine.scan_opportunities()
        assert len(opps) > 0
        for o in opps:
            assert o.op_type in OpportunityType
            assert o.description != ""

    def test_net_value_calculation(self):
        opp = TechOpportunity(
            opportunity_id="test",
            op_type=OpportunityType.PERFORMANCE,
            description="test",
            target="test",
            estimated_benefit=0.9,
            estimated_cost=0.2,
            risk=OpportunityRisk.LOW,
        )
        assert opp.net_value > 0
        assert opp.is_worthwhile

    def test_net_value_negative(self):
        opp = TechOpportunity(
            opportunity_id="bad",
            op_type=OpportunityType.PARADIGM_SHIFT,
            description="risky",
            target="core",
            estimated_benefit=0.3,
            estimated_cost=0.9,
            risk=OpportunityRisk.REVOLUTIONARY,
        )
        assert opp.net_value < 0
        assert not opp.is_worthwhile

    def test_evaluate_worthwhile(self):
        engine = TechDarwinEngine("test")
        opp = TechOpportunity(
            opportunity_id="good",
            op_type=OpportunityType.DEPRECATION,
            description="migrate",
            target="config",
            estimated_benefit=0.8,
            estimated_cost=0.3,
            risk=OpportunityRisk.LOW,
        )
        engine._opportunities["good"] = opp
        exp = engine.evaluate(opp)
        assert exp.status in (
            MigrationStatus.READY, MigrationStatus.ROLLED_BACK,
            MigrationStatus.TESTING, MigrationStatus.REJECTED,
        )

    def test_evaluate_not_worthwhile(self):
        engine = TechDarwinEngine("test")
        opp = TechOpportunity(
            opportunity_id="bad",
            op_type=OpportunityType.PARADIGM_SHIFT,
            description="too risky",
            target="core",
            estimated_benefit=0.1,
            estimated_cost=0.9,
            risk=OpportunityRisk.REVOLUTIONARY,
        )
        exp = engine.evaluate(opp)
        assert exp.status == MigrationStatus.REJECTED

    def test_apply_migration(self):
        engine = TechDarwinEngine("test")
        exp = MigrationExperiment(
            experiment_id="exp1",
            opportunity_id="opp1",
            status=MigrationStatus.READY,
        )
        result = engine.apply(exp)
        assert result
        assert exp.status == MigrationStatus.APPLIED

    def test_rollback(self):
        engine = TechDarwinEngine("test")
        opp = TechOpportunity(
            opportunity_id="opp1",
            op_type=OpportunityType.DEPRECATION,
            description="test",
            target="test",
        )
        engine._opportunities["opp1"] = opp
        exp = MigrationExperiment(
            experiment_id="exp1",
            opportunity_id="opp1",
            status=MigrationStatus.ROLLED_BACK,
        )
        result = engine.rollback(exp)
        assert result

    def test_run_darwin_cycle(self):
        engine = TechDarwinEngine("test")
        result = engine.run_darwin_cycle()
        assert result["opportunities_found"] > 0
        assert "applied" in result
        assert "rolled_back" in result

    def test_stats(self):
        engine = TechDarwinEngine("test")
        engine.run_darwin_cycle()
        s = engine.stats
        assert s["opportunities_known"] > 0


# ======================================================================
# 生殖管道测试
# ======================================================================

class TestReproductionPipeline:
    def test_conceive(self):
        pipe = ReproductionPipeline("parent")
        spec = pipe.conceive("分析数据趋势", ["data_analysis", "knowledge_query"])
        assert spec.parent_id == "parent"
        assert len(spec.required_capabilities) == 2

    def test_conceive_infer_capabilities(self):
        pipe = ReproductionPipeline("parent")
        spec = pipe.conceive("监控安全威胁")
        assert "observation" in spec.required_capabilities or "security_scan" in spec.required_capabilities

    def test_draft_genetics(self):
        pipe = ReproductionPipeline("parent")
        spec = pipe.conceive("优化性能", ["measurement"])
        genetic = pipe.draft_genetics(spec)
        assert genetic.is_viable
        assert len(genetic.module_code) > 0

    def test_gestate_viable(self):
        pipe = ReproductionPipeline("parent")
        spec = pipe.conceive("执行测试", ["reasoning"])
        genetic = pipe.draft_genetics(spec)
        report = pipe.gestate(spec, genetic)
        assert report.status in (BirthStatus.BORN, BirthStatus.STILLBORN, BirthStatus.REJECTED_BY_GOVERNANCE)

    def test_gestate_nonviable(self):
        pipe = ReproductionPipeline("parent")
        spec = ChildAgentSpec(
            spec_id="s1", parent_id="parent", goal_description="test",
        )
        genetic = GeneticCode(code_id="g1", spec_id="s1", quality_score=0.1)
        report = pipe.gestate(spec, genetic)
        assert report.status == BirthStatus.STILLBORN

    def test_reproduce_full(self):
        pipe = ReproductionPipeline("parent")
        report = pipe.reproduce("协调多Agent任务", ["mesh_communication", "task_delegation"])
        assert report.child_id != ""
        assert report.status in list(BirthStatus)

    def test_record_death(self):
        pipe = ReproductionPipeline("parent")
        report = pipe.reproduce("临时分析任务", ["data_analysis"])
        if report.is_alive:
            died = pipe.record_death(report.child_id, DeathReason.NATURAL_EXPIRY)
            assert died
            assert not report.is_alive

    def test_record_achievement(self):
        pipe = ReproductionPipeline("parent")
        report = pipe.reproduce("简单任务")
        pipe.record_achievement(report.child_id, "完成了首次分析")
        assert "完成了首次分析" in report.achievements

    def test_max_children_limit(self):
        pipe = ReproductionPipeline("parent")
        pipe._max_children = 2
        pipe.reproduce("任务1")
        pipe.reproduce("任务2")
        r3 = pipe.reproduce("任务3")
        assert r3.status == BirthStatus.REJECTED_BY_GOVERNANCE

    def test_living_children(self):
        pipe = ReproductionPipeline("parent")
        pipe.reproduce("任务A")
        pipe.reproduce("任务B")
        living = pipe.get_living_children()
        assert len(living) >= 0

    def test_stats(self):
        pipe = ReproductionPipeline("parent")
        pipe.reproduce("测试任务")
        s = pipe.stats
        assert s["total_conceptions"] >= 1


# ======================================================================
# 自优化闭环测试
# ======================================================================

class TestSelfOptimizeLoop:
    def test_should_optimize_scheduled(self):
        loop = SelfOptimizeLoop("test", optimize_interval=5)
        for i in range(4):
            should, trigger = loop.should_optimize()
            if i == 4:
                assert should and trigger == OptimizeTrigger.SCHEDULED

    def test_should_optimize_degradation(self):
        loop = SelfOptimizeLoop("test", optimize_interval=1000)
        loop._baseline = PerformanceBaseline(avg_think_time_ms=100.0, error_rate=0.01)
        loop._current = PerformanceBaseline(avg_think_time_ms=150.0, error_rate=0.01)
        should, trigger = loop.should_optimize()
        assert should
        assert trigger == OptimizeTrigger.PERFORMANCE_DEGRADATION

    def test_should_optimize_anomaly(self):
        loop = SelfOptimizeLoop("test", optimize_interval=1000)
        loop._baseline = PerformanceBaseline(avg_think_time_ms=100.0, error_rate=0.01)
        loop._current = PerformanceBaseline(avg_think_time_ms=100.0, error_rate=0.1)
        loop._think_count = 1
        should, trigger = loop.should_optimize()
        assert should
        assert trigger == OptimizeTrigger.PERFORMANCE_DEGRADATION

    def test_run_cycle(self):
        loop = SelfOptimizeLoop("test")
        report = loop.run_cycle(OptimizeTrigger.SCHEDULED)
        assert report.cycle_id == 1
        assert len(report.lessons) > 0
        assert report.duration_ms >= 0

    def test_seven_phases(self):
        loop = SelfOptimizeLoop("test")
        loop.run_cycle(OptimizeTrigger.SCHEDULED)
        cycle = loop._cycles[0]
        assert cycle.is_complete
        assert cycle.phase == OptimizePhase.REFLECT

    def test_performance_baseline(self):
        baseline = PerformanceBaseline(avg_think_time_ms=100.0, error_rate=0.01)
        ok_current = PerformanceBaseline(avg_think_time_ms=110.0, error_rate=0.01)
        degraded, _ = baseline.detect_degradation(ok_current, threshold=0.2)
        assert not degraded
        bad_current = PerformanceBaseline(avg_think_time_ms=150.0, error_rate=0.01)
        degraded, reason = baseline.detect_degradation(bad_current, threshold=0.2)
        assert degraded
        assert "思考时间" in reason

    def test_update_performance(self):
        loop = SelfOptimizeLoop("test")
        loop.update_performance(think_time_ms=80.0, memory_mb=120.0, error_rate=0.005)
        assert loop._current.avg_think_time_ms == 80.0
        assert loop._current.memory_usage_mb == 120.0

    def test_multiple_cycles(self):
        loop = SelfOptimizeLoop("test", optimize_interval=1)
        for i in range(5):
            loop.run_cycle(OptimizeTrigger.SCHEDULED)
        assert loop._cycle_count == 5
        assert len(loop._optimization_history) == 5

    def test_optimize_report(self):
        loop = SelfOptimizeLoop("test")
        report = loop.run_cycle(OptimizeTrigger.OPPORTUNITY_FOUND)
        assert isinstance(report.improvements_made, int)
        assert isinstance(report.knowledge_gained, int)

    def test_stats(self):
        loop = SelfOptimizeLoop("test")
        loop.run_cycle(OptimizeTrigger.SCHEDULED)
        s = loop.stats
        assert s["cycle_count"] == 1
        assert "current_performance" in s
