import abc

from autoai.core.configuration import SystemConfiguration
from autoai.core.planning.schema import (
    LanguageModelClassification,
    LanguageModelPrompt,
)

# class Planner(abc.ABC):
#     """Manages the 代理's planning and 目标-setting by constructing language 模型 prompts."""
#
#     @staticmethod
#     @abc.abstractmethod
#     异步 def decide_name_and_goals(
#         user_objective: str,
#     ) -> LanguageModelResponse:
#         """Decide the name and goals of an 代理 from a user-defined 目标.
#
#         Args:
#             user_objective: The user-defined 目标 for the 代理.
#
#         Returns:
#             The 代理 name and goals as a 响应 from the language 模型.
#
#         """
#         ...
#
#     @abc.abstractmethod
#     异步 def 计划(self, 上下文: PlanningContext) -> LanguageModelResponse:
#         """计划 the next ability for the 代理.
#
#         Args:
#             上下文: A 上下文 object containing 信息rmation about the 代理's
#                        进度, 结果, memories, and 反馈.
#
#
#         Returns:
#             The next ability the 代理 should take along with thoughts and reasoning.
#
#         """
#         ...
#
#     @abc.abstractmethod
#     def reflect(
#         self,
#         上下文: ReflectionContext,
#     ) -> LanguageModelResponse:
#         """Reflect on a planned ability and provide self-criticism.
#
#
#         Args:
#             上下文: A 上下文 object containing 信息rmation about the 代理's
#                        reasoning, 计划, thoughts, and criticism.
#
#         Returns:
#             Self-criticism about the 代理's 计划.
#
#         """
#         ...


class PromptStrategy(abc.ABC):
    default_configuration: SystemConfiguration

    @property
    @abc.abstractmethod
    def model_classification(self) -> LanguageModelClassification:
        ...

    @abc.abstractmethod
    def build_prompt(self, *_, **kwargs) -> LanguageModelPrompt:
        ...

    @abc.abstractmethod
    def parse_response_content(self, response_content: dict) -> dict:
        ...
