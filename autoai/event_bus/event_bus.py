from __future__ import annotations

import json
import logging
import os
from typing import Any, Callable

try:  # pragma: no cover - optional dependency
    import redis  # type: ignore[import]
except Exception:  # pragma: no cover - library not available
    redis = None  # type: ignore

from .message_types import EventMessage

logger = logging.getLogger(__name__)

_client: "redis.Redis | None" = None


def connect(
    host: str | None = None,
    port: int | None = None,
    db: int | None = None,
) -> "redis.Redis | None":
    """使用环境或配置设置连接到Redis。"""

    global _client

    if _client:
        return _client
    if redis is None:
        logger.warning("redis-py 非installed; Redis event bus disabled.")
        return None

    host = host or os.getenv("REDIS_HOST")
    port_env = os.getenv("REDIS_PORT")
    db_env = os.getenv("REDIS_DB")
    password = os.getenv("REDIS_PASSWORD")

    if host is None or port is None or db is None or password is None:
        try:  # pragma: no cover - optional configuration
            from autoai.config import Config

            cfg = Config()
            host = host or cfg.redis_host
            port = port or cfg.redis_port
            password = password or cfg.redis_password
        except Exception:  # pragma: no cover - configuration load failure
            pass

    host = host or "localhost"
    port = int(port if port is not None else (port_env or 6379))
    db = int(db if db is not None else (db_env or 0))

    try:
        _client = redis.Redis(host=host, port=port, db=db, password=password or None)
        _client.ping()
    except Exception as e:  # pragma: no cover - connection failure
        logger.warning(
            "Could not connect to Redis (%s:%s, db=%s): %s", host, port, db, e
        )
        _client = None
    return _client


def publish(event_type: str, payload: Any) -> None:
    """在``event_type``通道下发布``payload``。"""

    if _client is None and connect() is None:
        return

    assert _client is not None  # 用于type checkers

    if isinstance(payload, EventMessage):
        data = {
            "event_type": payload.event_type,
            "payload": payload.payload,
            "source_agent": payload.source_agent,
            "timestamp": payload.timestamp,
        }
    else:
        data = {"event_type": event_type, "payload": payload}

    _client.publish(event_type, json.dumps(data))


def subscribe(event_type: str, handler: Callable[[EventMessage], None]) -> None:
    """将``handler``订阅到``event_type``下发布的消息。"""

    if _client is None and connect() is None:
        return
    assert _client is not None

    pubsub = _client.pubsub()

    def _callback(message: dict[str, Any]) -> None:
        if message.get("type") != "message":
            return
        raw = message.get("data")
        if isinstance(raw, bytes):
            raw = raw.decode()
        raw_str = str(raw)
        try:
            data = json.loads(raw_str)
        except Exception:
            data = {"event_type": event_type, "payload": raw_str}
        if isinstance(data, dict) and data.get("event_type"):
            event = EventMessage(
                event_type=data.get("event_type", event_type),
                payload=data.get("payload"),
                source_agent=data.get("source_agent"),
                timestamp=data.get("timestamp"),
            )
        else:
            event = EventMessage(event_type=event_type, payload=data)
        handler(event)

    pubsub.subscribe(**{event_type: _callback})
    pubsub.run_in_thread(daemon=True)


__all__ = ["connect", "publish", "subscribe"]
