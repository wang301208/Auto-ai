"""Built-in messaging platform adapters."""

from ..base import PlatformConfig
from .dingtalk import DingTalkAdapter
from .feishu import FeishuAdapter
from .weixin import WeixinAdapter

__all__ = [
    "DingTalkAdapter",
    "FeishuAdapter",
    "PlatformConfig",
    "WeixinAdapter",
]
