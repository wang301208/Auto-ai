"""Tests for self-evolution closed loop and Config→ModelRouter bridging."""

import asyncio
import pytest
import tempfile
from pathlib import Path


class TestSelfThinkClosedLoop:
    def test_engine_new_fields(self):
        from autogpt.agents.self_think import SelfThinkEngine
        engine = SelfThinkEngine(workspace=Path("/tmp"), auto_fix=True, verify_after_fix=True)
        assert engine.auto_fix
        assert engine.verify_after_fix
        assert engine._fix_count == 0
        assert engine._fix_success == 0

    def test_scan_inject(self):
        from autogpt.agents.self_think import SelfThinkEngine, SelfReviewSource
        from autogpt.core.planning.schema import Task, TaskType

        class MockSource(SelfReviewSource):
            name = "mock"
            def discover(self, workspace):
                return [{"objective": "Fix issue X", "type": TaskType.EDIT, "priority": 3, "context": "test"}]

        engine = SelfThinkEngine(workspace=Path("/tmp"), sources=[MockSource()])
        queue = []
        injected = engine.inject_into_queue(queue)
        assert injected == 1
        assert len(queue) == 1
        assert queue[0].objective == "Fix issue X"

    @pytest.mark.asyncio
    async def test_auto_fix_cycle_success(self):
        from autogpt.agents.self_think import SelfThinkEngine, SelfReviewSource
        from autogpt.core.planning.schema import Task, TaskType, TaskStatus

        class MockSource(SelfReviewSource):
            name = "mock"
            def discover(self, workspace):
                return [{"objective": "Fix lint error", "type": TaskType.EDIT, "priority": 2, "context": "lint"}]

        engine = SelfThinkEngine(
            workspace=Path("/tmp"),
            sources=[MockSource()],
            auto_fix=True,
            verify_after_fix=True,
        )

        fix_calls = []

        async def fix_executor(task):
            fix_calls.append(task.objective)
            return {"fixed": True}

        queue = []
        summary = await engine.auto_fix_cycle(queue, fix_executor)

        assert summary["discovered"] == 1
        assert summary["fixed"] == 1
        assert summary["verified"] == 1
        assert len(fix_calls) == 1

    @pytest.mark.asyncio
    async def test_auto_fix_cycle_failure(self):
        from autogpt.agents.self_think import SelfThinkEngine, SelfReviewSource
        from autogpt.core.planning.schema import Task, TaskType

        class MockSource(SelfReviewSource):
            name = "mock"
            def discover(self, workspace):
                return [{"objective": "Fix broken test", "type": TaskType.TEST, "priority": 2, "context": "test"}]

        engine = SelfThinkEngine(
            workspace=Path("/tmp"),
            sources=[MockSource()],
            auto_fix=True,
            verify_after_fix=True,
        )

        async def failing_executor(task):
            raise RuntimeError("fix failed")

        queue = []
        summary = await engine.auto_fix_cycle(queue, failing_executor)

        assert summary["discovered"] == 1
        assert summary["fixed"] == 0
        assert summary["failed"] == 1
        assert len(queue) == 1  # task re-queued

    @pytest.mark.asyncio
    async def test_auto_fix_cycle_no_executor(self):
        from autogpt.agents.self_think import SelfThinkEngine, SelfReviewSource
        from autogpt.core.planning.schema import Task, TaskType

        class MockSource(SelfReviewSource):
            name = "mock"
            def discover(self, workspace):
                return [{"objective": "Improve coverage", "type": TaskType.TEST, "priority": 1, "context": "cov"}]

        engine = SelfThinkEngine(workspace=Path("/tmp"), sources=[MockSource()])
        queue = []
        summary = await engine.auto_fix_cycle(queue, fix_executor=None)

        assert summary["discovered"] == 1
        assert len(queue) == 1  # injected without fix attempt

    @pytest.mark.asyncio
    async def test_auto_fix_with_policy_evolver(self):
        from autogpt.agents.self_think import SelfThinkEngine, SelfReviewSource
        from autogpt.core.planning.schema import Task, TaskType
        from governance import GovernanceGate, PolicyEvolver

        class MockSource(SelfReviewSource):
            name = "mock"
            def discover(self, workspace):
                return [{"objective": "Fix perf issue", "type": TaskType.CODE, "priority": 1, "context": "perf"}]

        gate = GovernanceGate()
        evolver = PolicyEvolver(gate=gate)

        engine = SelfThinkEngine(
            workspace=Path("/tmp"),
            sources=[MockSource()],
            auto_fix=True,
            verify_after_fix=True,
            policy_evolver=evolver,
        )

        async def fix_executor(task):
            return "fixed"

        queue = []
        summary = await engine.auto_fix_cycle(queue, fix_executor)
        assert summary["policy_adjusted"] is True

    def test_stats(self):
        from autogpt.agents.self_think import SelfThinkEngine
        engine = SelfThinkEngine(workspace=Path("/tmp"))
        stats = engine.stats
        assert "scan_count" in stats
        assert "fix_count" in stats
        assert "fix_success" in stats

    def test_history_recording(self):
        from autogpt.agents.self_think import SelfThinkEngine
        engine = SelfThinkEngine(workspace=Path("/tmp"))
        from autogpt.core.planning.schema import Task, TaskType
        task = Task(objective="test", type=TaskType.CODE, priority=1, ready_criteria=[], acceptance_criteria=[])
        engine._record_history(task, "fixed_and_verified", {"success": True})
        assert len(engine._history) == 1
        assert engine._history[0]["outcome"] == "fixed_and_verified"


class TestPolicyEvolverFromCycle:
    def test_evolve_from_cycle_all_success(self):
        from governance import GovernanceGate, PolicyEvolver
        from governance.rate_limit import RateLimitRule
        gate = GovernanceGate()
        gate.rates.add_rule(RateLimitRule(operation="test_op", refill_rate=1.0, max_burst=10.0))
        evolver = PolicyEvolver(gate=gate)
        adjustments = evolver.evolve_from_cycle(fixed_count=3, failed_count=0)
        assert len(adjustments) >= 1
        assert adjustments[0]["type"] == "rate_limit_relax"

    def test_evolve_from_cycle_more_failures(self):
        from governance import GovernanceGate, PolicyEvolver
        gate = GovernanceGate()
        from governance.rate_limit import RateLimitRule
        gate.rates.add_rule(RateLimitRule(operation="*", principal="*", max_burst=10.0, refill_rate=5.0))
        evolver = PolicyEvolver(gate=gate)
        adjustments = evolver.evolve_from_cycle(fixed_count=1, failed_count=3)
        assert len(adjustments) >= 1
        assert adjustments[0]["type"] == "rate_limit_tighten"

    def test_evolve_from_cycle_no_change(self):
        from governance import GovernanceGate, PolicyEvolver
        gate = GovernanceGate()
        evolver = PolicyEvolver(gate=gate)
        adjustments = evolver.evolve_from_cycle(fixed_count=1, failed_count=1)
        assert len(adjustments) == 0


class TestConfigModelRouterBridge:
    def test_alias_setup(self):
        from autogpt.agents.system_bootstrap import MultiAgentSystem, SystemConfig
        with tempfile.TemporaryDirectory() as tmpdir:
            config = SystemConfig(
                enable_health_monitor=False,
                enable_agent_pool=False,
                enable_tui=False,
                enable_model_router=True,
                detect_local_models=False,
            )
            system = MultiAgentSystem(workspace_path=Path(tmpdir), config=config)
            system.setup()

            assert system.model_registry.get_model("fast") is not None
            assert system.model_registry.get_model("smart") is not None
            assert system.model_registry.get_model("embedding") is not None

    def test_resolve_model_alias(self):
        from autogpt.agents.system_bootstrap import MultiAgentSystem, SystemConfig
        with tempfile.TemporaryDirectory() as tmpdir:
            config = SystemConfig(
                enable_health_monitor=False,
                enable_agent_pool=False,
                enable_tui=False,
                enable_model_router=True,
                detect_local_models=False,
            )
            system = MultiAgentSystem(workspace_path=Path(tmpdir), config=config)
            system.setup()

            fast = system._resolve_model_alias("fast")
            smart = system._resolve_model_alias("smart")
            assert fast
            assert smart
            assert system.model_registry.get_model(fast) is not None
            assert system.model_registry.get_model(smart) is not None
