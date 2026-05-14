import os
from unittest.mock import MagicMock, patch

import pytest
import requests

from autoai.app.utils import get_bulletin_from_web, get_latest_bulletin
from autoai.config import Config
from autoai.json_utils.utilities import extract_dict_from_response, validate_dict
from autoai.utils import validate_yaml_file


@pytest.fixture
def valid_json_response() -> dict:
    return {
        "thoughts": {
            "text": "My task is complete. I will use the 'task_complete' command to shut down.",
            "reasoning": "I will use the 'task_complete' command because it allows me to shut down and signal that my task is complete.",
            "plan": "I will use the 'task_complete' command with the reason 'Task complete: retrieved Tesla's revenue in 2022.' to shut down.",
            "criticism": "I need to ensure that I have completed all necessary tasks before shutting down.",
            "speak": "",
        },
        "command": {
            "name": "task_complete",
            "args": {"reason": "Task complete: retrieved Tesla's revenue in 2022."},
        },
    }


@pytest.fixture
def invalid_json_response() -> dict:
    return {
        "thoughts": {
            "text": "My task is complete. I will use the 'task_complete' command to shut down.",
            "reasoning": "I will use the 'task_complete' command because it allows me to shut down and signal that my task is complete.",
            "plan": "I will use the 'task_complete' command with the reason 'Task complete: retrieved Tesla's revenue in 2022.' to shut down.",
            "criticism": "I need to ensure that I have completed all necessary tasks before shutting down.",
            "speak": "",
        },
        "command": {"name": "", "args": {}},
    }


def test_validate_yaml_file_valid() -> None:
    with open("valid_test_file.yaml", "w") as f:
        f.write("setting: value")
    result, message = validate_yaml_file("valid_test_file.yaml")
    os.remove("valid_test_file.yaml")

    assert result == True
    assert "Successfully validated" in message


def test_validate_yaml_file_not_found() -> None:
    result, message = validate_yaml_file("non_existent_file.yaml")

    assert result == False
    assert "wasn't found" in message


def test_validate_yaml_file_invalid() -> None:
    with open("invalid_test_file.yaml", "w") as f:
        f.write(
            "settings:\n  first_setting: value\n  second_setting: value\n    nested_setting: value\n  third_setting: value\nunindented_setting: value"
        )
    result, message = validate_yaml_file("invalid_test_file.yaml")
    os.remove("invalid_test_file.yaml")
    print(result)
    print(message)
    assert result == False
    assert "There was an issue while trying to read" in message


@patch("requests.get")
def test_get_bulletin_from_web_success(mock_get: MagicMock) -> None:
    expected_content = "Test bulletin from web"

    mock_get.return_value.status_code = 200
    mock_get.return_value.text = expected_content
    bulletin = get_bulletin_from_web()

    assert expected_content in bulletin
    mock_get.assert_called_with(
        "https://raw.githubusercontent.com/Significant-Gravitas/Auto-AI/master/BULLETIN.md"
    )


@patch("requests.get")
def test_get_bulletin_from_web_failure(mock_get: MagicMock) -> None:
    mock_get.return_value.status_code = 404
    bulletin = get_bulletin_from_web()

    assert bulletin == ""


@patch("requests.get")
def test_get_bulletin_from_web_exception(mock_get: MagicMock) -> None:
    mock_get.side_effect = requests.exceptions.RequestException()
    bulletin = get_bulletin_from_web()

    assert bulletin == ""


def test_get_latest_bulletin_no_file() -> None:
    if os.path.exists("data/CURRENT_BULLETIN.md"):
        os.remove("data/CURRENT_BULLETIN.md")
    with patch("autoai.app.utils.get_bulletin_from_web", return_value="bulletin"):
        bulletin, is_new = get_latest_bulletin()
        assert is_new


def test_get_latest_bulletin_with_file() -> None:
    expected_content = "Test bulletin"
    with open("data/CURRENT_BULLETIN.md", "w", encoding="utf-8") as f:
        f.write(expected_content)

    with patch("autoai.app.utils.get_bulletin_from_web", return_value=""):
        bulletin, is_new = get_latest_bulletin()
        assert expected_content in bulletin
        assert is_new == False

    os.remove("data/CURRENT_BULLETIN.md")


def test_get_latest_bulletin_with_new_bulletin() -> None:
    with open("data/CURRENT_BULLETIN.md", "w", encoding="utf-8") as f:
        f.write("Old bulletin")

    expected_content = "New bulletin from web"
    with patch(
        "autoai.app.utils.get_bulletin_from_web", return_value=expected_content
    ):
        bulletin, is_new = get_latest_bulletin()
        assert "::NEW BULLETIN::" in bulletin
        assert expected_content in bulletin
        assert is_new

    os.remove("data/CURRENT_BULLETIN.md")


def test_get_latest_bulletin_new_bulletin_same_as_old_bulletin() -> None:
    expected_content = "Current bulletin"
    with open("data/CURRENT_BULLETIN.md", "w", encoding="utf-8") as f:
        f.write(expected_content)

    with patch(
        "autoai.app.utils.get_bulletin_from_web", return_value=expected_content
    ):
        bulletin, is_new = get_latest_bulletin()
        assert expected_content in bulletin
        assert is_new == False

    os.remove("data/CURRENT_BULLETIN.md")


def test_validate_json_valid(valid_json_response: dict, config: Config) -> None:
    valid, errors = validate_dict(valid_json_response, config)
    assert valid
    assert errors is None


def test_validate_json_invalid(invalid_json_response: dict, config: Config) -> None:
    valid, errors = validate_dict(valid_json_response, config)
    assert not valid
    assert errors is not None


def test_extract_json_from_response(valid_json_response: dict) -> None:
    emulated_response_from_openai = str(valid_json_response)
    assert (
        extract_dict_from_response(emulated_response_from_openai) == valid_json_response
    )


def test_extract_json_from_response_wrapped_in_code_block(
    valid_json_response: dict,
) -> None:
    emulated_response_from_openai = "```" + str(valid_json_response) + "```"
    assert (
        extract_dict_from_response(emulated_response_from_openai) == valid_json_response
    )
