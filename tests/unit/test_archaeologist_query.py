import importlib
import sys
import types

import pytest

from autogpt.event_bus import MessageQueue
from autogpt.config import Config

# Avoid importing autogpt.agents package initializer with heavy dependencies
agents_pkg = types.ModuleType("autogpt.agents")
agents_pkg.__path__ = ["autogpt/agents"]
sys.modules.setdefault("autogpt.agents", agents_pkg)

arch_module = importlib.import_module("autogpt.agents.archaeologist")
Archaeologist = arch_module.Archaeologist


def make_agent() -> Archaeologist:
    return Archaeologist(MessageQueue(), config=Config(use_librarian=False))


@pytest.mark.parametrize(
    "payload, expected",
    [
        ({"description": "runtime error", "plugin": "test"}, "runtime error"),
        (
            {
                "plugin": "test_plugin",
                "issue_type": "bug",
                "error_log": "ValueError: bad",
                "file": "mod.py",
                "line": 10,
            },
            "bug in plugin test_plugin, ValueError: bad, file mod.py, line 10",
        ),
        (
            {"plugin": "p", "data": {"nested": 1}, "items": [1, 2, 3]},
            "in plugin p",
        ),
        ({}, ""),
    ],
)
def test_generate_query(payload, expected) -> None:
    agent = make_agent()
    assert agent._generate_query(payload) == expected
