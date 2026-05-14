"""所有语音类的基类."""
from __future__ import annotations

import abc
import re
from threading import Lock
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from autoai.config import Config

from autoai.singleton import AbstractSingleton


class VoiceBase(AbstractSingleton):
    """
        所有语音类的基类.
"""

    def __init__(self, config: Config):
        """
                初始化语音类.
"""
        self._url = None
        self._headers = None
        self._api_key = None
        self._voices = []
        self._mutex = Lock()
        self._setup(config)

    def say(self, text: str, voice_index: int = 0) -> bool:
        """
                朗读给定文本.

                Args:
                    text (str): The text to say.
                    voice_index (int): The index of the voice to use.
"""
        text = re.sub(
            r"\b(?:https?://[-\w_.]+/?\w[-\w_.]*\.(?:[-\w_.]+/?\w[-\w_.]*\.)?[a-z]+(?:/[-\w_.%]+)*\b(?!\.))",
            "",
            text,
        )
        with self._mutex:
            return self._speech(text, voice_index)

    @abc.abstractmethod
    def _setup(self, config: Config) -> None:
        """
                设置语音、API密钥等.
"""

    @abc.abstractmethod
    def _speech(self, text: str, voice_index: int = 0) -> bool:
        """
                播放给定文本.

                Args:
                    text (str): The text to play.
"""
