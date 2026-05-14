"""ElevenLabs speech module"""
from __future__ import annotations

import os
from typing import TYPE_CHECKING

try:
    import requests
except ImportError:
    requests = None
def _play_sound(filepath: str, block: bool = True) -> None:
    """Play a sound file using the system default player. Replaces playsound."""
    import subprocess, sys
    try:
        if sys.platform == "win32":
            subprocess.Popen(["start", "", filepath], shell=True).wait()
        elif sys.platform == "darwin":
            subprocess.run(["afplay", filepath], check=False)
        else:
            subprocess.run(["aplay", filepath], check=False)
    except FileNotFoundError:
        pass

if TYPE_CHECKING:
    from autoai.config import Config
from .base import VoiceBase

PLACEHOLDERS = {"your-voice-id"}


class ElevenLabsSpeech(VoiceBase):
    """ElevenLabs speech class"""

    def _setup(self, config: Config) -> None:
        """Set up the voices, API key, etc.

        Returns:
            None: None
        """

        default_voices = ["ErXwobaYiN019PkySvjV", "EXAVITQu4vr4xnSDxMaL"]
        voice_options = {
            "Rachel": "21m00Tcm4TlvDq8ikWAM",
            "Domi": "AZnzlk1XvdvUeBnXmlld",
            "Bella": "EXAVITQu4vr4xnSDxMaL",
            "Antoni": "ErXwobaYiN019PkySvjV",
            "Elli": "MF3mGyEYCl7XYWbV9V6O",
            "Josh": "TxGEqnHWrfWFTfGW9XjX",
            "Arnold": "VR6AewLTigWG4xSOukaG",
            "Adam": "pNInz6obpgDQGcFmaJgB",
            "Sam": "yoZ06aMxZJJ28mfd3POQ",
        }
        self._headers = {
            "Content-Type": "application/json",
            "xi-api-key": config.elevenlabs_api_key,
        }
        self._voices = default_voices.copy()
        if config.elevenlabs_voice_id in voice_options:
            config.elevenlabs_voice_id = voice_options[config.elevenlabs_voice_id]
        if config.elevenlabs_voice_2_id in voice_options:
            config.elevenlabs_voice_2_id = voice_options[config.elevenlabs_voice_2_id]
        self._use_custom_voice(config.elevenlabs_voice_id, 0)
        self._use_custom_voice(config.elevenlabs_voice_2_id, 1)

    def _use_custom_voice(self, voice, voice_index) -> None:
        """Use a custom voice if provided and not a placeholder

        Args:
            voice (str): The voice ID
            voice_index (int): The voice index

        Returns:
            None: None
        """
        # 占位符 values that should be treated as 空
        if voice and voice not in PLACEHOLDERS:
            self._voices[voice_index] = voice

    def _speech(self, text: str, voice_index: int = 0) -> bool:
        """Speak text using elevenlabs.io's API

        Args:
            text (str): The text to speak
            voice_index (int, optional): The voice to use. Defaults to 0.

        Returns:
            bool: True if the request was successful, False otherwise
        """
        from autoai.logs import logger

        if requests is None:
            raise ImportError("requests is not installed")
        tts_url = (
            f"https://api.elevenlabs.io/v1/text-to-speech/{self._voices[voice_index]}"
        )
        response = requests.post(tts_url, headers=self._headers, json={"text": text})

        if response.status_code == 200:
            with open("speech.mpeg", "wb") as f:
                f.write(response.content)
            _play_sound("speech.mpeg")
            os.remove("speech.mpeg")
            return True
        else:
            logger.warn("Request failed with status code:", response.status_code)
            logger.info("Response content:", response.content)
            return False
