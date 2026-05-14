from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from math import ceil, floor
from typing import TYPE_CHECKING, Literal, Optional, Type, TypedDict, TypeVar, overload

if TYPE_CHECKING:
    from autoai.llm.providers.openai import OpenAIFunctionCall

MessageRole = Literal["system", "user", "assistant", "function"]
MessageType = Literal["ai_response", "action_result"]

TText = list[int]
"""Token array representing tokenized text"""


class MessageDict(TypedDict):
    role: MessageRole
    content: str


class ResponseMessageDict(TypedDict):
    role: Literal["assistant"]
    content: Optional[str]
    function_call: Optional[FunctionCallDict]


class FunctionCallDict(TypedDict):
    name: str
    arguments: str


@dataclass
class Message:
    """包含角色和消息内容的OpenAI消息对象"""

    role: MessageRole
    content: str
    type: MessageType | None = None

    def raw(self) -> MessageDict:
        return {"role": self.role, "content": self.content}


@dataclass
class ModelInfo:
    """Struct for model information.

    Would be lovely to eventually get this directly from APIs, but needs to be scraped from
    websites for now.
    """

    name: str
    max_tokens: int
    prompt_token_cost: float


@dataclass
class CompletionModelInfo(ModelInfo):
    """通用补全模型信息结构。"""

    completion_token_cost: float


@dataclass
class ChatModelInfo(CompletionModelInfo):
    """聊天模型信息结构。"""

    supports_functions: bool = False


@dataclass
class TextModelInfo(CompletionModelInfo):
    """文本补全模型信息结构。"""


@dataclass
class EmbeddingModelInfo(ModelInfo):
    """嵌入模型信息结构。"""

    embedding_dimensions: int


# C一个be replaced 通过Self 在Pyth在3.11
TChatSequence = TypeVar("TChatSequence", bound="ChatSequence")


@dataclass
class ChatSequence:
    """聊天序列的实用容器"""

    model: ChatModelInfo
    messages: list[Message] = field(default_factory=list[Message])

    @overload
    def __getitem__(self, key: int) -> Message:
        ...

    @overload
    def __getitem__(self: TChatSequence, key: slice) -> TChatSequence:
        ...

    def __getitem__(self: TChatSequence, key: int | slice) -> Message | TChatSequence:
        if isinstance(key, slice):
            copy = deepcopy(self)
            copy.messages = self.messages[key]
            return copy
        return self.messages[key]

    def __iter__(self):
        return iter(self.messages)

    def __len__(self):
        return len(self.messages)

    def add(
        self,
        message_role: MessageRole,
        content: str,
        type: MessageType | None = None,
    ) -> None:
        self.append(Message(message_role, content, type))

    def append(self, message: Message):
        return self.messages.append(message)

    def extend(self, messages: list[Message] | ChatSequence):
        return self.messages.extend(messages)

    def insert(self, index: int, *messages: Message):
        for message in reversed(messages):
            self.messages.insert(index, message)

    @classmethod
    def for_model(
        cls: Type[TChatSequence],
        model_name: str,
        messages: list[Message] | ChatSequence = [],
        **kwargs,
    ) -> TChatSequence:
        from autoai.llm.providers.openai import OPEN_AI_CHAT_MODELS

        if not model_name in OPEN_AI_CHAT_MODELS:
            raise ValueError(f"Unknown chat model '{model_name}'")

        return cls(
            model=OPEN_AI_CHAT_MODELS[model_name], messages=list(messages), **kwargs
        )

    @property
    def token_length(self) -> int:
        from autoai.llm.utils import count_message_tokens

        return count_message_tokens(self.messages, self.model.name)

    def raw(self) -> list[MessageDict]:
        return [m.raw() for m in self.messages]

    def dump(self) -> str:
        SEPARATOR_LENGTH = 42

        def separator(text: str):
            half_sep_len = (SEPARATOR_LENGTH - 2 - len(text)) / 2
            return f"{floor(half_sep_len)*'-'} {text.upper()} {ceil(half_sep_len)*'-'}"

        formatted_messages = "\n".join(
            [f"{separator(m.role)}\n{m.content}" for m in self.messages]
        )
        return f"""
============== {__class__.__name__} ==============
Length: {self.token_length} tokens; {len(self.messages)} messages
{formatted_messages}
==========================================
"""


@dataclass
class LLMResponse:
    """LLM模型响应的标准响应结构。"""

    model_info: ModelInfo


@dataclass
class EmbeddingModelResponse(LLMResponse):
    """嵌入模型响应的标准响应结构。"""

    embedding: list[float] = field(default_factory=list)


@dataclass
class ChatModelResponse(LLMResponse):
    """聊天LLM响应的标准响应结构。"""

    content: Optional[str]
    function_call: Optional[OpenAIFunctionCall]
