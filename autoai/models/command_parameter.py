import dataclasses
import enum


class ParameterType(str, enum.Enum):
    """命令允许的参数类型枚举。"""

    STRING = "string"
    NUMBER = "number"
    BOOLEAN = "boolean"


@dataclasses.dataclass
class CommandParameter:
    name: str
    type: ParameterType | str
    description: str
    required: bool

    def __post_init__(self) -> None:
        if not isinstance(self.type, ParameterType):
            self.type = ParameterType(self.type)

    def __repr__(self):
        return (
            f"CommandParameter('{self.name}', '{self.type.value}', '{self.description}',"
            f" {self.required})"
        )
