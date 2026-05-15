from __future__ import annotations

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

from autoai.event_bus import EventMessage
from autoai.json_utils.utilities import extract_dict_from_response, validate_dict
from autoai.llm.api_manager import ApiManager
from autoai.llm.base import Message
from autoai.llm.utils import count_string_tokens
from autoai.logs import logger
from autoai.logs.log_cycle import (
    CURRENT_CONTEXT_FILE_NAME,
    FULL_MESSAGE_HISTORY_FILE_NAME,
    NEXT_ACTION_FILE_NAME,
    USER_INPUT_FILE_NAME,
    LogCycleHandler,
)
from autoai.memory.long_term import LongTermMemory
from autoai.self_improve import NEED_TOOL, DatabaseManager, PluginTodoQueue, Profiler
from autoai.skills import get_library
from autoai.workspace import Workspace

from .base import AgentThoughts, BaseAgent, CommandArgs, CommandName


class CommandRepetitionError(RuntimeError):
    """Raised when the same 命令 is executed too many times."""


class Agent(BaseAgent):
    """代理 类 for interacting with Auto-AI."""

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
        """Long-term memory 管理器"""

        self.workspace = Workspace(config.workspace_path, config.restrict_to_workspace)
        """工作区 that the 代理 has access to, e.g. for reading/writing files."""

        self.created_at = datetime.now().strftime("%Y%m%d_%H%M%S")
        """Timestamp the 代理 was 已创建; only used for structured 调试 logging."""

        self.log_cycle_handler = LogCycleHandler()
        """LogCycleHandler for structured 调试 logging."""

        self.plugin_queue = plugin_queue
        self.message_queue = message_queue
        self.db = db

        self._recent_commands: deque[tuple[str, float]] = deque()
        self._agent_enhancer: Any | None = None
        self._enhanced_context: Any | None = None

    def construct_base_prompt(self, *args: Any, **kwargs: Any) -> ChatSequence:
        if kwargs.get("prepend_messages") is None:
            kwargs["prepend_messages"] = []

        # 时钟
        kwargs["prepend_messages"].append(
            Message("system", f"The current time and date is {time.strftime('%c')}"),
        )

        # Add 预算 信息rmation (if any) to prompt
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
            logger.debug(budget_msg)

            if kwargs.get("append_messages") is None:
                kwargs["append_messages"] = []
            kwargs["append_messages"].append(budget_msg)

        return super().construct_base_prompt(*args, **kwargs)

    def think(
        self,
        instruction: Optional[str] = None,
        thought_process_id: BaseAgent.ThoughtProcessID = "one-shot",
    ) -> tuple[CommandName | None, CommandArgs | None, AgentThoughts]:
        """运行 one 代理 循环, checking the skill 库 before planning."""

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
        if self.message_queue:
            self.message_queue.publish(
                EventMessage(
                    event_type="skill_miss",
                    payload={"query": query},
                    source_agent=self.ai_config.ai_name,
                )
            )

        if self._agent_enhancer is not None:
            try:
                self._agent_enhancer.on_think_start(query)
            except Exception:
                pass

        return super().think(instruction, thought_process_id)

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
        """记录 a 命令 execution and 回报 the 计数 in the recent window."""
        now = time.time()
        self._recent_commands.append((signature, now))
        # 丢弃重复窗口外的命令
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
        if self._agent_enhancer is not None and command_name is not None:
            try:
                decision = self._agent_enhancer.on_decision(command_name, command_args)
                if not decision.get("allowed", True):
                    return f"Blocked by governance: {decision.get('effect', 'unknown')}"
            except Exception:
                pass

        # 执行 command
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
                result = f"Failure: command {command_name} returned too much output. \
                    Do not 执行 this 命令 again with the same arguments."

            for plugin in self.config.plugins:
                if not plugin.can_handle_post_command():
                    continue
                result = plugin.post_command(command_name, result)
        # 检查 if there's a 结果 from the command append it to the 消息
        if result is None:
            self.history.add("system", "Unable to execute command", "action_result")
        else:
            self.history.add("system", result, "action_result")

        if self._agent_enhancer is not None and command_name is not None:
            try:
                success = not (result is None or (isinstance(result, str) and result.startswith("Failure")))
                self._agent_enhancer.on_action_complete(command_name, success)
            except Exception:
                pass

        self.long_term_memory.maybe_transfer(self.history)

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
        """执行 a 命令 and 发射 an 事件 with the 结果."""
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

        # 打印 Assistant thoughts
        if assistant_reply_dict != {}:
            # 获取 command name and arguments
            try:
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


def extract_command(
    assistant_reply_json: dict, assistant_reply: ChatModelResponse, config: Config
) -> tuple[str, dict[str, str]]:
    """解析 the 响应 and 回报 the 命令 name and arguments

    Args:
        assistant_reply_json (dict): The response object from the AI
        assistant_reply (ChatModelResponse): The model response from the AI
        config (Config): The config object

    Returns:
        tuple: The command name and arguments

    Raises:
        json.decoder.JSONDecodeError: If the response is not valid JSON

        Exception: If any other error occurs
    """
    if config.openai_functions:
        if assistant_reply.function_call is None:
            return "Error:", {"message": "No 'function_call' in assistant reply"}
        assistant_reply_json["command"] = {
            "name": assistant_reply.function_call.name,
            "args": json.loads(assistant_reply.function_call.arguments),
        }
    try:
        if "command" not in assistant_reply_json:
            return "Error:", {"message": "Missing 'command' object in JSON"}

        if not isinstance(assistant_reply_json, dict):
            return (
                "Error:",
                {
                    "message": f"The previous message sent was not a dictionary {assistant_reply_json}"
                },
            )

        command = assistant_reply_json["command"]
        if not isinstance(command, dict):
            return "Error:", {"message": "'command' object is not a dictionary"}

        if "name" not in command:
            return "Error:", {"message": "Missing 'name' field in 'command' object"}

        command_name = command["name"]

        # Use an 空 dictionary if 'args' 字段 is not present in 'command' object
        arguments = command.get("args", {})

        return command_name, arguments
    except json.decoder.JSONDecodeError:
        return "Error:", {"message": "Invalid JSON"}
    # All other 错误s, return "错误: + 错误 消息"
    except Exception as e:
        return "Error:", {"message": str(e)}


def execute_command(
    command_name: str,
    arguments: dict[str, str],
    agent: Agent,
) -> Any:
    """执行 the 命令 and 回报 the 结果

    Args:
        command_name (str): The name of the command to execute
        arguments (dict): The arguments for the command
        agent (Agent): The agent that is executing the command

    Returns:
        str: The result of the command
    """
    try:
        # 执行 a native command with the same name or alias, if it exists
        if command := agent.command_registry.get_command(command_name):
            return command(**arguments, agent=agent)

        # 处理 non-native commands (e.g. from plugins)
        for command in agent.ai_config.prompt_generator.commands:
            if (
                command_name == command.label.lower()
                or command_name == command.name.lower()
            ):
                return command.function(**arguments)

        raise RuntimeError(
            f"Cannot execute '{command_name}': unknown command."
            " Do not try to use this 命令 again."
        )
    except Exception as e:
        return f"Error: {str(e)}"
