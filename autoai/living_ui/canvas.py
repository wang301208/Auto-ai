from __future__ import annotations

import time
import logging
from dataclasses import dataclass, field
from typing import Any
from enum import Enum

logger = logging.getLogger(__name__)


class CellStyle(Enum):
    NORMAL = "normal"
    BOLD = "bold"
    DIM = "dim"
    HIGHLIGHT = "highlight"
    ERROR = "error"
    SUCCESS = "success"
    WARNING = "warning"
    INFO = "info"


@dataclass
class Cell:
    """画布上的一个单元格。"""
    content: str = " "
    style: CellStyle = CellStyle.NORMAL
    fg: str = ""
    bg: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def render(self) -> str:
        style_map = {
            CellStyle.BOLD: "\033[1m",
            CellStyle.DIM: "\033[2m",
            CellStyle.HIGHLIGHT: "\033[7m",
            CellStyle.ERROR: "\033[31m",
            CellStyle.SUCCESS: "\033[32m",
            CellStyle.WARNING: "\033[33m",
            CellStyle.INFO: "\033[36m",
        }
        prefix = style_map.get(self.style, "")
        reset = "\033[0m" if prefix else ""
        return f"{prefix}{self.content}{reset}"


@dataclass
class Frame:
    """一帧画面: Agent某一时刻的思维可视化。"""
    cells: list[list[Cell]] = field(default_factory=list)
    width: int = 80
    height: int = 24
    timestamp: float = field(default_factory=time.time)
    frame_id: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def blank(cls, width: int = 80, height: int = 24) -> "Frame":
        cells = [[Cell() for _ in range(width)] for _ in range(height)]
        return cls(cells=cells, width=width, height=height)

    def set_cell(self, row: int, col: int, content: str, style: CellStyle = CellStyle.NORMAL) -> None:
        if 0 <= row < self.height and 0 <= col < self.width:
            self.cells[row][col] = Cell(content=content, style=style)

    def write_line(self, row: int, text: str, col: int = 0, style: CellStyle = CellStyle.NORMAL) -> None:
        for i, ch in enumerate(text):
            if col + i < self.width:
                self.set_cell(row, col + i, ch, style)

    def write_centered(self, row: int, text: str, style: CellStyle = CellStyle.NORMAL) -> None:
        col = max(0, (self.width - len(text)) // 2)
        self.write_line(row, text, col, style)

    def render(self) -> str:
        lines = []
        for row in self.cells:
            line = "".join(c.render() for c in row)
            lines.append(line)
        return "\n".join(lines)

    def diff(self, other: "Frame") -> list[tuple[int, int, Cell, Cell]]:
        changes = []
        min_h = min(self.height, other.height)
        min_w = min(self.width, other.width)
        for r in range(min_h):
            for c in range(min_w):
                if self.cells[r][c].content != other.cells[r][c].content:
                    changes.append((r, c, self.cells[r][c], other.cells[r][c]))
        return changes


class LivingCanvas:
    """活画布: Agent自渲染的虚拟终端。

    不是人画UI，是Agent根据自身状态、任务、数据
    在每一帧"涌现"出界面。
    """

    def __init__(self, width: int = 80, height: int = 24):
        self.width = width
        self.height = height
        self._current = Frame.blank(width, height)
        self._history: list[Frame] = []
        self._frame_counter = 0
        self._renderers: list[Any] = []

    def add_renderer(self, renderer: Any) -> None:
        self._renderers.append(renderer)

    def think_frame(self, context: dict[str, Any] | None = None) -> Frame:
        """Agent思考一帧: 根据上下文涌现界面。"""
        context = context or {}
        frame = Frame.blank(self.width, self.height)
        frame.frame_id = self._frame_counter
        self._frame_counter += 1
        for renderer in self._renderers:
            try:
                renderer.render(frame, context)
            except Exception as e:
                logger.debug(f"渲染器异常(非阻塞): {e}")
        self._history.append(self._current)
        if len(self._history) > 100:
            self._history = self._history[-100:]
        self._current = frame
        return frame

    def render(self) -> str:
        return self._current.render()

    @property
    def current_frame(self) -> Frame:
        return self._current

    @property
    def frame_count(self) -> int:
        return self._frame_counter

    def draw_border(self, frame: Frame, row: int, col: int, w: int, h: int, title: str = "") -> None:
        """在帧上画一个带标题的边框。"""
        if row < 0 or col < 0 or row + h > frame.height or col + w > frame.width:
            return
        frame.set_cell(row, col, "+")
        frame.set_cell(row, col + w - 1, "+")
        frame.set_cell(row + h - 1, col, "+")
        frame.set_cell(row + h - 1, col + w - 1, "+")
        for c in range(1, w - 1):
            frame.set_cell(row, col + c, "-")
            frame.set_cell(row + h - 1, col + c, "-")
        for r in range(1, h - 1):
            frame.set_cell(row + r, col, "|")
            frame.set_cell(row + r, col + w - 1, "|")
        if title:
            frame.write_line(row, f"| {title}", col + 1)

    @property
    def stats(self) -> dict[str, Any]:
        return {
            "width": self.width,
            "height": self.height,
            "frames_rendered": self._frame_counter,
            "renderers": len(self._renderers),
        }
