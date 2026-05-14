import abc
import typing
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field


def UserConfigurable(*args, **kwargs):
    return Field(*args, **kwargs, user_configurable=True)


class SystemConfiguration(BaseModel):
    def get_user_config(self) -> dict[str, Any]:
        return _get_user_config_fields(self)

    class Config:
        extra = "forbid"
        use_enum_values = True


class SystemSettings(BaseModel):
    """所有系统设置的基类."""

    name: str
    description: str

    class Config:
        extra = "forbid"
        use_enum_values = True


S = TypeVar("S", bound=SystemSettings)


class Configurable(abc.ABC, Generic[S]):
    """所有可配置对象的基类."""

    prefix: str = ""
    default_settings: typing.ClassVar[S]

    @classmethod
    def get_user_config(cls) -> dict[str, Any]:
        return _get_user_config_fields(cls.default_settings)

    @classmethod
    def build_agent_configuration(cls, configuration: dict) -> S:
        """处理此对象的配置."""

        defaults = cls.default_settings.dict()
        final_configuration = deep_update(defaults, configuration)

        return cls.default_settings.__class__.parse_obj(final_configuration)


def _get_user_config_fields(instance: BaseModel) -> dict[str, Any]:
    """
        获取用户配置字段 of a Pydantic model 实例.

        Args:
            instance: The Pydantic model 实例.

        Returns:
            The user config fields of the 实例.
"""
    user_config_fields = {}

    for name, value in instance.__dict__.items():
        field_info = instance.__fields__[name]
        if "user_configurable" in field_info.field_info.extra:
            user_config_fields[name] = value
        elif isinstance(value, SystemConfiguration):
            user_config_fields[name] = value.get_user_config()
        elif isinstance(value, list) and all(
            isinstance(i, SystemConfiguration) for i in value
        ):
            user_config_fields[name] = [i.get_user_config() for i in value]
        elif isinstance(value, dict) and all(
            isinstance(i, SystemConfiguration) for i in value.values()
        ):
            user_config_fields[name] = {
                k: v.get_user_config() for k, v in value.items()
            }

    return user_config_fields


def deep_update(original_dict: dict, update_dict: dict) -> dict:
    """
        递归更新字典.

        Args:
            original_dict (dict): 要更新的字典.
            update_dict (dict): 用于更新的字典.

        Returns:
            dict: 更新后的字典.
"""
    for key, value in update_dict.items():
        if (
            key in original_dict
            and isinstance(original_dict[key], dict)
            and isinstance(value, dict)
        ):
            original_dict[key] = deep_update(original_dict[key], value)
        else:
            original_dict[key] = value
    return original_dict
