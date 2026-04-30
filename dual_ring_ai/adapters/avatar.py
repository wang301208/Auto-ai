"""Avatar event adapter boundary."""

from __future__ import annotations

from datetime import UTC, datetime


class AvatarAdapter:
    """Produce render events for a future Three.js avatar frontend."""

    def render_event(self, text: str, emotion: str, action: str) -> dict[str, str]:
        return {
            "text": text,
            "emotion": emotion,
            "animation": action,
            "timestamp": datetime.now(UTC).isoformat(),
        }
