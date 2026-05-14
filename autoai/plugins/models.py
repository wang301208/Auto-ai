from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, HttpUrl


class SourceCodeAccessPolicy(str, Enum):
    """Policy describing how plugin source code may be accessed."""

    ALLOWED_FOR_READ_ONLY = "ALLOWED_FOR_READ_ONLY"
    RESTRICTED = "RESTRICTED"


class UnderlyingLibrary(BaseModel):
    """Information about the library a plugin depends on."""

    name: str
    version: str
    repo_url: HttpUrl
    local_source_path: str


class PluginMeta(BaseModel):
    """Metadata describing a plugin stub or implementation."""

    name: str
    description: str
    instructions: str
    developer: str
    policy_maker: str
    underlying_library: UnderlyingLibrary
    source_code_access_policy: SourceCodeAccessPolicy


class PluginMetaValidationError(ValueError):
    """Raised when plugin metadata is invalid."""

    pass
