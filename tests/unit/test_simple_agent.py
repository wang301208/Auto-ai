import logging

import pytest

from autoai.core.ability.schema import AbilityResult
from autoai.core.agent.simple import SimpleAgent
from autoai.core.planning.schema import Task, TaskStatus, TaskType


class DummyAbility:
    async def __call__(self, **kwargs) -> AbilityResult:
        return AbilityResult(
            ability_name="dummy",
            ability_args=kwargs,
            success=True,
            message="done",
        )


class DummyAbilityRegistry:
    def get_ability(self, ability_name: str) -> DummyAbility:
        return DummyAbility()


def make_agent() -> SimpleAgent:
    settings = SimpleAgent.default_settings.copy(deep=True)
    return SimpleAgent(
        settings=settings,
        logger=logging.getLogger("test"),
        ability_registry=DummyAbilityRegistry(),
        memory=object(),
        openai_provider=object(),
        planning=object(),
        workspace=object(),
    )


def make_task(status: TaskStatus = TaskStatus.IN_PROGRESS) -> Task:
    task = Task(
        objective="do something",
        type=TaskType.RESEARCH,
        priority=1,
        ready_criteria=[],
        acceptance_criteria=[],
    )
    task.context.status = status
    return task


@pytest.mark.asyncio
async def test_execute_next_ability_yes_branch() -> None:
    agent = make_agent()
    task = make_task(TaskStatus.DONE)
    agent._current_task = task
    agent._next_ability = {"next_ability": "dummy", "ability_arguments": {}}

    result = await agent.execute_next_ability("y")

    assert agent._current_task is None
    assert agent._next_ability is None
    assert task in agent._completed_tasks
    assert result["success"] is True


@pytest.mark.asyncio
async def test_execute_next_ability_no_branch() -> None:
    agent = make_agent()
    task = make_task(TaskStatus.IN_PROGRESS)
    agent._current_task = task
    agent._next_ability = {"next_ability": "dummy", "ability_arguments": {}}

    result = await agent.execute_next_ability("n")

    assert agent._current_task is None
    assert agent._next_ability is None
    assert task in agent._task_queue
    assert result["success"] is False
    assert result["message"] == "User cancelled ability execution."


@pytest.mark.asyncio
async def test_execute_next_ability_invalid_input() -> None:
    agent = make_agent()
    task = make_task()
    agent._current_task = task
    agent._next_ability = {"next_ability": "dummy", "ability_arguments": {}}

    with pytest.raises(ValueError):
        await agent.execute_next_ability("maybe")
