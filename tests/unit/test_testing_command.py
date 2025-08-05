import pytest

from autogpt.agents.agent import Agent
from autogpt.commands.testing import create_test_file, run_tests


def test_run_tests_success(workspace, agent: Agent):
    test_file = workspace.get_path("sample_test.py")
    with open(test_file, "w", encoding="utf-8") as f:
        f.write("def test_example():\n    assert True\n")

    result = run_tests(str(test_file), agent=agent)
    assert result["exit_code"] == 0
    assert result["status"] == "passed"
    assert result["successes"] == 1
    assert result["failures"] == 0
    assert result["errors"] == 0
    assert "1 passed" in result["logs"]


def test_run_tests_invalid_path(agent: Agent):
    with pytest.raises(ValueError, match="outside of workspace"):
        run_tests("../outside/test_sample.py", agent=agent)


def test_create_test_file_success(workspace, agent: Agent):
    test_file = workspace.get_path("tests/test_generated.py")
    content = "def test_example():\n    assert True\n"

    result = create_test_file(str(test_file), content, agent=agent)

    assert result == "File written to successfully."
    assert test_file.exists()
    with open(test_file, "r", encoding="utf-8") as f:
        assert content == f.read()


def test_create_test_file_invalid_path(workspace, agent: Agent):
    test_file = workspace.get_path("test_generated.py")

    result = create_test_file(str(test_file), "content", agent=agent)

    assert result.startswith("Error")
    assert not test_file.exists()


def test_create_test_file_invalid_name(workspace, agent: Agent):
    test_file = workspace.get_path("tests/generated.py")

    result = create_test_file(str(test_file), "content", agent=agent)

    assert result.startswith("Error")
    assert not test_file.exists()
