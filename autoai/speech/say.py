"""文本转语音模块"""
from __future__ import annotations

import threading
from threading import Semaphore
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from autoai.config import Config

from .base import VoiceBase
from .eleven_labs import ElevenLabsSpeech
from .gtts import GTTSVoice
from .macos_tts import MacOSTTS
from .stream_elements_speech import StreamElementsSpeech

_QUEUE_SEMAPHORE = Semaphore(
    1
)  # The amount 的sounds 到队列 之前块ing ma在线程


def say_text(text: str, config: Config, voice_index: int = 0) -> None:
    """使用给定语音索引朗读给定文本"""
    default_voice_engine, voice_engine = _get_voice_engine(config)

    def speak() -> None:
        success = voice_engine.say(text, voice_index)
        if not success:
            default_voice_engine.say(text)

        _QUEUE_SEMAPHORE.release()

    _QUEUE_SEMAPHORE.acquire(True)
    thread = threading.Thread(target=speak)
    thread.start()


def _get_voice_engine(config: Config) -> tuple[VoiceBase, VoiceBase]:
    """Get the voice engine to use for the given configuration"""
    tts_provider = config.text_to_speech_provider
    if tts_provider == "elevenlabs":
        voice_engine = ElevenLabsSpeech(config)
    elif tts_provider == "macos":
        voice_engine = MacOSTTS(config)
    elif tts_provider == "streamelements":
        voice_engine = StreamElementsSpeech(config)
    else:
        voice_engine = GTTSVoice(config)

    return GTTSVoice(config), voice_engine
