from __future__ import annotations

import time
import logging
from dataclasses import dataclass, field
from typing import Any, Callable
from enum import Enum

logger = logging.getLogger(__name__)


class InputType(Enum):
    COMMAND = "command"
    SELECT = "select"
    CONFIRM = "confirm"
    VALUE = "value"
    NAVIGATE = "navigate"


@dataclass
class InputAction:
    """用户输入直接变为Agent行动。"""
    input_type: InputType
    raw_input: str
    action_name: str = ""
    action_args: dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    source_panel: str = ""

    @property
    def is_command(self) -> bool:
        return self.input_type == InputType.COMMAND

    @property
    def as_cli_command(self) -> str:
        if self.action_name:
            args_str = " ".join(f"--{k} {v}" for k, v in self.action_args.items())
            return f"{self.action_name} {args_str}".strip()
        return self.raw_input


@dataclass
class InteractionResult:
    action: InputAction
    success: bool = True
    output: str = ""
    side_effects: list[str] = field(default_factory=list)


class InteractionBridge:
    """交互桥: 用户输入直接变为Agent行动。

    不存在"UI层"和"业务层"的分离——
    用户的每一个操作就是Agent的一个行动，
    没有中间层，没有适配器，没有DTO。
    """

    def __init__(self):
        self._handlers: dict[str, Callable] = {}
        self._history: list[InputAction] = []
        self._results: list[InteractionResult] = []

    def register_handler(self, action_name: str, handler: Callable) -> None:
        self._handlers[action_name] = handler

    def process_input(self, raw_input: str, source_panel: str = "") -> InteractionResult:
        """处理用户输入: 解析为行动并执行。"""
        action = self._parse_input(raw_input, source_panel)
        self._history.append(action)
        handler = self._handlers.get(action.action_name)
        if handler:
            try:
                result = handler(**action.action_args)
                ir = InteractionResult(
                    action=action, success=True,
                    output=str(result) if result else "",
                )
            except Exception as e:
                ir = InteractionResult(
                    action=action, success=False,
                    output=f"Error: {e}",
                )
        else:
            ir = InteractionResult(
                action=action, success=True,
                output=f"No handler for '{action.action_name}', raw: {raw_input}",
            )
        self._results.append(ir)
        return ir

    def _parse_input(self, raw_input: str, source_panel: str = "") -> InputAction:
        """解析输入为行动。"""
        stripped = raw_input.strip()
        if stripped.startswith("/"):
            parts = stripped[1:].split(maxsplit=1)
            action_name = parts[0] if parts else ""
            args_str = parts[1] if len(parts) > 1 else ""
            action_args = self._parse_args(args_str)
            return InputAction(
                input_type=InputType.COMMAND,
                raw_input=raw_input,
                action_name=action_name,
                action_args=action_args,
                source_panel=source_panel,
            )
        if stripped in ("y", "yes", "ok"):
            return InputAction(
                input_type=InputType.CONFIRM,
                raw_input=raw_input,
                action_name="confirm",
                action_args={"value": True},
                source_panel=source_panel,
            )
        if stripped in ("n", "no"):
            return InputAction(
                input_type=InputType.CONFIRM,
                raw_input=raw_input,
                action_name="confirm",
                action_args={"value": False},
                source_panel=source_panel,
            )
        return InputAction(
            input_type=InputType.VALUE,
            raw_input=raw_input,
            action_name="input",
            action_args={"value": raw_input},
            source_panel=source_panel,
        )

    def _parse_args(self, args_str: str) -> dict[str, str]:
        args = {}
        parts = args_str.split()
        i = 0
        while i < len(parts):
            if parts[i].startswith("--") and i + 1 < len(parts):
                key = parts[i][2:]
                args[key] = parts[i + 1]
                i += 2
            else:
                i += 1
        return args

    def create_select_action(self, options: list[str], selected: int = 0) -> InputAction:
        """创建选择行动(用于面板上的交互元素)。"""
        return InputAction(
            input_type=InputType.SELECT,
            raw_input=f"select:{selected}",
            action_name="select",
            action_args={"options": options, "selected": selected},
        )

    def create_navigate_action(self, target: str) -> InputAction:
        """创建导航行动。"""
        return InputAction(
            input_type=InputType.NAVIGATE,
            raw_input=f"nav:{target}",
            action_name="navigate",
            action_args={"target": target},
        )

    @property
    def history(self) -> list[InputAction]:
        return list(self._history)

    @property
    def stats(self) -> dict[str, Any]:
        return {
            "inputs_processed": len(self._history),
            "handlers_registered": len(self._handlers),
            "success_rate": (
                sum(1 for r in self._results if r.success) / len(self._results)
                if self._results else 0.0
            ),
        }
