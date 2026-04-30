"""Local voice adapter boundary."""

from __future__ import annotations


class LocalVoiceAdapter:
    """Text fallback for speech-to-text and text-to-speech integrations."""

    def __init__(self, mode: str = "text") -> None:
        self.mode = mode

    def transcribe_text(self, text: str) -> str:
        return text

    def synthesize_text(self, text: str) -> dict[str, str]:
        return {"mode": self.mode, "text": text}
