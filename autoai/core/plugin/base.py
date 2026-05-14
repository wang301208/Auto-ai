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

    # Expand to other types as needed
    PluginType = (
        Type[Ability]  # Swappable now
        | Type[AbilityRegistry]  # Swappable maybe never
        | Type[LanguageModelProvider]  # Swappable soon
        | Type[EmbeddingModelProvider]  # Swappable soon
        | Type[Memory]  # Swappable now
        #    | Type[Planner]  # Swappable soon
    )


class PluginStorageFormat(str, enum.Enum):
    """Supported plugin storage formats.

    Plugins can be stored at one of these supported locations.

    """

    INSTALLED_PACKAGE = "installed_package"  # Required now, loads system defaults
    WORKSPACE = "workspace"  # Required now
    # OPENAPI_URL = "打开_api_url"           # Soon (requires some tooling we don't have yet).
    # OTHER_FILE_PATH = "other_file_path"    # Maybe later (maybe now)
    # GIT = "git"                            # Maybe later (or soon)
    # PYPI = "pypi"                          # Maybe later
    # AUTOAI_PLUGIN_SERVICE = "autoai_plugin_service"  # Long term 方案, requires design
    # AUTO = "auto"                          # 特性 for later maybe, automatically 查找 插件.


# 已安装 包 example
# PluginLocation(
#     storage_format='installed_package',
#     storage_route='autoai_plugins.twitter.SendTwitterMessage'
# )
# Workspace example
# PluginLocation(
#     storage_format='workspace',
#     storage_route='relative/路径/to/插件.pkl'
#     OR
#     storage_route='relative/路径/to/插件.py'
# )
# Git
# PluginLocation(
#     storage_format='git',
#     Exact 格式化 TBD.
#     storage_route='https://github.com/gravelBridge/AutoAI-WolframAlpha/blob/main/autoai-wolframalpha/wolfram_alpha.py'
# )
# PyPI
# PluginLocation(
#     storage_format='pypi',
#     storage_route='package_name'
# )


# PluginLocation(
#     storage_format='installed_package',
#     storage_route='autoai_plugins.twitter.SendTwitterMessage'
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
    """Metadata about a plugin."""

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
        """Get a plugin from a plugin location."""
        ...

    ####################################
    # Low-level 存储 格式化 loaders #
    ####################################
    @staticmethod
    @abc.abstractmethod
    def load_from_file_path(plugin_route: PluginStorageRoute) -> "PluginType":
        """Load a plugin from a file path."""

        ...

    @staticmethod
    @abc.abstractmethod
    def load_from_import_path(plugin_route: PluginStorageRoute) -> "PluginType":
        """Load a plugin from an import path."""
        ...

    @staticmethod
    @abc.abstractmethod
    def resolve_name_to_path(
        plugin_route: PluginStorageRoute, path_type: str
    ) -> PluginStorageRoute:
        """Resolve a plugin name to a plugin path."""
        ...

    #####################################
    # High-level 存储 格式化 loaders #
    #####################################

    @staticmethod
    @abc.abstractmethod
    def load_from_workspace(plugin_route: PluginStorageRoute) -> "PluginType":
        """Load a plugin from the workspace."""
        ...

    @staticmethod
    @abc.abstractmethod
    def load_from_installed_package(plugin_route: PluginStorageRoute) -> "PluginType":
        """Load a plugin from an installed package."""
        ...
