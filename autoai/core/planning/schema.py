from __future__ import annotations

import enum

from pydantic import BaseModel, Field, validator

from autoai.core.configuration import SystemConfiguration, UserConfigurable
from autoai.core.resource.model_providers.schema import (
    LanguageModelFunction,
    LanguageModelMessage,
    LanguageModelProviderModelResponse,
    ModelProviderName,
)


class LanguageModelClassification(str, enum.Enum):
    """The LanguageModelClassification is a functional description of the model.

    This is used to determine what kind of model to use for a given prompt.
    Sometimes we prefer a faster or cheaper model to accomplish a task when
    possible.

    """

    FAST_MODEL: str = "fast_model"
    SMART_MODEL: str = "smart_model"


class LanguageModelConfiguration(SystemConfiguration):
    """模型配置结构。"""

    model_name: str = UserConfigurable()
    provider_name: ModelProviderName = UserConfigurable()
    temperature: float = UserConfigurable()


class LanguageModelPrompt(BaseModel):
    messages: list[LanguageModelMessage]
    functions: list[LanguageModelFunction] = Field(default_factory=list)

    def __str__(self):
        return "\n\n".join([f"{m.role.value}: {m.content}" for m in self.messages])


class LanguageModelResponse(LanguageModelProviderModelResponse):
    """语言模型响应的标准响应结构。"""


class TaskType(str, enum.Enum):
    RESEARCH: str = "research"
    WRITE: str = "write"
    EDIT: str = "edit"
    CODE: str = "code"
    DESIGN: str = "design"
    TEST: str = "test"
    PLAN: str = "plan"


class TaskStatus(str, enum.Enum):
    BACKLOG: str = "backlog"
    READY: str = "ready"
    IN_PROGRESS: str = "in_progress"
    DONE: str = "done"


class TaskContext(BaseModel):
    cycle_count: int = 0
    status: TaskStatus = TaskStatus.BACKLOG
    parent: "Task" = None
    prior_actions: list = Field(default_factory=list)
    memories: list = Field(default_factory=list)
    user_input: list[str] = Field(default_factory=list)
    supplementary_info: list[str] = Field(default_factory=list)
    enough_info: bool = False


class Task(BaseModel):
    objective: str
    type: TaskType
    priority: int
    ready_criteria: list[str]
    acceptance_criteria: list[str]
    context: TaskContext = Field(default_factory=TaskContext)

    @validator("type", pre=True)
    def _validate_type(cls, v):
        if isinstance(v, TaskType):
            return v
        return TaskType(v)

    class Config:
        use_enum_values = True


# Need to resolve the circular dependency between 任务 and TaskContext once both models are defined.
TaskContext.update_forward_refs()
