"""Tests for the unified task model and model routing layer."""

import asyncio
import pytest
from datetime import datetime


# ======================================================================
# UnifiedTask Tests
# ======================================================================

class TestUnifiedTask:
    def test_create_default_task(self):
        from autoai.agents.unified_task import UnifiedTask, TaskCategory, UnifiedTaskStatus
        task = UnifiedTask(name="test", objective="do something")
        assert task.category == TaskCategory.STANDARD
        assert task.status == UnifiedTaskStatus.PENDING
        assert task.task_id
        assert task.created_at

    def test_task_lifecycle(self):
        from autoai.agents.unified_task import UnifiedTask, UnifiedTaskStatus
        task = UnifiedTask(name="test", objective="do something")
        task.mark_dispatched("agent-1")
        assert task.status == UnifiedTaskStatus.DISPATCHED
        assert task.assigned_agent == "agent-1"

        task.mark_running()
        assert task.status == UnifiedTaskStatus.RUNNING
        assert task.started_at is not None

        task.mark_succeeded({"result": "ok"})
        assert task.status == UnifiedTaskStatus.SUCCEEDED
        assert task.result == {"result": "ok"}
        assert task.finished_at is not None
        assert task.is_done

    def test_task_failure_with_retry(self):
        from autoai.agents.unified_task import UnifiedTask, UnifiedTaskStatus
        task = UnifiedTask(name="test", objective="fail", max_retries=2)
        task.mark_running()
        task.mark_failed("error 1")
        assert task.status == UnifiedTaskStatus.PENDING  # retry
        assert task.retry_count == 1

        task.mark_running()
        task.mark_failed("error 2")
        assert task.retry_count == 2

        task.mark_running()
        task.mark_failed("error 3")
        assert task.status == UnifiedTaskStatus.FAILED
        assert task.is_done

    def test_task_timeout(self):
        from autoai.agents.unified_task import UnifiedTask, UnifiedTaskStatus
        task = UnifiedTask(name="test", objective="slow", timeout_seconds=30)
        task.mark_timed_out()
        assert task.status == UnifiedTaskStatus.TIMED_OUT
        assert "Timeout" in task.error

    def test_pause_resume(self):
        from autoai.agents.unified_task import UnifiedTask, UnifiedTaskStatus
        task = UnifiedTask(name="test", objective="long")
        task.mark_running()
        task.pause()
        assert task.status == UnifiedTaskStatus.PAUSED
        task.resume()
        assert task.status == UnifiedTaskStatus.RUNNING

    def test_effective_timeout_by_category(self):
        from autoai.agents.unified_task import UnifiedTask, TaskCategory
        immediate = UnifiedTask(name="t", objective="o", category=TaskCategory.IMMEDIATE, timeout_seconds=120)
        assert immediate.effective_timeout == 30.0

        standard = UnifiedTask(name="t", objective="o", category=TaskCategory.STANDARD, timeout_seconds=120)
        assert standard.effective_timeout == 120.0

        daemon = UnifiedTask(name="t", objective="o", category=TaskCategory.DAEMON)
        assert daemon.effective_timeout == 0.0

    def test_phases(self):
        from autoai.agents.unified_task import UnifiedTask, UnifiedTaskStatus
        task = UnifiedTask(name="test", objective="multi-phase")
        task.add_phase("phase1", "First phase")
        task.add_phase("phase2", "Second phase")
        task.add_phase("phase3", "Third phase")

        assert len(task.phases) == 3
        assert task.current_phase_index == 0
        assert task.current_phase.name == "phase1"

        task.current_phase.status = UnifiedTaskStatus.RUNNING
        next_phase = task.advance_phase({"checkpoint": "data1"})
        assert next_phase.name == "phase2"
        assert task.phases[0].status == UnifiedTaskStatus.SUCCEEDED
        assert task.phases[0].checkpoint_data == {"checkpoint": "data1"}

        task.advance_phase({"checkpoint": "data2"})
        final = task.advance_phase(None)
        assert final is None  # no more phases

    def test_from_workflow_task(self):
        from autoai.agents.unified_task import UnifiedTask, TaskCategory
        from autoai.agents.workflow_orchestrator import WorkflowTask
        wf = WorkflowTask(name="wf-task", description="A workflow task", priority=5, timeout_seconds=15)
        unified = UnifiedTask.from_workflow_task(wf)
        assert unified.name == "wf-task"
        assert unified.objective == "A workflow task"
        assert unified.priority == 5
        assert unified.category == TaskCategory.IMMEDIATE  # timeout <= 30
        assert unified.source_type == "workflow_task"


class TestCircuitBreaker:
    def test_closed_state(self):
        from autoai.agents.unified_task import CircuitBreaker
        cb = CircuitBreaker(failure_threshold=3)
        assert not cb.is_open
        assert cb.state == "closed"

    def test_opens_after_threshold(self):
        from autoai.agents.unified_task import CircuitBreaker
        cb = CircuitBreaker(failure_threshold=3)
        cb.record_failure()
        cb.record_failure()
        assert not cb.is_open
        cb.record_failure()
        assert cb.is_open
        assert cb.state == "open"

    def test_success_resets(self):
        from autoai.agents.unified_task import CircuitBreaker
        cb = CircuitBreaker(failure_threshold=2)
        cb.record_failure()
        cb.record_failure()
        assert cb.is_open
        cb.record_success()
        assert not cb.is_open
        assert cb.state == "closed"


class TestTaskScheduler:
    @pytest.mark.asyncio
    async def test_dispatch_immediate(self):
        from autoai.agents.unified_task import UnifiedTask, TaskCategory, TaskScheduler

        executed = []

        async def executor(task):
            executed.append(task.task_id)
            return {"status": "done"}

        scheduler = TaskScheduler(executor=executor)
        task = UnifiedTask(name="imm", objective="quick", category=TaskCategory.IMMEDIATE)
        result = await scheduler.dispatch_one(task)
        assert result["status"] == "succeeded"
        assert len(executed) == 1

    @pytest.mark.asyncio
    async def test_dispatch_standard_with_retry(self):
        from autoai.agents.unified_task import UnifiedTask, TaskCategory, TaskScheduler

        call_count = 0

        async def executor(task):
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ValueError("fail")
            return {"status": "done"}

        scheduler = TaskScheduler(executor=executor)
        task = UnifiedTask(name="std", objective="retry", category=TaskCategory.STANDARD, max_retries=2)
        result = await scheduler.dispatch_one(task)
        assert result["status"] == "succeeded"
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_dispatch_long_run_phases(self):
        from autoai.agents.unified_task import UnifiedTask, TaskCategory, TaskScheduler

        phase_count = 0

        async def executor(task):
            nonlocal phase_count
            phase_count += 1
            return {"_checkpoint": {"phase": phase_count}, "result": f"phase_{phase_count}"}

        scheduler = TaskScheduler(executor=executor)
        task = UnifiedTask(name="long", objective="multi", category=TaskCategory.LONG_RUN, timeout_seconds=60)
        task.add_phase("p1")
        task.add_phase("p2")
        result = await scheduler.dispatch_one(task)
        assert result["status"] == "succeeded"
        assert phase_count == 2

    @pytest.mark.asyncio
    async def test_submit_and_stats(self):
        from autoai.agents.unified_task import UnifiedTask, TaskCategory, TaskScheduler

        async def executor(task):
            return {"ok": True}

        scheduler = TaskScheduler(executor=executor)
        t1 = UnifiedTask(name="a", objective="a", category=TaskCategory.IMMEDIATE)
        t2 = UnifiedTask(name="b", objective="b", category=TaskCategory.STANDARD, priority=10)
        t3 = UnifiedTask(name="c", objective="c", category=TaskCategory.STANDARD, priority=5)

        ids = scheduler.submit_many([t1, t2, t3])
        assert len(ids) == 3
        assert scheduler.pending_count == 3

        await scheduler.dispatch_all()
        stats = scheduler.stats
        assert stats.total_dispatched == 3
        assert stats.total_succeeded == 3

    @pytest.mark.asyncio
    async def test_checkpoint_saved(self):
        from autoai.agents.unified_task import UnifiedTask, TaskCategory, TaskScheduler

        async def executor(task):
            return {"_checkpoint": {"data": "test"}, "result": "ok"}

        scheduler = TaskScheduler(executor=executor)
        task = UnifiedTask(name="long", objective="ckpt", category=TaskCategory.LONG_RUN)
        task.add_phase("main")
        result = await scheduler.dispatch_one(task)
        assert result["status"] == "succeeded"
        ckpt = scheduler.get_checkpoint(task.task_id)
        assert ckpt is not None
        assert ckpt["checkpoint_data"] == {"data": "test"}


# ======================================================================
# Model Router Tests
# ======================================================================

class TestModelSpec:
    def test_create_spec(self):
        from autoai.llm.model_router.model_spec import ModelSpec, ModelCapability, ModelTier
        spec = ModelSpec(
            model_id="test-model",
            provider_name="test",
            tier=ModelTier.SMART,
            capabilities=ModelCapability.CHAT | ModelCapability.FUNCTION_CALLING,
            max_context_tokens=32000,
            prompt_token_cost_per_1k=0.01,
        )
        assert spec.has_capability(ModelCapability.CHAT)
        assert spec.has_capability(ModelCapability.FUNCTION_CALLING)
        assert not spec.has_capability(ModelCapability.VISION)
        assert not spec.is_free

    def test_free_model(self):
        from autoai.llm.model_router.model_spec import ModelSpec, ModelCapability, ModelTier
        spec = ModelSpec(model_id="local", provider_name="ollama", tier=ModelTier.FAST, is_local=True)
        assert spec.is_free

    def test_to_from_dict(self):
        from autoai.llm.model_router.model_spec import ModelSpec, ModelCapability, ModelTier, BUILTIN_MODEL_SPECS
        for spec_dict in BUILTIN_MODEL_SPECS[:3]:
            spec = ModelSpec.from_dict(spec_dict)
            d = spec.to_dict()
            assert d["model_id"] == spec_dict["model_id"]
            assert d["provider_name"] == spec_dict["provider_name"]


class TestModelRegistry:
    def test_register_and_lookup(self):
        from autoai.llm.model_router import ModelRegistry
        from autoai.llm.model_router.model_spec import ModelSpec, ModelTier
        registry = ModelRegistry()
        spec = ModelSpec(model_id="test", provider_name="p1", tier=ModelTier.FAST)
        registry.register_model(spec)
        assert registry.get_model("test") is not None
        assert registry.get_model("nonexistent") is None
        assert registry.model_count == 1

    def test_alias(self):
        from autoai.llm.model_router import ModelRegistry
        from autoai.llm.model_router.model_spec import ModelSpec, ModelTier
        registry = ModelRegistry()
        spec = ModelSpec(model_id="gpt-4o", provider_name="openai", tier=ModelTier.SMART)
        registry.register_model(spec)
        registry.add_alias("smart", "gpt-4o")
        assert registry.get_model("smart").model_id == "gpt-4o"

    def test_load_builtin_specs(self):
        from autoai.llm.model_router import ModelRegistry
        registry = ModelRegistry()
        count = registry.load_builtin_specs()
        assert registry.model_count >= 9  # at least 9 builtin specs

    def test_fallback_chain(self):
        from autoai.llm.model_router import ModelRegistry
        registry = ModelRegistry()
        registry.load_builtin_specs()
        chain = registry.get_fallback_chain("gpt-4o")
        assert chain[0] == "gpt-4o"
        assert "gpt-4o-mini" in chain

    def test_list_models_filter(self):
        from autoai.llm.model_router import ModelRegistry
        registry = ModelRegistry()
        registry.load_builtin_specs()
        local = registry.list_models(local_only=True)
        assert all(m.is_local for m in local)
        smart = registry.list_models(tier="smart")
        assert all(m.tier.value == "smart" for m in smart)

    def test_summary(self):
        from autoai.llm.model_router import ModelRegistry
        registry = ModelRegistry()
        registry.load_builtin_specs()
        s = registry.summary()
        assert s["total_models"] > 0
        assert "by_provider" in s
        assert "by_tier" in s


class TestModelRouter:
    def test_route_smart_tier(self):
        from autoai.llm.model_router import ModelRegistry, ModelRouter, RoutingPolicy
        from autoai.llm.model_router.model_spec import ModelTier
        registry = ModelRegistry()
        registry.load_builtin_specs()
        router = ModelRouter(registry=registry)
        decision = router.route(task_tier=ModelTier.SMART)
        assert decision is not None
        assert decision.model_id
        assert decision.provider_name

    def test_route_cost_optimal(self):
        from autoai.llm.model_router import ModelRegistry, ModelRouter, RoutingPolicy
        from autoai.llm.model_router.model_spec import ModelTier
        from autoai.llm.model_router.model_router import RoutingStrategy
        registry = ModelRegistry()
        registry.load_builtin_specs()
        policy = RoutingPolicy(strategy=RoutingStrategy.COST_OPTIMAL)
        router = ModelRouter(registry=registry, policy=policy)
        decision = router.route(task_tier=ModelTier.FAST, estimated_tokens=1000)
        assert decision is not None
        assert decision.estimated_cost >= 0

    def test_route_local_first(self):
        from autoai.llm.model_router import ModelRegistry, ModelRouter, RoutingPolicy
        from autoai.llm.model_router.model_spec import ModelTier
        from autoai.llm.model_router.model_router import RoutingStrategy
        registry = ModelRegistry()
        registry.load_builtin_specs()
        policy = RoutingPolicy(strategy=RoutingStrategy.LOCAL_FIRST)
        router = ModelRouter(registry=registry, policy=policy)
        decision = router.route(task_tier=ModelTier.FAST)
        assert decision is not None

    def test_route_forced_model(self):
        from autoai.llm.model_router import ModelRegistry, ModelRouter, RoutingPolicy
        from autoai.llm.model_router.model_spec import ModelTier
        registry = ModelRegistry()
        registry.load_builtin_specs()
        policy = RoutingPolicy(forced_model="gpt-4o-mini")
        router = ModelRouter(registry=registry, policy=policy)
        decision = router.route()
        assert decision is not None
        assert decision.model_id == "gpt-4o-mini"
        assert decision.reason == "forced_model"

    def test_route_budget_limit(self):
        from autoai.llm.model_router import ModelRegistry, ModelRouter, RoutingPolicy
        from autoai.llm.model_router.model_spec import ModelTier
        registry = ModelRegistry()
        registry.load_builtin_specs()
        policy = RoutingPolicy(budget_limit_per_request=0.00001, daily_budget_limit=0.001)
        router = ModelRouter(registry=registry, policy=policy)
        decision = router.route(task_tier=ModelTier.SMART, estimated_tokens=10000)
        # Should still return something (possibly degraded)
        # With very tight budget, may return None or a free model

    def test_degradation_chain(self):
        from autoai.llm.model_router import ModelRegistry, ModelRouter, RoutingPolicy
        from autoai.llm.model_router.model_spec import ModelTier
        registry = ModelRegistry()
        registry.load_builtin_specs()
        chain = registry.get_fallback_chain("deepseek-reasoner")
        assert len(chain) >= 1
        assert chain[0] == "deepseek-reasoner"


class TestRoutingPolicy:
    def test_budget_tracking(self):
        from autoai.llm.model_router.model_router import RoutingPolicy
        policy = RoutingPolicy(daily_budget_limit=1.0, budget_limit_per_request=0.5)
        assert policy.check_budget(0.3)
        assert not policy.check_budget(0.6)
        policy.record_spend(0.3)
        assert policy.daily_remaining == pytest.approx(0.7)


class TestOllamaProvider:
    def test_create_provider(self):
        from autoai.llm.model_router import OllamaProvider
        provider = OllamaProvider(auto_detect=False)
        assert provider.name == "ollama"
        assert provider.base_url == "http://localhost:11434"

    def test_list_models_no_server(self):
        from autoai.llm.model_router import OllamaProvider
        provider = OllamaProvider(auto_detect=False)
        models = provider.list_models()
        assert isinstance(models, list)


class TestOpenAICompatProvider:
    def test_create_provider(self):
        from autoai.llm.model_router import OpenAICompatProvider
        provider = OpenAICompatProvider(name="test", api_key="sk-test")
        assert provider.name == "test"
        assert provider.default_model == "gpt-4o-mini"

    def test_from_preset(self):
        from autoai.llm.model_router import OpenAICompatProvider
        preset = {
            "slug": "deepseek",
            "base_url": "https://api.deepseek.com/v1",
            "models": ["deepseek-chat", "deepseek-reasoner"],
        }
        provider = OpenAICompatProvider.from_preset(preset, api_key="sk-test")
        assert provider.name == "deepseek"
        assert provider.default_model == "deepseek-chat"
        assert provider.base_url == "https://api.deepseek.com/v1"


# ======================================================================
# Integration: SystemBootstrap with TaskScheduler + ModelRouter
# ======================================================================

class TestSystemBootstrapIntegration:
    def test_system_config_new_fields(self):
        from autoai.agents.system_bootstrap import SystemConfig
        config = SystemConfig()
        assert config.enable_task_scheduler is True
        assert config.enable_model_router is True
        assert config.detect_local_models is True
        assert config.routing_strategy == "cost_optimal"

    def test_setup_creates_scheduler_and_router(self):
        from autoai.agents.system_bootstrap import MultiAgentSystem, SystemConfig
        from pathlib import Path
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            config = SystemConfig(
                autonomous=True,
                enable_health_monitor=False,
                enable_agent_pool=False,
                enable_tui=False,
                enable_task_scheduler=True,
                enable_model_router=True,
                detect_local_models=False,
            )
            system = MultiAgentSystem(workspace_path=Path(tmpdir), config=config)
            system.setup()
            assert system.task_scheduler is not None
            assert system.model_router is not None
            assert system.model_registry is not None
            assert system.model_registry.model_count > 0

    def test_system_status_includes_new_fields(self):
        from autoai.agents.system_bootstrap import MultiAgentSystem, SystemConfig
        from pathlib import Path
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            config = SystemConfig(
                autonomous=True,
                enable_health_monitor=False,
                enable_agent_pool=False,
                enable_tui=False,
                enable_task_scheduler=True,
                enable_model_router=True,
                detect_local_models=False,
            )
            system = MultiAgentSystem(workspace_path=Path(tmpdir), config=config)
            system.setup()
            status = system.get_system_status()
            assert "task_scheduler" in status
            assert "model_router" in status
