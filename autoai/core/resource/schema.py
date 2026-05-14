import abc
import enum

try:
    from pydantic import SecretBytes, SecretStr
    SecretField = SecretStr
except ImportError:
    from pydantic import SecretStr
    SecretField = SecretStr

from autoai.core.configuration import (
    SystemConfiguration,
    SystemSettings,
    UserConfigurable,
)


class ResourceType(str, enum.Enum):
    """资源类型的枚举。"""

    MODEL = "model"
    MEMORY = "memory"


class ProviderUsage(SystemConfiguration, abc.ABC):
    @abc.abstractmethod
    def update_usage(self, *args, **kwargs) -> None:
        """更新资源使用量。"""
        ...


class ProviderBudget(SystemConfiguration):
    total_budget: float = UserConfigurable()
    total_cost: float
    remaining_budget: float
    usage: ProviderUsage

    @abc.abstractmethod
    def update_usage_and_cost(self, *args, **kwargs) -> None:
        """更新资源使用量和成本。"""
        ...


class ProviderCredentials(SystemConfiguration):
    """凭据结构。"""

    class Config:
        json_encoders = {
            SecretStr: lambda v: v.get_secret_value() if v else None,
            SecretBytes: lambda v: v.get_secret_value() if v else None,
            SecretField: lambda v: v.get_secret_value() if v else None,
        }


class ProviderSettings(SystemSettings):
    resource_type: ResourceType
    credentials: ProviderCredentials | None = None
    budget: ProviderBudget | None = None


# Used both by 模型 providers and 内存 providers
Embedding = list[float]
