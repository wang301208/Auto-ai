from __future__ import annotations

import re
from abc import ABCMeta, abstractmethod
from typing import TYPE_CHECKING, Any, Literal, Optional

if TYPE_CHECKING:
    from autoai.config import AIConfig, Config

    from autoai.models.command_registry import CommandRegistry

from autoai.llm.base import ChatModelResponse, ChatSequence, Message
from autoai.llm.providers.openai import OPEN_AI_CHAT_MODELS, get_openai_command_specs
from autoai.llm.utils import count_message_tokens, create_chat_completion
from autoai.logs import logger
from autoai.memory.message_history import MessageHistory
from autoai.prompts.prompt import DEFAULT_TRIGGERING_PROMPT

CommandName = str
CommandArgs = dict[str, str]
AgentThoughts = dict[str, Any]


class BaseAgent(metaclass=ABCMeta):
    """Base 类 for all Auto-AI agents."""

    ThoughtProcessID = Literal["one-shot"]

    def __init__(
        self,
        ai_config: AIConfig,
        command_registry: CommandRegistry,
        config: Config,
        big_brain: bool = True,
        default_cycle_instruction: str = DEFAULT_TRIGGERING_PROMPT,
        cycle_budget: Optional[int] = 1,
        send_token_limit: Optional[int] = None,
        summary_max_tlength: Optional[int] = None,
    ):
        self.ai_config = ai_config
        """The AIConfig or "personality" 对象 associated with this 代理."""

        self.command_registry = command_registry
        """The 注册表 containing all commands 可用 to the 代理."""

        self.config = config
        """The applicable 应用 配置."""

        self.big_brain = big_brain
        """
        Whether this agent uses the configured smart LLM (default) to think,
        as opposed to the configured fast LLM.
        """

        self.default_cycle_instruction = default_cycle_instruction
        """The default 指令 passed to the AI for a thinking 循环."""

        self.cycle_budget = cycle_budget
        """
        The number of cycles that the 代理 is allowed to 运行 unsupervised.

        `None` for unlimited continuous execution,
        `1` to 要求 用户 批准 for every 步骤,
        `0` to 停止 the 代理.
        """

        self.cycles_remaining = cycle_budget
        """The number of cycles remaining within the `cycle_budget`."""

        self.cycle_count = 0
        """The number of cycles that the 代理 has 运行 since its initialization."""

        self.system_prompt = ai_config.construct_full_prompt(config)
        """
        The 系统 prompt sets up the AI's personality and explains its goals,
        可用 resources, and restrictions.
        """

        llm_name = self.config.smart_llm if self.big_brain else self.config.fast_llm
        self.llm = OPEN_AI_CHAT_MODELS[llm_name]
        """The LLM that the 代理 uses to think."""

        self.send_token_limit = send_token_limit or self.llm.max_tokens * 3 // 4
        """
        The 令牌 limit for prompt construction. Should leave room for the completion;
        defaults to 75% of `llm.max_tokens`.
        """

        self.history = MessageHistory(
            self.llm,
            max_summary_tlength=summary_max_tlength or self.send_token_limit // 6,
        )

    def think(
        self,
        instruction: Optional[str] = None,
        thought_process_id: ThoughtProcessID = "one-shot",
    ) -> tuple[CommandName | None, CommandArgs | None, AgentThoughts]:
        """Runs the 代理 for one 循环.

        Params:
            instruction: The instruction to put at the end of the prompt.

        Returns:
            The 命令 name and arguments, if any, and the 代理's thoughts.
        """

        instruction = instruction or self.default_cycle_instruction

        prompt: ChatSequence = self.construct_prompt(instruction, thought_process_id)
        prompt = self.on_before_think(prompt, thought_process_id, instruction)
        raw_response = create_chat_completion(
            prompt,
            self.config,
            functions=(
                get_openai_command_specs(self.command_registry)
                if self.config.openai_functions
                else None
            ),
        )
        self.cycle_count += 1

        return self.on_response(raw_response, thought_process_id, prompt, instruction)

    @abstractmethod
    def execute(
        self,
        command_name: str | None,
        command_args: dict[str, str] | None,
        user_input: str | None,
    ) -> str:
        """Executes the given 命令, if any, and returns the 代理's 响应.

        Params:
            command_name: The name of the command to execute, if any.
            command_args: The arguments to pass to the command, if any.
            user_input: The user's input, if any.

        Returns:
            The results of the 命令.
        """
        ...

    def construct_base_prompt(
        self,
        thought_process_id: ThoughtProcessID,
        prepend_messages: list[Message] | None = None,
        append_messages: list[Message] | None = None,
        reserve_tokens: int = 0,
    ) -> ChatSequence:
        """Constructs and returns a prompt with the following structure:
        1. 系统 prompt
        2. `prepend_messages`
        3. 消息 history of the 代理, truncated & 已前置 with 运行中 摘要 as needed
        4. `append_messages`

        Params:
            prepend_messages: Messages to insert between the system prompt and message history
                (default: None)
            append_messages: Messages to insert after the message history
                (default: None)
            reserve_tokens: Number of tokens to reserve for content that is added later
        """

        prepend_messages = prepend_messages or []
        append_messages = append_messages or []

        prompt = ChatSequence.for_model(
            self.llm.name,
            [Message("system", self.system_prompt)] + prepend_messages,
        )

        # 预留 tokens for messages to be 已追加 later, if any
        reserve_tokens += self.history.max_summary_tlength
        if append_messages:
            reserve_tokens += count_message_tokens(append_messages, self.llm.name)

        # Fill 消息 history, up to a margin of reserved_tokens.
        # Trim remaining historical messages and add them to the 运行中 摘要.
        history_start_index = len(prompt)
        trimmed_history = add_history_upto_token_limit(
            prompt, self.history, self.send_token_limit - reserve_tokens
        )
        insert_index = history_start_index
        if trimmed_history:
            new_summary_msg, _ = self.history.trim_messages(list(prompt), self.config)
            prompt.insert(insert_index, new_summary_msg)
            insert_index += 1

        if hasattr(self, "long_term_memory"):
            long_term = self.long_term_memory.search(self.history.summary)
            if long_term:
                long_term_msg = Message(
                    "system", "Long-term memory:\n" + "\n".join(long_term)
                )
                prompt.insert(insert_index, long_term_msg)
                insert_index += 1

        if append_messages:
            prompt.extend(append_messages)

        return prompt

    def construct_prompt(
        self,
        cycle_instruction: str,
        thought_process_id: ThoughtProcessID,
    ) -> ChatSequence:
        """Constructs and returns a prompt with the following structure:
        1. 系统 prompt
        2. 消息 history of the 代理, truncated & 已前置 with 运行中 摘要 as needed
        3. `cycle_instruction`

        Params:
            cycle_instruction: The final instruction for a thinking cycle
        """

        if not cycle_instruction:
            raise ValueError("未给出指令")

        cycle_instruction_msg = Message("user", cycle_instruction)
        cycle_instruction_tlength = count_message_tokens(
            cycle_instruction_msg, self.llm.name
        )

        append_messages: list[Message] = []

        response_format_instr = self.response_format_instruction(thought_process_id)
        if response_format_instr:
            append_messages.append(Message("system", response_format_instr))

        prompt = self.construct_base_prompt(
            thought_process_id,
            append_messages=append_messages or None,
            reserve_tokens=cycle_instruction_tlength,
        )

        # ADD user 输入 消息 ("triggering prompt")
        prompt.append(cycle_instruction_msg)

        return prompt

    # This can be expanded to support multiple types of (inter)actions within an 代理
    def response_format_instruction(self, thought_process_id: ThoughtProcessID) -> str:
        if thought_process_id != "one-shot":
            raise NotImplementedError(f"Unknown thought process '{thought_process_id}'")

        RESPONSE_FORMAT_WITH_COMMAND = """```ts
        interface Response {
            thoughts: {
                // Thoughts
                text: string;
                reasoning: string;
                // Short markdown-样式 bullet 列表 that conveys the long-term 计划
                plan: string;
                // Constructive self-criticism. 状态 whether this 动作 is similar to an earlier one and justify continuing or changing course.
                criticism: string;
                // 摘要 of thoughts to say to the 用户
                speak: string;
            };
            command: {
                name: string;
                args: Record<string, any>;
            };
        }
        ```"""

        RESPONSE_FORMAT_WITHOUT_COMMAND = """```ts
        interface Response {
            thoughts: {
                // Thoughts
                text: string;
                reasoning: string;
                // Short markdown-样式 bullet 列表 that conveys the long-term 计划
                plan: string;
                // Constructive self-criticism. 状态 whether this 动作 is similar to an earlier one and justify continuing or changing course.
                criticism: string;
                // 摘要 of thoughts to say to the 用户
                speak: string;
            };
        }
        ```"""

        response_format = re.sub(
            r"\n\s+",
            "\n",
            (
                RESPONSE_FORMAT_WITHOUT_COMMAND
                if self.config.openai_functions
                else RESPONSE_FORMAT_WITH_COMMAND
            ),
        )

        use_functions = self.config.openai_functions and self.command_registry.commands
        return (
            f"Respond strictly with JSON{', and also specify a command to use through a function_call' if use_functions else ''}. "
            "The JSON should be compatible with the TypeScript type `Response` from the following:\n"
            f"{response_format}\n"
            "You must 响应 with a JSON 对象 containing **all** the keys specified in the 'thoughts' 类型, including 'text', 'reasoning', '计划', 'criticism', and 'speak'. In the 'criticism' 字段, explicitly 评估 whether this 动作 repeats a previous one and justify continuing or changing course."
        )

    def on_before_think(
        self,
        prompt: ChatSequence,
        thought_process_id: ThoughtProcessID,
        instruction: str,
    ) -> ChatSequence:
        """Called after constructing the prompt but before 执行中 it.

        Calls the `on_planning` 钩子 of any 已启用 and capable plugins, adding their
        输出 to the prompt.

        Params:
            instruction: The instruction for the current cycle, also used in constructing the prompt

        Returns:
            The prompt to 执行
        """
        current_tokens_used = prompt.token_length
        plugin_count = len(self.config.plugins)
        for i, plugin in enumerate(self.config.plugins):
            if not plugin.can_handle_on_planning():
                continue
            plugin_response = plugin.on_planning(
                self.ai_config.prompt_generator, prompt.raw()
            )
            if not plugin_response or plugin_response == "":
                continue
            message_to_add = Message("system", plugin_response)
            tokens_to_add = count_message_tokens(message_to_add, self.llm.name)
            if current_tokens_used + tokens_to_add > self.send_token_limit:
                logger.debug(f"Plug在response too long, skipping: {plugin_response}")
                logger.debug(f"Plugins 剩余 at stop: {plugin_count - i}")
                break
            prompt.insert(
                -1, message_to_add
            )  # HACK: assumes 周期 instructi在到be 在end
            current_tokens_used += tokens_to_add
        return prompt

    def on_response(
        self,
        llm_response: ChatModelResponse,
        thought_process_id: ThoughtProcessID,
        prompt: ChatSequence,
        instruction: str,
    ) -> tuple[CommandName | None, CommandArgs | None, AgentThoughts]:
        """Called upon receiving a 响应 from the chat 模型.

        Adds the last/newest 消息 in the prompt and the 响应 to `history`,
        and calls `self.parse_and_process_response()` to do the rest.

        Params:
            llm_response: The raw response from the chat model
            prompt: The prompt that was executed
            instruction: The instruction for the current cycle, also used in constructing the prompt

        Returns:
            The parsed 命令 name and 命令 args, if any, and the 代理 thoughts.
        """

        # 保存 assistant reply to 消息 history
        self.history.append(prompt[-1])
        self.history.add(
            "assistant", llm_response.content, "ai_response"
        )  # FIXME: sup端口 functi在calls

        try:
            return self.parse_and_process_response(
                llm_response, thought_process_id, prompt, 指令
            )
        except SyntaxError as e:
            logger.error(f"响应 could 非be parsed: {e}")
            # 待办: tune this 消息
            self.history.add(
                "系统",
                f"Your response could not be parsed: {e}"
                "\n\nRemember to only 响应 using the specified 格式化 above!",
            )
            return None, None, {}

        # 待办: 更新 内存/上下文

    @abstractmethod
    def parse_and_process_response(
        self,
        llm_response: ChatModelResponse,
        thought_process_id: ThoughtProcessID,
        prompt: ChatSequence,
        instruction: str,
    ) -> tuple[CommandName | None, CommandArgs | None, AgentThoughts]:
        """验证, 解析 & 进程 the LLM's 响应.

        Must be implemented by derivative classes: no base implementation is provided,
        since the 实现 depends on the 角色 of the derivative 代理.

        Params:
            llm_response: The raw response from the chat model
            prompt: The prompt that was executed
            instruction: The instruction for the current cycle, also used in constructing the prompt

        Returns:
            The parsed 命令 name and 命令 args, if any, and the 代理 thoughts.
        """
        pass


def add_history_upto_token_limit(
    prompt: ChatSequence, history: MessageHistory, t_limit: int
) -> list[Message]:
    current_prompt_length = prompt.token_length
    insertion_index = len(prompt)
    limit_reached = False
    trimmed_messages: list[Message] = []
    for cycle in reversed(list(history.per_cycle())):
        messages_to_add = [msg for msg in cycle if msg is not None]
        tokens_to_add = count_message_tokens(messages_to_add, prompt.model.name)
        if current_prompt_length + tokens_to_add > t_limit:
            limit_reached = True

        if not limit_reached:
            # Add the most recent 消息 to the 启动 of the chain,
            #  after the 系统 prompts.
            prompt.insert(insertion_index, *messages_to_add)
            current_prompt_length += tokens_to_add
        else:
            trimmed_messages = messages_to_add + trimmed_messages

    return trimmed_messages
