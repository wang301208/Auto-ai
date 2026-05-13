"""Tests for Phase 7: Health Monitor, Workflow Checkpoint, Agent Pool."""

import asyncio
import json
import tempfile
import time
from pathlib import Path

import pytest


class TestAgentHealthMonitor:
    """Test health monitoring, heartbeat, and eviction."""

    def test_register_and_heartbeat(self):
        from autogpt.agents.health_monitor import AgentHealthMonitor, AgentHealthStatus
        monitor = AgentHealthMonitor()
        monitor.register("a1", role="coder")
        assert monitor.get_status("a1") == AgentHealthStatus.HEALTHY
        monitor.heartbeat("a1")
        status = monitor.get_all_status()
        assert "a1" in status
        assert status["a1"]["heartbeat_count"] == 1

    def test_consecutive_misses_detection(self):
        from autogpt.agents.health_monitor import (
            AgentHealthMonitor, HealthCheckConfig, AgentHealthStatus,
        )
        config = HealthCheckConfig(
            heartbeat_interval_seconds=1.0,
            unhealthy_threshold=2,
            dead_threshold=5,
            eviction_threshold=10,
            check_interval_seconds=0.5,
            auto_evict=False,
        )
        monitor = AgentHealthMonitor(config=config)
        monitor.register("a1", role="coder")
        monitor.heartbeat("a1")
        time.sleep(4.0)
        monitor._perform_check()
        status = monitor.get_status("a1")
        assert status in {AgentHealthStatus.UNHEALTHY, AgentHealthStatus.DEGRADED}

    def test_recovery_after_heartbeat(self):
        from autogpt.agents.health_monitor import AgentHealthMonitor, AgentHealthStatus
        monitor = AgentHealthMonitor()
        monitor.register("a1")
        monitor._records["a1"].status = AgentHealthStatus.DEGRADED
        monitor._records["a1"].consecutive_misses = 2
        monitor.heartbeat("a1")
        assert monitor.get_status("a1") == AgentHealthStatus.HEALTHY

    def test_healthy_agents_filter(self):
        from autogpt.agents.health_monitor import AgentHealthMonitor, AgentHealthStatus
        monitor = AgentHealthMonitor()
        monitor.register("a1", role="coder")
        monitor.register("a2", role="reviewer")
        monitor._records["a2"].status = AgentHealthStatus.UNHEALTHY
        healthy = monitor.get_healthy_agents()
        assert "a1" in healthy
        assert "a2" not in healthy
        coders = monitor.get_healthy_agents(role="coder")
        assert coders == ["a1"]

    def test_eviction_removes_from_comm_bus(self):
        from autogpt.agents.health_monitor import AgentHealthMonitor, AgentHealthStatus
        from autogpt.agents.agent_comm import AgentCommunicationBus
        bus = AgentCommunicationBus()
        bus.register_agent("a1", "coder")
        monitor = AgentHealthMonitor(comm_bus=bus)
        monitor.register("a1")
        monitor._records["a1"].status = AgentHealthStatus.DEAD
        monitor._evict_agent("a1")
        assert "a1" not in bus._mailboxes

    def test_restart_callback(self):
        from autogpt.agents.health_monitor import AgentHealthMonitor, AgentHealthStatus
        restart_log = []
        def on_restart(agent_id, role):
            restart_log.append(agent_id)
            return True
        monitor = AgentHealthMonitor(restart_callback=on_restart)
        monitor.register("a1")
        monitor._records["a1"].status = AgentHealthStatus.UNHEALTHY
        monitor._restart_agent("a1")
        assert "a1" in restart_log


class TestWorkflowCheckpoint:
    """Test workflow checkpoint save/load/restore."""

    def test_save_and_load(self):
        from autogpt.agents.workflow_checkpoint import WorkflowCheckpoint, CheckpointManager
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = CheckpointManager(checkpoint_dir=tmpdir)
            ckpt = WorkflowCheckpoint(
                workflow_id="w1",
                workflow_name="test",
                task_states={"t1": "success", "t2": "pending"},
                task_results={"t1": {"output": "done"}},
            )
            path = mgr.save(ckpt)
            assert path.exists()
            loaded = mgr.load("w1")
            assert loaded is not None
            assert loaded.workflow_name == "test"
            assert loaded.task_states["t1"] == "success"
            assert loaded.task_results["t1"]["output"] == "done"

    def test_delete(self):
        from autogpt.agents.workflow_checkpoint import WorkflowCheckpoint, CheckpointManager
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = CheckpointManager(checkpoint_dir=tmpdir)
            ckpt = WorkflowCheckpoint(workflow_id="w1")
            mgr.save(ckpt)
            assert mgr.delete("w1") is True
            assert mgr.load("w1") is None

    def test_list_checkpoints(self):
        from autogpt.agents.workflow_checkpoint import WorkflowCheckpoint, CheckpointManager
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = CheckpointManager(checkpoint_dir=tmpdir)
            mgr.save(WorkflowCheckpoint(workflow_id="w1", workflow_name="a"))
            mgr.save(WorkflowCheckpoint(workflow_id="w2", workflow_name="b"))
            listing = mgr.list_checkpoints()
            assert len(listing) == 2

    def test_snapshot_and_restore_workflow(self):
        from autogpt.agents.workflow_orchestrator import WorkflowDAG, WorkflowTask, TaskState
        from autogpt.agents.workflow_checkpoint import CheckpointManager
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = CheckpointManager(checkpoint_dir=tmpdir)
            dag = WorkflowDAG("test", workflow_id="w1")
            t1 = WorkflowTask(name="t1")
            t2 = WorkflowTask(name="t2", dependencies={t1.task_id})
            dag.add_task(t1)
            dag.add_task(t2)
            t1.state = TaskState.SUCCESS
            t1.result = {"output": "done"}
            ckpt = mgr.snapshot_workflow(dag)
            mgr.save(ckpt)

            dag2 = WorkflowDAG("test", workflow_id="w1")
            t1b = WorkflowTask(task_id=t1.task_id, name="t1")
            t2b = WorkflowTask(task_id=t2.task_id, name="t2", dependencies={t1b.task_id})
            dag2.add_task(t1b)
            dag2.add_task(t2b)
            loaded = mgr.load("w1")
            restored = mgr.restore_workflow(dag2, loaded)
            assert restored == 2
            assert t1b.state == TaskState.SUCCESS
            assert t1b.result["output"] == "done"

    def test_round_trip_serialization(self):
        from autogpt.agents.workflow_checkpoint import WorkflowCheckpoint
        ckpt = WorkflowCheckpoint(
            workflow_id="w1",
            workflow_name="test",
            task_states={"t1": "running"},
            task_results={"t1": {"x": 1}},
            task_assignments={"t1": "agent1"},
            task_errors={"t1": ""},
            task_retry_counts={"t1": 0},
            task_dependencies={"t1": []},
        )
        data = ckpt.to_dict()
        restored = WorkflowCheckpoint.from_dict(data)
        assert restored.workflow_id == "w1"
        assert restored.task_states == ckpt.task_states


class TestAgentPool:
    """Test agent pool management and elastic scaling."""

    def test_add_and_remove_agent(self):
        from autogpt.agents.agent_pool import AgentPool
        from autogpt.agents.workflow_orchestrator import WorkflowOrchestrator
        from autogpt.agents.agent_comm import AgentCommunicationBus
        bus = AgentCommunicationBus()
        orch = WorkflowOrchestrator(comm_bus=bus)
        pool = AgentPool(orchestrator=orch, comm_bus=bus)
        pool.add_agent("a1", roles={"coder"})
        status = pool.get_pool_status()
        assert status["total_agents"] == 1
        pool.remove_agent("a1")
        status = pool.get_pool_status()
        assert status["total_agents"] == 0

    def test_permanent_agent_not_removed(self):
        from autogpt.agents.agent_pool import AgentPool
        from autogpt.agents.workflow_orchestrator import WorkflowOrchestrator
        from autogpt.agents.agent_comm import AgentCommunicationBus
        bus = AgentCommunicationBus()
        orch = WorkflowOrchestrator(comm_bus=bus)
        pool = AgentPool(orchestrator=orch, comm_bus=bus)
        pool.add_agent("a1", roles={"coder"}, permanent=True)
        result = pool.remove_agent("a1")
        assert result is False
        assert pool.get_pool_status()["total_agents"] == 1

    def test_default_capabilities(self):
        from autogpt.agents.agent_pool import AgentPool
        caps = AgentPool._default_capabilities("coder")
        assert "plan" in caps
        assert "execute" in caps
        caps_reviewer = AgentPool._default_capabilities("reviewer")
        assert "review" in caps_reviewer

    def test_pool_status_includes_role_counts(self):
        from autogpt.agents.agent_pool import AgentPool
        from autogpt.agents.workflow_orchestrator import WorkflowOrchestrator
        from autogpt.agents.agent_comm import AgentCommunicationBus
        bus = AgentCommunicationBus()
        orch = WorkflowOrchestrator(comm_bus=bus)
        pool = AgentPool(orchestrator=orch, comm_bus=bus)
        pool.add_agent("a1", roles={"coder"})
        pool.add_agent("a2", roles={"reviewer"})
        pool.add_agent("a3", roles={"coder"})
        status = pool.get_pool_status()
        assert status["by_role"]["coder"] == 2
        assert status["by_role"]["reviewer"] == 1


class TestGovernanceDefaultPolicy:
    """Test the updated default policy."""

    def test_default_policy_loads(self):
        from governance.policy import Policy
        from pathlib import Path
        policy_path = Path("governance/default_policy.json")
        policy = Policy.load(policy_path)
        assert policy.name == "default"
        assert len(policy.rules) > 0

    def test_default_policy_has_hard_boundaries(self):
        from governance.policy import Policy, PolicyEffect
        from pathlib import Path
        policy = Policy.load(Path("governance/default_policy.json"))
        deny_ops = {r.operation for r in policy.rules if r.effect == PolicyEffect.DENY}
        assert "budget_exceeded" in deny_ops
        assert "file_delete" in deny_ops
        assert "sandbox_escape" in deny_ops

    def test_default_policy_allows_self_improve(self):
        from governance.policy import Policy, PolicyEffect, PolicyEvaluator
        from pathlib import Path
        policy = Policy.load(Path("governance/default_policy.json"))
        evaluator = PolicyEvaluator(fallback_effect=PolicyEffect.DENY)
        evaluator.add_policy(policy)
        effect, name = evaluator.evaluate("self_improve.scan")
        assert effect == PolicyEffect.ALLOW

    def test_default_policy_allows_agent_comm(self):
        from governance.policy import Policy, PolicyEffect, PolicyEvaluator
        from pathlib import Path
        policy = Policy.load(Path("governance/default_policy.json"))
        evaluator = PolicyEvaluator(fallback_effect=PolicyEffect.DENY)
        evaluator.add_policy(policy)
        effect, name = evaluator.evaluate("agent.direct")
        assert effect == PolicyEffect.ALLOW
