import abc
import enum
from typing import TYPE_CHECKING, Type

from pydantic import BaseModel

from autoai.core.configuration import SystemConfiguration, UserConfigurable

if TYPE_CHECKING:
    from autoai.core.ability import Ability, AbilityRegistry
    from autoai.core.memory import Memory
    from autoai.core.resource.model_providers import (
        EmbeddingModelProvider,
        LanguageModelProvider,
    )

    # Exp和到other types 作为needed
    PluginType = (
        Type[Ability]  # 交换pable now
        | Type[AbilityRegistry]  # 交换pable maybe never
        | Type[LanguageModelProvider]  # 交换pable soon
        | Type[EmbeddingModelProvider]  # 交换pable soon
        | Type[Memory]  # 交换pable now
        # | 类型[Planner]  # 交换pable soon
    )


class PluginStorageFormat(str, enum.Enum):
    """Supported plugin storage formats.

    Plugins can be stored at one of these supported locations.

    """

    INSTALLED_PACKAGE = "installed_package"  # Required now, loads system 默认s
    WORKSPACE = "workspace"  # Required now
    # OPENAPI_URL = "打开_api_url"           # Soon (requires some tooling we don't have yet).
    # OTHER_FILE_PATH = "other_文件_路径"    # Maybe 稍后(maybe now)
    # GIT = "git"                            # Maybe 稍后(或soon)
    # PYPI = "pypi"                          # Maybe later
    # AUTOAI_PLUGIN_SERVICE = "autoai_plugin_service"  # Long term 方案, requires design
    # AUTO = "auto"                          # 特性 for later maybe, automatically 查找 插件.


# 已安装 包 example
# PluginLocation(
#     storage_format='installed_package',
# storage_路由='autoai_plugins.twitter.发送Twitter消息'
# )
# Workspace example
# PluginLocation(
# storage_format='工作区',
#     storage_route='relative/路径/to/插件.pkl'
#     OR
#     storage_route='relative/路径/to/插件.py'
# )
# Git
# PluginLocation(
#     storage_format='git',
#     Exact 格式化 TBD.
# storage_路由='https://github.com/gravelBridge/AutoAI-WolframAlpha/blob/main/autoai-wolframalpha/wolfram_alpha.py'
# )
# PyPI
# PluginLocation(
#     storage_format='pypi',
# storage_路由='package_名称'
# )


# PluginLocation(
#     storage_format='installed_package',
# storage_路由='autoai_plugins.twitter.发送Twitter消息'
# )


# A 插件 存储 路由.
#
# This is a string that specifies where to 加载 a 插件 from
# (e.g. an 导入 路径 or file 路径).
PluginStorageRoute = str


class PluginLocation(SystemConfiguration):
    """A plugin location.

    This is a combination of a plugin storage format and a plugin storage route.
    It is used by the PluginService to load plugins.

    """

    storage_format: PluginStorageFormat = UserConfigurable()
    storage_route: PluginStorageRoute = UserConfigurable()


class PluginMetadata(BaseModel):
    """关于插件的元数据。"""

    name: str
    description: str
    location: PluginLocation


class PluginService(abc.ABC):
    """Base class for plugin service.

    The plugin service should be stateless. This defines the interface for
    loading plugins from various storage formats.

    """

    @staticmethod
    @abc.abstractmethod
    def get_plugin(plugin_location: PluginLocation) -> "PluginType":
        """从插件位置获取插件。"""
        ...

    ####################################
    # Low-level 存储 格式化 loaders #
    ####################################
    @staticmethod
    @abc.abstractmethod
    def load_from_file_path(plugin_route: PluginStorageRoute) -> "PluginType":
        """从文件路径加载插件。"""

        ...

    @staticmethod
    @abc.abstractmethod
    def load_from_import_path(plugin_route: PluginStorageRoute) -> "PluginType":
        """从导入路径加载插件。"""
        ...

    @staticmethod
    @abc.abstractmethod
    def resolve_name_to_path(
        plugin_route: PluginStorageRoute, path_type: str
    ) -> PluginStorageRoute:
        """将插件名称解析为插件路径。"""
        ...

    #####################################
    # High-level 存储 格式化 loaders #
    #####################################

    @staticmethod
    @abc.abstractmethod
    def load_from_workspace(plugin_route: PluginStorageRoute) -> "PluginType":
        """从工作区加载插件。"""
        ...

    @staticmethod
    @abc.abstractmethod
    def load_from_installed_package(plugin_route: PluginStorageRoute) -> "PluginType":
        """从已安装的包加载插件。"""
        ...
