"""Tests for streaming layer, TUI stream integration, and terminal dashboard."""

import asyncio
import pytest
import time


# ======================================================================
# Streaming Layer Tests
# ======================================================================

class TestStreamingEvent:
    def test_create_event(self):
        from autogpt.llm.model_router.streaming import StreamingEvent, StreamEventType
        event = StreamingEvent(type=StreamEventType.THINK_TOKEN, content="hello")
        assert event.type == StreamEventType.THINK_TOKEN
        assert event.content == "hello"

    def test_event_types(self):
        from autogpt.llm.model_router.streaming import StreamEventType
        assert StreamEventType.THINK_START.value == "think_start"
        assert StreamEventType.THINK_TOKEN.value == "think_token"
        assert StreamEventType.EXEC_TOKEN.value == "exec_token"
        assert StreamEventType.DONE.value == "done"


class TestStreamEmitter:
    def test_emit_think(self):
        from autogpt.llm.model_router.streaming import StreamEmitter, StreamEventType
        events = []
        emitter = StreamEmitter(model="test", on_event=lambda e: events.append(e))
        emitter.start()
        emitter.emit_think_start()
        emitter.emit_think_token("Hello ")
        emitter.emit_think_token("world")
        emitter.emit_think_end(prompt_tokens=10, completion_tokens=5, cost=0.001)
        assert len(events) == 4
        assert events[0].type == StreamEventType.THINK_START
        assert events[1].content == "Hello "
        assert events[2].content == "world"
        assert events[3].type == StreamEventType.THINK_END
        assert events[3].completion_tokens == 5

    def test_emit_exec(self):
        from autogpt.llm.model_router.streaming import StreamEmitter, StreamEventType
        events = []
        emitter = StreamEmitter(on_event=lambda e: events.append(e))
        emitter.emit_exec_start("write_file")
        emitter.emit_exec_token("content...")
        emitter.emit_exec_end("ok")
        assert len(events) == 3
        assert events[0].type == StreamEventType.EXEC_START
        assert events[0].content == "write_file"

    def test_emit_tool_call(self):
        from autogpt.llm.model_router.streaming import StreamEmitter, StreamEventType
        events = []
        emitter = StreamEmitter(on_event=lambda e: events.append(e))
        emitter.emit_tool_call("read_file", {"path": "/tmp/test"})
        emitter.emit_tool_result("read_file", "file content")
        assert events[0].tool_name == "read_file"
        assert events[0].tool_args == {"path": "/tmp/test"}
        assert events[1].tool_result == "file content"

    def test_emit_done_with_stats(self):
        from autogpt.llm.model_router.streaming import StreamEmitter, StreamEventType
        events = []
        emitter = StreamEmitter(on_event=lambda e: events.append(e))
        emitter.start()
        emitter.emit_think_token("test")
        emitter.emit_think_end(prompt_tokens=10, completion_tokens=20, cost=0.01)
        emitter.emit_done()
        assert events[-1].type == StreamEventType.DONE
        assert events[-1].prompt_tokens == 10
        assert events[-1].completion_tokens == 20

    def test_pending_events_drain(self):
        from autogpt.llm.model_router.streaming import StreamEmitter
        emitter = StreamEmitter()
        emitter.emit_think_token("a")
        emitter.emit_think_token("b")
        events = emitter.pending_events
        assert len(events) == 2
        assert len(emitter.pending_events) == 0


class TestStreamStats:
    def test_elapsed_and_tps(self):
        from autogpt.llm.model_router.streaming import StreamStats
        stats = StreamStats()
        stats.start_time = time.monotonic() - 2.0
        stats.end_time = time.monotonic()
        stats.completion_tokens = 100
        assert stats.elapsed_seconds >= 1.5
        assert stats.tokens_per_second > 0


class TestStreamBuffer:
    def test_push_and_accumulate(self):
        from autogpt.llm.model_router.streaming import StreamBuffer, StreamingEvent, StreamEventType
        buf = StreamBuffer()
        buf.push(StreamingEvent(type=StreamEventType.THINK_TOKEN, content="Hello "))
        buf.push(StreamingEvent(type=StreamEventType.THINK_TOKEN, content="world"))
        assert buf.think_text == "Hello world"

    def test_exec_accumulate(self):
        from autogpt.llm.model_router.streaming import StreamBuffer, StreamingEvent, StreamEventType
        buf = StreamBuffer()
        buf.push(StreamingEvent(type=StreamEventType.EXEC_TOKEN, content="result"))
        assert buf.exec_text == "result"

    def test_stats_update(self):
        from autogpt.llm.model_router.streaming import StreamBuffer, StreamingEvent, StreamEventType
        buf = StreamBuffer()
        buf.push(StreamingEvent(
            type=StreamEventType.THINK_END,
            prompt_tokens=100,
            completion_tokens=50,
            total_cost=0.01,
        ))
        assert buf.stats.prompt_tokens == 100
        assert buf.stats.completion_tokens == 50
        assert buf.stats.total_cost == 0.01

    def test_make_callback(self):
        from autogpt.llm.model_router.streaming import StreamBuffer, StreamingEvent, StreamEventType
        buf = StreamBuffer()
        cb = buf.make_callback()
        cb(StreamingEvent(type=StreamEventType.THINK_TOKEN, content="via cb"))
        assert buf.think_text == "via cb"

    def test_max_events_trimming(self):
        from autogpt.llm.model_router.streaming import StreamBuffer, StreamingEvent, StreamEventType
        buf = StreamBuffer(max_events=5)
        for i in range(10):
            buf.push(StreamingEvent(type=StreamEventType.META, metadata={"i": i}))
        assert len(buf.all_events) == 5

    def test_clear(self):
        from autogpt.llm.model_router.streaming import StreamBuffer, StreamingEvent, StreamEventType
        buf = StreamBuffer()
        buf.push(StreamingEvent(type=StreamEventType.THINK_TOKEN, content="x"))
        buf.clear()
        assert buf.think_text == ""
        assert len(buf.all_events) == 0


class TestStreamingChat:
    @pytest.mark.asyncio
    async def test_stream_chat_with_non_streaming_provider(self):
        from autogpt.llm.model_router.streaming import StreamingChat, StreamEventType
        from autogpt.llm.model_router.base_provider import BaseProvider, ChatMessage, ChatResponse

        class MockProvider(BaseProvider):
            async def chat(self, messages, model="", **kwargs):
                return ChatResponse(content="Hello world!", model="mock", provider="mock")
            async def embed(self, text, model="", **kwargs):
                pass
            async def check_health(self):
                pass
            def list_models(self):
                return ["mock"]

        sc = StreamingChat(provider=MockProvider(name="mock"))
        events = []
        async for event in sc.stream_chat(messages=[], model="mock"):
            events.append(event)

        tokens = [e.content for e in events if e.type == StreamEventType.THINK_TOKEN]
        text = "".join(tokens)
        assert "Hello world!" in text
        assert events[-1].type == StreamEventType.DONE

    @pytest.mark.asyncio
    async def test_stream_think_execute(self):
        from autogpt.llm.model_router.streaming import StreamingChat, StreamEventType

        sc = StreamingChat()
        events = []

        async def think():
            return "I should write a file"

        async def execute(thought):
            return f"Executed based on: {thought}"

        async for event in sc.stream_think_execute(think, execute):
            events.append(event)

        think_events = [e for e in events if e.type == StreamEventType.THINK_TOKEN]
        exec_events = [e for e in events if e.type == StreamEventType.EXEC_TOKEN]
        assert len(think_events) > 0
        assert len(exec_events) > 0
        assert events[-1].type == StreamEventType.DONE


# ======================================================================
# TUI Stream Integration Tests
# ======================================================================

class TestTUIStreamIntegration:
    def test_tui_on_stream_event(self):
        from autogpt.app.tui import TUIObservationWindow
        from autogpt.llm.model_router.streaming import StreamingEvent, StreamEventType

        tui = TUIObservationWindow()
        tui.on_stream_event(StreamingEvent(type=StreamEventType.THINK_TOKEN, content="thinking..."))
        assert tui._current_think == "thinking..."

        tui.on_stream_event(StreamingEvent(type=StreamEventType.THINK_END, completion_tokens=10, prompt_tokens=5, total_cost=0.001))
        assert tui._current_think == ""
        assert len(tui._think_lines) == 1

    def test_tui_exec_stream(self):
        from autogpt.app.tui import TUIObservationWindow
        from autogpt.llm.model_router.streaming import StreamingEvent, StreamEventType

        tui = TUIObservationWindow()
        tui.on_stream_event(StreamingEvent(type=StreamEventType.EXEC_TOKEN, content="result data"))
        assert tui._current_exec == "result data"

        tui.on_stream_event(StreamingEvent(type=StreamEventType.EXEC_END))
        assert tui._current_exec == ""
        assert len(tui._exec_lines) == 1

    def test_tui_attach_stream_buffer(self):
        from autogpt.app.tui import TUIObservationWindow
        from autogpt.llm.model_router.streaming import StreamBuffer, StreamingEvent, StreamEventType

        buf = StreamBuffer()
        tui = TUIObservationWindow()
        tui.attach_stream_buffer(buf)

        buf.push(StreamingEvent(type=StreamEventType.THINK_TOKEN, content="via buffer"))
        tui.on_stream_event(StreamingEvent(type=StreamEventType.THINK_TOKEN, content="via callback"))
        assert "via callback" in tui._current_think


# ======================================================================
# Terminal Dashboard Tests
# ======================================================================

class TestTerminalDashboard:
    def test_create_dashboard(self):
        from autogpt.app.dashboard import TerminalDashboard
        dash = TerminalDashboard()
        assert dash._system is None

    def test_log_event(self):
        from autogpt.app.dashboard import TerminalDashboard
        dash = TerminalDashboard()
        dash.log_event("test event", "info")
        dash.log_event("warning!", "warn")
        assert len(dash._event_log) == 2

    def test_render_without_system(self):
        from autogpt.app.dashboard import TerminalDashboard
        dash = TerminalDashboard()
        layout = dash.render()
        assert layout is not None

    def test_render_with_system(self):
        from autogpt.app.dashboard import TerminalDashboard
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
            )
            system = MultiAgentSystem(workspace_path=Path(tmpdir), config=config)
            system.setup()
            dash = TerminalDashboard(system=system)
            layout = dash.render()
            assert layout is not None

    def test_create_dashboard_factory(self):
        from autogpt.app.dashboard import create_dashboard
        dash = create_dashboard(None)
        assert dash is not None
