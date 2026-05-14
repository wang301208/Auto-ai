import abc
from pprint import pformat
from typing import Any, ClassVar

from autoai.utils.stdlib_replacements import underscore
from pydantic import Field

from autoai.core.ability.schema import AbilityResult
from autoai.core.configuration import SystemConfiguration
from autoai.core.planning.schema import LanguageModelConfiguration


class AbilityConfiguration(SystemConfiguration):
    """模型配置结构。"""

    from autoai.core.plugin.base import PluginLocation

    location: PluginLocation
    packages_required: list[str] = Field(default_factory=list)
    language_model_required: LanguageModelConfiguration = None
    memory_provider_required: bool = False
    workspace_required: bool = False


class Ability(abc.ABC):
    """表示代理技能的类。"""

    default_configuration: ClassVar[AbilityConfiguration]

    @classmethod
    def name(cls) -> str:
        """技能名称。"""
        return underscore(cls.__name__)

    @classmethod
    @abc.abstractmethod
    def description(cls) -> str:
        """技能功能的详细描述。"""
        ...

    @classmethod
    @abc.abstractmethod
    def arguments(cls) -> dict:
        """标准JSON模式格式的参数字典。"""
        ...

    @classmethod
    def required_arguments(cls) -> list[str]:
        """必需参数列表。"""
        return []

    @abc.abstractmethod
    async def __call__(self, *args: Any, **kwargs: Any) -> AbilityResult:
        ...

    def __str__(self) -> str:
        return pformat(self.dump())

    def dump(self) -> dict:
        return {
            "name": self.name(),
            "description": self.description(),
            "parameters": {
                "type": "object",
                "properties": self.arguments(),
                "required": self.required_arguments(),
            },
        }


class AbilityRegistry(abc.ABC):
    @abc.abstractmethod
    def register_ability(
        self, ability_name: str, ability_configuration: AbilityConfiguration
    ) -> None:
        ...

    @abc.abstractmethod
    def list_abilities(self) -> list[str]:
        ...

    @abc.abstractmethod
    def dump_abilities(self) -> list[dict]:
        ...

    @abc.abstractmethod
    def get_ability(self, ability_name: str) -> Ability:
        ...

    @abc.abstractmethod
    async def perform(self, ability_name: str, **kwargs: Any) -> AbilityResult:
        ...
