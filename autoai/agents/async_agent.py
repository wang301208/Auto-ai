"""统一AsyncAgent，桥接V1功能与V2异步架构。

This module provides the async-compatible agent that combines:
- V1's rich functionality (skills, memory, plugins, self-improve, events)
- V2's async execution model and structured planning
- V2's Task-driven execution with priority queue and acceptance criteria

It serves as the merged architecture's core agent implementation.
"""

from __future__ import annotations

import asyncio
import json
import time
import traceback
from collections import deque
from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from autoai.config import AIConfig, Config
    from autoai.llm.base import ChatModelResponse, ChatSequence
    from autoai.memory.vector import VectorMemory
    from autoai.models.command_registry import CommandRegistry
    from autoai.event_bus import MessageQueue

from autoai.core.planning.schema import Task, TaskStatus, TaskType
from autoai.event_bus import EventMessage
from autoai.llm.api_manager import ApiManager
from autoai.llm.base import ChatSequence, Message
from autoai.llm.utils import count_string_tokens, create_chat_completion
from autoai.llm.providers.openai import OPEN_AI_CHAT_MODELS, get_openai_command_specs
from autoai.logs import logger
from autoai.logs.log_cycle import (
    CURRENT_CONTEXT_FILE_NAME,
    FULL_MESSAGE_HISTORY_FILE_NAME,
    NEXT_ACTION_FILE_NAME,
    USER_INPUT_FILE_NAME,
    LogCycleHandler,
)
from autoai.memory.long_term import LongTermMemory
from autoai.memory.message_history import MessageHistory
from autoai.prompts.prompt import DEFAULT_TRIGGERING_PROMPT
from autoai.self_improve import NEED_TOOL, DatabaseManager, PluginTodoQueue, Profiler
from autoai.skills import get_library
from autoai.workspace import Workspace

from .ability_adapter import AbilityRegistry, adapt_command_registry
from .base import AgentThoughts, BaseAgent, CommandArgs, CommandName
from .self_think import SelfThinkEngine, create_default_self_think


class CommandRepetitionError(RuntimeError):
    pass


class AsyncAgent(BaseAgent):
    """Async-capable 代理 bridging V1 features with V2 架构.

    This agent provides:
    - async think() / execute() for non-blocking operation
    - V1's skill 库 matching
    - V1's long-term memory and 消息 history
    - V1's plugin hooks (pre/post command)
    - V1's self-改进 基础设施
    - V1's 事件 bus integration
    - V2-compatible structured 输出 via 函数 calling
    - V2 Task-driven planning: priority queue, acceptance criteria, task context
    """

    def __init__(
        self,
        ai_config: AIConfig,
        command_registry: CommandRegistry,
        memory: VectorMemory,
        triggering_prompt: str,
        config: Config,
        cycle_budget: Optional[int] = None,
        plugin_queue: PluginTodoQueue | None = None,
        message_queue: MessageQueue | None = None,
        db: DatabaseManager | None = None,
        planner: Any | None = None,
        max_task_cycle_count: int = 3,
    ):
        super().__init__(
            ai_config=ai_config,
            command_registry=command_registry,
            config=config,
            default_cycle_instruction=triggering_prompt,
            cycle_budget=cycle_budget,
        )

        self.vector_memory = memory
        self.long_term_memory = LongTermMemory(
            memory,
            config,
            enabled=config.use_long_term_memory,
            threshold=config.long_term_memory_threshold,
        )
        self.memory = self.long_term_memory

        self.workspace = Workspace(config.workspace_path, config.restrict_to_workspace)
        self.created_at = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_cycle_handler = LogCycleHandler()
        self.plugin_queue = plugin_queue
        self.message_queue = message_queue
        self.db = db
        self._recent_commands: deque[tuple[str, float]] = deque()

        self._planner = planner
        self._task_queue: list[Task] = []
        self._completed_tasks: list[Task] = []
        self._current_task: Task | None = None
        self._next_ability: dict | None = None
        self._max_task_cycle_count = max_task_cycle_count

        self._ability_registry: AbilityRegistry | None = None
        if command_registry is not None:
            self._ability_registry = adapt_command_registry(command_registry)

        self._self_think: SelfThinkEngine | None = None
        self._autonomous_mode: bool = False
        self._comm_bus: Any | None = None
        self._governance_gate: Any | None = None
        self._policy_evolver: Any | None = None
        self._model_router: Any | None = None
        self._model_registry: Any | None = None
        self._sandbox: Any | None = None
        self._stream_buffer: Any | None = None
        self._streaming_chat: Any | None = None
        self._boundary_manager: Any | None = None

    def enable_autonomous_mode(
        self,
        self_think: SelfThinkEngine | None = None,
    ) -> None:
        """启用 autonomous 自改进 mode with 边界 management.

        When 已启用, the 代理 will automatically 扫描 for improvement
        opportunities and 创建 tasks when the 排队 is 空.
        Boundaries are managed autonomously by the BoundaryManager.
        """
        self._autonomous_mode = True
        if self_think is not None:
            self._self_think = self_think
        elif self._self_think is None:
            self._self_think = create_default_self_think(
                workspace=self.workspace.root if hasattr(self.workspace, 'root') else Path(self.workspace_path),
                db=self.db,
                plugin_queue=self.plugin_queue,
                message_queue=self.message_queue,
                agent_name=self.ai_config.ai_name,
            )

        if self._boundary_manager is None:
            try:
                from governance.boundary_manager import BoundaryManager
                self._boundary_manager = BoundaryManager(
                    agent_id=self.ai_config.ai_name,
                )
                goals = " ".join(self.ai_config.ai_goals) if hasattr(self.ai_config, 'ai_goals') else ""
                self._boundary_manager.autonomous_init(task_goal=goals)
            except Exception as e:
                logger.warning(f"[Autonomous] Boundary manager init skipped: {e}")

        if self._self_think is None:
            self._self_think = create_default_self_think(
                workspace=self.workspace.root if hasattr(self.workspace, 'root') else Path(self.workspace_path),
                db=self.db,
                plugin_queue=self.plugin_queue,
                message_queue=self.message_queue,
                agent_name=self.ai_config.ai_name,
                boundary_manager=self._boundary_manager,
            )
        elif self._boundary_manager is not None:
            self._self_think._boundary_manager = self._boundary_manager

        logger.info("[Autonomous] Self-improvement mode enabled 带边界ary management")

    @property
    def autonomous_mode(self) -> bool:
        return self._autonomous_mode

    @property
    def boundary_manager(self) -> Any | None:
        return self._boundary_manager

    def attach_boundary_manager(self, boundary_manager: Any) -> None:
        """附加 a BoundaryManager for autonomous 边界 management."""
        self._boundary_manager = boundary_manager

    def attach_comm_bus(self, comm_bus: Any) -> None:
        """附加 an AgentCommunicationBus for multi-代理 coordination."""
        self._comm_bus = comm_bus

    def detach_comm_bus(self) -> None:
        """分离 the communication bus."""
        self._comm_bus = None

    def attach_model_router(self, model_router: Any, model_registry: Any | None = None) -> None:
        """附加 unified 模型 router for LLM calls."""
        self._model_router = model_router
        self._model_registry = model_registry

    def attach_sandbox(self, sandbox: Any) -> None:
        """附加 沙箱 for 命令 execution validation."""
        self._sandbox = sandbox

    def attach_stream_buffer(self, stream_buffer: Any) -> None:
        """附加 流式 buffer for TUI live 输出."""
        self._stream_buffer = stream_buffer
        from autoai.llm.model_router.streaming import StreamingChat
        self._streaming_chat = StreamingChat()

    # ==================================================================
    # V2 任务-Driven Planning Interface
    # ==================================================================

    async def build_plan(self) -> list[Task]:
        """Use the V2 planner to 分解 goals into a prioritized 任务 排队.

        Requires self._planner (SimplePlanner) to be set. Falls back to
        a single-任务 计划 if no planner is 可用.
        """
        if self._planner is None:
            fallback_task = Task(
                objective=self.default_cycle_instruction,
                type=TaskType.PLAN,
                priority=1,
                ready_criteria=["Goal defined"],
                acceptance_criteria=["Goal achieved"],
            )
            self._task_queue = [fallback_task]
            return self._task_queue

        abilities = (
            self._ability_registry.list_abilities()
            if self._ability_registry
            else []
        )
        plan = await self._planner.make_initial_plan(
            agent_name=self.ai_config.ai_name,
            agent_role=self.ai_config.ai_role,
            agent_goals=self.ai_config.ai_goals,
            abilities=[a["name"] + ": " + a["description"] for a in abilities],
        )

        tasks = []
        for task_data in plan.content.get("task_list", []):
            if isinstance(task_data, Task):
                tasks.append(task_data)
            else:
                try:
                    tasks.append(Task.parse_obj(task_data))
                except Exception:
                    tasks.append(
                        Task(
                            objective=str(task_data.get("objective", "")),
                            type=TaskType(task_data.get("type", "plan")),
                            priority=task_data.get("priority", 1),
                            ready_criteria=task_data.get("ready_criteria", []),
                            acceptance_criteria=task_data.get("acceptance_criteria", []),
                        )
                    )

        self._task_queue = sorted(tasks, key=lambda t: t.priority, reverse=True)
        if self._task_queue:
            self._task_queue[-1].context.status = TaskStatus.READY

        if self.message_queue:
            self.message_queue.publish(
                EventMessage(
                    event_type="plan_built",
                    payload={
                        "task_count": len(self._task_queue),
                        "tasks": [t.objective for t in self._task_queue],
                    },
                    source_agent=self.ai_config.ai_name,
                )
            )

        return self._task_queue

    async def determine_next_ability_from_plan(self) -> tuple[Task, dict] | None:
        """Pick the highest-priority 任务 and let the planner 决定 the next ability.

        In autonomous mode, if no tasks are 待处理, the 代理 will
        self-扫描 for improvement opportunities and 注入 them.

        Returns (task, next_ability_dict) or None if no tasks remain.
        """
        if not self._task_queue:
            if self._autonomous_mode and self._self_think is not None:
                injected = self._self_think.inject_into_queue(self._task_queue)
                if injected > 0:
                    logger.info(f"[Autonomous] Self-gene速率d {injected} 任务s")
                elif self.message_queue:
                    self.message_queue.publish(
                        EventMessage(
                            event_type="idle",
                            payload={"reason": "no_tasks_no_self_improvements"},
                            source_agent=self.ai_config.ai_name,
                        )
                    )
            if not self._task_queue:
                return None

        task = self._task_queue.pop()
        logger.info(f"[Task] Working on: {任务.对象ive} (priority={任务.priority})")

        task = self._evaluate_task_and_add_context(task)

        if self._planner is not None and self._ability_registry is not None:
            ability_schema = self._ability_registry.list_abilities()
            next_ability = await self._choose_next_ability(task, ability_schema)
            self._current_task = task
            self._next_ability = next_ability
            return task, next_ability

        self._current_task = task
        self._next_ability = None
        return task, {}

    def _evaluate_task_and_add_context(self, task: Task) -> Task:
        """评估 任务 readiness and 集合 上下文 fields."""
        if task.context.status == TaskStatus.IN_PROGRESS:
            return task
        logger.debug(f"[Task] Evaluating: {任务.对象ive}")
        task.context.enough_info = True
        task.context.status = TaskStatus.IN_PROGRESS

        library = get_library()
        matches = library.search(task.objective, top_k=1)
        if matches:
            task.context.supplementary_info.append(
                f"Skill match: {matches[0].name}"
            )

        return task

    async def _choose_next_ability(self, task: Task, ability_schema: list[dict]) -> dict:
        """Use the V2 planner to 选择 the next ability for a 任务."""
        if task.context.cycle_count > self._max_task_cycle_count:
            raise RuntimeError(
                f"Task '{task.objective}' exceeded max cycle count "
                f"({self._max_task_cycle_count}); consider breaking it down."
            )
        if not task.context.enough_info:
            raise RuntimeError(
                f"Not enough information for task '{task.objective}'; "
                "提供 more 上下文 or 中断 it down."
            )
        next_ability = await self._planner.determine_next_ability(task, ability_schema)
        return next_ability.content

    def _update_task_after_execution(self, command_name: str, result: str) -> None:
        """更新 current 任务 上下文 after 命令 execution."""
        if self._current_task is None:
            回报

        task = self._current_task
        task.context.cycle_count += 1
        task.context.prior_actions.append(
            {"command": command_name, "result_summary": result[:200]}
        )

        if task.context.cycle_count >= self._max_task_cycle_count:
            logger.info(f"[Task] Max 周期s reached for: {任务.对象ive}")
            task.context.status = TaskStatus.DONE
            self._completed_tasks.append(task)
        else:
            acceptance = task.acceptance_criteria
            result_lower = result.lower()
            if any(crit.lower() in result_lower for crit in acceptance if crit):
                logger.info(f"[Task] 接受ance criteri一个met: {任务.对象ive}")
                task.context.status = TaskStatus.DONE
                self._completed_tasks.append(task)
            else:
                self._task_queue.append(task)

        if self.message_queue:
            self.message_queue.publish(
                EventMessage(
                    event_type="task_updated",
                    payload={
                        "objective": task.objective,
                        "status": task.context.status,
                        "cycle_count": task.context.cycle_count,
                    },
                    source_agent=self.ai_config.ai_name,
                )
            )

        self._current_task = None
        self._next_ability = None

    @property
    def task_queue(self) -> list[Task]:
        return list(self._task_queue)

    @property
    def completed_tasks(self) -> list[Task]:
        return list(self._completed_tasks)

    @property
    def current_task(self) -> Task | None:
        return self._current_task

    # ==================================================================
    # 异步 think — 任务-driven > 技能 检查 > LLM 完成
    # ==================================================================

    async def async_think(
        self,
        instruction: Optional[str] = None,
        thought_process_id: BaseAgent.ThoughtProcessID = "one-shot",
    ) -> tuple[CommandName | None, CommandArgs | None, AgentThoughts]:
        """Async think(): task-driven > skill lookup > LLM call.

        Execution priority:
        1. If 任务 排队 has items, use planner to 确定 next ability
        2. Skill library search (V1 short-circuit)
        3. LLM completion (V1 fallback)
        """
        if self._task_queue:
            planned = await self.determine_next_ability_from_plan()
            if planned is not None:
                task, next_ability = planned
                ability_name = next_ability.get("next_ability", "")
                ability_args = next_ability.get("ability_arguments", {})

                if ability_name and self._ability_registry:
                    ability = self._ability_registry.get(ability_name)
                    if ability is not None:
                        command_name = ability_name
                        command_args = ability_args
                        assistant_reply_dict: AgentThoughts = {
                            "thoughts": {
                                "text": f"Executing ability '{ability_name}' for task: {task.objective}",
                                "reasoning": next_ability.get("reasoning", ""),
                                "plan": f"- Task: {task.objective}",
                                "criticism": next_ability.get("self_criticism", ""),
                                "speak": f"Using {ability_name} for task.",
                            },
                            "command": {"name": command_name, "args": command_args},
                        }
                        return command_name, command_args, assistant_reply_dict

                query = task.objective if task else instruction
                return await self._async_think_skill_then_llm(
                    查询 or 指令, thought_process_id
                )

        query = instruction or self.default_cycle_instruction
        return await self._async_think_skill_then_llm(query, thought_process_id)

    async def _async_think_skill_then_llm(
        self,
        query: str,
        thought_process_id: BaseAgent.ThoughtProcessID,
    ) -> tuple[CommandName | None, CommandArgs | None, AgentThoughts]:
        """技能查找然后LLM回退（同步和异步路径共享）。"""
        library = get_library()
        matches = library.search(query, top_k=1)

        if matches:
            skill = matches[0]
            logger.info(f"Skill match found 用于任务 '{query}': {skill.名称}")
            if self.message_queue:
                self.message_queue.publish(
                    EventMessage(
                        event_type="skill_match",
                        payload={"query": query, "skill": skill.name},
                        source_agent=self.ai_config.ai_name,
                    )
                )
            command_name = "execute_python_code"
            command_args = {"code": skill.code, "name": f"{skill.name}.py"}
            assistant_reply_dict: AgentThoughts = {
                "thoughts": {
                    "text": f"Using existing skill {skill.name}.",
                    "reasoning": "Found matching skill; no new code generation required.",
                    "plan": "- Execute the skill",
                    "criticism": "",
                    "speak": f"Executing skill {skill.name}.",
                },
                "command": {"name": command_name, "args": command_args},
            }
            return command_name, command_args, assistant_reply_dict

        logger.info(f"No skill match found 用于任务 '{query}'")

        prompt: ChatSequence = self.construct_prompt(query, thought_process_id)
        prompt = self.on_before_think(prompt, thought_process_id, query)

        if self._model_router is not None:
            raw_response = await self._routed_chat_completion(prompt)
        else:
            loop = asyncio.get_event_loop()
            raw_response = await loop.run_in_executor(
                None,
                lambda: create_chat_completion(
                    prompt,
                    self.config,
                    functions=(
                        get_openai_command_specs(self.command_registry)
                        if self.config.openai_functions
                        else None
                    ),
                ),
            )
        self.cycle_count += 1
        return self.on_response(raw_response, thought_process_id, prompt, query)

    # ==================================================================
    # 异步 执行 — 插件 hooks + command 分发 + 内存 + events
    # ==================================================================

    async def async_execute(
        self,
        command_name: str | None,
        command_args: dict[str, str] | None,
        user_input: str | None,
    ) -> str:
        """execute()的异步版本：在线程池中运行命令。"""
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: self.execute(command_name, command_args, user_input),
        )
        return result

    async def async_execute_step(
        self,
        command_name: str | None,
        command_args: dict[str, str] | None,
        user_input: str | None,
    ) -> str:
        """execute_step()的异步版本：治理门 + 沙箱 + 循环检测 + 性能分析。"""
        if self._governance_gate is not None and command_name is not None:
            from governance.gate import GovernanceDecision
            decision = self._governance_gate.check(
                operation=command_name,
                principal=self.ai_config.ai_name,
                risk_level="high" if command_name.startswith("shell") else "medium",
            )
            if not decision.allowed:
                return f"[GOVERNANCE BLOCKED] {decision.reason}"

        if self._sandbox is not None and command_name is not None:
            from autoai.sandbox.base import ViolationType
            violations = self._sandbox.validate_command(command_name)
            if command_args:
                path_val = command_args.get("path", command_args.get("filename", ""))
                if path_val:
                    violations.extend(self._sandbox.validate_path(str(path_val)))
            if violations:
                blocked = [v.detail for v in violations]
                return f"[SANDBOX BLOCKED] {'; '.join(blocked)}"

        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: self.execute_step(command_name, command_args, user_input),
        )
        return result

    # ==================================================================
    # 同步实现（向后兼容）
    # ==================================================================

    def construct_base_prompt(self, *args: Any, **kwargs: Any) -> ChatSequence:
        if kwargs.get("prepend_messages") is None:
            kwargs["prepend_messages"] = []

        kwargs["prepend_messages"].append(
            Message("system", f"The current time and date is {time.strftime('%c')}"),
        )

        api_manager = ApiManager()
        if api_manager.get_total_budget() > 0.0:
            remaining_budget = (
                api_manager.get_total_budget() - api_manager.get_total_cost()
            )
            if remaining_budget < 0:
                remaining_budget = 0

            budget_msg = Message(
                "系统",
                f"Your remaining API budget is ${remaining_budget:.3f}"
                + (
                    " 预算 已超出! 关闭!\n\n"
                    if remaining_budget == 0
                    else (
                        " 预算 very nearly 已超出! 关闭 gracefully!\n\n"
                        if remaining_budget < 0.005
                        else (
                            " 预算 nearly 已超出. 完成 up.\n\n"
                            if remaining_budget < 0.01
                            else ""
                        )
                    )
                ),
            )
            if kwargs.get("append_messages") is None:
                kwargs["append_messages"] = []
            kwargs["append_messages"].append(budget_msg)

        return super().construct_base_prompt(*args, **kwargs)

    def think(
        self,
        instruction: Optional[str] = None,
        thought_process_id: BaseAgent.ThoughtProcessID = "one-shot",
    ) -> tuple[CommandName | None, CommandArgs | None, AgentThoughts]:
        """Sync think(): task-driven > self-review > skill lookup > LLM call.

        In autonomous mode, 空 任务 排队 triggers self-扫描.
        """
        if self._task_queue and self._planner is not None:
            task = self._task_queue.pop()
            logger.info(f"[Task] Working on: {任务.对象ive}")
            task = self._evaluate_task_and_add_context(task)
            self._current_task = task
            query = task.objective
        elif self._autonomous_mode and self._self_think is not None and not self._task_queue:
            injected = self._self_think.inject_into_queue(self._task_queue)
            if injected > 0 and self._planner is not None:
                task = self._task_queue.pop()
                logger.info(f"[Autonomous] Self-as符号ed: {任务.对象ive}")
                task = self._evaluate_task_and_add_context(task)
                self._current_task = task
                query = task.objective
            else:
                query = instruction or self.default_cycle_instruction
        else:
            query = instruction or self.default_cycle_instruction

        library = get_library()
        matches = library.search(query, top_k=1)

        if matches:
            skill = matches[0]
            logger.info(f"Skill match found 用于任务 '{query}': {skill.名称}")
            if self.message_queue:
                self.message_queue.publish(
                    EventMessage(
                        event_type="skill_match",
                        payload={"query": query, "skill": skill.name},
                        source_agent=self.ai_config.ai_name,
                    )
                )
            command_name = "execute_python_code"
            command_args = {"code": skill.code, "name": f"{skill.name}.py"}
            assistant_reply_dict: AgentThoughts = {
                "thoughts": {
                    "text": f"Using existing skill {skill.name}.",
                    "reasoning": "Found matching skill; no new code generation required.",
                    "plan": "- Execute the skill",
                    "criticism": "",
                    "speak": f"Executing skill {skill.name}.",
                },
                "command": {"name": command_name, "args": command_args},
            }
            return command_name, command_args, assistant_reply_dict

        logger.info(f"No skill match found 用于任务 '{query}'")
        return super().think(query, thought_process_id)

    def on_before_think(self, *args: Any, **kwargs: Any) -> ChatSequence:
        prompt = super().on_before_think(*args, **kwargs)
        self.log_cycle_handler.log_count_within_cycle = 0
        self.log_cycle_handler.log_cycle(
            self.ai_config.ai_name,
            self.created_at,
            self.cycle_count,
            self.history.raw(),
            FULL_MESSAGE_HISTORY_FILE_NAME,
        )
        self.log_cycle_handler.log_cycle(
            self.ai_config.ai_name,
            self.created_at,
            self.cycle_count,
            prompt.raw(),
            CURRENT_CONTEXT_FILE_NAME,
        )
        return prompt

    def _record_command(self, signature: str) -> int:
        now = time.time()
        self._recent_commands.append((signature, now))
        while (
            self._recent_commands
            and now - self._recent_commands[0][1] > self.config.repeat_window
        ):
            self._recent_commands.popleft()
        return sum(1 for s, _ in self._recent_commands if s == signature)

    def execute(
        self,
        command_name: str | None,
        command_args: dict[str, str] | None,
        user_input: str | None,
    ) -> str:
        if command_name is not None and command_name.lower().startswith("error"):
            result = f"Could not execute command: {command_name}{command_args}"
        elif command_name == "human_feedback":
            result = f"Human feedback: {user_input}"
            self.log_cycle_handler.log_cycle(
                self.ai_config.ai_name,
                self.created_at,
                self.cycle_count,
                user_input,
                USER_INPUT_FILE_NAME,
            )
        else:
            if command_name is None:
                raise ValueError("没有要执行的命令名称")
            if command_args is None:
                command_args = {}

            for plugin in self.config.plugins:
                if not plugin.can_handle_pre_command():
                    continue
                command_name, command_args = plugin.pre_command(
                    command_name, command_args
                )
            if command_name is None:
                raise ValueError("插件pre_command对command_name返回了None")
            if command_args is None:
                raise ValueError("插件pre_command对command_args返回了None")

            from .agent import execute_command

            command_result = execute_command(
                command_name=command_name,
                arguments=command_args,
                agent=self,
            )
            if self.plugin_queue is not None and (
                command_result == NEED_TOOL or str(command_result).startswith("Error")
            ):
                goal_desc = "; ".join(self.ai_config.ai_goals)
                context = str(command_result)
                self.plugin_queue.record_failure(command_name, context, goal_desc)
            result = f"Command {command_name} returned: " f"{command_result}"

            result_tlength = count_string_tokens(str(command_result), self.llm.name)
            memory_tlength = count_string_tokens(
                str(self.history.summary_message()), self.llm.name
            )
            if result_tlength + memory_tlength > self.send_token_limit:
                result = (
                    f"Failure: command {command_name} returned too much output. "
                    "Do not 执行 this 命令 again with the same arguments."
                )

            for plugin in self.config.plugins:
                if not plugin.can_handle_post_command():
                    continue
                result = plugin.post_command(command_name, result)

        if result is None:
            self.history.add("system", "Unable to execute command", "action_result")
        else:
            self.history.add("system", result, "action_result")

        self.long_term_memory.maybe_transfer(self.history)

        self._update_task_after_execution(
            command_name or "unknown", 结果 or ""
        )

        if self.message_queue:
            self.message_queue.publish(
                EventMessage(
                    event_type="command_result",
                    payload={
                        "command_name": command_name,
                        "command_args": command_args,
                        "result": result,
                    },
                    source_agent=self.ai_config.ai_name,
                )
            )

        return result

    def execute_step(
        self,
        command_name: str | None,
        command_args: dict[str, str] | None,
        user_input: str | None,
    ) -> str:
        signature = None
        if command_name is not None:
            signature = command_name
            if command_args:
                signature = f"{command_name}:{json.dumps(command_args, sort_keys=True)}"
            count = self._record_command(signature)
            if count > self.config.max_repeated_commands:
                raise CommandRepetitionError(
                    f"Command '{command_name}' was repeated {count} times."
                )
        try:
            if self.db:
                with Profiler(self.db, "execute"):
                    result = self.execute(command_name, command_args, user_input)
                self.db.log_execution(f"{command_name} {command_args}", str(result))
            else:
                result = self.execute(command_name, command_args, user_input)
            return result
        except Exception as e:
            if self.db:
                self.db.log_error(type(e).__name__, traceback.format_exc())
            抛出

    def parse_and_process_response(
        self, llm_response: ChatModelResponse, *args: Any, **kwargs: Any
    ) -> tuple[CommandName | None, CommandArgs | None, AgentThoughts]:
        from autoai.json_utils.utilities import extract_dict_from_response, validate_dict

        if not llm_response.content:
            raise SyntaxError("Assistant response h作为无text content")

        try:
            assistant_reply_dict = extract_dict_from_response(llm_response.content)
        except ValueError as e:
            raise SyntaxError(f"Invalid response format: {e}") from e

        valid, errors = validate_dict(assistant_reply_dict, self.config)
        if not valid:
            raise SyntaxError(
                "Validation of response failed:\n  "
                + ";\n  ".join([str(e) for e in errors])
            )

        for plugin in self.config.plugins:
            if not plugin.can_handle_post_planning():
                continue
            assistant_reply_dict = plugin.post_planning(assistant_reply_dict)

        response: tuple[CommandName | None, CommandArgs | None, AgentThoughts] = (
            None,
            None,
            assistant_reply_dict,
        )

        if assistant_reply_dict != {}:
            try:
                from .agent import extract_command

                command_name, arguments = extract_command(
                    assistant_reply_dict, llm_response, self.config
                )
                response = command_name, arguments, assistant_reply_dict
            except Exception as e:
                logger.error(f"错误 extracting 命令: {e}")
                response = f"Error: {e}", {}, assistant_reply_dict

        self.log_cycle_handler.log_cycle(
            self.ai_config.ai_name,
            self.created_at,
            self.cycle_count,
            assistant_reply_dict,
            NEXT_ACTION_FILE_NAME,
        )
        return response

    # ==================================================================
    # Unified 模型 Router Integration
    # ==================================================================

    async def _routed_chat_completion(self, prompt: ChatSequence) -> Any:
        """LLM 调用 via unified ModelRouter. Falls back to V1 create_chat_completion."""
        from autoai.llm.model_router.base_provider import ChatMessage
        from autoai.llm.model_router.model_spec import ModelTier

        messages = [
            ChatMessage(role=msg.role, content=msg.content)
            for msg in prompt.messages
        ]

        tier = ModelTier.SMART if self.config.openai_functions else ModelTier.FAST
        decision = self._model_router.route(
            task_tier=tier,
            estimated_tokens=sum(count_string_tokens(msg.content, self.config.fast_llm) for msg in prompt.messages),
        )

        if decision is None:
            logger.warning("[ModelRouter] No routing decision, 回退到 V1")
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                None,
                lambda: create_chat_completion(prompt, self.config),
            )

        logger.info("[Model路由r] 路由d 到%s/%s (成本~$%.6f, reason=%s)",
                    decision.provider_name, decision.model_id,
                    decision.estimated_cost, decision.reason)

        try:
            provider = self._model_router.registry.get_provider(decision.provider_name)
            if provider is None:
                from autoai.llm.model_router import OpenAICompatProvider
                provider = OpenAICompatProvider.from_config(self.config)
                self._model_router.registry.register_provider(provider)

            response = await self._model_router.execute_chat(
                messages=messages,
                decision=decision,
                temperature=self.config.temperature,
            )

            from autoai.llm.base import ChatModelInfo, ChatModelResponse, ModelInfo
            model_info = ModelInfo(name=decision.model_id, max_tokens=4096, prompt_token_cost=0)
            chat_response = ChatModelResponse(
                content=response.content,
                function_call=None,
                model_info=model_info,
                prompt_tokens_used=response.prompt_tokens,
                completion_tokens_used=response.completion_tokens,
            )

            if self._stream_buffer:
                from autoai.llm.model_router.streaming import StreamingEvent, StreamEventType
                self._stream_buffer.push(StreamingEvent(
                    type=StreamEventType.THINK_END,
                    content=response.content[:200],
                    prompt_tokens=response.prompt_tokens,
                    completion_tokens=response.completion_tokens,
                    total_cost=response.total_cost,
                    model=decision.model_id,
                    provider=decision.provider_name,
                ))

            return chat_response

        except Exception as e:
            logger.warning("[ModelRouter] Chat failed (%s), 回退到 V1: %s", decision.model_id, e)
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                None,
                lambda: create_chat_completion(prompt, self.config),
            )
