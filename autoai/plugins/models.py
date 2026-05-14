from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, HttpUrl


class SourceCodeAccessPolicy(str, Enum):
    """描述插件源代码访问方式的策略。"""

    ALLOWED_FOR_READ_ONLY = "ALLOWED_FOR_READ_ONLY"
    RESTRICTED = "RESTRICTED"


class UnderlyingLibrary(BaseModel):
    """插件依赖的库信息。"""

    name: str
    version: str
    repo_url: HttpUrl
    local_source_path: str


class PluginMeta(BaseModel):
    """描述插件存根或实现的元数据。"""

    name: str
    description: str
    instructions: str
    developer: str
    policy_maker: str
    underlying_library: UnderlyingLibrary
    source_code_access_policy: SourceCodeAccessPolicy


class PluginMetaValidationError(ValueError):
    """当插件元数据无效时引发。"""

    pass
