"""Streaming output layer for pure terminal TUI.

No SSE, no WebSocket, no HTTP — just async generators that yield
StreamingEvent objects. The TUI consumes these via Rich Live to
append tokens/marks in real time.

Usage:
    async for event in stream_chat(messages, model="gpt-4o-mini"):
        if event.type == StreamEventType.TOKEN:
            print(event.content, end="", flush=True)
        elif event.type == StreamEventType.DONE:
            print()
"""

from __future__ import annotations

import enum
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, AsyncIterator, Callable, Coroutine


class StreamEventType(enum.Enum):
    THINK_START = "think_start"
    THINK_TOKEN = "think_token"
    THINK_END = "think_end"
    EXEC_START = "exec_start"
    EXEC_TOKEN = "exec_token"
    EXEC_END = "exec_end"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    ERROR = "error"
    DONE = "done"
    META = "meta"


@dataclass
class StreamingEvent:
    type: StreamEventType
    content: str = ""
    stream_id: str = ""
    model: str = ""
    provider: str = ""
    tool_name: str = ""
    tool_args: dict[str, Any] = field(default_factory=dict)
    tool_result: Any = None
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_cost: float = 0.0
    elapsed_ms: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()


@dataclass
class StreamStats:
    total_tokens: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_cost: float = 0.0
    start_time: float = 0.0
    end_time: float = 0.0

    @property
    def elapsed_seconds(self) -> float:
        if self.end_time and self.start_time:
            return self.end_time - self.start_time
        return 0.0

    @property
    def tokens_per_second(self) -> float:
        elapsed = self.elapsed_seconds
        if elapsed > 0 and self.completion_tokens > 0:
            return self.completion_tokens / elapsed
        return 0.0


class StreamEmitter:
    """Buffered stream emitter with stats tracking.

    Collects tokens and yields StreamingEvent objects.
    Used by providers to emit streaming responses.
    """

    def __init__(
        self,
        stream_id: str | None = None,
        model: str = "",
        provider: str = "",
        on_event: Callable[[StreamingEvent], None] | None = None,
    ) -> None:
        self.stream_id = stream_id or uuid.uuid4().hex[:8]
        self.model = model
        self.provider = provider
        self._on_event = on_event
        self._stats = StreamStats()
        self._buffer: list[StreamingEvent] = []
        self._started = False

    def emit_think_start(self) -> None:
        event = StreamingEvent(
            type=StreamEventType.THINK_START,
            stream_id=self.stream_id,
            model=self.model,
            provider=self.provider,
        )
        self._dispatch(event)

    def emit_think_token(self, token: str) -> None:
        event = StreamingEvent(
            type=StreamEventType.THINK_TOKEN,
            content=token,
            stream_id=self.stream_id,
        )
        self._dispatch(event)

    def emit_think_end(self, prompt_tokens: int = 0, completion_tokens: int = 0, cost: float = 0.0) -> None:
        self._stats.prompt_tokens += prompt_tokens
        self._stats.completion_tokens += completion_tokens
        self._stats.total_cost += cost
        event = StreamingEvent(
            type=StreamEventType.THINK_END,
            stream_id=self.stream_id,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_cost=cost,
        )
        self._dispatch(event)

    def emit_exec_start(self, command: str = "") -> None:
        event = StreamingEvent(
            type=StreamEventType.EXEC_START,
            content=command,
            stream_id=self.stream_id,
        )
        self._dispatch(event)

    def emit_exec_token(self, token: str) -> None:
        event = StreamingEvent(
            type=StreamEventType.EXEC_TOKEN,
            content=token,
            stream_id=self.stream_id,
        )
        self._dispatch(event)

    def emit_exec_end(self, result: str = "") -> None:
        event = StreamingEvent(
            type=StreamEventType.EXEC_END,
            content=result,
            stream_id=self.stream_id,
        )
        self._dispatch(event)

    def emit_tool_call(self, name: str, args: dict[str, Any]) -> None:
        event = StreamingEvent(
            type=StreamEventType.TOOL_CALL,
            stream_id=self.stream_id,
            tool_name=name,
            tool_args=args,
        )
        self._dispatch(event)

    def emit_tool_result(self, name: str, result: Any) -> None:
        event = StreamingEvent(
            type=StreamEventType.TOOL_RESULT,
            stream_id=self.stream_id,
            tool_name=name,
            tool_result=result,
        )
        self._dispatch(event)

    def emit_error(self, error: str) -> None:
        event = StreamingEvent(
            type=StreamEventType.ERROR,
            content=error,
            stream_id=self.stream_id,
        )
        self._dispatch(event)

    def emit_done(self) -> None:
        self._stats.end_time = time.monotonic()
        event = StreamingEvent(
            type=StreamEventType.DONE,
            stream_id=self.stream_id,
            prompt_tokens=self._stats.prompt_tokens,
            completion_tokens=self._stats.completion_tokens,
            total_cost=self._stats.total_cost,
            elapsed_ms=self._stats.elapsed_seconds * 1000,
        )
        self._dispatch(event)

    def emit_meta(self, key: str, value: Any) -> None:
        event = StreamingEvent(
            type=StreamEventType.META,
            stream_id=self.stream_id,
            metadata={key: value},
        )
        self._dispatch(event)

    def start(self) -> None:
        self._stats.start_time = time.monotonic()
        self._started = True

    @property
    def stats(self) -> StreamStats:
        return self._stats

    def _dispatch(self, event: StreamingEvent) -> None:
        self._buffer.append(event)
        if self._on_event:
            self._on_event(event)

    @property
    def pending_events(self) -> list[StreamingEvent]:
        events = list(self._buffer)
        self._buffer.clear()
        return events


class StreamingChat:
    """High-level streaming chat interface.

    Wraps a BaseProvider and yields StreamingEvent objects.
    The TUI consumes these events to render tokens in real time.
    """

    def __init__(self, provider: Any | None = None) -> None:
        self._provider = provider

    def set_provider(self, provider: Any) -> None:
        self._provider = provider

    async def stream_chat(
        self,
        messages: list[Any],
        model: str = "",
        temperature: float = 0.0,
        max_tokens: int | None = None,
        on_event: Callable[[StreamingEvent], None] | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[StreamingEvent]:
        emitter = StreamEmitter(model=model, on_event=on_event)
        emitter.start()
        emitter.emit_think_start()

        try:
            if self._provider and hasattr(self._provider, "stream_chat"):
                async for event in self._provider.stream_chat(
                    messages=messages,
                    model=model,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    **kwargs,
                ):
                    if isinstance(event, StreamingEvent):
                        emitter._dispatch(event)
                        yield event
                    elif isinstance(event, str):
                        tok_event = StreamingEvent(
                            type=StreamEventType.THINK_TOKEN,
                            content=event,
                            stream_id=emitter.stream_id,
                        )
                        emitter._dispatch(tok_event)
                        yield tok_event
            elif self._provider and hasattr(self._provider, "chat"):
                from .base_provider import ChatMessage
                response = await self._provider.chat(
                    messages=messages,
                    model=model,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    **kwargs,
                )
                chunk_size = max(1, len(response.content) // 20)
                for i in range(0, len(response.content), chunk_size):
                    token = response.content[i:i + chunk_size]
                    tok_event = StreamingEvent(
                        type=StreamEventType.THINK_TOKEN,
                        content=token,
                        stream_id=emitter.stream_id,
                    )
                    emitter._dispatch(tok_event)
                    yield tok_event

                emitter.emit_think_end(
                    prompt_tokens=response.prompt_tokens,
                    completion_tokens=response.completion_tokens,
                    cost=response.total_cost,
                )
                yield emitter._buffer[-1]
            else:
                emitter.emit_error("No provider available")
                yield emitter._buffer[-1]

        except Exception as e:
            emitter.emit_error(str(e))
            yield emitter._buffer[-1]
        finally:
            emitter.emit_done()
            yield emitter._buffer[-1]

    async def stream_think_execute(
        self,
        think_fn: Callable[[], Coroutine[Any, Any, str]],
        execute_fn: Callable[[str], Coroutine[Any, Any, str]],
        on_event: Callable[[StreamingEvent], None] | None = None,
    ) -> AsyncIterator[StreamingEvent]:
        emitter = StreamEmitter(on_event=on_event)
        emitter.start()

        emitter.emit_think_start()
        yield emitter._buffer[-1]

        try:
            think_result = await think_fn()

            chunk_size = max(1, len(think_result) // 20)
            for i in range(0, len(think_result), chunk_size):
                token = think_result[i:i + chunk_size]
                emitter.emit_think_token(token)
                yield emitter._buffer[-1]

            emitter.emit_think_end()
            yield emitter._buffer[-1]

            emitter.emit_exec_start()
            yield emitter._buffer[-1]

            exec_result = await execute_fn(think_result)

            chunk_size = max(1, len(exec_result) // 20)
            for i in range(0, len(exec_result), chunk_size):
                token = exec_result[i:i + chunk_size]
                emitter.emit_exec_token(token)
                yield emitter._buffer[-1]

            emitter.emit_exec_end()
            yield emitter._buffer[-1]

        except Exception as e:
            emitter.emit_error(str(e))
            yield emitter._buffer[-1]
        finally:
            emitter.emit_done()
            yield emitter._buffer[-1]


class StreamBuffer:
    """Thread-safe buffer for TUI consumption.

    The agent writes events; the TUI reads and renders them.
    """

    def __init__(self, max_events: int = 1000) -> None:
        self._events: list[StreamingEvent] = []
        self._max_events = max_events
        self._accumulated_think: str = ""
        self._accumulated_exec: str = ""
        self._stats = StreamStats()

    def push(self, event: StreamingEvent) -> None:
        self._events.append(event)
        if len(self._events) > self._max_events:
            self._events = self._events[-self._max_events:]

        if event.type == StreamEventType.THINK_TOKEN:
            self._accumulated_think += event.content
        elif event.type == StreamEventType.EXEC_TOKEN:
            self._accumulated_exec += event.content
        elif event.type == StreamEventType.THINK_END:
            self._stats.prompt_tokens += event.prompt_tokens
            self._stats.completion_tokens += event.completion_tokens
            self._stats.total_cost += event.total_cost
        elif event.type == StreamEventType.DONE:
            self._stats.end_time = time.monotonic()

    def push_many(self, events: list[StreamingEvent]) -> None:
        for e in events:
            self.push(e)

    @property
    def think_text(self) -> str:
        return self._accumulated_think

    @property
    def exec_text(self) -> str:
        return self._accumulated_exec

    @property
    def stats(self) -> StreamStats:
        return self._stats

    @property
    def recent_events(self) -> list[StreamingEvent]:
        return list(self._events[-50:])

    @property
    def all_events(self) -> list[StreamingEvent]:
        return list(self._events)

    def clear(self) -> None:
        self._events.clear()
        self._accumulated_think = ""
        self._accumulated_exec = ""

    def make_callback(self) -> Callable[[StreamingEvent], None]:
        def _cb(event: StreamingEvent) -> None:
            self.push(event)
        return _cb


__all__ = [
    "StreamEventType",
    "StreamingEvent",
    "StreamStats",
    "StreamEmitter",
    "StreamingChat",
    "StreamBuffer",
]
