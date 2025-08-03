# Module to apply strategy YAML to AIConfig
from __future__ import annotations

from pathlib import Path
import yaml

from autogpt.config import AIConfig


def apply_strategy(yaml_path: str) -> AIConfig:
    """Load a strategy YAML file and return a populated AIConfig.

    The YAML file may define ``ai_name``, ``ai_role``, ``ai_goals`` and
    ``api_budget`` keys. Missing keys default to empty values.
    """

    path = Path(yaml_path)
    try:
        data = yaml.safe_load(path.read_text()) if path.is_file() else {}
    except Exception:
        data = {}

    if not isinstance(data, dict):
        data = {}

    ai_name = data.get("ai_name", "")
    ai_role = data.get("ai_role", "")
    ai_goals = data.get("ai_goals", []) or []
    api_budget = data.get("api_budget", 0.0)
    think_mode = data.get("think_mode")
    prompt_template = data.get("prompt_template")
    toolset = data.get("toolset", [])
    step_sequence = data.get("step_sequence", [])

    # Ensure goals are list of strings
    if not isinstance(ai_goals, list):
        ai_goals = list(ai_goals) if ai_goals is not None else []
    ai_goals = [str(goal) for goal in ai_goals]

    cfg = AIConfig(
        ai_name=ai_name,
        ai_role=ai_role,
        ai_goals=ai_goals,
        api_budget=float(api_budget) if api_budget is not None else 0.0,
        think_mode=think_mode,
        prompt_template=prompt_template,
        toolset=toolset,
        step_sequence=step_sequence,
    )

    return cfg
