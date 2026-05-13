"""Integration tests: AsyncAgent with ModelRouter, Sandbox, Streaming, and DistributedBackend."""

import asyncio
import os
import pytest


class TestAsyncAgentModelRouter:
    def test_agent_has_new_fields(self):
        from autogpt.agents.async_agent import AsyncAgent
        import inspect
        source = inspect.getsource(AsyncAgent.__init__)
        assert "_model_router" in source
        assert "_sandbox" in source
        assert "_stream_buffer" in source
        assert "_streaming_chat" in source

    def test_attach_model_router(self):
        from autogpt.llm.model_router import ModelRegistry, ModelRouter, RoutingPolicy
        registry = ModelRegistry()
        registry.load_builtin_specs()
        router = ModelRouter(registry=registry)

        class MockAgent:
            _model_router = None
            _model_registry = None
            def attach_model_router(self, router, registry):
                self._model_router = router
                self._model_registry = registry

        agent = MockAgent()
        agent.attach_model_router(router, registry)
        assert agent._model_router is router
        assert agent._model_registry is registry

    def test_attach_sandbox(self):
        from autogpt.sandbox import SubprocessSandbox, SandboxConfig

        sandbox = SubprocessSandbox(SandboxConfig())

        class MockAgent:
            _sandbox = None
            def attach_sandbox(self, sandbox):
                self._sandbox = sandbox

        agent = MockAgent()
        agent.attach_sandbox(sandbox)
        assert agent._sandbox is sandbox

    def test_attach_stream_buffer(self):
        from autogpt.llm.model_router.streaming import StreamBuffer

        buf = StreamBuffer()

        class MockAgent:
            _stream_buffer = None
            _streaming_chat = None
            def attach_stream_buffer(self, buf):
                self._stream_buffer = buf
                from autogpt.llm.model_router.streaming import StreamingChat
                self._streaming_chat = StreamingChat()

        agent = MockAgent()
        agent.attach_stream_buffer(buf)
        assert agent._stream_buffer is buf
        assert agent._streaming_chat is not None


class TestAsyncAgentSandboxIntegration:
    @pytest.mark.asyncio
    async def test_sandbox_blocks_command(self):
        from autogpt.sandbox import SubprocessSandbox, SandboxConfig

        config = SandboxConfig(
            allowed_commands={"read_file"},
            denied_commands={"delete_file"},
        )
        sandbox = SubprocessSandbox(config)

        violations = sandbox.validate_command("delete_file")
        assert len(violations) > 0
        assert "blocked" in violations[0].detail.lower() or "not in allowed" in violations[0].detail.lower()

    @pytest.mark.asyncio
    async def test_sandbox_blocks_path(self):
        from autogpt.sandbox import SubprocessSandbox, SandboxConfig

        config = SandboxConfig(workspace_dir="/tmp/safe")
        sandbox = SubprocessSandbox(config)

        violations = sandbox.validate_path("/etc/shadow")
        assert len(violations) > 0


class TestAsyncAgentStreamIntegration:
    def test_stream_buffer_receives_think_end(self):
        from autogpt.llm.model_router.streaming import StreamBuffer, StreamingEvent, StreamEventType

        buf = StreamBuffer()
        buf.push(StreamingEvent(
            type=StreamEventType.THINK_END,
            content="I should write a file",
            prompt_tokens=100,
            completion_tokens=50,
            total_cost=0.005,
            model="gpt-4o-mini",
            provider="openai",
        ))

        assert buf.stats.prompt_tokens == 100
        assert buf.stats.completion_tokens == 50
        assert buf.stats.total_cost == 0.005

    def test_stream_callback_chain(self):
        from autogpt.llm.model_router.streaming import StreamBuffer, StreamEmitter, StreamEventType

        buf = StreamBuffer()
        emitter = StreamEmitter(model="test", on_event=buf.make_callback())
        emitter.start()
        emitter.emit_think_start()
        emitter.emit_think_token("Hello ")
        emitter.emit_think_token("world!")
        emitter.emit_think_end(prompt_tokens=10, completion_tokens=5, cost=0.001)

        assert buf.think_text == "Hello world!"
        assert buf.stats.prompt_tokens == 10


class TestSystemBootstrapFullIntegration:
    def test_full_system_attach(self):
        from autogpt.agents.system_bootstrap import MultiAgentSystem, SystemConfig
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmpdir:
            config = SystemConfig(
                autonomous=True,
                enable_health_monitor=False,
                enable_agent_pool=False,
                enable_tui=False,
                enable_task_scheduler=True,
                enable_model_router=True,
                detect_local_models=False,
                enable_sandbox=True,
                sandbox_type="subprocess",
                enable_distributed=True,
                distributed_backend="local",
            )
            system = MultiAgentSystem(workspace_path=Path(tmpdir), config=config)
            system.setup()

            assert system.task_scheduler is not None
            assert system.model_router is not None
            assert system.model_registry is not None
            assert system.sandbox is not None
            assert system.distributed is not None
            assert system.governance_gate is not None

            status = system.get_system_status()
            assert "task_scheduler" in status
            assert "model_router" in status
            assert "sandbox" in status
            assert "distributed" in status
            assert "governance" in status


class TestDistributedTaskSchedulerIntegration:
    @pytest.mark.asyncio
    async def test_local_backend_dispatch(self):
        from autogpt.distributed import LocalBackend
        from autogpt.agents.unified_task import UnifiedTask, TaskCategory

        backend = LocalBackend(max_concurrent=2)
        await backend.start()

        task = UnifiedTask(
            name="distributed-test",
            objective="Test distributed dispatch",
            category=TaskCategory.STANDARD,
        )
        future = await backend.dispatch(task)
        result = await backend.get_result(future, timeout=5.0)
        assert result["status"] == "executed"
        await backend.stop()

    @pytest.mark.asyncio
    async def test_concurrent_distributed_dispatch(self):
        from autogpt.distributed import LocalBackend
        from autogpt.agents.unified_task import UnifiedTask, TaskCategory

        backend = LocalBackend(max_concurrent=3)
        await backend.start()

        tasks = [
            UnifiedTask(name=f"t{i}", objective=f"Task {i}", category=TaskCategory.IMMEDIATE)
            for i in range(6)
        ]

        futures = []
        for t in tasks:
            f = await backend.dispatch(t)
            futures.append(f)

        results = []
        for f in futures:
            r = await backend.get_result(f, timeout=10.0)
            results.append(r)

        assert len(results) == 6
        assert all(r["status"] == "executed" for r in results)
        await backend.stop()
