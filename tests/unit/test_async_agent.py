"""Tests for the unified AsyncAgent (V1+V2 merged architecture).

Covers:
- Initialization with and without planner
- Task-driven think() flow (build_plan, determine_next_ability)
- Task lifecycle (queue, completion, acceptance criteria)
- Subsystem injection (SelfDevelopAbility, SkillSearchAbility, EventBus abilities)
- Command repetition detection
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from autogpt.agents.async_agent import AsyncAgent, CommandRepetitionError
from autogpt.agents.ability_adapter import AbilityRegistry, AbilityResult
from autogpt.agents.subsystem_injection import (
    EventBusPublishAbility,
    EventBusQueryAbility,
    SelfDevelopAbility,
    SkillExecuteAbility,
    SkillSearchAbility,
    inject_v1_subsystems,
)

from autogpt.core.planning.schema import Task, TaskStatus, TaskType

from autogpt.event_bus import EventMessage, MessageQueue


class _FakePlanner:
    async def make_initial_plan(self, **kwargs):
        return MagicMock(
            content={
                "task_list": [
                    {
                        "objective": "Research topic",
                        "type": "research",
                        "priority": 2,
                        "ready_criteria": ["Query defined"],
                        "acceptance_criteria": ["Results found"],
                    },
                    {
                        "objective": "Write report",
                        "type": "write",
                        "priority": 1,
                        "ready_criteria": ["Research done"],
                        "acceptance_criteria": ["Report complete"],
                    },
                ]
            }
        )

    async def determine_next_ability(self, task, ability_schema):
        objective = getattr(task, "objective", "")
        return MagicMock(
            content={
                "next_ability": "skill_search",
                "ability_arguments": {"query": objective},
                "reasoning": "Search for relevant skill",
                "self_criticism": "",
            }
        )


def _make_task(objective="Test task", ttype="code", priority=1,
                ready_criteria=None, acceptance_criteria=None, cycle_count=0):
    return Task(
        objective=objective,
        type=TaskType(ttype),
        priority=priority,
        ready_criteria=ready_criteria or ["Ready"],
        acceptance_criteria=acceptance_criteria or ["Done"],
    )


# ======================================================================
# Initialization Tests (using project fixtures)
# ======================================================================


class TestAsyncAgentInit:
    def test_init_without_planner(self, agent):
        async_agent = AsyncAgent(
            memory=agent.vector_memory if hasattr(agent, "vector_memory") else agent.memory,
            command_registry=agent.command_registry,
            triggering_prompt="Test",
            ai_config=agent.ai_config,
            config=agent.config,
            plugin_queue=getattr(agent, "plugin_queue", None),
            message_queue=getattr(agent, "message_queue", None),
            db=getattr(agent, "db", None),
        )
        assert async_agent._planner is None
        assert async_agent._task_queue == []
        assert async_agent._completed_tasks == []
        assert async_agent._current_task is None
        assert async_agent._ability_registry is not None

    def test_init_with_planner(self, agent):
        planner = _FakePlanner()
        async_agent = AsyncAgent(
            memory=agent.vector_memory if hasattr(agent, "vector_memory") else agent.memory,
            command_registry=agent.command_registry,
            triggering_prompt="Test",
            ai_config=agent.ai_config,
            config=agent.config,
            planner=planner,
        )
        assert async_agent._planner is planner
        assert async_agent._max_task_cycle_count == 3


# ======================================================================
# Task-Driven Planning Tests
# ======================================================================


class TestTaskPlanning:
    @pytest.mark.asyncio
    async def test_build_plan_with_planner(self, agent):
        planner = _FakePlanner()
        async_agent = AsyncAgent(
            memory=agent.vector_memory if hasattr(agent, "vector_memory") else agent.memory,
            command_registry=agent.command_registry,
            triggering_prompt="Test",
            ai_config=agent.ai_config,
            config=agent.config,
            planner=planner,
        )
        tasks = await async_agent.build_plan()
        assert len(tasks) == 2
        assert tasks[0].objective == "Research topic"
        assert tasks[0].priority == 2
        assert tasks[1].objective == "Write report"

    @pytest.mark.asyncio
    async def test_build_plan_without_planner(self, agent):
        async_agent = AsyncAgent(
            memory=agent.vector_memory if hasattr(agent, "vector_memory") else agent.memory,
            command_registry=agent.command_registry,
            triggering_prompt="Test",
            ai_config=agent.ai_config,
            config=agent.config,
        )
        tasks = await async_agent.build_plan()
        assert len(tasks) == 1
        assert tasks[0].objective == "Test"

    @pytest.mark.asyncio
    async def test_build_plan_marks_last_task_ready(self, agent):
        planner = _FakePlanner()
        async_agent = AsyncAgent(
            memory=agent.vector_memory if hasattr(agent, "vector_memory") else agent.memory,
            command_registry=agent.command_registry,
            triggering_prompt="Test",
            ai_config=agent.ai_config,
            config=agent.config,
            planner=planner,
        )
        await async_agent.build_plan()
        last_task = async_agent._task_queue[-1]
        assert last_task.context.status == TaskStatus.READY

    @pytest.mark.asyncio
    async def test_determine_next_ability_empty_queue(self, agent):
        async_agent = AsyncAgent(
            memory=agent.vector_memory if hasattr(agent, "vector_memory") else agent.memory,
            command_registry=agent.command_registry,
            triggering_prompt="Test",
            ai_config=agent.ai_config,
            config=agent.config,
        )
        result = await async_agent.determine_next_ability_from_plan()
        assert result is None

    @pytest.mark.asyncio
    async def test_determine_next_ability_with_tasks(self, agent):
        planner = _FakePlanner()
        async_agent = AsyncAgent(
            memory=agent.vector_memory if hasattr(agent, "vector_memory") else agent.memory,
            command_registry=agent.command_registry,
            triggering_prompt="Test",
            ai_config=agent.ai_config,
            config=agent.config,
            planner=planner,
        )
        await async_agent.build_plan()
        result = await async_agent.determine_next_ability_from_plan()
        assert result is not None
        task, next_ability = result
        assert task.objective == "Research topic"
        assert next_ability["next_ability"] == "skill_search"


# ======================================================================
# Task Lifecycle Tests
# ======================================================================


class TestTaskLifecycle:
    def test_evaluate_task_sets_in_progress(self, agent):
        async_agent = AsyncAgent(
            memory=agent.vector_memory if hasattr(agent, "vector_memory") else agent.memory,
            command_registry=agent.command_registry,
            triggering_prompt="Test",
            ai_config=agent.ai_config,
            config=agent.config,
        )
        task = _make_task()
        result = async_agent._evaluate_task_and_add_context(task)
        assert result.context.status == TaskStatus.IN_PROGRESS
        assert result.context.enough_info is True

    def test_evaluate_task_keeps_in_progress(self, agent):
        async_agent = AsyncAgent(
            memory=agent.vector_memory if hasattr(agent, "vector_memory") else agent.memory,
            command_registry=agent.command_registry,
            triggering_prompt="Test",
            ai_config=agent.ai_config,
            config=agent.config,
        )
        task = _make_task()
        task.context.status = TaskStatus.IN_PROGRESS
        result = async_agent._evaluate_task_and_add_context(task)
        assert result.context.cycle_count == 0

    def test_update_task_after_execution_completes_on_max_cycles(self, agent):
        async_agent = AsyncAgent(
            memory=agent.vector_memory if hasattr(agent, "vector_memory") else agent.memory,
            command_registry=agent.command_registry,
            triggering_prompt="Test",
            ai_config=agent.ai_config,
            config=agent.config,
        )
        async_agent._max_task_cycle_count = 1
        task = _make_task()
        async_agent._current_task = task
        task.context.cycle_count = 1
        async_agent._update_task_after_execution("test_cmd", "result")
        assert task.context.status == TaskStatus.DONE
        assert task in async_agent._completed_tasks
        assert async_agent._current_task is None

    def test_update_task_requeues_on_unmet_criteria(self, agent):
        async_agent = AsyncAgent(
            memory=agent.vector_memory if hasattr(agent, "vector_memory") else agent.memory,
            command_registry=agent.command_registry,
            triggering_prompt="Test",
            ai_config=agent.ai_config,
            config=agent.config,
        )
        task = _make_task(acceptance_criteria=["specific success keyword"])
        async_agent._current_task = task
        async_agent._update_task_after_execution("test_cmd", "no match here")
        assert task in async_agent._task_queue
        assert async_agent._current_task is None

    def test_update_task_completes_on_acceptance_match(self, agent):
        async_agent = AsyncAgent(
            memory=agent.vector_memory if hasattr(agent, "vector_memory") else agent.memory,
            command_registry=agent.command_registry,
            triggering_prompt="Test",
            ai_config=agent.ai_config,
            config=agent.config,
        )
        task = _make_task(acceptance_criteria=["success"])
        async_agent._current_task = task
        async_agent._update_task_after_execution("test_cmd", "Operation was a success!")
        assert task in async_agent._completed_tasks
        assert task.context.status == TaskStatus.DONE

    @pytest.mark.asyncio
    async def test_choose_next_ability_exceeds_cycle_count(self, agent):
        planner = _FakePlanner()
        async_agent = AsyncAgent(
            memory=agent.vector_memory if hasattr(agent, "vector_memory") else agent.memory,
            command_registry=agent.command_registry,
            triggering_prompt="Test",
            ai_config=agent.ai_config,
            config=agent.config,
            planner=planner,
        )
        async_agent._max_task_cycle_count = 2
        task = _make_task(objective="Overdue task")
        task.context.cycle_count = 3
        task.context.enough_info = True
        with pytest.raises(RuntimeError, match="exceeded max cycle count"):
            await async_agent._choose_next_ability(task, [])

    @pytest.mark.asyncio
    async def test_choose_next_ability_insufficient_info(self, agent):
        planner = _FakePlanner()
        async_agent = AsyncAgent(
            memory=agent.vector_memory if hasattr(agent, "vector_memory") else agent.memory,
            command_registry=agent.command_registry,
            triggering_prompt="Test",
            ai_config=agent.ai_config,
            config=agent.config,
            planner=planner,
        )
        task = _make_task(objective="Uninformed task")
        task.context.enough_info = False
        with pytest.raises(RuntimeError, match="Not enough information"):
            await async_agent._choose_next_ability(task, [])

    def test_update_task_with_dict_fallback(self, agent):
        async_agent = AsyncAgent(
            memory=agent.vector_memory if hasattr(agent, "vector_memory") else agent.memory,
            command_registry=agent.command_registry,
            triggering_prompt="Test",
            ai_config=agent.ai_config,
            config=agent.config,
        )
        async_agent._max_task_cycle_count = 1
        task_dict = {"objective": "Dict task", "cycle_count": 0, "status": "in_progress"}
        async_agent._current_task = task_dict
        async_agent._update_task_after_execution("cmd", "result")
        assert task_dict["cycle_count"] == 1
        assert task_dict["status"] == "done"


# ======================================================================
# Task Property Tests
# ======================================================================


class TestTaskProperties:
    def test_completed_tasks_property(self, agent):
        async_agent = AsyncAgent(
            memory=agent.vector_memory if hasattr(agent, "vector_memory") else agent.memory,
            command_registry=agent.command_registry,
            triggering_prompt="Test",
            ai_config=agent.ai_config,
            config=agent.config,
        )
        assert async_agent.completed_tasks == []

    def test_current_task_property_none(self, agent):
        async_agent = AsyncAgent(
            memory=agent.vector_memory if hasattr(agent, "vector_memory") else agent.memory,
            command_registry=agent.command_registry,
            triggering_prompt="Test",
            ai_config=agent.ai_config,
            config=agent.config,
        )
        assert async_agent.current_task is None


# ======================================================================
# Subsystem Injection Tests (no project fixtures needed)
# ======================================================================


class TestSubsystemInjection:
    @pytest.mark.asyncio
    async def test_skill_search_ability(self):
        ability = SkillSearchAbility(library=None)
        with patch("autogpt.agents.subsystem_injection.get_library") as mock_get:
            mock_lib = MagicMock()
            mock_lib.search.return_value = []
            mock_get.return_value = mock_lib
            result = await ability(query="test query", top_k=3)
            assert result.success is True
            assert result.output == "No skills found"

    @pytest.mark.asyncio
    async def test_skill_search_ability_with_results(self):
        mock_skill = MagicMock()
        mock_skill.name = "test_skill"
        mock_skill.version = "1.0"
        mock_skill.description = "A test skill"
        ability = SkillSearchAbility(library=None)
        with patch("autogpt.agents.subsystem_injection.get_library") as mock_get:
            mock_lib = MagicMock()
            mock_lib.search.return_value = [mock_skill]
            mock_get.return_value = mock_lib
            result = await ability(query="test", top_k=1)
            assert result.success is True
            assert len(result.output) == 1
            assert result.output[0]["name"] == "test_skill"

    @pytest.mark.asyncio
    async def test_skill_execute_ability_not_found(self):
        ability = SkillExecuteAbility()
        with patch("autogpt.agents.subsystem_injection.get_library") as mock_get:
            mock_lib = MagicMock()
            mock_lib.get_skill.return_value = None
            mock_get.return_value = mock_lib
            result = await ability(skill_name="nonexistent")
            assert result.success is False
            assert "not found" in result.error

    @pytest.mark.asyncio
    async def test_event_publish_ability(self):
        mock_queue = MagicMock(spec=MessageQueue)
        ability = EventBusPublishAbility(message_queue=mock_queue)
        result = await ability(event_type="test_event", payload={"key": "val"}, source_agent="tester")
        assert result.success is True
        mock_queue.publish.assert_called_once()

    @pytest.mark.asyncio
    async def test_event_publish_no_queue(self):
        ability = EventBusPublishAbility(message_queue=None)
        result = await ability(event_type="test_event")
        assert result.success is False

    @pytest.mark.asyncio
    async def test_event_query_ability(self):
        mock_queue = MagicMock(spec=MessageQueue)
        mock_event = EventMessage(event_type="test", payload={"k": "v"}, source_agent="a")
        mock_queue.get_events.return_value = [mock_event]
        ability = EventBusQueryAbility(message_queue=mock_queue)
        result = await ability(limit=10)
        assert result.success is True
        assert len(result.output) == 1

    @pytest.mark.asyncio
    async def test_self_develop_ability(self):
        mock_manager = MagicMock()
        ability = SelfDevelopAbility(manager=mock_manager)
        result = await ability()
        assert result.success is True
        mock_manager.review_repository.assert_called_once()

    def test_inject_v1_subsystems_registers_all(self):
        registry = AbilityRegistry()
        mock_queue = MagicMock(spec=MessageQueue)
        inject_v1_subsystems(registry, message_queue=mock_queue)
        assert registry.get("skill_search") is not None
        assert registry.get("skill_execute") is not None
        assert registry.get("event_publish") is not None
        assert registry.get("event_query") is not None

    def test_inject_v1_subsystems_with_self_develop(self):
        registry = AbilityRegistry()
        mock_manager = MagicMock()
        mock_queue = MagicMock(spec=MessageQueue)
        inject_v1_subsystems(
            registry,
            self_develop_manager=mock_manager,
            message_queue=mock_queue,
        )
        assert registry.get("self_develop_review") is not None

    def test_inject_v1_subsystems_without_self_develop(self):
        registry = AbilityRegistry()
        inject_v1_subsystems(registry)
        assert registry.get("self_develop_review") is None


# ======================================================================
# Command Repetition Detection Tests
# ======================================================================


class TestCommandRepetition:
    def test_record_command_counts(self, agent):
        async_agent = AsyncAgent(
            memory=agent.vector_memory if hasattr(agent, "vector_memory") else agent.memory,
            command_registry=agent.command_registry,
            triggering_prompt="Test",
            ai_config=agent.ai_config,
            config=agent.config,
        )
        count = async_agent._record_command("cmd1")
        assert count == 1
        count = async_agent._record_command("cmd1")
        assert count == 2

    def test_record_command_different_signatures(self, agent):
        async_agent = AsyncAgent(
            memory=agent.vector_memory if hasattr(agent, "vector_memory") else agent.memory,
            command_registry=agent.command_registry,
            triggering_prompt="Test",
            ai_config=agent.ai_config,
            config=agent.config,
        )
        async_agent._record_command("cmd1")
        count = async_agent._record_command("cmd2")
        assert count == 1
