import tempfile
from types import SimpleNamespace
import sys

import yaml

import autoai.config_injector as injector
from autoai.config import AIConfig


def test_apply_strategy_populates_ai_config(tmp_path):
    data = {
        "ai_name": "TestAI",
        "ai_role": "Testing agent",
        "ai_goals": ["goal1", "goal2"],
        "api_budget": 10.5,
        "think_mode": "manual",
        "prompt_template": "template",
        "toolset": ["search"],
        "step_sequence": ["plan"],
    }
    yaml_file = tmp_path / "strategy.yaml"
    yaml_file.write_text(yaml.safe_dump(data))

    cfg = injector.apply_strategy(str(yaml_file))
    assert isinstance(cfg, AIConfig)
    assert cfg.ai_name == data["ai_name"]
    assert cfg.ai_role == data["ai_role"]
    assert cfg.ai_goals == data["ai_goals"]
    assert cfg.api_budget == data["api_budget"]
    assert cfg.think_mode == data["think_mode"]
    assert cfg.prompt_template == data["prompt_template"]
    assert cfg.toolset == data["toolset"]
    assert cfg.step_sequence == data["step_sequence"]


def test_build_agent_from_strategy_uses_ai_config(tmp_path, monkeypatch):
    data = {
        "ai_name": "TestAI",
        "ai_role": "Testing agent",
        "ai_goals": ["goal1"],
    }
    yaml_file = tmp_path / "strategy.yaml"
    yaml_file.write_text(yaml.safe_dump(data))

    # stub dependencies to avoid heavy imports
    sys.modules['autoai.agents'] = SimpleNamespace(Agent=lambda **kwargs: SimpleNamespace(**kwargs))
    sys.modules['autoai.app.main'] = SimpleNamespace(COMMAND_CATEGORIES=[])
    sys.modules['autoai.memory.vector'] = SimpleNamespace(get_memory=lambda cfg: SimpleNamespace())
    sys.modules['autoai.models.command_registry'] = SimpleNamespace(CommandRegistry=SimpleNamespace(with_command_modules=lambda modules, config: SimpleNamespace()))
    sys.modules['autoai.prompts.prompt'] = SimpleNamespace(DEFAULT_TRIGGERING_PROMPT='default')
    import autoai.config as config_module
    monkeypatch.setattr(config_module, 'ConfigBuilder', SimpleNamespace(build_config_from_env=lambda *a, **k: SimpleNamespace()))

    import autoai
    agent = autoai.build_agent_from_strategy(str(yaml_file))
    assert agent.ai_config.ai_name == data["ai_name"]
    assert agent.ai_config.ai_role == data["ai_role"]
    assert agent.ai_config.ai_goals == data["ai_goals"]
