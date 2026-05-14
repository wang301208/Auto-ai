"""Self improvement utilities."""

from autoai.event_bus import MessageQueue

from .critic import CriticAgent
from .database import DatabaseManager
from .logging import install_exception_logger
from .patcher import PatchAgent
from .plugin_processor import start_plugin_queue_processor
from .plugin_todo_queue import NEED_TOOL, PluginTodoQueue
from .self_develop import SelfDevelopManager
from .profiler import Profiler

__all__ = [
    "DatabaseManager",
    "install_exception_logger",
    "Profiler",
    "CriticAgent",
    "PatchAgent",
    "PluginTodoQueue",
    "start_plugin_queue_processor",
    "SelfDevelopManager",
    "NEED_TOOL",
    "MessageQueue",
]
