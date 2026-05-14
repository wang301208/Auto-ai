import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from autoai.core.ability import (
    AbilityRegistrySettings,
    AbilityResult,
    SimpleAbilityRegistry,
)
from autoai.core.agent.base import Agent
from autoai.core.configuration import Configurable, SystemConfiguration, SystemSettings
from autoai.core.memory import MemorySettings, SimpleMemory
from autoai.core.planning import (
    PlannerSettings,
    SimplePlanner,
    Task,
    TaskStatus,
    TaskType,
)
from autoai.core.plugin.simple import (
    PluginLocation,
    PluginStorageFormat,
    SimplePluginService,
)
from autoai.core.resource.model_providers import OpenAIProvider, OpenAISettings
from autoai.core.workspace.simple import SimpleWorkspace, WorkspaceSettings


class AgentSystems(SystemConfiguration):
    ability_registry: PluginLocation
    memory: PluginLocation
    openai_provider: PluginLocation
    planning: PluginLocation
    workspace: PluginLocation


class AgentConfiguration(SystemConfiguration):
    cycle_count: int
    max_task_cycle_count: int
    creation_time: str
    name: str
    role: str
    goals: list[str]
    systems: AgentSystems


class AgentSystemSettings(SystemSettings):
    configuration: AgentConfiguration


class AgentSettings(BaseModel):
    agent: AgentSystemSettings
    ability_registry: AbilityRegistrySettings
    memory: MemorySettings
    openai_provider: OpenAISettings
    planning: PlannerSettings
    workspace: WorkspaceSettings

    def update_agent_name_and_goals(self, agent_goals: dict) -> None:
        self.agent.configuration.name = agent_goals["agent_name"]
        self.agent.configuration.role = agent_goals["agent_role"]
        self.agent.configuration.goals = agent_goals["agent_goals"]


class SimpleAgent(Agent, Configurable):
    default_settings = AgentSystemSettings(
        name="simple_agent",
        description="A simple agent.",
        configuration=AgentConfiguration(
            name="Entrepreneur-GPT",
            role=(
                "An AI designed to autonomously develop and run businesses with "
                "the sole goal of increasing your net worth."
            ),
            goals=[
                "Increase net worth",
                "Grow Twitter Account",
                "Develop and manage multiple businesses autonomously",
            ],
            cycle_count=0,
            max_task_cycle_count=3,
            creation_time="",
            systems=AgentSystems(
                ability_registry=PluginLocation(
                    storage_format=PluginStorageFormat.INSTALLED_PACKAGE,
                    storage_route="autoai.core.ability.SimpleAbilityRegistry",
                ),
                memory=PluginLocation(
                    storage_format=PluginStorageFormat.INSTALLED_PACKAGE,
                    storage_route="autoai.core.memory.SimpleMemory",
                ),
                openai_provider=PluginLocation(
                    storage_format=PluginStorageFormat.INSTALLED_PACKAGE,
                    storage_route="autoai.core.resource.model_providers.OpenAIProvider",
                ),
                planning=PluginLocation(
                    storage_format=PluginStorageFormat.INSTALLED_PACKAGE,
                    storage_route="autoai.core.planning.SimplePlanner",
                ),
                workspace=PluginLocation(
                    storage_format=PluginStorageFormat.INSTALLED_PACKAGE,
                    storage_route="autoai.core.workspace.SimpleWorkspace",
                ),
            ),
        ),
    )

    def __init__(
        self,
        settings: AgentSystemSettings,
        logger: logging.Logger,
        ability_registry: SimpleAbilityRegistry,
        memory: SimpleMemory,
        openai_provider: OpenAIProvider,
        planning: SimplePlanner,
        workspace: SimpleWorkspace,
    ):
        self._configuration = settings.configuration
        self._logger = logger
        self._ability_registry = ability_registry
        self._memory = memory
        # 修复: Need some work to make this work as a dict of providers
        # 获取ting constructi在的config 到work is 一个位 tricky
        self._openai_provider = openai_provider
        self._planning = planning
        self._workspace = workspace
        self._task_queue = []
        self._completed_tasks = []
        self._current_task = None
        self._next_ability = None

    @classmethod
    def from_workspace(
        cls,
        workspace_path: Path,
        logger: logging.Logger,
    ) -> "SimpleAgent":
        agent_settings = SimpleWorkspace.load_agent_settings(workspace_path)
        agent_args = {}

        agent_args["settings"] = agent_settings.agent
        agent_args["logger"] = logger
        agent_args["workspace"] = cls._get_system_instance(
            "workspace",
            agent_settings,
            logger,
        )
        agent_args["openai_provider"] = cls._get_system_instance(
            "openai_provider",
            agent_settings,
            logger,
        )
        agent_args["planning"] = cls._get_system_instance(
            "planning",
            agent_settings,
            logger,
            model_providers={"openai": agent_args["openai_provider"]},
        )
        agent_args["memory"] = cls._get_system_instance(
            "memory",
            agent_settings,
            logger,
            workspace=agent_args["workspace"],
        )

        agent_args["ability_registry"] = cls._get_system_instance(
            "ability_registry",
            agent_settings,
            logger,
            workspace=agent_args["workspace"],
            memory=agent_args["memory"],
            model_providers={"openai": agent_args["openai_provider"]},
        )

        return cls(**agent_args)

    async def build_initial_plan(self) -> dict:
        plan = await self._planning.make_initial_plan(
            agent_name=self._configuration.name,
            agent_role=self._configuration.role,
            agent_goals=self._configuration.goals,
            abilities=self._ability_registry.list_abilities(),
        )
        tasks = [
            task
            if isinstance(task, Task)
            else Task.parse_obj({**task, "type": TaskType(task["type"])})
            for task in plan.content["task_list"]
        ]

        # 待办: Should probably do a 步骤 to evaluate the quality of the generated tasks,
        #  and ensure that they have actionable 就绪 and acceptance criteria

        self._task_queue.extend(tasks)
        self._task_queue.sort(key=lambda t: t.priority, reverse=True)
        self._task_queue[-1].context.status = TaskStatus.READY
        return plan.content

    async def determine_next_ability(self, *args, **kwargs):
        if not self._task_queue:
            return {"response": "I don't have any tasks to work on right now."}

        self._configuration.cycle_count += 1
        task = self._task_queue.pop()
        self._logger.info(f"正在处理任务: {task}")

        task = await self._evaluate_task_and_add_context(task)
        next_ability = await self._choose_next_ability(
            task,
            self._ability_registry.dump_abilities(),
        )
        self._current_task = task
        self._next_ability = next_ability.content
        return self._current_task, self._next_ability

    async def execute_next_ability(self, user_input: str, *args, **kwargs):
        user_input = user_input.lower()
        if user_input == "y":
            ability = self._ability_registry.get_ability(
                self._next_ability["next_ability"]
            )
            ability_response = await ability(**self._next_ability["ability_arguments"])
            await self._update_tasks_and_memory(ability_response)
            if self._current_task.context.status == TaskStatus.DONE:
                self._completed_tasks.append(self._current_task)
            else:
                self._task_queue.append(self._current_task)
            self._current_task = None
            self._next_ability = None

            return ability_response.dict()
        elif user_input == "n":
            ability_result = AbilityResult(
                ability_name=self._next_ability["next_ability"],
                ability_args=self._next_ability["ability_arguments"],
                success=False,
                message="User cancelled ability execution.",
            )
            # Re-队列 the 任务 for future execution
            self._task_queue.append(self._current_task)
            self._current_task = None
            self._next_ability = None
            return ability_result.dict()
        else:
            raise ValueError("Invalid user input. Please respond 带'y' 或'n'.")

    async def _evaluate_task_and_add_context(self, task: Task) -> Task:
        """评估任务并添加上下文。"""
        if task.context.status == TaskStatus.IN_PROGRESS:
            # Nothing 到do here
            return task
        else:
            self._logger.debug(f"Evaluating 任务 {任务} 和adding relevant 上下文.")
            # 待办: Look up relevant memories (need working 内存 system)
            # 待办: Evaluate whether there is enough 信息rmation to 启动 the 任务 (language 模型 call).
            task.context.enough_info = True
            task.context.status = TaskStatus.IN_PROGRESS
            return task

    async def _choose_next_ability(self, task: Task, ability_schema: list[dict]):
        """选择任务使用的下一个技能。"""
        self._logger.debug(f"为任务选择下一个技能 {task}.")
        if task.context.cycle_count > self._configuration.max_task_cycle_count:
            # Don't hit the LLM, just 集合 the next action as "breakdown_task" with an appropriate 原因
            raise RuntimeError(
                "Task exceeded maximum cycle count; consider breaking it down or revising."
            )
        elif not task.context.enough_info:
            # Don't ask the LLM, just 集合 the next action as "breakdown_task" with an appropriate 原因
            raise RuntimeError(
                "Not enough information to proceed with the task; provide more context or break it down."
            )
        else:
            next_ability = await self._planning.determine_next_ability(
                task, ability_schema
            )
            return next_ability

    async def _update_tasks_and_memory(self, ability_result: AbilityResult):
        self._current_task.context.cycle_count += 1
        self._current_task.context.prior_actions.append(ability_result)
        # 待办: Summarize new 知识
        # 待办: store 知识 and summaries in 内存 and in relevant tasks
        # 待办: evaluate whether the 任务 is 完整

    def __repr__(self):
        return "SimpleAgent()"

    ################################################################
    # 工厂 interface for 代理 bootstrapping and initialization #
    ################################################################

    @classmethod
    def build_user_configuration(cls) -> dict[str, Any]:
        """构建用户配置。"""
        configuration_dict = {
            "agent": cls.get_user_config(),
        }

        system_locations = configuration_dict["agent"]["configuration"]["systems"]
        for system_name, system_location in system_locations.items():
            system_class = SimplePluginService.get_plugin(system_location)
            configuration_dict[system_name] = system_class.get_user_config()
        configuration_dict = _prune_empty_dicts(configuration_dict)
        return configuration_dict

    @classmethod
    def compile_settings(
        cls, logger: logging.Logger, user_configuration: dict
    ) -> AgentSettings:
        """用默认值编译用户配置。"""
        logger.debug("Processing 代理 system configu比率n.")
        configuration_dict = {
            "agent": cls.build_agent_configuration(
                user_configuration.get("agent", {})
            ).dict(),
        }

        system_locations = configuration_dict["agent"]["configuration"]["systems"]

        # 构建 up default configuration
        for system_name, system_location in system_locations.items():
            logger.debug(f"为系统编译配置 {system_name}")
            system_class = SimplePluginService.get_plugin(system_location)
            configuration_dict[system_name] = system_class.build_agent_configuration(
                user_configuration.get(system_name, {})
            ).dict()

        return AgentSettings.parse_obj(configuration_dict)

    @classmethod
    async def determine_agent_name_and_goals(
        cls,
        user_objective: str,
        agent_settings: AgentSettings,
        logger: logging.Logger,
    ) -> dict:
        logger.debug("加载OpenAI提供者。")
        provider: OpenAIProvider = cls._get_system_instance(
            "openai_provider",
            agent_settings,
            logger=logger,
        )
        logger.debug("加载代理规划器。")
        agent_planner: SimplePlanner = cls._get_system_instance(
            "planning",
            agent_settings,
            logger=logger,
            model_providers={"openai": provider},
        )
        logger.debug("de项ining 代理 名称 和goals.")
        model_response = await agent_planner.decide_name_and_goals(
            user_objective,
        )

        return model_response.content

    @classmethod
    def provision_agent(
        cls,
        agent_settings: AgentSettings,
        logger: logging.Logger,
    ):
        agent_settings.agent.configuration.creation_time = datetime.now().strftime(
            "%Y%m%d_%H%M%S"
        )
        workspace: SimpleWorkspace = cls._get_system_instance(
            "workspace",
            agent_settings,
            logger=logger,
        )
        return workspace.setup_workspace(agent_settings, logger)

    @classmethod
    def _get_system_instance(
        cls,
        system_name: str,
        agent_settings: AgentSettings,
        logger: logging.Logger,
        *args,
        **kwargs,
    ):
        system_locations = agent_settings.agent.configuration.systems.dict()

        system_settings = getattr(agent_settings, system_name)
        system_class = SimplePluginService.get_plugin(system_locations[system_name])
        system_instance = system_class(
            system_settings,
            *args,
            logger=logger.getChild(system_name),
            **kwargs,
        )
        return system_instance


def _prune_empty_dicts(d: dict) -> dict:
    """
    Prune branches from a nested dictionary if the branch only contains empty dictionaries at the leaves.

    Args:
        d: The dictionary to prune.

    Returns:
        The pruned dictionary.
    """
    pruned = {}
    for key, value in d.items():
        if isinstance(value, dict):
            pruned_value = _prune_empty_dicts(value)
            if (
                pruned_value
            ):  # 如果pruned 字典ionary is 非empty, add it 到result
                pruned[key] = pruned_value
        else:
            pruned[key] = value
    return pruned
