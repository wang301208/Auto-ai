"""Phase nu: 自愈+自测试+自文档+自升级 测试。"""

import time
import pytest
from autoai.self_heal.engine import (
    SelfHealEngine, HealIncident, HealAction, HealOutcome,
    IncidentType, IncidentSeverity, HealActionType,
)
from autoai.self_test.engine import (
    SelfTestEngine, TestSpec, TestRun, TestStatus, TestPriority,
)
from autoai.self_doc.engine import (
    SelfDocEngine, DocSpec, DocArtifact, DocType, DocStatus,
)
from autoai.self_upgrade.engine import (
    SelfUpgradeEngine, UpgradeCandidate, UpgradeResult,
    UpgradeType, UpgradeRisk, UpgradeStatus,
)


# ======================================================================
# 自愈引擎测试
# ======================================================================

class TestSelfHealEngine:
    def test_detect_incident(self):
        engine = SelfHealEngine("test")
        incident = engine.detect_incident(
            IncidentType.EXCEPTION, IncidentSeverity.HIGH,
            "memory", "内存分配失败"
        )
        assert incident.incident_id != ""
        assert incident.is_urgent

    def test_diagnose(self):
        engine = SelfHealEngine("test")
        incident = engine.detect_incident(
            IncidentType.EXCEPTION, IncidentSeverity.MEDIUM,
            "mesh", "连接超时"
        )
        actions = engine.diagnose(incident)
        assert len(actions) > 0
        assert actions[0].action_type == HealActionType.RETRY

    def test_execute_heal(self):
        engine = SelfHealEngine("test")
        incident = engine.detect_incident(
            IncidentType.PERFORMANCE, IncidentSeverity.LOW,
            "dream_engine", "执行时间超过阈值"
        )
        outcome = engine.execute_heal(incident)
        assert outcome.incident_id == incident.incident_id
        assert len(outcome.actions_taken) > 0

    def test_heal_strategies(self):
        engine = SelfHealEngine("test")
        inc = engine.detect_incident(
            IncidentType.CONSISTENCY, IncidentSeverity.HIGH,
            "belief_system", "信念不一致"
        )
        actions = engine.diagnose(inc)
        action_types = [a.action_type for a in actions]
        assert HealActionType.ROLLBACK_STATE in action_types

    def test_auto_heal_cycle(self):
        engine = SelfHealEngine("test")
        engine.detect_incident(IncidentType.EXCEPTION, IncidentSeverity.HIGH, "a", "err1")
        engine.detect_incident(IncidentType.PERFORMANCE, IncidentSeverity.LOW, "b", "err2")
        result = engine.auto_heal_cycle()
        assert result["checked"] == 2

    def test_stats(self):
        engine = SelfHealEngine("test")
        engine.detect_incident(IncidentType.EXCEPTION, IncidentSeverity.MEDIUM, "x", "err")
        s = engine.stats
        assert s["total_incidents"] == 1

    def test_incident_urgency(self):
        low = HealIncident("l", IncidentType.EXCEPTION, IncidentSeverity.LOW, "m", "d")
        crit = HealIncident("c", IncidentType.EXCEPTION, IncidentSeverity.CRITICAL, "m", "d")
        assert not low.is_urgent
        assert crit.is_urgent


# ======================================================================
# 自测试引擎测试
# ======================================================================

class TestSelfTestEngine:
    def test_generate_test(self):
        engine = SelfTestEngine("test")
        spec = engine.generate_test("autoai.knowledge.graph", "add_node")
        assert spec.is_complete
        assert len(spec.test_code) > 0

    def test_run_test(self):
        engine = SelfTestEngine("test")
        spec = engine.generate_test("autoai.mesh", "gossip")
        run = engine.run_test(spec)
        assert run.status in (TestStatus.PASSED, TestStatus.FAILED)

    def test_run_all_tests(self):
        engine = SelfTestEngine("test")
        engine.generate_test("a", "f1")
        engine.generate_test("b", "f2")
        result = engine.run_all_tests()
        assert result["total"] == 2
        assert "pass_rate" in result

    def test_generate_module_tests(self):
        engine = SelfTestEngine("test")
        specs = engine.generate_module_tests("autoai.evolution", ["enhanced_loop", "auto_agent_writer"])
        assert len(specs) == 4

    def test_edge_case_inputs(self):
        engine = SelfTestEngine("test")
        spec = engine.generate_test("a", "f", priority=TestPriority.EDGE_CASE)
        assert None in spec.inputs
        assert 0 in spec.inputs

    def test_failing_tests(self):
        engine = SelfTestEngine("test")
        engine.generate_test("a", "f1")
        engine.run_all_tests()
        failing = engine.get_failing_tests()
        assert isinstance(failing, list)

    def test_stats(self):
        engine = SelfTestEngine("test")
        engine.generate_test("a", "f")
        engine.run_all_tests()
        s = engine.stats
        assert s["specs_generated"] >= 1
        assert s["total_runs"] >= 1


# ======================================================================
# 自文档引擎测试
# ======================================================================

class TestSelfDocEngine:
    def test_generate_api_doc(self):
        engine = SelfDocEngine("test")
        artifact = engine.generate_doc("knowledge.graph", DocType.API)
        assert len(artifact.content) > 0
        assert artifact.completeness > 0.5

    def test_generate_architecture_doc(self):
        engine = SelfDocEngine("test")
        artifact = engine.generate_doc("holistic.agent", DocType.ARCHITECTURE)
        assert "组件" in artifact.sections
        assert "依赖" in artifact.sections

    def test_generate_runbook(self):
        engine = SelfDocEngine("test")
        artifact = engine.generate_doc("mesh", DocType.RUNBOOK)
        assert "启动" in artifact.sections
        assert "故障排除" in artifact.sections

    def test_doc_completeness(self):
        engine = SelfDocEngine("test")
        artifact = engine.generate_doc("safety_intuition", DocType.CAPABILITY)
        assert artifact.completeness == 1.0

    def test_doc_token_count(self):
        engine = SelfDocEngine("test")
        artifact = engine.generate_doc("evolution", DocType.API)
        assert artifact.token_count > 0

    def test_check_freshness(self):
        engine = SelfDocEngine("test")
        artifact = engine.generate_doc("mesh", DocType.API)
        stale = engine.check_freshness()
        assert len(stale) == 0

    def test_stale_detection(self):
        engine = SelfDocEngine("test")
        artifact = engine.generate_doc("x", DocType.API)
        artifact.generated_at = time.time() - 200000
        stale = engine.check_freshness()
        assert len(stale) == 1
        assert artifact.status == DocStatus.STALE

    def test_regenerate_stale(self):
        engine = SelfDocEngine("test")
        artifact = engine.generate_doc("y", DocType.API)
        artifact.generated_at = time.time() - 200000
        count = engine.regenerate_stale()
        assert count == 1

    def test_stats(self):
        engine = SelfDocEngine("test")
        engine.generate_doc("a", DocType.API)
        s = engine.stats
        assert s["total_generated"] == 1


# ======================================================================
# 自升级引擎测试
# ======================================================================

class TestSelfUpgradeEngine:
    def test_scan_upgrades(self):
        engine = SelfUpgradeEngine("test")
        candidates = engine.scan_upgrades()
        assert len(candidates) >= 3
        for c in candidates:
            assert c.upgrade_type in UpgradeType

    def test_safe_auto_upgrade(self):
        candidate = UpgradeCandidate(
            candidate_id="safe",
            upgrade_type=UpgradeType.PERFORMANCE,
            target="json",
            risk=UpgradeRisk.LOW,
            auto_applicable=True,
        )
        assert candidate.is_safe_auto

    def test_unsafe_auto_upgrade(self):
        candidate = UpgradeCandidate(
            candidate_id="risky",
            upgrade_type=UpgradeType.API_MIGRATION,
            target="core",
            risk=UpgradeRisk.HIGH,
            breaking_changes=["API变化"],
        )
        assert not candidate.is_safe_auto

    def test_analyze_safe(self):
        engine = SelfUpgradeEngine("test")
        candidate = UpgradeCandidate(
            candidate_id="safe1",
            upgrade_type=UpgradeType.SECURITY,
            target="auth",
            risk=UpgradeRisk.LOW,
            auto_applicable=True,
        )
        engine._candidates["safe1"] = candidate
        result = engine.analyze(candidate)
        assert result.status == UpgradeStatus.READY

    def test_analyze_dangerous(self):
        engine = SelfUpgradeEngine("test")
        candidate = UpgradeCandidate(
            candidate_id="danger1",
            upgrade_type=UpgradeType.API_MIGRATION,
            target="core",
            risk=UpgradeRisk.DANGEROUS,
            breaking_changes=["一切"],
        )
        engine._candidates["danger1"] = candidate
        result = engine.analyze(candidate)
        assert result.status == UpgradeStatus.DEFERRED

    def test_apply(self):
        engine = SelfUpgradeEngine("test")
        candidate = UpgradeCandidate(
            candidate_id="apply1",
            upgrade_type=UpgradeType.PERFORMANCE,
            target="json",
            risk=UpgradeRisk.LOW,
            auto_applicable=True,
        )
        candidate.status = UpgradeStatus.READY
        engine._candidates["apply1"] = candidate
        result = engine.apply(candidate)
        assert result.status in (UpgradeStatus.APPLIED, UpgradeStatus.ROLLED_BACK)

    def test_apply_not_ready(self):
        engine = SelfUpgradeEngine("test")
        candidate = UpgradeCandidate(
            candidate_id="notready",
            upgrade_type=UpgradeType.FEATURE,
            target="x",
        )
        result = engine.apply(candidate)
        assert result.status == UpgradeStatus.CANDIDATE

    def test_run_upgrade_cycle(self):
        engine = SelfUpgradeEngine("test")
        result = engine.run_upgrade_cycle()
        assert result["candidates"] >= 3
        assert "applied" in result
        assert "deferred" in result

    def test_stats(self):
        engine = SelfUpgradeEngine("test")
        engine.run_upgrade_cycle()
        s = engine.stats
        assert s["candidates_known"] >= 3
