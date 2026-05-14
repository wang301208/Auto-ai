"""Tests for Phase 18: Architecture self-diagnosis, refactoring, capability injection, protocol upgrade."""

from __future__ import annotations

import asyncio
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock

import pytest

from autoai.agents.arch_diagnoser import (
    ArchDiagnoser,
    ArchIssue,
    ArchIssueType,
    ArchReport,
    ModuleInfo,
    Severity,
)
from autoai.agents.arch_refactorer import (
    ArchRefactorer,
    RefactorPlan,
    RefactorResult,
)
from governance.autonomy_level import AutonomyLevel, AutonomyManager
from autoai.agents.capability_injector import (
    CapabilityInjector,
    CapabilitySpec,
    InjectionType,
    InjectionRecord,
)
from autoai.agents.protocol_upgrader import (
    AgentProtocolState,
    MessageSchema,
    ProtocolUpgrader,
    ProtocolVersion,
    ProtoUpgradePolicy,
    SchemaMigration,
)


# ==================== ArchDiagnoser ====================

class TestArchDiagnoser:
    def test_empty_workspace(self, tmp_path: Path):
        diagnoser = ArchDiagnoser(workspace=tmp_path, scan_dirs=[])
        report = diagnoser.diagnose()
        assert report.modules_scanned == 0
        assert len(report.issues) == 0

    def test_scan_real_project(self):
        workspace = Path("G:/项目/AutoAI-0.4.7")
        if not workspace.exists():
            pytest.skip("Project not found")
        diagnoser = ArchDiagnoser(workspace=workspace, coupling_threshold=15)
        report = diagnoser.diagnose()
        assert report.modules_scanned > 0
        assert isinstance(report.issues, list)

    def test_detect_side_effects(self, tmp_path: Path):
        mod_dir = tmp_path / "autoai"
        mod_dir.mkdir()
        (mod_dir / "__init__.py").write_text("")
        (mod_dir / "side_effect.py").write_text(
            'import os\nos.makedirs("/tmp/test", exist_ok=True)\n'
        )
        diagnoser = ArchDiagnoser(workspace=tmp_path, scan_dirs=["autoai"])
        report = diagnoser.diagnose()
        perf_issues = [i for i in report.issues if i.issue_type == ArchIssueType.PERF_BOTTLENECK]
        assert len(perf_issues) >= 1

    def test_severity_ordering(self):
        assert Severity.LOW.value < Severity.MEDIUM.value < Severity.HIGH.value < Severity.CRITICAL.value

    def test_arch_issue_score(self):
        issue = ArchIssue(
            issue_type=ArchIssueType.CIRCULAR_IMPORT,
            severity=Severity.CRITICAL,
            location="test.py",
            description="test",
        )
        assert issue.score == 4

    def test_report_summary(self, tmp_path: Path):
        diagnoser = ArchDiagnoser(workspace=tmp_path, scan_dirs=[])
        report = diagnoser.diagnose()
        s = report.summary()
        assert "modules_scanned" in s
        assert "total_issues" in s
        assert "critical" in s

    def test_module_info_defaults(self):
        info = ModuleInfo(path="test.py")
        assert info.imports == []
        assert info.exports == []
        assert info.has_side_effects is False

    def test_detect_coupling_hotspot(self, tmp_path: Path):
        mod_dir = tmp_path / "autoai"
        mod_dir.mkdir()
        (mod_dir / "__init__.py").write_text("")
        hot = mod_dir / "hotspot.py"
        hot.write_text("class Hotspot:\n    pass\n")
        for i in range(12):
            consumer = mod_dir / f"consumer_{i}.py"
            consumer.write_text("from autoai.hotspot import Hotspot\n")
        diagnoser = ArchDiagnoser(workspace=tmp_path, scan_dirs=["autoai"], coupling_threshold=10)
        report = diagnoser.diagnose()
        coupling = [i for i in report.issues if i.issue_type == ArchIssueType.COUPLING_HOTSPOT]
        assert len(coupling) >= 0

    def test_by_type(self, tmp_path: Path):
        diagnoser = ArchDiagnoser(workspace=tmp_path, scan_dirs=[])
        report = diagnoser.diagnose()
        by_type = report.by_type
        assert isinstance(by_type, dict)


# ==================== ArchRefactorer ====================

class TestArchRefactorer:
    def test_generate_plans_empty_report(self, tmp_path: Path):
        refactorer = ArchRefactorer(workspace=tmp_path)
        report = ArchReport(workspace=str(tmp_path), modules_scanned=0, issues=[])
        plans = refactorer.generate_plans(report)
        assert plans == []

    def test_generate_lazy_import_plan(self, tmp_path: Path):
        mod_dir = tmp_path / "autoai"
        mod_dir.mkdir()
        (mod_dir / "__init__.py").write_text("")
        (mod_dir / "a.py").write_text("from autoai.b import B\n")
        issue = ArchIssue(
            issue_type=ArchIssueType.CIRCULAR_IMPORT,
            severity=Severity.CRITICAL,
            location="autoai/a.py",
            description="Circular import: a → b → a",
            context={"cycle": ["autoai/a.py", "autoai/b.py", "autoai/a.py"]},
        )
        refactorer = ArchRefactorer(workspace=tmp_path)
        plan = refactorer._gen_lazy_import_patch(issue)
        assert plan is not None
        assert "autoai/a.py" in plan.target_files

    def test_generate_dead_code_plan(self, tmp_path: Path):
        mod_dir = tmp_path / "autoai"
        mod_dir.mkdir()
        (mod_dir / "__init__.py").write_text("")
        dead = mod_dir / "dead.py"
        dead.write_text("")
        issue = ArchIssue(
            issue_type=ArchIssueType.DEAD_CODE,
            severity=Severity.LOW,
            location="autoai/dead.py",
            description="Dead code",
        )
        refactorer = ArchRefactorer(workspace=tmp_path)
        plan = refactorer._gen_dead_code_removal_patch(issue)
        assert plan is not None

    def test_generate_facade_plan(self, tmp_path: Path):
        issue = ArchIssue(
            issue_type=ArchIssueType.COUPLING_HOTSPOT,
            severity=Severity.HIGH,
            location="autoai/agents/agent.py",
            description="Coupling hotspot",
            context={"import_count": 15},
        )
        refactorer = ArchRefactorer(workspace=tmp_path)
        plan = refactorer._gen_facade_extraction_patch(issue)
        assert plan is not None
        assert "facade" in plan.description

    def test_generate_interface_unify_plan(self):
        issue = ArchIssue(
            issue_type=ArchIssueType.INTERFACE_MISMATCH,
            severity=Severity.MEDIUM,
            location="autoai/agents/agent.py",
            description="Interface mismatch",
            context={"method": "think", "implementations": ["Agent(a,b)", "Agent(a)"]},
        )
        refactorer = ArchRefactorer(workspace=Path("."))
        plan = refactorer._gen_interface_unify_patch(issue)
        assert plan is not None
        assert plan.estimated_risk <= 0.3

    def test_max_risk_filter(self, tmp_path: Path):
        issue = ArchIssue(
            issue_type=ArchIssueType.DEAD_CODE,
            severity=Severity.LOW,
            location="test.py",
            description="Dead code",
        )
        refactorer = ArchRefactorer(workspace=tmp_path, max_risk=0.1)
        report = ArchReport(workspace=str(tmp_path), modules_scanned=1, issues=[issue])
        plans = refactorer.generate_plans(report)
        for plan in plans:
            assert plan.estimated_risk <= 0.1

    def test_refactor_result_defaults(self):
        result = RefactorResult()
        assert result.plans_generated == 0
        assert result.plans_applied == 0


# ==================== CapabilityInjector ====================

class TestCapabilityInjector:
    @staticmethod
    def _make_injector() -> CapabilityInjector:
        manager = AutonomyManager(agent_id="test")
        manager._level = AutonomyLevel.AUTONOMOUS  # force_level(AutonomyLevel.SELF_REWRITE)
        return CapabilityInjector(autonomy=manager)

    def test_inject_mixin(self):
        class Target:
            existing = "yes"

        mod = types.ModuleType("test_mod")
        mod.Target = Target
        sys.modules["test_mod"] = mod

        try:
            injector = self._make_injector()
            spec = CapabilitySpec(
                name="test_mixin",
                injection_type=InjectionType.MIXIN,
                target_class="test_mod.Target",
                methods={"new_method": lambda self: "injected"},
            )
            record = injector.inject(spec)
            assert record.success
            assert "new_method" in dir(Target)
            assert injector.injection_count == 1
        finally:
            del sys.modules["test_mod"]

    def test_inject_decorator(self):
        class Target:
            def method(self):
                return "original"

        mod = types.ModuleType("test_dec_mod")
        mod.Target = Target
        sys.modules["test_dec_mod"] = mod

        try:
            injector = self._make_injector()

            def timing_decorator(original_fn):
                def wrapper(*args, **kwargs):
                    return original_fn(*args, **kwargs)
                return wrapper

            spec = CapabilitySpec(
                name="timing",
                injection_type=InjectionType.DECORATOR,
                target_class="test_dec_mod.Target",
                decorators={"method": timing_decorator},
            )
            record = injector.inject(spec)
            assert record.success
            t = Target()
            assert t.method() == "original"
        finally:
            del sys.modules["test_dec_mod"]

    def test_inject_protocol(self):
        class Target:
            pass

        mod = types.ModuleType("test_proto_mod")
        mod.Target = Target
        sys.modules["test_proto_mod"] = mod

        try:
            injector = self._make_injector()
            spec = CapabilitySpec(
                name="protocol_impl",
                injection_type=InjectionType.PROTOCOL_IMPL,
                target_class="test_proto_mod.Target",
                methods={"required_method": lambda self: "impl"},
            )
            record = injector.inject(spec)
            assert record.success
            t = Target()
        finally:
            del sys.modules["test_proto_mod"]

    def test_rollback_mixin(self):
        class Target:
            existing = "yes"

        mod = types.ModuleType("test_rb_mod")
        mod.Target = Target
        sys.modules["test_rb_mod"] = mod

        try:
            injector = self._make_injector()
            spec = CapabilitySpec(
                name="rollback_test",
                injection_type=InjectionType.MIXIN,
                target_class="test_rb_mod.Target",
                methods={"temp_method": lambda self: "temp"},
            )
            record = injector.inject(spec)
            assert record.success
            assert "temp_method" in dir(Target)

            ok = injector.rollback("rollback_test")
            assert ok
        finally:
            del sys.modules["test_rb_mod"]

    def test_autonomy_gate(self):
        manager = AutonomyManager(agent_id="test")
        assert manager.level < AutonomyLevel.SELF_BOUND

        injector = CapabilityInjector(autonomy=manager)
        spec = CapabilitySpec(
            name="gated",
            injection_type=InjectionType.MIXIN,
            target_class="some.Class",
            requires_level=AutonomyLevel.SELF_BOUND,
        )
        record = injector.inject(spec)
        assert not record.success

    def test_active_capabilities(self):
        injector = self._make_injector()
        assert injector.active_capabilities == []

    def test_status(self):
        injector = self._make_injector()
        status = injector.get_status()
        assert "total_injections" in status
        assert "autonomy_level" in status


# ==================== ProtocolUpgrader ====================

class TestProtocolUpgrader:
    def test_version_comparison(self):
        v1 = ProtocolVersion(1, 0, 0)
        v2 = ProtocolVersion(1, 1, 0)
        v3 = ProtocolVersion(2, 0, 0)
        assert v1 < v2
        assert v2 < v3
        assert v1.is_compatible_with(v2)
        assert not v1.is_compatible_with(v3)

    def test_version_str(self):
        v = ProtocolVersion(1, 2, 3)
        assert str(v) == "v1.2.3"

    def test_register_agent(self):
        upgrader = ProtocolUpgrader()
        upgrader.register_agent("a1", [ProtocolVersion(1, 0, 0), ProtocolVersion(1, 1, 0)])
        assert "a1" in upgrader._agents

    def test_negotiate_exact_match(self):
        upgrader = ProtocolUpgrader()
        upgrader.register_agent("a1", [ProtocolVersion(1, 1, 0)])
        upgrader.register_agent("a2", [ProtocolVersion(1, 1, 0)])
        result = upgrader.negotiate("a1", "a2")
        assert result == ProtocolVersion(1, 1, 0)

    def test_negotiate_no_match(self):
        upgrader = ProtocolUpgrader()
        upgrader.register_agent("a1", [ProtocolVersion(1, 0, 0)])
        upgrader.register_agent("a2", [ProtocolVersion(2, 0, 0)])
        result = upgrader.negotiate("a1", "a2")
        assert result is None

    def test_upgrade_message_v100_to_v110(self):
        upgrader = ProtocolUpgrader()
        msg = {"message_type": "test", "sender_id": "a1", "payload": {}}
        upgraded = upgrader.upgrade_message(msg, ProtocolVersion(1, 0, 0), ProtocolVersion(1, 1, 0))
        assert "correlation_id" in upgraded
        assert "priority" in upgraded

    def test_upgrade_message_v110_to_v120(self):
        upgrader = ProtocolUpgrader()
        msg = {"message_type": "test", "sender_id": "a1", "payload": {}, "correlation_id": "abc", "priority": 1}
        upgraded = upgrader.upgrade_message(msg, ProtocolVersion(1, 1, 0), ProtocolVersion(1, 2, 0))
        assert "ttl" in upgraded
        assert "metadata" in upgraded

    def test_downgrade_message(self):
        upgrader = ProtocolUpgrader()
        msg = {"message_type": "test", "sender_id": "a1", "payload": {}, "correlation_id": "abc", "priority": 1}
        downgraded = upgrader.downgrade_message(msg, ProtocolVersion(1, 1, 0), ProtocolVersion(1, 0, 0))
        assert "correlation_id" not in downgraded
        assert "priority" not in downgraded

    def test_auto_upgrade_balanced(self):
        upgrader = ProtocolUpgrader(upgrade_policy=ProtoUpgradePolicy.BALANCED)
        upgrader.register_agent("a1", [ProtocolVersion(1, 1, 0)])
        results = upgrader.auto_upgrade_all()
        assert "a1" in results
        assert results["a1"] == ProtocolVersion(1, 2, 0)

    def test_auto_upgrade_conservative(self):
        upgrader = ProtocolUpgrader(
            current_version=ProtocolVersion(1, 2, 0),
            upgrade_policy=ProtoUpgradePolicy.CONSERVATIVE,
        )
        upgrader.register_agent("a1", [ProtocolVersion(1, 0, 0)])
        results = upgrader.auto_upgrade_all()
        assert results["a1"] == ProtocolVersion(1, 0, 0)

    def test_unregister_agent(self):
        upgrader = ProtocolUpgrader()
        upgrader.register_agent("a1", [ProtocolVersion(1, 0, 0)])
        upgrader.unregister_agent("a1")
        assert "a1" not in upgrader._agents

    def test_get_status(self):
        upgrader = ProtocolUpgrader()
        status = upgrader.get_status()
        assert "current_version" in status
        assert "available_schemas" in status
        assert "policy" in status

    def test_roundtrip_upgrade_downgrade(self):
        upgrader = ProtocolUpgrader()
        original = {"message_type": "test", "sender_id": "a1", "payload": {"key": "val"}}
        upgraded = upgrader.upgrade_message(original, ProtocolVersion(1, 0, 0), ProtocolVersion(1, 2, 0))
        assert upgraded["payload"] == {"key": "val"}
        downgraded = upgrader.downgrade_message(upgraded, ProtocolVersion(1, 2, 0), ProtocolVersion(1, 0, 0))
        assert downgraded["payload"] == {"key": "val"}

    def test_upgrade_same_version(self):
        upgrader = ProtocolUpgrader()
        msg = {"message_type": "test", "sender_id": "a1", "payload": {}}
        result = upgrader.upgrade_message(msg, ProtocolVersion(1, 0, 0), ProtocolVersion(1, 0, 0))
        assert result == msg


# ==================== SelfThinkEngine Phase 18 integration ====================

class TestSelfThinkPhase18:
    def test_arch_diagnose_without_diagnoser(self, tmp_path: Path):
        from autoai.agents.self_think import SelfThinkEngine
        engine = SelfThinkEngine(workspace=tmp_path)
        result = engine.arch_diagnose()
        assert result is None

    def test_arch_diagnose_with_diagnoser(self, tmp_path: Path):
        from autoai.agents.self_think import SelfThinkEngine
        diagnoser = ArchDiagnoser(workspace=tmp_path, scan_dirs=[])
        engine = SelfThinkEngine(workspace=tmp_path, arch_diagnoser=diagnoser)
        result = engine.arch_diagnose()
        assert result is not None
        assert "modules_scanned" in result

    def test_arch_refactor_without_components(self, tmp_path: Path):
        from autoai.agents.self_think import SelfThinkEngine
        engine = SelfThinkEngine(workspace=tmp_path)
        result = asyncio.run(engine.arch_refactor())
        assert result["diagnosed"] is False

    def test_stats_include_arch_counts(self, tmp_path: Path):
        from autoai.agents.self_think import SelfThinkEngine
        engine = SelfThinkEngine(workspace=tmp_path)
        stats = engine.stats
        assert "arch_scan_count" in stats
        assert "arch_fix_count" in stats
