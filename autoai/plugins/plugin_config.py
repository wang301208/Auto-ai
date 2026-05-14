from typing import Any

from pydantic import BaseModel


class PluginConfig(BaseModel):
    """保存单个插件配置的类"""

    name: str
    enabled: bool = False
    config: dict[str, Any] = None
