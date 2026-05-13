"""End-to-end integration tests for Phase 8: System Bootstrap & Agent Factory."""

import asyncio
import json
import tempfile
import time
from pathlib import Path

import pytest


class TestAgentFactory:
    """Test agent factory and fleet creation."""

    def test_create_fleet_from_default_config(self):
        from autogpt.agents.agent_factory import AgentFactory, create_default_fleet_config
        from autogpt.agents.agent_comm import AgentCommunicationBus
        from autogpt.agents.workflow_orchestrator import WorkflowOrchestrator
        bus = AgentCommunicationBus()
        orch = WorkflowOrchestrator(comm_bus=bus)
        factory = AgentFactory(orchestrator=orch, comm_bus=bus)
        config = create_default_fleet_config()
        created = factory.create_fleet(config)
        assert len(created) == 3
        assert "primary" in created
        assert "reviewer" in created
        assert "tester" in created

    def test_destroy_all(self):
        from autogpt.agents.agent_factory import AgentFactory, create_default_fleet_config
        from autogpt.agents.agent_comm import AgentCommunicationBus
        from autogpt.agents.workflow_orchestrator import WorkflowOrchestrator
        bus = AgentCommunicationBus()
        orch = WorkflowOrchestrator(comm_bus=bus)
        factory = AgentFactory(orchestrator=orch, comm_bus=bus)
        config = create_default_fleet_config()
        factory.create_fleet(config)
        count = factory.destroy_all()
        assert count == 3
        assert len(factory.created_agents) == 0

    def test_agent_spec_from_dict(self):
        from autogpt.agents.agent_factory import AgentSpec
        spec = AgentSpec.from_dict({
            "agent_id": "coder1",
            "name": "Coder",
            "roles": "coder,debugger",
            "capabilities": "python,debug",
            "max_concurrent_tasks": 5,
        })
        assert spec.roles == {"coder", "debugger"}
        assert spec.capabilities == {"python", "debug"}
        assert spec.max_concurrent_tasks == 5

    def test_fleet_config_save_load(self):
        from autogpt.agents.agent_factory import AgentFleetConfig, AgentSpec
        config = AgentFleetConfig(
            fleet_name="test",
            agents=[
                AgentSpec(agent_id="a1", role="coder", roles={"coder"}, capabilities={"python"}),
            ],
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "fleet.json"
            config.save(path)
            loaded = AgentFleetConfig.load(path)
            assert loaded.fleet_name == "test"
            assert len(loaded.agents) == 1
            assert loaded.agents[0].agent_id == "a1"

    def test_agent_spec_to_profile(self):
        from autogpt.agents.agent_factory import AgentSpec
        spec = AgentSpec(
            agent_id="a1",
            roles={"coder"},
            capabilities={"python"},
            reliability_score=0.9,
        )
        profile = spec.to_profile()
        assert profile.agent_id == "a1"
        assert profile.roles == {"coder"}
        assert profile.reliability_score == 0.9


class TestSystemBootstrap:
    """Test the complete multi-agent system bootstrap."""

    def test_full_setup_and_teardown(self):
        from autogpt.agents.system_bootstrap import MultiAgentSystem, SystemConfig
        config = SystemConfig(
            autonomous=True,
            enable_tui=False,
            enable_health_monitor=True,
            enable_agent_pool=True,
            enable_policy_evolver=True,
            enable_checkpoint=True,
        )
        system = MultiAgentSystem(config=config)
        system.setup()
        assert system.comm_bus is not None
        assert system.orchestrator is not None
        assert system.health_monitor is not None
        assert system.agent_pool is not None
        assert system.governance_gate is not None
        assert system.policy_evolver is not None
        assert system.checkpoint_mgr is not None
        assert system.agent_factory is not None
        assert len(system.agent_factory.created_agents) == 3

        system.start()
        time.sleep(0.1)
        assert system._running is True

        system.stop()
        assert system._running is False

    def test_system_status(self):
        from autogpt.agents.system_bootstrap import MultiAgentSystem, SystemConfig
        config = SystemConfig(autonomous=True, enable_tui=False)
        system = MultiAgentSystem(config=config)
        system.setup()
        status = system.get_system_status()
        assert "comm" in status
        assert "governance" in status
        assert "fleet" in status
        assert status["governance"]["autonomous"] is True
        system.stop()

    def test_governance_gate_blocks_hard_boundary(self):
        from autogpt.agents.system_bootstrap import MultiAgentSystem, SystemConfig
        config = SystemConfig(autonomous=True, enable_tui=False)
        system = MultiAgentSystem(config=config)
        system.setup()
        d = system.governance_gate.check("file_delete", risk_level="critical")
        assert d.allowed is False
        system.stop()

    def test_governance_gate_allows_normal_in_autonomous(self):
        from autogpt.agents.system_bootstrap import MultiAgentSystem, SystemConfig
        config = SystemConfig(autonomous=True, enable_tui=False)
        system = MultiAgentSystem(config=config)
        system.setup()
        d = system.governance_gate.check("file.read", risk_level="low")
        assert d.allowed is True
        system.stop()

    def test_bootstrap_convenience_function(self):
        from autogpt.agents.system_bootstrap import bootstrap_multi_agent_system
        system = bootstrap_multi_agent_system(autonomous=True)
        assert system.comm_bus is not None
        assert system.governance_gate is not None
        assert len(system.agent_factory.created_agents) == 3
        system.stop()


class TestGovernanceGateInExecution:
    """Test governance gate integrated in AsyncAgent execution path."""

    def test_gate_blocks_hard_boundary_command(self):
        from governance.gate import GovernanceGate
        gate = GovernanceGate()
        d = gate.check("file_delete", principal="test_agent", risk_level="critical")
        assert d.allowed is False
        assert "Hard boundary" in d.reason

    def test_gate_allows_normal_command(self):
        from governance.gate import GovernanceGate
        gate = GovernanceGate()
        d = gate.check("read_file", principal="test_agent", risk_level="low")
        assert d.allowed is True

    def test_gate_shell_high_risk_allowed_in_autonomous(self):
        from governance.gate import GovernanceGate
        gate = GovernanceGate()
        d = gate.check("shell.execute", principal="test_agent", risk_level="high")
        assert d.allowed is True
        assert "audit-net" in d.reason

    def test_supervised_gate_allows_high_risk_in_autonomous_mode(self):
        from governance.gate import GovernanceGate
        from governance.policy import Policy, PolicyRule, PolicyEffect, PolicyEvaluator
        evaluator = PolicyEvaluator(fallback_effect=PolicyEffect.ALLOW)
        evaluator.add_policy(Policy(name="allow", rules=[
            PolicyRule(effect=PolicyEffect.ALLOW, operation="*", priority=1)
        ], default_effect=PolicyEffect.ALLOW))
        gate = GovernanceGate(policy_evaluator=evaluator)
        d = gate.check("shell.execute", principal="test_agent", risk_level="high")
        assert d.allowed is True


class TestEndToEndWorkflow:
    """Test complete workflow: create system → define DAG → execute → checkpoint."""

    def test_full_workflow_lifecycle(self):
        from autogpt.agents.workflow_orchestrator import (
            WorkflowDAG, WorkflowTask, WorkflowOrchestrator, AgentProfile,
        )
        from autogpt.agents.workflow_checkpoint import CheckpointManager

        with tempfile.TemporaryDirectory() as tmpdir:
            orch = WorkflowOrchestrator()
            orch.register_agent(AgentProfile(
                agent_id="coder1", roles={"coder"}, capabilities={"python"},
            ))
            orch.register_agent(AgentProfile(
                agent_id="reviewer1", roles={"reviewer"}, capabilities={"review"},
            ))

            dag = WorkflowDAG("e2e_test")
            t1 = WorkflowTask(name="analyze", required_roles={"coder"})
            t2 = WorkflowTask(name="implement", required_roles={"coder"}, dependencies={t1.task_id})
            t3 = WorkflowTask(name="review", required_roles={"reviewer"}, dependencies={t2.task_id})
            dag.add_task(t1)
            dag.add_task(t2)
            dag.add_task(t3)

            errors = dag.validate()
            assert len(errors) == 0

            result = asyncio.run(orch.execute(dag))
            assert result.success is True

            mgr = CheckpointManager(checkpoint_dir=tmpdir)
            checkpoint = mgr.snapshot_workflow(dag)
            mgr.save(checkpoint)

            loaded = mgr.load(dag.workflow_id)
            assert loaded is not None
            assert loaded.task_states[t1.task_id] == "success"
            assert loaded.task_states[t3.task_id] == "success"

    def test_inter_agent_communication_in_system(self):
        from autogpt.agents.system_bootstrap import MultiAgentSystem, SystemConfig
        from autogpt.agents.agent_comm import AgentMessage, AgentMessageType

        config = SystemConfig(autonomous=True, enable_tui=False, enable_agent_pool=False)
        system = MultiAgentSystem(config=config)
        system.setup()

        msg = AgentMessage(
            message_type=AgentMessageType.DIRECT,
            sender_id="primary",
            target_id="reviewer",
            payload={"code": "def hello(): pass"},
        )
        ok = system.comm_bus.send(msg)
        assert ok is True

        received = system.comm_bus.receive("reviewer")
        assert received is not None
        assert received.payload["code"] == "def hello(): pass"

        system.stop()
