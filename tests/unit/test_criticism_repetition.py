from unittest.mock import ANY

from pytest_mock import MockerFixture

from autoai.app.main import print_assistant_thoughts
from autoai.config.config import Config
from autoai.core.runner.client_lib.parser import parse_next_ability


class DummyTask:
    objective = "Test objective"


def test_parse_next_ability_includes_repetition_assessment() -> None:
    next_ability = {
        "next_ability": "do_something",
        "ability_arguments": {"arg": "value"},
        "motivation": "Need to act",
        "self_criticism": "Yes, this action is similar to an earlier one because it repeats data collection, but continuing will refine the results.",
        "reasoning": "Further refinement is required.",
    }

    parsed = parse_next_ability(DummyTask(), next_ability)

    assert "Self-criticism (Is this action similar to an earlier one?):" in parsed
    assert "Yes, this action is similar to an earlier one" in parsed


def test_print_assistant_thoughts_displays_repetition_assessment(
    mocker: MockerFixture,
) -> None:
    ai_name = "TestAI"
    assistant_reply_json_valid = {
        "thoughts": {
            "text": "",
            "reasoning": "",
            "plan": "",
            "criticism": "No, this action is not similar to an earlier one; it explores a new approach.",
            "speak": "",
        }
    }
    logger_mock = mocker.patch("autoai.app.main.logger.typewriter_log")

    print_assistant_thoughts(ai_name, assistant_reply_json_valid, Config())

    logger_mock.assert_any_call(
        "CRITICISM (Is this action similar to an earlier one?):",
        ANY,
        "No, this action is not similar to an earlier one; it explores a new approach.",
    )
