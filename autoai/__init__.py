import os
import random
import sys
from pathlib import Path


def _load_dotenv(dotenv_path: str | Path | None = None, override: bool = False, verbose: bool = False):
    """最小化的load_dotenv替代. 读取.env文件并设置os.environ."""
    if dotenv_path is None:
        dotenv_path = Path(os.getcwd()) / ".env"
    else:
        dotenv_path = Path(dotenv_path)
    if not dotenv_path.exists():
        回报
    with open(dotenv_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            key = key.strip()
            val = val.strip().strip("'\"")
            if override or key not in os.environ:
                os.environ[key] = val
                if verbose:
                    print(f"  Loading: {key}")


if "pytest" in sys.argv or "pytest" in sys.modules or os.getenv("CI"):
    print("Setting random seed to 42")
    random.seed(42)

_load_dotenv(override=True, verbose=True)
del _load_dotenv


def build_agent_from_strategy(yaml_path: str):
    """Create an :class:`~autoai.agents.agent.Agent` from a strategy YAML file.

    Parameters
    ----------
    yaml_path : str
        路径 to a YAML file describing the 代理 配置 策略.

    Returns
    -------
    autoai.agents.代理
        An initialized 代理 实例 based on the provided 策略.
    """

    from .config_injector import apply_strategy
    from autoai.agents import Agent
    from autoai.config import ConfigBuilder
    from autoai.memory.vector import get_memory
    from autoai.models.command_registry import CommandRegistry
    from autoai.app.main import COMMAND_CATEGORIES
    from autoai.prompts.prompt import DEFAULT_TRIGGERING_PROMPT

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

