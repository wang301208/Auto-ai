from autoai.agents.agent import Agent, execute_command
from autoai.agents.base import BaseAgent
from autoai.llm.base import Message


def test_agent_initialization(agent: Agent):
    assert agent.ai_config.ai_name == "Base"
    assert agent.history.messages == []
    assert agent.cycle_budget is None
    assert "You are Base" in agent.system_prompt


def test_execute_command_plugin(agent: Agent):
    """Test that executing a command that came from a plugin works as expected"""
    command_name = "check_plan"
    agent.ai_config.prompt_generator.add_command(
        command_name,
        "Read the plan.md with the next goals to achieve",
        {},
        lambda: "hi",
    )
    command_result = execute_command(
        command_name=command_name,
        arguments={},
        agent=agent,
    )
    assert command_result == "hi"


def test_construct_base_prompt_handles_none(agent: Agent):
    prompt1 = BaseAgent.construct_base_prompt(agent, "one-shot")
    prompt2 = BaseAgent.construct_base_prompt(agent, "one-shot")

    assert len(prompt1) == 1
    assert len(prompt2) == 1


def test_construct_base_prompt_custom_messages(agent: Agent):
    prepend = [Message("user", "prepend")]
    append = [Message("assistant", "append")]

    prompt = agent.construct_base_prompt(
        "one-shot", prepend_messages=prepend, append_messages=append
    )

    assert prompt[1].content == "prepend"
    assert prompt[-1].content == "append"


# More test methods can be added for specific agent interactions
# For example, mocking chat_with_ai and testing the agent's interaction loop
