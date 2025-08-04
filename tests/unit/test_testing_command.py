import pytest

from autogpt.agents.agent import Agent
from autogpt.commands.testing import run_tests


def test_run_tests_success(workspace, agent: Agent):
    test_file = workspace.get_path("sample_test.py")
    with open(test_file, "w", encoding="utf-8") as f:
        f.write("def test_example():\n    assert True\n")

    result = run_tests(str(test_file), agent=agent)
    assert "1 passed" in result


def test_run_tests_invalid_path(agent: Agent):
    with pytest.raises(ValueError, match="outside of workspace"):
        run_tests("../outside/test_sample.py", agent=agent)
