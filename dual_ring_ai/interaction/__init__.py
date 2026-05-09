"""Interaction layer for 助手 (Zhushou).

Provides natural language interface for voice/text interaction.
"""

from .natural_language_interface import NaturalLanguageInterface

__all__ = ["NaturalLanguageInterface"]

"""Interaction layer composition for local multimodal IO."""

from .pipeline import InteractionPipeline
from .terminal_ui import TerminalUI, TUIConfig, create_tui
from .natural_language_interface import (
    NaturalLanguageInterface,
    InteractionConfig,
    UserInput,
    SystemResponse,
)

__all__ = [
    "InteractionPipeline",
    "TerminalUI",
    "TUIConfig",
    "create_tui",
    "NaturalLanguageInterface",
    "InteractionConfig",
    "UserInput",
    "SystemResponse",
]
