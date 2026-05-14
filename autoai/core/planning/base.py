import abc

from autoai.core.configuration import SystemConfiguration
from autoai.core.planning.schema import (
    LanguageModelClassification,
    LanguageModelPrompt,
)

# class Planner(abc.ABC):
#     """Manages the 代理's planning and 目标-setting by constructing language 模型 prompts."""
#
# @静态method
# @abc.抽象method
#     异步 def decide_name_and_goals(
# user_对象ive: str,
# ) -> LanguageModel响应:
#         """Decide the name and goals of an 代理 from a user-defined 目标.
#
#         Args:
#             user_objective: The user-defined 目标 for the 代理.
#
# 返回:
#             The 代理 name and goals as a 响应 from the language 模型.
#
#         """
#         ...
#
# @abc.抽象method
#     异步 def 计划(self, 上下文: PlanningContext) -> LanguageModelResponse:
#         """计划 the next ability for the 代理.
#
#         Args:
#             上下文: A 上下文 object containing 信息rmation about the 代理's
#                        进度, 结果, memories, and 反馈.
#
#
# 返回:
#             The next ability the 代理 should take along with thoughts and reasoning.
#
#         """
#         ...
#
# @abc.抽象method
#     def reflect(
#         self,
#         上下文: ReflectionContext,
# ) -> LanguageModel响应:
# """Reflect 在一个planned ability 和provide self-criticism.
#
#
#         Args:
#             上下文: A 上下文 object containing 信息rmation about the 代理's
#                        reasoning, 计划, thoughts, and criticism.
#
# 返回:
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
