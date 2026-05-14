"""V1 subsystem injection as V2 Abilities.

Wraps SelfDevelopManager, SkillLibrary, and EventBus/MessageQueue
as V2 Ability 实例s so they can be discovered and invoked through
the V2 AbilityRegistry by the planner.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from autoai.event_bus import EventMessage, MessageQueue
from autoai.logs import logger
from autoai.self_improve import DatabaseManager, PluginTodoQueue
from autoai.self_improve.patcher import PatchAgent
from autoai.self_improve.self_develop import SelfDevelopManager
from autoai.skills import get_library
from autoai.skills.library import SkillLibrary

from .ability_adapter import Ability, AbilityResult, AbilityRegistry


class SelfDevelopAbility(Ability):
    """V2 Ability wrapper for SelfDevelopManager.

    Invoking this ability triggers a single review_repository() cycle.
    """

    def __init__(
        self,
        manager: SelfDevelopManager,
    ) -> None:
        self._manager = manager

    @classmethod
    def name(cls) -> str:
        return "self_develop_review"

    @classmethod
    def description(cls) -> str:
        return "Run a self-improvement review cycle: collect issues and apply fixes."

    @classmethod
    def arguments(cls) -> dict[str, Any]:
        return {}

    async def __call__(self, **kwargs: Any) -> AbilityResult:
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._manager.review_repository)
            return AbilityResult(output="Self-develop review completed", success=True)
        except Exception as e:
            logger.error(f"Self-develop re视图 failed: {e}")
            return AbilityResult.failure(str(e))


class SkillSearchAbility(Ability):
    """V2 Ability wrapper for SkillLibrary semantic search.

    Arguments:
        query: The search query string.
        top_k: Number of results to return (default 5).
    """

    def __init__(self, library: SkillLibrary | None = None) -> None:
        self._library = library

    @classmethod
    def name(cls) -> str:
        return "skill_search"

    @classmethod
    def description(cls) -> str:
        return "Search the skill library for relevant skills by semantic query."

    @classmethod
    def arguments(cls) -> dict[str, Any]:
        return {
            "query": {"type": "string", "description": "Search query"},
            "top_k": {"type": "integer", "description": "Max results", "default": 5},
        }

    async def __call__(self, **kwargs: Any) -> AbilityResult:
        query = kwargs.get("query", "")
        top_k = kwargs.get("top_k", 5)
        try:
            lib = self._library or get_library()
            matches = lib.search(query, top_k=top_k)
            if not matches:
                return AbilityResult(output="No skills found", success=True)
            results = [
                {"name": s.name, "version": s.version, "description": s.description}
                for s in matches
            ]
            return AbilityResult(output=results, success=True)
        except Exception as e:
            return AbilityResult.failure(str(e))


class SkillExecuteAbility(Ability):
    """V2 Ability wrapper for executing a skill by name.

    Arguments:
        skill_name: Name of the skill to execute.
        skill_version: Version of the skill (default "latest").
    """

    @classmethod
    def name(cls) -> str:
        return "skill_execute"

    @classmethod
    def description(cls) -> str:
        return "Execute a named skill from the skill library."

    @classmethod
    def arguments(cls) -> dict[str, Any]:
        return {
            "skill_name": {"type": "string", "description": "Skill name"},
            "skill_version": {"type": "string", "description": "Skill version", "default": "latest"},
        }

    async def __call__(self, **kwargs: Any) -> AbilityResult:
        skill_name = kwargs.get("skill_name", "")
        skill_version = kwargs.get("skill_version", "latest")
        try:
            library = get_library()
            skill = library.get_skill(skill_name, skill_version)
            if skill is None:
                return AbilityResult.failure(f"Skill '{skill_name}' not found")
            return AbilityResult(
                output={"code": skill.code, "name": skill.name},
                success=True,
            )
        except Exception as e:
            return AbilityResult.failure(str(e))


class EventBusPublishAbility(Ability):
    """V2 Ability wrapper for publishing events to EventBus.

    Arguments:
        event_type: Type of event.
        payload: Event payload dict.
        source_agent: Source agent name.
    """

    def __init__(self, message_queue: MessageQueue | None = None) -> None:
        self._queue = message_queue

    @classmethod
    def name(cls) -> str:
        return "event_publish"

    @classmethod
    def description(cls) -> str:
        return "Publish an event to the event bus."

    @classmethod
    def arguments(cls) -> dict[str, Any]:
        return {
            "event_type": {"type": "string", "description": "Event type"},
            "payload": {"type": "object", "description": "Event payload"},
            "source_agent": {"type": "string", "description": "Source agent"},
        }

    async def __call__(self, **kwargs: Any) -> AbilityResult:
        if self._queue is None:
            return AbilityResult.failure("No MessageQueue configured")
        try:
            event = EventMessage(
                event_type=kwargs.get("event_type", "custom"),
                payload=kwargs.get("payload"),
                source_agent=kwargs.get("source_agent"),
            )
            self._queue.publish(event)
            return AbilityResult(output="Event published", success=True)
        except Exception as e:
            return AbilityResult.failure(str(e))


class EventBusQueryAbility(Ability):
    """V2 Ability wrapper for querying events from EventBus.

    Arguments:
        limit: Maximum number of recent events to return.
    """

    def __init__(self, message_queue: MessageQueue | None = None) -> None:
        self._queue = message_queue

    @classmethod
    def name(cls) -> str:
        return "event_query"

    @classmethod
    def description(cls) -> str:
        return "Query recent events from the event bus."

    @classmethod
    def arguments(cls) -> dict[str, Any]:
        return {
            "limit": {"type": "integer", "description": "Max events", "default": 10},
        }

    async def __call__(self, **kwargs: Any) -> AbilityResult:
        if self._queue is None:
            return AbilityResult.failure("No MessageQueue configured")
        try:
            limit = kwargs.get("limit", 10)
            events = list(self._queue.get_events(limit=limit))
            result = [
                {
                    "event_type": e.event_type,
                    "payload": e.payload,
                    "timestamp": e.timestamp,
                }
                for e in events
            ]
            return AbilityResult(output=result, success=True)
        except Exception as e:
            return AbilityResult.failure(str(e))


def inject_v1_subsystems(
    ability_registry: AbilityRegistry,
    *,
    self_develop_manager: SelfDevelopManager | None = None,
    skill_library: SkillLibrary | None = None,
    message_queue: MessageQueue | None = None,
) -> None:
    """Register V1 subsystems as V2 Abilities into the given AbilityRegistry.

        Args:
            ability_registry: The V2 AbilityRegistry to register into.
            self_develop_manager: Optional SelfDevelopManager 实例.
            skill_library: Optional SkillLibrary 实例.
            message_queue: Optional MessageQueue 实例.
"""
    if self_develop_manager is not None:
        ability_registry.register(SelfDevelopAbility(self_develop_manager))
        logger.debug("[Inject] 已注册 SelfDevelopAbility")

    ability_registry.register(SkillSearchAbility(skill_library))
    logger.debug("[Inject] 已注册 SkillSearchAbility")

    ability_registry.register(SkillExecuteAbility())
    logger.debug("[Inject] 已注册 SkillExecuteAbility")

    ability_registry.register(EventBusPublishAbility(message_queue))
    logger.debug("[Inject] 已注册 EventBusPublishAbility")

    ability_registry.register(EventBusQueryAbility(message_queue))
    logger.debug("[Inject] 已注册 EventBusQueryAbility")


def create_self_develop_manager(
    *,
    plugin_queue: PluginTodoQueue,
    db: DatabaseManager,
    message_queue: MessageQueue | None,
    workspace: Path,
    patch_agent: PatchAgent | None = None,
    **kwargs: Any,
) -> SelfDevelopManager:
    """创建具有合理默认值的SelfDevelopManager的工厂辅助函数。"""
    if patch_agent is None:
        patch_agent = PatchAgent(workspace=workspace)
    return SelfDevelopManager(
        plugin_queue=plugin_queue,
        patch_agent=patch_agent,
        db=db,
        message_queue=message_queue,
        workspace=workspace,
        **kwargs,
    )
