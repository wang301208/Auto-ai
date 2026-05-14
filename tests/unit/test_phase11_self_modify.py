"""Tests for Phase 11: Modification Chain, Autonomy Level, Self-Modify Pipeline."""

import asyncio
import tempfile
import pytest
from pathlib import Path


class TestModificationChain:
    def test_genesis_hash(self):
        from governance.modification_chain import GENESIS_HASH
        assert len(GENESIS_HASH) == 64
        assert GENESIS_HASH == "0" * 64

    def test_append_single_block(self):
        from governance.modification_chain import ModificationChain, ModificationType, ModificationStatus
        chain = ModificationChain()
        block = chain.append(
            agent_id="test-agent",
            patch_diff="--- a/foo.py\n+++ b/foo.py\n@@ -1 +1 @@\n-old\n+new\n",
            target_files=["foo.py"],
            mod_type=ModificationType.CODE_PATCH,
            autonomy_level=2,
        )
        assert block.index == 0
        assert block.prev_hash == "0" * 64
        assert block.hash != "0" * 64
        assert block.status == ModificationStatus.PENDING
        assert chain.length == 1

    def test_append_with_test_result(self):
        from governance.modification_chain import ModificationChain, ModificationType, TestResult, ModificationStatus
        chain = ModificationChain()
        block = chain.append(
            agent_id="test",
            patch_diff="fix",
            target_files=["a.py"],
            test_result=TestResult(passed=True, test_count=10),
        )
        assert block.status == ModificationStatus.TEST_PASSED
        assert block.test_result.passed

    def test_append_failed_test(self):
        from governance.modification_chain import ModificationChain, TestResult, ModificationStatus
        chain = ModificationChain()
        block = chain.append(
            agent_id="test",
            patch_diff="fix",
            target_files=["a.py"],
            test_result=TestResult(passed=False, fail_count=2),
        )
        assert block.status == ModificationStatus.TEST_FAILED

    def test_chain_integrity(self):
        from governance.modification_chain import ModificationChain, ModificationType
        chain = ModificationChain()
        for i in range(5):
            chain.append(
                agent_id="test",
                patch_diff=f"patch_{i}",
                target_files=[f"file_{i}.py"],
                mod_type=ModificationType.CODE_PATCH,
            )
        ok, bad_idx = chain.verify_integrity()
        assert ok
        assert bad_idx == -1

    def test_chain_hash_linking(self):
        from governance.modification_chain import ModificationChain
        chain = ModificationChain()
        b0 = chain.append(agent_id="a", patch_diff="p0", target_files=["f0"])
        b1 = chain.append(agent_id="a", patch_diff="p1", target_files=["f1"])
        assert b1.prev_hash == b0.hash

    def test_mark_reverted(self):
        from governance.modification_chain import ModificationChain, ModificationStatus
        chain = ModificationChain()
        block = chain.append(agent_id="a", patch_diff="p", target_files=["f"])
        chain.mark_reverted(0)
        assert chain.get_block(0).status == ModificationStatus.REVERTED

    def test_mark_hot_reloaded(self):
        from governance.modification_chain import ModificationChain, ModificationStatus
        chain = ModificationChain()
        block = chain.append(agent_id="a", patch_diff="p", target_files=["f"])
        chain.mark_hot_reloaded(0)
        assert chain.get_block(0).status == ModificationStatus.HOT_RELOADED

    def test_persistence(self):
        from governance.modification_chain import ModificationChain
        with tempfile.TemporaryDirectory() as tmpdir:
            ws = Path(tmpdir)
            chain1 = ModificationChain(workspace=ws)
            chain1.append(agent_id="a", patch_diff="p1", target_files=["f1"])
            chain1.append(agent_id="a", patch_diff="p2", target_files=["f2"])

            chain2 = ModificationChain(workspace=ws)
            assert chain2.length == 2
            ok, _ = chain2.verify_integrity()
            assert ok

    def test_stats(self):
        from governance.modification_chain import ModificationChain, ModificationType, TestResult
        chain = ModificationChain()
        chain.append(agent_id="a", patch_diff="p1", target_files=["f1"],
                       test_result=TestResult(passed=True))
        chain.append(agent_id="a", patch_diff="p2", target_files=["f2"],
                       test_result=TestResult(passed=False))
        s = chain.stats()
        assert s["total"] == 2
        assert s["by_status"]["test_passed"] == 1
        assert s["by_status"]["test_failed"] == 1
        assert s["integrity_ok"] is True

    def test_recent_blocks(self):
        from governance.modification_chain import ModificationChain
        chain = ModificationChain()
        for i in range(20):
            chain.append(agent_id="a", patch_diff=f"p{i}", target_files=[f"f{i}"])
        recent = chain.recent_blocks(5)
        assert len(recent) == 5
        assert recent[-1].index == 19


class TestAutonomyLevel:
    def test_level_values(self):
        from governance.autonomy_level import AutonomyLevel
        assert AutonomyLevel.MANUAL == 0
        assert AutonomyLevel.AUTONOMOUS == 5

    def test_capabilities_l0(self):
        from governance.autonomy_level import AutonomyLevel, AutonomyCapabilities
        caps = AutonomyCapabilities.for_level(AutonomyLevel.MANUAL)
        assert not caps.can_modify_code
        assert not caps.can_auto_commit

    def test_capabilities_l2(self):
        from governance.autonomy_level import AutonomyLevel, AutonomyCapabilities
        caps = AutonomyCapabilities.for_level(AutonomyLevel.SELF_BOUND)
        assert caps.can_modify_code
        assert caps.can_auto_commit
        assert caps.can_hot_reload
        assert not caps.can_self_rewrite

    def test_capabilities_l3(self):
        from governance.autonomy_level import AutonomyLevel, AutonomyCapabilities
        caps = AutonomyCapabilities.for_level(AutonomyLevel.SELF_REWRITE)
        assert caps.can_self_rewrite
        assert caps.can_auto_push
        assert caps.can_skip_approval

    def test_capabilities_l4(self):
        from governance.autonomy_level import AutonomyLevel, AutonomyCapabilities
        caps = AutonomyCapabilities.for_level(AutonomyLevel.SELF_SPAWN)
        assert caps.can_create_agents
        assert caps.can_destroy_agents

    def test_escalation(self):
        from governance.autonomy_level import AutonomyLevel, AutonomyManager, AutonomyConfig
        config = AutonomyConfig(successes_to_escalate=5, escalation_cooldown_seconds=0)
        mgr = AutonomyManager(agent_id="test", initial_level=AutonomyLevel.SUPERVISED, config=config)
        for _ in range(5):
            result = mgr.record_success()
        assert mgr.level == AutonomyLevel.SELF_BOUND

    def test_de_escalation(self):
        from governance.autonomy_level import AutonomyLevel, AutonomyManager, AutonomyConfig
        config = AutonomyConfig(failures_to_de_escalate=2, escalation_cooldown_seconds=0)
        mgr = AutonomyManager(agent_id="test", initial_level=AutonomyLevel.SELF_BOUND, config=config)
        mgr.record_failure()
        mgr.record_failure()
        assert mgr.level == AutonomyLevel.SUPERVISED

    def test_escalation_and_de_escalation(self):
        from governance.autonomy_level import AutonomyLevel, AutonomyManager, AutonomyConfig
        config = AutonomyConfig(successes_to_escalate=3, failures_to_de_escalate=2, escalation_cooldown_seconds=0)
        mgr = AutonomyManager(agent_id="test", initial_level=AutonomyLevel.SUPERVISED, config=config)
        for _ in range(3):
            mgr.record_success()
        assert mgr.level == AutonomyLevel.SELF_BOUND
        mgr.record_failure()
        mgr.record_failure()
        assert mgr.level == AutonomyLevel.SUPERVISED

    def test_force_level(self):
        from governance.autonomy_level import AutonomyLevel, AutonomyManager
        mgr = AutonomyManager(initial_level=AutonomyLevel.MANUAL)
        mgr.autonomous_adjust_level(reason="agent_self_eval")
        assert mgr.level == AutonomyLevel.MANUAL

    def test_consecutive_counters(self):
        from governance.autonomy_level import AutonomyLevel, AutonomyManager, AutonomyConfig
        config = AutonomyConfig(successes_to_escalate=100, escalation_cooldown_seconds=0)
        mgr = AutonomyManager(config=config)
        mgr.record_success()
        mgr.record_success()
        assert mgr.consecutive_successes == 2
        mgr.record_failure()
        assert mgr.consecutive_successes == 0
        assert mgr.consecutive_failures == 1

    def test_stats(self):
        from governance.autonomy_level import AutonomyLevel, AutonomyManager, AutonomyConfig
        config = AutonomyConfig(successes_to_escalate=100, escalation_cooldown_seconds=0)
        mgr = AutonomyManager(config=config)
        mgr.record_success()
        mgr.record_failure()
        s = mgr.stats()
        assert s["total_successes"] == 1
        assert s["total_failures"] == 1


class TestSelfModifyPipeline:
    def test_can_modify_l2(self):
        from autoai.agents.self_modify import SelfModifyPipeline
        from governance.autonomy_level import AutonomyLevel, AutonomyManager
        autonomy = AutonomyManager(initial_level=AutonomyLevel.SELF_BOUND)
        pipeline = SelfModifyPipeline(workspace=Path("/tmp"), autonomy=autonomy)
        assert pipeline.can_modify is True

    def test_cannot_modify_l1(self):
        from autoai.agents.self_modify import SelfModifyPipeline
        from governance.autonomy_level import AutonomyLevel, AutonomyManager
        autonomy = AutonomyManager(initial_level=AutonomyLevel.SUPERVISED)
        pipeline = SelfModifyPipeline(workspace=Path("/tmp"), autonomy=autonomy)
        assert pipeline.can_modify is False

    def test_can_hot_reload_l3(self):
        from autoai.agents.self_modify import SelfModifyPipeline
        from governance.autonomy_level import AutonomyLevel, AutonomyManager
        autonomy = AutonomyManager(initial_level=AutonomyLevel.SELF_REWRITE)
        pipeline = SelfModifyPipeline(workspace=Path("/tmp"), autonomy=autonomy)
        assert pipeline.can_hot_reload is True
        assert pipeline.can_auto_push is True

    @pytest.mark.asyncio
    async def test_low_autonomy_returns_suggestion(self):
        from autoai.agents.self_modify import SelfModifyPipeline
        from governance.autonomy_level import AutonomyLevel, AutonomyManager
        autonomy = AutonomyManager(initial_level=AutonomyLevel.MANUAL)
        pipeline = SelfModifyPipeline(workspace=Path("/tmp"), autonomy=autonomy)
        result = await pipeline.execute_modification(
            patch_diff="fix",
            target_files=["foo.py"],
        )
        assert result["success"] is False
        assert "suggestion" in result

    def test_sandbox_workspace_context_manager(self):
        from autoai.agents.self_modify import SandboxWorkspace
        with tempfile.TemporaryDirectory() as tmpdir:
            src = Path(tmpdir) / "src"
            src.mkdir()
            (src / "test.py").write_text("x = 1")
            with SandboxWorkspace(src) as sandbox_path:
                assert sandbox_path.exists()
                assert (sandbox_path / "test.py").exists()
                assert (sandbox_path / "test.py").read_text() == "x = 1"
            assert not sandbox_path.exists()

    def test_file_to_module(self):
        from autoai.agents.self_modify import SelfModifyPipeline
        from governance.autonomy_level import AutonomyManager
        pipeline = SelfModifyPipeline(workspace=Path("/tmp"))
        assert pipeline._file_to_module("autoai/agents/agent.py") == "autoai.agents.agent"
        assert pipeline._file_to_module("autoai/agents/__init__.py") == "autoai.agents"
        assert pipeline._file_to_module("data.json") is None


class TestSelfThinkWithPipeline:
    @pytest.mark.asyncio
    async def test_auto_fix_with_pipeline_l2(self):
        from autoai.agents.self_think import SelfThinkEngine, SelfReviewSource
        from autoai.agents.self_modify import SelfModifyPipeline
        from autoai.core.planning.schema import Task, TaskType
        from governance.autonomy_level import AutonomyLevel, AutonomyManager

        class MockSource(SelfReviewSource):
            name = "mock"
            def discover(self, workspace):
                return [{"objective": "Fix bug X", "type": TaskType.CODE, "priority": 2, "context": "bug"}]

        autonomy = AutonomyManager(initial_level=AutonomyLevel.SELF_BOUND)
        pipeline = SelfModifyPipeline(workspace=Path("/tmp/nonexistent"), autonomy=autonomy)
        engine = SelfThinkEngine(
            workspace=Path("/tmp"),
            sources=[MockSource()],
            auto_fix=True,
            self_modify_pipeline=pipeline,
        )
        queue = []
        summary = await engine.auto_fix_cycle(queue)
        assert summary["discovered"] == 1
        assert "self_modified" in summary

    @pytest.mark.asyncio
    async def test_auto_fix_without_pipeline_fallback(self):
        from autoai.agents.self_think import SelfThinkEngine, SelfReviewSource
        from autoai.core.planning.schema import Task, TaskType

        class MockSource(SelfReviewSource):
            name = "mock"
            def discover(self, workspace):
                return [{"objective": "Fix issue", "type": TaskType.CODE, "priority": 1, "context": "test"}]

        engine = SelfThinkEngine(workspace=Path("/tmp"), sources=[MockSource()], auto_fix=True)
        queue = []
        summary = await engine.auto_fix_cycle(queue)
        assert summary["discovered"] == 1
        assert summary.get("self_modified", 0) == 0
