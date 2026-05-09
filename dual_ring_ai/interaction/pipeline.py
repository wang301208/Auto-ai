"""Local multimodal interaction pipeline used by the terminal UI backend."""

from __future__ import annotations

from typing import Any

from ..adapters.avatar import AvatarAdapter
from ..adapters.voice import LocalVoiceAdapter


class InteractionPipeline:
    """Compose text input, local or remote reasoning, speech text, and avatar state."""

    def __init__(
        self,
        voice: LocalVoiceAdapter | None = None,
        llm: Any | None = None,
        avatar: AvatarAdapter | None = None,
    ) -> None:
        from ..adapters.local_llm import LocalLLMAdapter

        self.voice = voice or LocalVoiceAdapter(mode="text")
        self.llm = llm or LocalLLMAdapter()
        self.avatar = avatar or AvatarAdapter()

    def handle_text(
        self,
        text: str,
        backend_payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        transcript = self.voice.transcribe_text(text)
        response = self.llm.generate_response(transcript, backend_payload or {})
        speech = self.voice.synthesize_text(response["text"])
        avatar_event = self.avatar.render_event(
            text=response["text"],
            emotion=response["emotion"],
            action=response["action"],
        )
        return {
            "transcript": transcript,
            "response_text": response["text"],
            "response": response,
            "speech": speech,
            "avatar_event": avatar_event,
        }
