""" GTTS Voice. """
import os

try:
    import gtts
except ImportError:
    gtts = None
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


class GTTSVoice(VoiceBase):
    """GTTS Voice."""

    def _setup(self, config: Config) -> None:
        pass

    def _speech(self, text: str, _: int = 0) -> bool:
        """Play the given text."""
        if gtts is None:
            raise ImportError("gTTS is not installed")
        tts = gtts.gTTS(text)
        tts.save("speech.mp3")
        _play_sound("speech.mp3")
        os.remove("speech.mp3")
        return True
