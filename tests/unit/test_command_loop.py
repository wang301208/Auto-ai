import pytest

from autogpt.agents import Agent, CommandRepetitionError
from autogpt.app.main import UserFeedback, run_interaction_loop


def test_execute_step_repeated_command_raises(agent: Agent, mocker):
    agent.config.max_repeated_commands = 2
    agent.config.repeat_window = 10
    mocker.patch.object(agent, "execute", return_value="done")

    agent.execute_step("test", {}, None)
    agent.execute_step("test", {}, None)
    with pytest.raises(CommandRepetitionError):
        agent.execute_step("test", {}, None)


def test_run_loop_prompts_user_on_repeated_command(agent: Agent, mocker):
    agent.config.max_repeated_commands = 2
    agent.config.repeat_window = 10
    agent.config.continuous_mode = True

    mocker.patch.object(agent, "think", return_value=("repeat", {}, {}))
    mock_execute = mocker.patch.object(agent, "execute", return_value="ok")

    mocker.patch("autogpt.app.main.update_user")
    mock_get_user_feedback = mocker.patch(
        "autogpt.app.main.get_user_feedback",
        return_value=(UserFeedback.EXIT, "", None),
    )

    with pytest.raises(SystemExit):
        run_interaction_loop(agent)

    assert mock_get_user_feedback.call_count == 1
    assert mock_execute.call_count == agent.config.max_repeated_commands
