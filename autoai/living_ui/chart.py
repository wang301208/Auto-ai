from __future__ import annotations

import time
import logging
from dataclasses import dataclass, field
from typing import Any
from enum import Enum

logger = logging.getLogger(__name__)


class ChartType(Enum):
    BAR = "bar"
    SPARKLINE = "sparkline"
    PIE_TEXT = "pie_text"
    TABLE = "table"
    GAUGE = "gauge"
    TREND = "trend"
    HEATMAP_TEXT = "heatmap_text"
    NONE = "none"


@dataclass
class ChartSpec:
    chart_type: ChartType
    title: str = ""
    data: Any = None
    width: int = 40
    height: int = 10
    options: dict[str, Any] = field(default_factory=dict)

    def render_text(self) -> list[str]:
        """渲染为文本行(终端输出)。"""
        renderer = {
            ChartType.BAR: self._render_bar,
            ChartType.SPARKLINE: self._render_sparkline,
            ChartType.GAUGE: self._render_gauge,
            ChartType.TABLE: self._render_table,
            ChartType.PIE_TEXT: self._render_pie,
            ChartType.TREND: self._render_trend,
        }.get(self.chart_type, lambda: [str(self.data)])
        return renderer()

    def _render_bar(self) -> list[str]:
        if not isinstance(self.data, dict):
            return [str(self.data)]
        lines = []
        max_val = max(self.data.values()) if self.data else 1
        bar_width = self.width - 12
        for label, value in self.data.items():
            bar_len = int((value / max_val) * bar_width) if max_val > 0 else 0
            bar = "#" * bar_len
            lines.append(f"  {label:<8s} |{bar:<{bar_width}s}| {value}")
        return lines

    def _render_sparkline(self) -> list[str]:
        if not isinstance(self.data, list):
            return [str(self.data)]
        chars = "_`'-.,:;=+*#%@"
        max_v = max(self.data) if self.data else 1
        min_v = min(self.data) if self.data else 0
        rng = max_v - min_v if max_v != min_v else 1
        spark = ""
        for v in self.data:
            idx = int((v - min_v) / rng * (len(chars) - 1))
            spark += chars[min(idx, len(chars) - 1)]
        return [f"  {spark}"]

    def _render_gauge(self) -> list[str]:
        value = self.data if isinstance(self.data, (int, float)) else 0.5
        value = max(0.0, min(1.0, value))
        filled = int(value * (self.width - 4))
        empty = self.width - 4 - filled
        bar = "=" * filled + "-" * empty
        pct = f"{value * 100:.0f}%"
        return [f"  [{bar}] {pct}"]

    def _render_table(self) -> list[str]:
        if not isinstance(self.data, list):
            return [str(self.data)]
        lines = []
        for row in self.data[:self.height - 1]:
            if isinstance(row, dict):
                lines.append("  " + " | ".join(str(v) for v in row.values()))
            else:
                lines.append(f"  {row}")
        return lines

    def _render_pie(self) -> list[str]:
        if not isinstance(self.data, dict):
            return [str(self.data)]
        total = sum(self.data.values()) if self.data else 1
        lines = []
        for label, value in self.data.items():
            pct = value / total * 100 if total > 0 else 0
            bar_len = int(pct / 2)
            lines.append(f"  {label:<8s} {'#' * bar_len:<25s} {pct:.1f}%")
        return lines

    def _render_trend(self) -> list[str]:
        if not isinstance(self.data, list) or len(self.data) < 2:
            return [str(self.data)]
        latest = self.data[-1]
        prev = self.data[-2]
        if isinstance(latest, (int, float)) and isinstance(prev, (int, float)):
            delta = latest - prev
            arrow = "+" if delta >= 0 else "-"
            return [f"  {latest} ({arrow}{abs(delta):.2f})"]
        return [f"  {latest}"]


class ChartSelector:
    """图表自选器: Agent根据数据特征自动选择最佳可视化。"""

    def __init__(self):
        self._selections: list[tuple[ChartType, str]] = []

    def select(self, data: Any, context: dict[str, Any] | None = None) -> ChartSpec:
        """根据数据特征自动选择图表类型。"""
        chart_type = self._infer_chart_type(data)
        title = context.get("title", "") if context else ""
        self._selections.append((chart_type, title))
        return ChartSpec(chart_type=chart_type, title=title, data=data)

    def _infer_chart_type(self, data: Any) -> ChartType:
        if isinstance(data, dict):
            values = list(data.values())
            if all(isinstance(v, (int, float)) for v in values):
                if len(data) <= 6:
                    return ChartType.PIE_TEXT
                return ChartType.BAR
            return ChartType.TABLE
        if isinstance(data, list):
            if len(data) == 0:
                return ChartType.NONE
            if all(isinstance(v, (int, float)) for v in data):
                if len(data) <= 20:
                    return ChartType.SPARKLINE
                return ChartType.TREND
            if isinstance(data[0], dict):
                return ChartType.TABLE
            return ChartType.TABLE
        if isinstance(data, (int, float)):
            if 0 <= data <= 1:
                return ChartType.GAUGE
            return ChartType.GAUGE
        return ChartType.TABLE

    @property
    def stats(self) -> dict[str, Any]:
        return {
            "selections_made": len(self._selections),
            "type_distribution": {
                ct.value: sum(1 for t, _ in self._selections if t == ct)
                for ct in ChartType
            },
        }
