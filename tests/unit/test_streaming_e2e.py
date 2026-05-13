"""End-to-end streaming pipeline test: MockProvider → StreamingChat → StreamBuffer → TUI callback."""

import asyncio
import pytest

from autogpt.llm.model_router.streaming import (
    StreamEventType,
    StreamingEvent,
    StreamEmitter,
    StreamingChat,
    StreamBuffer,
    StreamStats,
)
from autogpt.llm.model_router.base_provider import ChatMessage, ChatResponse


class MockStreamingProvider:
    """Mock provider that yields tokens via stream_chat."""

    def __init__(self, tokens: list[str] | None = None):
        self._tokens = tokens or ["Hello", " ", "world", "!"]

    async def stream_chat(self, messages, model="", **kwargs):
        for tok in self._tokens:
            yield tok

    async def chat(self, messages, model="", **kwargs):
        full = "".join(self._tokens)
        return ChatResponse(
            content=full,
            prompt_tokens=10,
            completion_tokens=len(self._tokens),
            total_cost=0.001,
        )


class MockNonStreamingProvider:
    """Mock provider with only chat() (no stream_chat)."""

    def __init__(self, content: str = "Non-streaming response"):
        self._content = content

    async def chat(self, messages, model="", **kwargs):
        return ChatResponse(
            content=self._content,
            model="mock",
            provider="mock",
            prompt_tokens=5,
            completion_tokens=10,
            total_cost=0.002,
        )


class TestStreamingE2E:
    @pytest.mark.asyncio
    async def test_streaming_provider_full_pipeline(self):
        provider = MockStreamingProvider(tokens=["foo", "bar", "baz"])
        chat = StreamingChat(provider=provider)
        buf = StreamBuffer()

        events = []
        async for event in chat.stream_chat(
            messages=[ChatMessage(role="user", content="test")],
            model="mock",
            on_event=buf.make_callback(),
        ):
            events.append(event)

        types = [e.type for e in events]
        assert StreamEventType.DONE in types

        buf_types = [e.type for e in buf.all_events]
        assert StreamEventType.THINK_START in buf_types

        assert buf.think_text == "foobarbaz"

    @pytest.mark.asyncio
    async def test_non_streaming_provider_fallback(self):
        provider = MockNonStreamingProvider(content="Hello terminal!")
        chat = StreamingChat(provider=provider)
        buf = StreamBuffer()

        events = []
        async for event in chat.stream_chat(
            messages=[ChatMessage(role="user", content="hi")],
            model="mock",
            on_event=buf.make_callback(),
        ):
            events.append(event)

        types = [e.type for e in events]
        assert StreamEventType.THINK_END in types
        assert StreamEventType.DONE in types

        assert buf.think_text == "Hello terminal!"
        assert buf.stats.completion_tokens == 10
        assert buf.stats.total_cost == 0.002

    @pytest.mark.asyncio
    async def test_no_provider_emits_error(self):
        chat = StreamingChat(provider=None)
        buf = StreamBuffer()

        events = []
        async for event in chat.stream_chat(
            messages=[ChatMessage(role="user", content="test")],
            on_event=buf.make_callback(),
        ):
            events.append(event)

        types = [e.type for e in events]
        assert StreamEventType.ERROR in types
        assert StreamEventType.DONE in types

    @pytest.mark.asyncio
    async def test_stream_think_execute_pipeline(self):
        chat = StreamingChat()
        buf = StreamBuffer()

        async def think_fn():
            return "think step result"

        async def exec_fn(think_result: str):
            return f"executed: {think_result}"

        events = []
        async for event in chat.stream_think_execute(
            think_fn=think_fn,
            execute_fn=exec_fn,
            on_event=buf.make_callback(),
        ):
            events.append(event)

        types = [e.type for e in events]
        assert StreamEventType.THINK_START in types
        assert StreamEventType.THINK_END in types
        assert StreamEventType.EXEC_START in types
        assert StreamEventType.EXEC_END in types
        assert StreamEventType.DONE in types

        assert "think step result" in buf.think_text
        assert "executed" in buf.exec_text

    @pytest.mark.asyncio
    async def test_stream_think_execute_with_error(self):
        chat = StreamingChat()
        buf = StreamBuffer()

        async def think_fn():
            raise RuntimeError("think failed")

        async def exec_fn(think_result: str):
            return ""

        events = []
        async for event in chat.stream_think_execute(
            think_fn=think_fn,
            execute_fn=exec_fn,
            on_event=buf.make_callback(),
        ):
            events.append(event)

        types = [e.type for e in events]
        assert StreamEventType.ERROR in types
        assert StreamEventType.DONE in types

    def test_emitter_stats_tracking(self):
        emitter = StreamEmitter(model="test-model")
        emitter.start()
        emitter.emit_think_start()
        emitter.emit_think_token("hello")
        emitter.emit_think_end(prompt_tokens=10, completion_tokens=5, cost=0.01)
        emitter.emit_done()

        assert emitter.stats.prompt_tokens == 10
        assert emitter.stats.completion_tokens == 5
        assert emitter.stats.total_cost == 0.01
        assert emitter.stats.elapsed_seconds >= 0

    def test_buffer_max_events_eviction(self):
        buf = StreamBuffer(max_events=5)
        for i in range(10):
            buf.push(StreamingEvent(type=StreamEventType.META, content=str(i)))

        assert len(buf.all_events) == 5
        assert buf.all_events[0].content == "5"

    def test_buffer_clear(self):
        buf = StreamBuffer()
        buf.push(StreamingEvent(type=StreamEventType.THINK_TOKEN, content="x"))
        buf.push(StreamingEvent(type=StreamEventType.EXEC_TOKEN, content="y"))
        buf.clear()

        assert buf.think_text == ""
        assert buf.exec_text == ""
        assert len(buf.all_events) == 0

    @pytest.mark.asyncio
    async def test_on_event_callback_fires(self):
        received = []

        def cb(event):
            received.append(event.type)

        provider = MockStreamingProvider(tokens=["a", "b"])
        chat = StreamingChat(provider=provider)

        async for _ in chat.stream_chat(
            messages=[ChatMessage(role="user", content="go")],
            on_event=cb,
        ):
            pass

        assert StreamEventType.DONE in received

    @pytest.mark.asyncio
    async def test_provider_exception_handled(self):
        class FailingProvider:
            async def stream_chat(self, messages, **kwargs):
                raise ConnectionError("API down")
                yield

        chat = StreamingChat(provider=FailingProvider())
        buf = StreamBuffer()

        events = []
        async for event in chat.stream_chat(
            messages=[ChatMessage(role="user", content="test")],
            on_event=buf.make_callback(),
        ):
            events.append(event)

        types = [e.type for e in events]
        assert StreamEventType.ERROR in types
        assert StreamEventType.DONE in types
        assert "API down" in buf.all_events[-2].content
