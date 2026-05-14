import logging
import os

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

from autoai.config import Config
from autoai.speech.base import VoiceBase


class StreamElementsSpeech(VoiceBase):
    """Streamelements speech module for autoai"""

    def _setup(self, config: Config) -> None:
        """Setup the voices, API key, etc."""

    def _speech(self, text: str, voice: str, _: int = 0) -> bool:
        """Speak text using the streamelements API

        Args:
            text (str): The text to speak
            voice (str): The voice to use

        Returns:
            bool: True if the request was successful, False otherwise
        """
        if requests is None:
            raise ImportError("requests is not installed")
        tts_url = (
            f"https://api.streamelements.com/kappa/v2/speech?voice={voice}&text={text}"
        )
        response = requests.get(tts_url)

        if response.status_code == 200:
            with open("speech.mp3", "wb") as f:
                f.write(response.content)
            _play_sound("speech.mp3")
            os.remove("speech.mp3")
            return True
        else:
            logging.error(
                "Request failed with status code: %s, response content: %s",
                response.status_code,
                response.content,
            )
            return False
