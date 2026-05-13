"""Tests for Phase 20: L5 full autonomy — unattended runner, evolution loop, community."""

from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock

import pytest

from governance.autonomy_level import AutonomyLevel, AutonomyManager
from governance.modification_chain import ModificationChain
from governance.experience_store import ExperienceStore
from autogpt.agents.unattended_runner import (
    HealthStatus,
    Heartbeat,
    RunJournalEntry,
    RunnerState,
    UnattendedRunner,
    WatchdogEntry,
)
from autogpt.agents.full_evolution_loop import (
    EvolutionCycleResult,
    FullEvolutionLoop,
)
from autogpt.agents.arch_diagnoser import ArchDiagnoser
from autogpt.agents.arch_refactorer import ArchRefactorer
from autogpt.agents.evolution_community import (
    CommunityMember,
    DistilledRule,
    EvolutionCommunity,
    PeerReview,
    ReviewVerdict,
)


# ==================== UnattendedRunner ====================

class TestUnattendedRunner:
    def test_initial_state(self):
        runner = UnattendedRunner()
        assert runner.state == RunnerState.IDLE
        assert runner.uptime_seconds == 0.0

    def test_is_l5_check(self):
        runner = UnattendedRunner()
        assert not runner.is_l5
        runner.autonomy._level = AutonomyLevel.AUTONOMOUS
        assert runner.is_l5

    def test_register_agent(self):
        runner = UnattendedRunner()
        runner.register_agent("a1", think_fn=lambda: None, heartbeat_interval=10)
        assert "a1" in runner._agents
        assert "a1" in runner._watchdogs

    def test_journal_recording(self):
        runner = UnattendedRunner()
        runner._record_journal("test_event", agent_id="a1", decision="test", outcome="ok")
        entries = runner.get_journal()
        assert len(entries) == 1
        assert entries[0].event == "test_event"

    def test_journal_with_filter(self):
        runner = UnattendedRunner()
        runner._record_journal("event_a", decision="d1")
        runner._record_journal("event_b", decision="d2")
        runner._record_journal("event_a", decision="d3")
        entries = runner.get_journal(event_filter="event_a")
        assert len(entries) == 2

    def test_health_default(self):
        runner = UnattendedRunner()
        assert runner.get_health("unknown") == HealthStatus.CRITICAL

    def test_heartbeat_dataclass(self):
        hb = Heartbeat(agent_id="a1", status=HealthStatus.HEALTHY, sequence=5)
        assert hb.agent_id == "a1"
        assert hb.sequence == 5

    def test_watchdog_entry(self):
        wd = WatchdogEntry(agent_id="a1", timeout_seconds=30.0, max_misses=3)
        assert wd.miss_count == 0

    def test_journal_entry_dataclass(self):
        entry = RunJournalEntry(event="test", agent_id="a1")
        assert entry.event == "test"

    def test_status(self):
        runner = UnattendedRunner()
        status = runner.get_status()
        assert "state" in status
        assert "uptime_seconds" in status
        assert "is_l5" in status

    @pytest.mark.asyncio
    async def test_short_run_and_stop(self):
        runner = UnattendedRunner()
        runner.autonomy._level = AutonomyLevel.AUTONOMOUS
        call_count = 0

        async def think():
            nonlocal call_count
            call_count += 1
            return "ok"

        runner.register_agent("a1", think_fn=think, heartbeat_interval=0.1)
        runner._watchdog_timeout = 5.0

        run_task = asyncio.create_task(runner.start())
        await asyncio.sleep(0.5)
        runner.stop()
        await asyncio.sleep(0.2)
        assert call_count >= 1
        assert runner.state == RunnerState.STOPPED


# ==================== FullEvolutionLoop ====================

class TestFullEvolutionLoop:
    def test_initial_state(self):
        loop = FullEvolutionLoop()
        assert loop.cycle_count == 0
        assert loop.last_result is None

    @pytest.mark.asyncio
    async def test_empty_cycle(self):
        loop = FullEvolutionLoop()
        result = await loop.run_cycle()
        assert result.success
        assert result.cycle_id != ""
        assert result.duration_seconds >= 0

    @pytest.mark.asyncio
    async def test_cycle_with_diagnoser(self, tmp_path: Path):
        diagnoser = ArchDiagnoser(workspace=tmp_path, scan_dirs=[])
        loop = FullEvolutionLoop(diagnoser=diagnoser)
        result = await loop.run_cycle()
        assert result.success
        assert "modules_scanned" in result.diagnosis

    @pytest.mark.asyncio
    async def test_cycle_with_protocol_upgrader(self):
        from autogpt.agents.protocol_upgrader import ProtocolUpgrader, ProtocolVersion
        upgrader = ProtocolUpgrader()
        upgrader.register_agent("a1", [ProtocolVersion(1, 1, 0)])
        loop = FullEvolutionLoop(protocol_upgrader=upgrader)
        result = await loop.run_cycle()
        assert result.success
        assert "a1" in result.protocol_upgrades

    @pytest.mark.asyncio
    async def test_multiple_cycles(self):
        loop = FullEvolutionLoop()
        for _ in range(3):
            result = await loop.run_cycle()
            assert result.success
        assert loop.cycle_count == 3

    @pytest.mark.asyncio
    async def test_cycle_result_fields(self):
        loop = FullEvolutionLoop()
        result = await loop.run_cycle()
        assert result.started_at != ""
        assert result.completed_at != ""
        assert result.duration_seconds >= 0
        assert isinstance(result.errors, list)

    def test_status(self):
        loop = FullEvolutionLoop()
        status = loop.get_status()
        assert "cycle_count" in status
        assert "autonomy_level" in status


# ==================== EvolutionCommunity ====================

class TestEvolutionCommunity:
    def test_join(self):
        community = EvolutionCommunity()
        community.join("a1", specializations=["python"])
        assert community.member_count == 1
        member = community._members["a1"]
        assert "python" in member.specializations

    def test_leave(self):
        community = EvolutionCommunity()
        community.join("a1")
        community.leave("a1")
        assert community.member_count == 0

    def test_record_outcome_success(self):
        community = EvolutionCommunity()
        community.join("a1")
        community.record_outcome("a1", success=True)
        member = community._members["a1"]
        assert member.successful_fixes == 1
        assert member.reputation > 1.0

    def test_record_outcome_failure(self):
        community = EvolutionCommunity()
        community.join("a1")
        community.record_outcome("a1", success=False)
        member = community._members["a1"]
        assert member.failed_fixes == 1

    def test_success_rate(self):
        community = EvolutionCommunity()
        community.join("a1")
        community.record_outcome("a1", success=True)
        community.record_outcome("a1", success=True)
        community.record_outcome("a1", success=False)
        member = community._members["a1"]
        assert abs(member.success_rate - 2.0 / 3.0) < 0.01

    def test_broadcast_experience(self):
        community = EvolutionCommunity()
        community.join("a1")
        fid = community.broadcast_experience("a1", "circular_import_fix", "Use lazy imports")
        assert fid != ""

    def test_query_knowledge(self):
        community = EvolutionCommunity()
        community.join("a1")
        community.broadcast_experience("a1", "perf_fix", "Optimize loop", topic="performance")
        results = community.query_community_knowledge(topic="performance")
        assert len(results) >= 1

    def test_peer_review(self):
        community = EvolutionCommunity(min_reviews_for_approval=2)
        community.join("a1")
        community.join("a2")
        community.join("a3")
        community.submit_review("a2", "a1", "mod1", ReviewVerdict.APPROVE, "Looks good")
        community.submit_review("a3", "a1", "mod1", ReviewVerdict.APPROVE, "LGTM")
        assert community.check_approval("mod1")

    def test_peer_review_rejection(self):
        community = EvolutionCommunity(min_reviews_for_approval=2)
        community.join("a1")
        community.join("a2")
        community.join("a3")
        community.submit_review("a2", "a1", "mod1", ReviewVerdict.REJECT, "Bad")
        community.submit_review("a3", "a1", "mod1", ReviewVerdict.REJECT, "Nope")
        assert not community.check_approval("mod1")

    def test_distill_knowledge(self):
        community = EvolutionCommunity()
        community.join("a1")
        community.join("a2")
        community.join("a3")
        for aid in ["a1", "a2", "a3"]:
            community.broadcast_experience(aid, "common_fix", "Fix pattern content", topic="fixes", tags=["common_fix"])
        rules = community.distill_knowledge(min_samples=2, min_success_rate=0.2)
        assert len(rules) >= 1

    def test_top_contributors(self):
        community = EvolutionCommunity()
        community.join("a1")
        community.join("a2")
        for _ in range(5):
            community.record_outcome("a1", success=True)
        for _ in range(2):
            community.record_outcome("a2", success=True)
        top = community.get_top_contributors()
        assert top[0].agent_id == "a1"

    def test_reputation_decay(self):
        community = EvolutionCommunity(reputation_decay=0.9)
        community.join("a1")
        community._members["a1"].reputation = 2.0
        community.apply_reputation_decay()
        assert community._members["a1"].reputation < 2.0

    def test_community_member_dataclass(self):
        m = CommunityMember(agent_id="a1", reputation=1.5)
        assert abs(m.success_rate - 0.5) < 0.01

    def test_distilled_rule_dataclass(self):
        r = DistilledRule(pattern="test_pattern", success_rate=0.85, sample_count=10)
        assert r.success_rate == 0.85

    def test_status(self):
        community = EvolutionCommunity()
        s = community.get_status()
        assert "members" in s
        assert "distilled_rules" in s
