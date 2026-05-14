from __future__ import annotations

from pytest_mock import MockerFixture

from autoai.agents.agent import Agent


class CommandModifyingPlugin:
    """Plugin that modifies command name and arguments before execution."""

    def can_handle_pre_command(self) -> bool:  # noqa: D401
        """Indicate capability to handle pre_command."""
        return True

    def pre_command(
        self, command_name: str, arguments: dict[str, str]
    ) -> tuple[str, dict[str, str]]:
        return "modified_cmd", {"new_arg": "value"}

    def can_handle_post_command(self) -> bool:  # noqa: D401
        """Indicate capability to handle post_command."""
        return False


def test_pre_command_modifies_arguments(agent: Agent, mocker: MockerFixture) -> None:
    plugin = CommandModifyingPlugin()
    agent.config.plugins = [plugin]

    mocked_execute = mocker.patch(
        "autoai.agents.agent.execute_command", return_value="result"
    )

    agent.execute("orig", {"arg": "old"}, None)

    mocked_execute.assert_called_once()
    kwargs = mocked_execute.call_args.kwargs
    assert kwargs["command_name"] == "modified_cmd"
    assert kwargs["arguments"] == {"new_arg": "value"}
    assert kwargs["agent"] is agent
