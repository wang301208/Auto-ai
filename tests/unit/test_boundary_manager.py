"""Tests for Agent-autonomous boundary management (Phase: Boundary Manager).

Validates the three-phase boundary lifecycle:
  1. autonomous_init()  - Agent defines initial constraints
  2. autonomous_adjust() - Agent dynamically tunes constraints
  3. autonomous_break()  - Agent breaks constraints when they block goals

Also validates:
  - No human intervention in any boundary decision
  - Break log records for post-hoc audit
  - Risk multiplier convergence (breaks become harder over time)
  - Compensation mechanism after breaks
  - Autonomy level self-management
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from governance.boundary_manager import (
    AUTONOMY_PRESETS,
    SEED_CONSTRAINTS,
    BoundaryManager,
    Constraint,
    ConstraintKind,
    ConstraintSet,
)
from governance.break_log import BreakLog, BreakRecord
from governance.break_report import BreakReport
from governance.autonomy_level import AutonomyLevel, AutonomyManager


@pytest.fixture
def tmp_dir():
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)


@pytest.fixture
def boundary_manager(tmp_dir):
    from governance.audit import AuditLog
    from governance.break_log import BreakLog
    audit = AuditLog(log_path=tmp_dir / "audit.jsonl")
    break_log = BreakLog(log_path=tmp_dir / "break_log.jsonl")
    return BoundaryManager(
        agent_id="test-agent",
        audit_log=audit,
        break_log=break_log,
    )


class TestBoundaryInit:
    def test_autonomous_init_creates_constraints(self, boundary_manager):
        cs = boundary_manager.autonomous_init(task_goal="Fix all lint errors")
        assert cs is not None
        assert cs.agent_id == "test-agent"
        assert len(cs.constraints) > 0

    def test_autonomous_init_has_all_constraint_kinds(self, boundary_manager):
        cs = boundary_manager.autonomous_init()
        for kind in ConstraintKind:
            assert kind in cs.constraints, f"Missing constraint: {kind}"

    def test_autonomous_init_applies_autonomy_preset(self, boundary_manager):
        cs = boundary_manager.autonomous_init()
        level = boundary_manager.autonomy.level
        preset = AUTONOMY_PRESETS.get(level, {})
        for kind, value in preset.items():
            if kind in cs.constraints:
                assert cs.constraints[kind].value == value

    def test_autonomous_init_with_env_hints(self, boundary_manager):
        cs = boundary_manager.autonomous_init(
            environment_hints={"network_available": False}
        )
        assert cs.constraints[ConstraintKind.NETWORK_ACCESS].value is False
        assert cs.constraints[ConstraintKind.NETWORK_ACCESS].breakable is False

    def test_autonomous_init_records_audit(self, boundary_manager, tmp_dir):
        boundary_manager.autonomous_init(task_goal="Test goal")
        from governance.audit import AuditLog
        log = AuditLog(log_path=tmp_dir / "audit.jsonl")
        entries = log.query(limit=10)
        init_entries = [e for e in entries if e.operation == "boundary_init"]
        assert len(init_entries) == 1


class TestBoundaryAdjust:
    def test_autonomous_adjust_numeric(self, boundary_manager):
        boundary_manager.autonomous_init()
        initial = boundary_manager.constraints.constraints[ConstraintKind.TOKEN_BUDGET].value
        cs = boundary_manager.autonomous_adjust(
            {ConstraintKind.TOKEN_BUDGET: initial * 3},
            reason="task_needs_more_tokens",
        )
        budget = cs.constraints[ConstraintKind.TOKEN_BUDGET].value
        assert budget > initial
        assert budget <= initial * 1.3 + 1

    def test_autonomous_adjust_non_numeric(self, boundary_manager):
        boundary_manager.autonomous_init()
        cs = boundary_manager.autonomous_adjust(
            {ConstraintKind.SHELL_EXECUTE: "unsandboxed"},
            reason="need_direct_shell",
        )
        assert cs.constraints[ConstraintKind.SHELL_EXECUTE].value == "unsandboxed"

    def test_autonomous_adjust_records_audit(self, boundary_manager, tmp_dir):
        boundary_manager.autonomous_init()
        boundary_manager.autonomous_adjust(
            {ConstraintKind.TOKEN_BUDGET: 200000},
            reason="test",
        )
        from governance.audit import AuditLog
        log = AuditLog(log_path=tmp_dir / "audit.jsonl")
        entries = log.query(limit=10)
        adjust_entries = [e for e in entries if e.operation == "boundary_adjust"]
        assert len(adjust_entries) == 1

    def test_adjust_gradient_escalation(self, boundary_manager):
        boundary_manager.autonomous_init()
        initial = boundary_manager.constraints.constraints[ConstraintKind.TOKEN_BUDGET].value
        for _ in range(4):
            boundary_manager.autonomous_adjust(
                {ConstraintKind.TOKEN_BUDGET: initial * 10},
                reason="escalation_test",
            )
        budget = boundary_manager.constraints.constraints[ConstraintKind.TOKEN_BUDGET].value
        assert budget > initial

    def test_adjust_before_init_raises(self, boundary_manager):
        with pytest.raises(RuntimeError, match="not initialized"):
            boundary_manager.autonomous_adjust({ConstraintKind.TOKEN_BUDGET: 200000})


class TestBoundaryBreak:
    def test_autonomous_break_allowed(self, boundary_manager):
        boundary_manager.autonomous_init()
        record = boundary_manager.autonomous_break(
            kind=ConstraintKind.TOKEN_BUDGET,
            new_value=500000,
            goal_value=10.0,
            break_risk=2.0,
        )
        assert record.decision == "break_executed"
        assert record.old_value != record.new_value

    def test_autonomous_break_rejected_high_risk(self, boundary_manager):
        boundary_manager.autonomous_init()
        record = boundary_manager.autonomous_break(
            kind=ConstraintKind.TOKEN_BUDGET,
            new_value=500000,
            goal_value=0.1,
            break_risk=100.0,
        )
        assert record.decision == "break_rejected_risk_too_high"

    def test_risk_multiplier_increases(self, boundary_manager):
        boundary_manager.autonomous_init()
        r1 = boundary_manager.autonomous_break(
            ConstraintKind.TOKEN_BUDGET, 200000, goal_value=10.0, break_risk=2.0,
        )
        r2 = boundary_manager.autonomous_break(
            ConstraintKind.TOKEN_BUDGET, 300000, goal_value=10.0, break_risk=2.0,
        )
        assert r2.risk_multiplier > r1.risk_multiplier

    def test_compensation_after_break(self, boundary_manager):
        boundary_manager.autonomous_init()
        record = boundary_manager.autonomous_break(
            ConstraintKind.TOKEN_BUDGET, 500000,
            goal_value=10.0, break_risk=1.0,
        )
        assert record.decision == "break_executed"
        assert "sandbox_strictness" in record.compensation or "token_budget" in record.compensation

    def test_unbreakable_constraint(self, boundary_manager):
        boundary_manager.autonomous_init(
            environment_hints={"network_available": False},
        )
        record = boundary_manager.autonomous_break(
            ConstraintKind.NETWORK_ACCESS, True,
            goal_value=10.0, break_risk=0.0,
        )
        assert record.decision == "blocked_unbreakable"

    def test_break_creates_break_log_entry(self, boundary_manager, tmp_dir):
        boundary_manager.autonomous_init()
        boundary_manager.autonomous_break(
            ConstraintKind.TOKEN_BUDGET, 200000,
            goal_value=10.0, break_risk=1.0,
        )
        break_log = BreakLog(log_path=tmp_dir / "break_log.jsonl")
        records = break_log.query()
        assert len(records) >= 1


class TestBreakLog:
    def test_record_and_query(self, tmp_dir):
        bl = BreakLog(log_path=tmp_dir / "breaks.jsonl")
        rec = bl.record(
            constraint_kind="token_budget",
            old_value=100000,
            new_value=200000,
            goal_value=10.0,
            break_risk=2.0,
            decision="break_executed",
            agent_id="test",
        )
        assert rec.record_id
        results = bl.query()
        assert len(results) == 1
        assert results[0].constraint_kind == "token_budget"

    def test_query_by_kind(self, tmp_dir):
        bl = BreakLog(log_path=tmp_dir / "breaks.jsonl")
        bl.record(constraint_kind="token_budget", old_value=100, new_value=200, decision="break_executed", agent_id="a")
        bl.record(constraint_kind="shell_execute", old_value="sandboxed", new_value="unsandboxed", decision="break_executed", agent_id="a")
        assert len(bl.query(constraint_kind="token_budget")) == 1

    def test_stats(self, tmp_dir):
        bl = BreakLog(log_path=tmp_dir / "breaks.jsonl")
        bl.record(constraint_kind="token_budget", old_value=100, new_value=200, decision="break_executed", agent_id="a")
        bl.record(constraint_kind="token_budget", old_value=200, new_value=300, decision="break_rejected_risk_too_high", agent_id="a")
        stats = bl.stats()
        assert stats["total"] == 2
        assert stats["by_constraint_kind"]["token_budget"] == 2


class TestBreakReport:
    def test_generate_report(self, tmp_dir):
        bl = BreakLog(log_path=tmp_dir / "breaks.jsonl")
        bl.record(
            constraint_kind="token_budget", old_value=100000, new_value=200000,
            goal_value=10.0, break_risk=2.0, risk_multiplier=1.0,
            decision="break_executed", compensation={"monitor": True},
            alternative_paths=["use_smaller_model"], agent_id="test",
        )
        reporter = BreakReport(break_log=bl)
        report = reporter.generate()
        assert "token_budget" in report
        assert "break_executed" in report

    def test_summary_only(self, tmp_dir):
        bl = BreakLog(log_path=tmp_dir / "breaks.jsonl")
        bl.record(constraint_kind="token_budget", old_value=100, new_value=200, decision="break_executed", agent_id="a")
        reporter = BreakReport(break_log=bl)
        report = reporter.generate(summary_only=True)
        assert "Summary" in report


class TestAutonomyLevelSelfManage:
    def test_autonomous_adjust_level(self):
        mgr = AutonomyManager(agent_id="test", initial_level=AutonomyLevel.SELF_BOUND)
        mgr.autonomous_adjust_level(reason="agent_self_eval")
        assert mgr.level == AutonomyLevel.SELF_BOUND

    def test_no_force_level(self):
        mgr = AutonomyManager(agent_id="test")
        assert not hasattr(mgr, "force_level")

    def test_auto_escalate(self):
        mgr = AutonomyManager(
            agent_id="test",
            initial_level=AutonomyLevel.SELF_BOUND,
            config=type('', (), {'successes_to_escalate': 3, 'failures_to_de_escalate': 3, 'max_level': AutonomyLevel.AUTONOMOUS, 'min_level': AutonomyLevel.MANUAL, 'escalation_cooldown_seconds': 0.0})(),
        )
        for _ in range(3):
            mgr.record_success()
        assert mgr.level > AutonomyLevel.SELF_BOUND


class TestBoundaryManagerStats:
    def test_stats(self, boundary_manager):
        boundary_manager.autonomous_init()
        stats = boundary_manager.stats()
        assert stats["agent_id"] == "test-agent"
        assert stats["constraints_initialized"] is True
        assert stats["break_count"] == 0
