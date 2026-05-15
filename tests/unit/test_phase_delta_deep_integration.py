"""Phase delta: 深度集成测试 - 验证AgentEnhancer与SelfThink/Agent/SystemBootstrap的连接。"""
from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from autoai.agents.self_think import SelfThinkEngine, SelfReviewSource
from autoai.integration.agent_enhancer import AgentEnhancer, EnhancedAgentContext


class _DummySource(SelfReviewSource):
    name = "dummy"

    def __init__(self, items: list[dict] | None = None):
        self._items = items or []

    def discover(self, workspace: Path) -> list[dict]:
        return self._items


class TestSelfThinkEnhancerIntegration:
    """SelfThinkEngine与AgentEnhancer的集成。"""

    def test_engine_accepts_enhancer(self):
        enhancer = AgentEnhancer(agent_id="test-st")
        engine = SelfThinkEngine(
            workspace=Path("."),
            agent_enhancer=enhancer,
        )
        assert engine._agent_enhancer is enhancer

    def test_scan_with_enhancer_records_enhanced_scan(self):
        enhancer = AgentEnhancer(agent_id="test-scan")
        enhancer.initialize()
        engine = SelfThinkEngine(
            workspace=Path("."),
            agent_enhancer=enhancer,
        )
        engine.scan()
        assert engine._enhanced_scan_count == 1

    def test_scan_with_enhancer_think_hook_called(self):
        enhancer = AgentEnhancer(agent_id="test-think-hook")
        enhancer.initialize()
        engine = SelfThinkEngine(
            workspace=Path("."),
            agent_enhancer=enhancer,
        )
        result = engine.scan()
        assert isinstance(result, list)

    def test_auto_fix_with_enhancer_decision_hook(self):
        enhancer = AgentEnhancer(agent_id="test-fix-decision")
        enhancer.initialize()
        engine = SelfThinkEngine(
            workspace=Path("."),
            agent_enhancer=enhancer,
            auto_fix=False,
        )
        engine.add_source(_DummySource([{
            "objective": "test fix",
            "type": "code",
            "priority": 1,
        }]))
        summary = asyncio.run(engine.auto_fix_cycle([]))
        assert summary["enhanced_decisions"] >= 1

    def test_stats_includes_enhanced_counts(self):
        enhancer = AgentEnhancer(agent_id="test-stats")
        enhancer.initialize()
        engine = SelfThinkEngine(
            workspace=Path("."),
            agent_enhancer=enhancer,
        )
        engine.scan()
        stats = engine.stats
        assert "enhanced_scan_count" in stats
        assert "enhanced_decision_count" in stats

    def test_notify_action_complete_calls_enhancer(self):
        enhancer = AgentEnhancer(agent_id="test-notify")
        enhancer.initialize()
        engine = SelfThinkEngine(
            workspace=Path("."),
            agent_enhancer=enhancer,
        )
        engine._notify_action_complete("fix", True)
        engine._notify_action_complete("fix", False)

    def test_no_enhancer_graceful_degradation(self):
        engine = SelfThinkEngine(workspace=Path("."), agent_enhancer=None)
        result = engine.scan()
        assert isinstance(result, list)
        assert engine._enhanced_scan_count == 0


class TestAgentEnhancerContext:
    """EnhancedAgentContext验证。"""

    def test_context_initialized(self):
        enhancer = AgentEnhancer(agent_id="test-ctx")
        ctx = enhancer.initialize()
        assert ctx._initialized is True
        assert ctx.layered_memory is not None
        assert ctx.event_stream is not None
        assert ctx.governance is not None
        assert ctx.continuous_autonomy is not None
        assert ctx.model_matrix is not None
        assert ctx.tracer is not None
        assert ctx.metrics is not None
        assert ctx.reasoning_selector is not None

    def test_context_double_init_safe(self):
        enhancer = AgentEnhancer(agent_id="test-dbl")
        ctx1 = enhancer.initialize()
        ctx2 = enhancer.initialize()
        assert ctx1 is ctx2

    def test_get_status(self):
        enhancer = AgentEnhancer(agent_id="test-status")
        enhancer.initialize()
        status = enhancer.get_status()
        assert status["initialized"] is True
        assert "autonomy" in status
        assert "governance" in status
        assert "events" in status
        assert "metrics" in status


class TestSystemBootstrapEnhancer:
    """SystemBootstrap集成验证。"""

    def test_config_has_enable_enhancer(self):
        from autoai.agents.system_bootstrap import SystemConfig
        config = SystemConfig()
        assert hasattr(config, "enable_enhancer")
        assert config.enable_enhancer is True

    def test_system_has_enhancer_attributes(self):
        from autoai.agents.system_bootstrap import MultiAgentSystem
        system = MultiAgentSystem()
        assert hasattr(system, "agent_enhancer")
        assert hasattr(system, "enhanced_context")

    def test_setup_initializes_enhancer(self):
        from autoai.agents.system_bootstrap import MultiAgentSystem, SystemConfig
        config = SystemConfig(
            enable_health_monitor=False,
            enable_agent_pool=False,
            enable_policy_evolver=False,
            enable_checkpoint=False,
            enable_task_scheduler=False,
            enable_model_router=False,
            enable_sandbox=False,
            enable_enhancer=True,
        )
        system = MultiAgentSystem(config=config)
        system.setup()
        assert system.agent_enhancer is not None
        assert system.enhanced_context is not None
        assert system.enhanced_context._initialized is True

    def test_setup_without_enhancer(self):
        from autoai.agents.system_bootstrap import MultiAgentSystem, SystemConfig
        config = SystemConfig(
            enable_health_monitor=False,
            enable_agent_pool=False,
            enable_policy_evolver=False,
            enable_checkpoint=False,
            enable_task_scheduler=False,
            enable_model_router=False,
            enable_sandbox=False,
            enable_enhancer=False,
        )
        system = MultiAgentSystem(config=config)
        system.setup()
        assert system.agent_enhancer is None
        assert system.enhanced_context is None

    def test_system_status_includes_enhancer(self):
        from autoai.agents.system_bootstrap import MultiAgentSystem, SystemConfig
        config = SystemConfig(
            enable_health_monitor=False,
            enable_agent_pool=False,
            enable_policy_evolver=False,
            enable_checkpoint=False,
            enable_task_scheduler=False,
            enable_model_router=False,
            enable_sandbox=False,
            enable_enhancer=True,
        )
        system = MultiAgentSystem(config=config)
        system.setup()
        status = system.get_system_status()
        assert "enhancer" in status


class TestAgentEnhancerHooks:
    """Agent类增强钩子集成验证。"""

    def test_agent_has_enhancer_attributes(self):
        from autoai.agents.agent import Agent
        agent = MagicMock(spec=["_agent_enhancer", "_enhanced_context"])
        assert hasattr(agent, "_agent_enhancer")
        assert hasattr(agent, "_enhanced_context")

    def test_enhancer_on_think_start(self):
        enhancer = AgentEnhancer(agent_id="test-think")
        enhancer.initialize()
        result = enhancer.on_think_start("review code")
        assert "event_id" in result or "trace_id" in result

    def test_enhancer_on_decision_allow(self):
        enhancer = AgentEnhancer(agent_id="test-dec-allow")
        enhancer.initialize()
        result = enhancer.on_decision("read_file")
        assert result["allowed"] is True

    def test_enhancer_on_action_complete(self):
        enhancer = AgentEnhancer(agent_id="test-complete")
        enhancer.initialize()
        enhancer.on_action_complete("execute", True)
        enhancer.on_action_complete("execute", False)

    def test_enhancer_on_self_modify(self):
        enhancer = AgentEnhancer(agent_id="test-selfmod")
        enhancer.initialize()
        result = enhancer.on_self_modify("test.py", "diff", True)
        assert isinstance(result, dict)

    def test_enhancer_route_model(self):
        enhancer = AgentEnhancer(agent_id="test-route")
        enhancer.initialize()
        result = enhancer.route_model(0.5, 0.8)
        assert "model" in result
        assert "cost" in result

    def test_enhancer_store_memory(self):
        enhancer = AgentEnhancer(agent_id="test-mem")
        enhancer.initialize()
        mid = enhancer.store_memory("test content")
        assert isinstance(mid, str)
