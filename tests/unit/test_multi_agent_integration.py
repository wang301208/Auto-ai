"""Integration tests for Phase 5-6: Multi-Agent, Governance Audit-Net, and Policy Evolution."""

import asyncio
import pytest
import tempfile
import time
from pathlib import Path


class TestGovernanceAuditNet:
    """Test the audit-net governance mode (autonomous default-allow, hard-boundary block)."""

    def test_autonomous_mode_normal_allowed(self):
        from governance.gate import GovernanceGate
        gate = GovernanceGate()
        d = gate.check("file.read", risk_level="low")
        assert d.allowed is True
        assert "audit-net" in d.reason

    def test_autonomous_mode_hard_boundary_blocked(self):
        from governance.gate import GovernanceGate
        gate = GovernanceGate()
        d = gate.check("file_delete", risk_level="critical")
        assert d.allowed is False
        assert "Hard boundary" in d.reason

    def test_autonomous_mode_budget_exceeded_blocked(self):
        from governance.gate import GovernanceGate
        gate = GovernanceGate()
        d = gate.check("budget_exceeded", risk_level="high")
        assert d.allowed is False

    def test_autonomous_mode_sandbox_escape_blocked(self):
        from governance.gate import GovernanceGate
        gate = GovernanceGate()
        d = gate.check("sandbox_escape", risk_level="critical")
        assert d.allowed is False

    def test_autonomous_mode_critical_risk_file_delete_blocked(self):
        from governance.gate import GovernanceGate
        gate = GovernanceGate()
        d = gate.check("some.operation", risk_level="critical")
        assert d.allowed is False

    def test_supervised_mode_normal_flow(self):
        from governance.gate import GovernanceGate
        from governance.policy import Policy, PolicyRule, PolicyEffect
        policy = Policy(name="allow_all", rules=[
            PolicyRule(effect=PolicyEffect.ALLOW, operation="*", priority=1)
        ], default_effect=PolicyEffect.ALLOW)
        from governance.policy import PolicyEvaluator
        evaluator = PolicyEvaluator(fallback_effect=PolicyEffect.ALLOW)
        evaluator.add_policy(policy)
        gate = GovernanceGate(policy_evaluator=evaluator)
        d = gate.check("file.read", risk_level="low")
        assert d.allowed is True

    def test_autonomous_rate_limit_is_soft_warning(self):
        from governance.gate import GovernanceGate
        from governance.rate_limit import RateLimitRule
        from governance.policy import Policy, PolicyRule, PolicyEffect, PolicyEvaluator
        evaluator = PolicyEvaluator(fallback_effect=PolicyEffect.ALLOW)
        evaluator.add_policy(Policy(name="allow", rules=[
            PolicyRule(effect=PolicyEffect.ALLOW, operation="*", priority=1)
        ], default_effect=PolicyEffect.ALLOW))
        gate = GovernanceGate(policy_evaluator=evaluator)
        gate.rates.add_rule(RateLimitRule(operation="shell.*", max_burst=1, refill_rate=0.01))
        gate.rates.check("shell.exec", "*", 1.0)
        d = gate.check("shell.exec", risk_level="low")
        assert d.allowed is True
        assert "warnings" in d.reason


class TestPolicyEvolver:
    """Test the policy auto-evolution engine."""

    def test_evolver_skips_insufficient_data(self):
        from governance.policy_evolver import PolicyEvolver, EvolutionConfig
        from governance.gate import GovernanceGate
        from governance.audit import AuditLog
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            audit = AuditLog(log_path=f"{tmpdir}/audit.jsonl")
            config = EvolutionConfig(min_sample_size=9999)
            gate = GovernanceGate(audit_log=audit)
            evolver = PolicyEvolver(gate=gate, config=config)
            result = evolver.evolve(lookback_hours=1.0)
            assert result.skipped is True

    def test_evolver_cooldown(self):
        from governance.policy_evolver import PolicyEvolver, EvolutionConfig
        from governance.gate import GovernanceGate
        config = EvolutionConfig(cooldown_seconds=0.0, min_sample_size=1)
        gate = GovernanceGate()
        evolver = PolicyEvolver(gate=gate, config=config)
        result = evolver.evolve(lookback_hours=1.0)
        assert result.skipped is True or result.adjustments == []

    def test_evolution_config_bounds(self):
        from governance.policy_evolver import EvolutionConfig
        config = EvolutionConfig()
        assert config.min_refill_rate < config.max_refill_rate
        assert config.min_burst < config.max_burst
        assert config.rate_adjust_factor > 1.0


class TestAgentCommunication:
    """Test the inter-agent communication protocol."""

    def test_direct_message(self):
        from autoai.agents.agent_comm import AgentCommunicationBus, AgentMessage, AgentMessageType
        bus = AgentCommunicationBus()
        bus.register_agent("a1", "coder")
        bus.register_agent("a2", "reviewer")
        msg = AgentMessage(
            message_type=AgentMessageType.DIRECT,
            sender_id="a1",
            target_id="a2",
            payload={"code": "print('hello')"},
        )
        assert bus.send(msg) is True
        received = bus.receive("a2")
        assert received is not None
        assert received.payload["code"] == "print('hello')"

    def test_broadcast(self):
        from autoai.agents.agent_comm import AgentCommunicationBus, AgentMessageType
        bus = AgentCommunicationBus()
        bus.register_agent("a1", "coder")
        bus.register_agent("a2", "reviewer")
        bus.register_agent("a3", "reviewer")
        count = bus.broadcast("a1", {"event": "build_complete"}, target_role="reviewer")
        assert count == 2

    def test_request_response(self):
        from autoai.agents.agent_comm import AgentCommunicationBus, AgentMessage, AgentMessageType
        bus = AgentCommunicationBus()
        bus.register_agent("a1", "coder")
        bus.register_agent("a2", "reviewer")

        async def _test():
            async def _respond():
                await asyncio.sleep(0.05)
                req = bus.receive("a2")
                if req and req.message_type == AgentMessageType.REQUEST:
                    bus.respond(req, "a2", {"approved": True})

            asyncio.create_task(_respond())
            result = await bus.request("a1", "a2", {"code": "fix"}, timeout_seconds=2.0)
            assert result.payload["approved"] is True

        asyncio.run(_test())

    def test_channel(self):
        from autoai.agents.agent_comm import AgentCommunicationBus, AgentMessage, AgentMessageType
        bus = AgentCommunicationBus()
        bus.register_agent("a1", "coder")
        bus.register_agent("a2", "reviewer")
        bus.join_channel("build", "a1")
        bus.join_channel("build", "a2")
        count = bus.publish_to_channel("build", "a1", {"status": "building"})
        assert count == 1

    def test_stats(self):
        from autoai.agents.agent_comm import AgentCommunicationBus
        bus = AgentCommunicationBus()
        bus.register_agent("a1", "coder")
        stats = bus.get_stats()
        assert stats["registered_agents"] == 1

    def test_message_expiry(self):
        from autoai.agents.agent_comm import AgentMessage, AgentMessageType
        msg = AgentMessage(
            message_type=AgentMessageType.DIRECT,
            sender_id="a1",
            target_id="a2",
            payload={},
            ttl_seconds=-1,
        )
        assert msg.is_expired()


class TestWorkflowOrchestrator:
    """Test the DAG workflow orchestrator."""

    def test_dag_validation_no_cycle(self):
        from autoai.agents.workflow_orchestrator import WorkflowDAG, WorkflowTask
        dag = WorkflowDAG("test")
        t1 = WorkflowTask(name="t1")
        t2 = WorkflowTask(name="t2", dependencies={t1.task_id})
        dag.add_task(t1)
        dag.add_task(t2)
        errors = dag.validate()
        assert len(errors) == 0

    def test_dag_validation_missing_dep(self):
        from autoai.agents.workflow_orchestrator import WorkflowDAG, WorkflowTask
        dag = WorkflowDAG("test")
        t1 = WorkflowTask(name="t1", dependencies={"nonexistent"})
        dag.add_task(t1)
        errors = dag.validate()
        assert len(errors) > 0

    def test_dag_ready_tasks(self):
        from autoai.agents.workflow_orchestrator import WorkflowDAG, WorkflowTask
        dag = WorkflowDAG("test")
        t1 = WorkflowTask(name="t1")
        t2 = WorkflowTask(name="t2", dependencies={t1.task_id})
        dag.add_task(t1)
        dag.add_task(t2)
        ready = dag.get_ready_tasks()
        assert len(ready) == 1
        assert ready[0].name == "t1"

    def test_agent_profile_matching(self):
        from autoai.agents.workflow_orchestrator import AgentProfile, WorkflowTask
        profile = AgentProfile(
            agent_id="coder1",
            roles={"coder"},
            capabilities={"python", "debug"},
        )
        task = WorkflowTask(
            name="fix_bug",
            required_roles={"coder"},
            required_capabilities={"python"},
        )
        assert profile.can_handle(task) is True
        score = profile.suitability_score(task)
        assert score > 0

    def test_workflow_execution(self):
        from autoai.agents.workflow_orchestrator import (
            WorkflowDAG, WorkflowTask, WorkflowOrchestrator, AgentProfile, TaskState,
        )
        dag = WorkflowDAG("test")
        t1 = WorkflowTask(name="t1", required_roles={"coder"})
        dag.add_task(t1)

        orchestrator = WorkflowOrchestrator()
        orchestrator.register_agent(AgentProfile(
            agent_id="coder1",
            roles={"coder"},
            capabilities={"python"},
        ))

        result = asyncio.run(orchestrator.execute(dag))
        assert result.success is True
        assert t1.task_id in result.task_results

    def test_skip_dependents_of_failed(self):
        from autoai.agents.workflow_orchestrator import WorkflowDAG, WorkflowTask, TaskState
        dag = WorkflowDAG("test")
        t1 = WorkflowTask(name="t1")
        t2 = WorkflowTask(name="t2", dependencies={t1.task_id})
        dag.add_task(t1)
        dag.add_task(t2)
        t1.state = TaskState.FAILED
        skipped = dag.skip_dependents_of_failed()
        assert t2.task_id in skipped
        assert t2.state == TaskState.SKIPPED


class TestMultiAgentTUI:
    """Test the multi-agent TUI observation window."""

    def test_add_remove_agent(self):
        from autoai.app.multi_agent_tui import MultiAgentTUI, AgentViewData
        tui = MultiAgentTUI()
        tui.update_agent(AgentViewData(agent_id="a1", name="Agent1", role="coder"))
        assert len(tui._agents) == 1
        tui.remove_agent("a1")
        assert len(tui._agents) == 0

    def test_tab_cycling(self):
        from autoai.app.multi_agent_tui import MultiAgentTUI
        tui = MultiAgentTUI()
        assert tui._current_tab == 0
        tui.cycle_tab()
        assert tui._current_tab == 1
        tui.cycle_tab()
        tui.cycle_tab()
        assert tui._current_tab == 0

    def test_workflow_data_update(self):
        from autoai.app.multi_agent_tui import MultiAgentTUI, WorkflowViewData
        tui = MultiAgentTUI()
        tui.update_workflow(WorkflowViewData(
            workflow_id="w1",
            workflow_name="build",
            total_tasks=5,
            completed_tasks=2,
        ))
        assert tui._workflow.total_tasks == 5

    def test_comm_data_update(self):
        from autoai.app.multi_agent_tui import MultiAgentTUI, CommViewData
        tui = MultiAgentTUI()
        tui.update_comm(CommViewData(active_agents=3, total_direct=10))
        assert tui._comm.active_agents == 3

    def test_render_does_not_crash(self):
        from autoai.app.multi_agent_tui import MultiAgentTUI, AgentViewData
        tui = MultiAgentTUI()
        tui.update_agent(AgentViewData(agent_id="a1", name="Agent1"))
        layout = tui.render()
        assert layout is not None
