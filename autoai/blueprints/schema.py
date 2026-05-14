from __future__ import annotations

from dataclasses import dataclass, field
from importlib import import_module
from pathlib import Path
from typing import Any, Callable

import yaml


@dataclass
class AgentBlueprint:
    """Machine-readable blueprint describing an agent.

    YAML fields:
        role_name: Human-readable role identifier
        version: Version string
        core_prompt: Multiline system prompt
        agent_class: Dotted import path to the agent class
        authorized_plugins: List of plugin identifiers the agent may use
        subscribed_events: List of event types the agent subscribes to
        config: Arbitrary configuration dict passed to the agent constructor
    """

    role_name: str
    version: str
    core_prompt: str
    agent_class: str
    authorized_plugins: list[str] = field(default_factory=list)
    subscribed_events: list[str] = field(default_factory=list)
    config: dict[str, Any] = field(default_factory=dict)

    @staticmethod
    def load_from_file(path: str | Path) -> "AgentBlueprint":
        data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
        return AgentBlueprint(
            role_name=str(data.get("role_name", "")),
            version=str(data.get("version", "")),
            core_prompt=str(data.get("core_prompt", "")),
            agent_class=str(data.get("agent_class", "")),
            authorized_plugins=list(data.get("authorized_plugins", []) or []),
            subscribed_events=list(data.get("subscribed_events", []) or []),
            config=dict(data.get("config", {}) or {}),
        )

    def resolve_class(self) -> type:
        """Import and return the agent class specified by ``agent_class``.

        The ``agent_class`` must be a dotted import path like
        ``dual_ring_ai.genesis.tdd_developer.TDDDeveloperAgent``.
        """

        module_name, _, class_name = self.agent_class.rpartition(".")
        if not module_name:
            raise ImportError(f"Invalid agent_class path: {self.agent_class}")
        module = import_module(module_name)
        klass = getattr(module, class_name, None)
        if klass is None:
            raise ImportError(f"Class {class_name} not found in module {module_name}")
        return klass


def load_blueprints(directory: str | Path) -> list[AgentBlueprint]:
    """从目录加载所有``*.yaml``蓝图（非递归）。"""
    dir_path = Path(directory)
    blueprints: list[AgentBlueprint] = []
    for yaml_file in sorted(dir_path.glob("*.yaml")):
        try:
            blueprints.append(AgentBlueprint.load_from_file(yaml_file))
        except Exception:
            # 跳过 invalid blueprint files
            continue
    return blueprints


def instantiate_agent(blueprint: AgentBlueprint, *ctor_args: Any, **ctor_kwargs: Any) -> Any:
    """Instantiate an agent from ``blueprint`` using provided constructor args.

    This helper allows the caller to provide system resources like event bus,
    librarian, message queues, etc., as positional or keyword arguments.
    """

    agent_cls = blueprint.resolve_class()
    # Prefer classmethod 'from_蓝图' 如果present
    factory = getattr(agent_cls, "from_blueprint", None)
    if callable(factory):
        return factory(blueprint=blueprint, *ctor_args, **ctor_kwargs)  # type: ignore[misc]

    try:
        return agent_cls(*ctor_args, **ctor_kwargs)
    except TypeError:
        # As 一个last resort try calling 无positional args
        return agent_cls(**ctor_kwargs)


