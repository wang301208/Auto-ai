""" GTTS语音。"""
import os

try:
    import gtts
except ImportError:
    gtts = None
def _play_sound(filepath: str, block: bool = True) -> None:
    """使用系统默认播放器播放音频文件. 替代playsound."""
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
    """GTTS语音。"""

    def _setup(self, config: Config) -> None:
        pass

    def _speech(self, text: str, _: int = 0) -> bool:
        """播放给定文本."""
        if gtts is None:
            raise ImportError("gTTS未安装")
        tts = gtts.gTTS(text)
        tts.save("speech.mp3")
        _play_sound("speech.mp3")
        os.remove("speech.mp3")
        return True
