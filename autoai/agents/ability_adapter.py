"""Adapter bridging V1 CommandRegistry commands to V2 Ability interface.

Each V1 @command-decorated function is wrapped as an Ability subclass
instance, enabling the V2 architecture to invoke V1 commands through
the standardized async Ability.__call__() interface.
"""

from __future__ import annotations

import asyncio
from abc import ABCMeta, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable

from autoai.models.command_registry import CommandRegistry


@dataclass
class AbilityResult:
    """Standard result container for ability execution."""

    output: Any = None
    success: bool = True
    error: str | None = None

    @classmethod
    def failure(cls, error: str) -> AbilityResult:
        return cls(success=False, error=error)


class Ability(metaclass=ABCMeta):
    """Abstract base class for all abilities (V2 interface)."""

    @classmethod
    @abstractmethod
    def name(cls) -> str: ...

    @classmethod
    @abstractmethod
    def description(cls) -> str: ...

    @classmethod
    def arguments(cls) -> dict[str, Any]:
        return {}

    @abstractmethod
    async def __call__(self, **kwargs: Any) -> AbilityResult:
        ...

    def __repr__(self) -> str:
        return f"Ability({self.name()})"


class CommandAbility(Ability):
    """Wraps a V1 command function as a V2 Ability.

    Bridges the synchronous V1 command execution into the async
    V2 ability interface using asyncio.run_in_executor.
    """

    def __init__(
        self,
        command_name: str,
        command_fn: Callable,
        command_description: str = "",
        command_args_spec: dict[str, Any] | None = None,
    ) -> None:
        self._command_name = command_name
        self._command_fn = command_fn
        self._description = command_description
        self._args_spec = command_args_spec or {}

    @classmethod
    def name(cls) -> str:
        return cls._command_name

    @classmethod
    def description(cls) -> str:
        return cls._description

    @classmethod
    def arguments(cls) -> dict[str, Any]:
        return cls._args_spec

    async def __call__(self, **kwargs: Any) -> AbilityResult:
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None, lambda: self._command_fn(**kwargs)
            )
            return AbilityResult(output=result, success=True)
        except Exception as e:
            return AbilityResult.failure(str(e))

    def __repr__(self) -> str:
        return f"CommandAbility({self._command_name})"


class AbilityRegistry:
    """Registry of abilities, supporting both V2 native and V1 adapted commands."""

    def __init__(self) -> None:
        self._abilities: dict[str, Ability] = {}

    def register(self, ability: Ability) -> None:
        key = ability._command_name if isinstance(ability, CommandAbility) else ability.name()
        self._abilities[key] = ability

    def get(self, name: str) -> Ability | None:
        return self._abilities.get(name)

    def list_abilities(self) -> list[dict[str, Any]]:
        return [
            {
                "name": a._command_name if isinstance(a, CommandAbility) else a.name(),
                "description": a._description if isinstance(a, CommandAbility) else a.description(),
            }
            for a in self._abilities.values()
        ]

    async def perform(self, name: str, **kwargs: Any) -> AbilityResult:
        ability = self._abilities.get(name)
        if ability is None:
            return AbilityResult.failure(f"Unknown ability: {name}")
        return await ability(**kwargs)


def adapt_command_registry(command_registry: CommandRegistry) -> AbilityRegistry:
    """Convert a V1 CommandRegistry into a V2 AbilityRegistry.

    Each registered command is wrapped in a CommandAbility adapter.
    """
    ability_registry = AbilityRegistry()
    for name, command in command_registry.commands.items():
        ability = CommandAbility(
            command_name=name,
            command_fn=command.method,
            command_description=command.description or "",
            command_args_spec=getattr(command, "parameters", {}),
        )
        ability_registry.register(ability)
    return ability_registry
