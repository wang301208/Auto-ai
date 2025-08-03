import os
import random
import sys

from dotenv import load_dotenv

if "pytest" in sys.argv or "pytest" in sys.modules or os.getenv("CI"):
    print("Setting random seed to 42")
    random.seed(42)

# Load the users .env file into environment variables
load_dotenv(verbose=True, override=True)

del load_dotenv


def build_agent_from_strategy(yaml_path: str):
    """Create an :class:`~autogpt.agents.agent.Agent` from a strategy YAML file.

    Parameters
    ----------
    yaml_path : str
        Path to a YAML file describing the agent configuration strategy.

    Returns
    -------
    autogpt.agents.Agent
        An initialized agent instance based on the provided strategy.
    """

    from .config_injector import apply_strategy
    from autogpt.agents import Agent
    from autogpt.config import ConfigBuilder
    from autogpt.memory.vector import get_memory
    from autogpt.models.command_registry import CommandRegistry
    from autogpt.app.main import COMMAND_CATEGORIES
    from autogpt.prompts.prompt import DEFAULT_TRIGGERING_PROMPT

    cfg = apply_strategy(yaml_path)

    config = ConfigBuilder.build_config_from_env()
    command_registry = CommandRegistry.with_command_modules(COMMAND_CATEGORIES, config)
    cfg.command_registry = command_registry

    agent = Agent(
        memory=get_memory(config),
        command_registry=command_registry,
        ai_config=cfg,
        config=config,
        triggering_prompt=cfg.prompt_template or DEFAULT_TRIGGERING_PROMPT,
    )

    return agent

