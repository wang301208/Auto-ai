from __future__ import annotations

import time
import logging
from dataclasses import dataclass, field
from typing import Any
from enum import Enum

logger = logging.getLogger(__name__)


class PanelType(Enum):
    STATUS = "status"
    METRICS = "metrics"
    LOG = "log"
    CHART = "chart"
    TABLE = "table"
    TREE = "tree"
    INTERACTIVE = "interactive"
    ALERT = "alert"
    CUSTOM = "custom"


@dataclass
class EmergentPanel:
    """涌现的面板: 不是设计师画的，是Agent根据数据长出来的。"""
    panel_id: str
    panel_type: PanelType
    title: str = ""
    x: int = 0
    y: int = 0
    width: int = 40
    height: int = 10
    priority: float = 0.5
    data: Any = None
    content_lines: list[str] = field(default_factory=list)
    born_at: float = field(default_factory=time.time)
    lifetime_seconds: float = 0.0
    refreshed_count: int = 0

    @property
    def is_expired(self) -> bool:
        if self.lifetime_seconds <= 0:
            return False
        return (time.time() - self.born_at) > self.lifetime_seconds

    @property
    def age(self) -> float:
        return time.time() - self.born_at

    def refresh(self, new_data: Any = None, new_lines: list[str] | None = None) -> None:
        if new_data is not None:
            self.data = new_data
        if new_lines is not None:
            self.content_lines = new_lines
        self.refreshed_count += 1


class PanelEmerger:
    """面板涌现器: 根据数据/任务自动涌现面板。"""

    def __init__(self):
        self._panels: dict[str, EmergentPanel] = {}
        self._emergence_rules: list[dict] = []
        self._panel_counter = 0
        self._setup_default_rules()

    def _setup_default_rules(self) -> None:
        self._emergence_rules = [
            {"trigger": "has_errors", "panel_type": PanelType.ALERT, "title": "ERRORS", "priority": 0.9},
            {"trigger": "has_metrics", "panel_type": PanelType.METRICS, "title": "METRICS", "priority": 0.7},
            {"trigger": "has_tasks", "panel_type": PanelType.STATUS, "title": "TASKS", "priority": 0.6},
            {"trigger": "has_data_table", "panel_type": PanelType.TABLE, "title": "DATA", "priority": 0.5},
            {"trigger": "has_log", "panel_type": PanelType.LOG, "title": "LOG", "priority": 0.3},
        ]

    def emerge_from_context(self, context: dict[str, Any]) -> list[EmergentPanel]:
        """根据上下文自动涌现面板。"""
        emerged = []
        errors = context.get("errors", [])
        metrics = context.get("metrics", {})
        tasks = context.get("tasks", [])
        data = context.get("data", None)
        logs = context.get("logs", [])
        if errors:
            panel = self._create_panel(
                PanelType.ALERT, "ERRORS",
                content_lines=[str(e) for e in errors[:5]],
                priority=0.9, lifetime=30,
            )
            emerged.append(panel)
        if metrics:
            lines = [f"  {k}: {v}" for k, v in metrics.items()]
            panel = self._create_panel(
                PanelType.METRICS, "METRICS",
                content_lines=lines, priority=0.7,
            )
            emerged.append(panel)
        if tasks:
            lines = [f"  [{t.get('status','?')}] {t.get('name','?')}" for t in tasks[:8]]
            panel = self._create_panel(
                PanelType.STATUS, "TASKS",
                content_lines=lines, priority=0.6,
            )
            emerged.append(panel)
        if data and isinstance(data, (list, dict)):
            if isinstance(data, list) and len(data) > 0 and isinstance(data[0], dict):
                keys = list(data[0].keys())[:5]
                lines = ["  " + " | ".join(str(d.get(k, "")) for k in keys) for d in data[:5]]
                panel = self._create_panel(
                    PanelType.TABLE, "DATA",
                    content_lines=lines, priority=0.5,
                )
                emerged.append(panel)
        if logs:
            panel = self._create_panel(
                PanelType.LOG, "LOG",
                content_lines=[str(l) for l in logs[-5:]], priority=0.3,
            )
            emerged.append(panel)
        return emerged

    def _create_panel(self, panel_type: PanelType, title: str,
                      content_lines: list[str] | None = None,
                      priority: float = 0.5, lifetime: float = 0) -> EmergentPanel:
        self._panel_counter += 1
        panel = EmergentPanel(
            panel_id=f"panel-{self._panel_counter}",
            panel_type=panel_type,
            title=title,
            content_lines=content_lines or [],
            priority=priority,
            lifetime_seconds=lifetime,
        )
        self._panels[panel.panel_id] = panel
        logger.debug(f"面板涌现: {panel.panel_id} [{panel_type.value}] {title}")
        return panel

    def layout(self, canvas_width: int = 80, canvas_height: int = 24) -> list[EmergentPanel]:
        """自动布局: 根据面板优先级和数量分配画布空间。"""
        active = [p for p in self._panels.values() if not p.is_expired]
        active.sort(key=lambda p: p.priority, reverse=True)
        if not active:
            return []
        cols = min(3, len(active))
        rows = (len(active) + cols - 1) // cols
        panel_w = canvas_width // cols
        panel_h = max(5, canvas_height // rows)
        for i, panel in enumerate(active):
            col_idx = i % cols
            row_idx = i // cols
            panel.x = col_idx * panel_w
            panel.y = row_idx * panel_h
            panel.width = panel_w - 1
            panel.height = panel_h - 1
        return active

    def get_active_panels(self) -> list[EmergentPanel]:
        return [p for p in self._panels.values() if not p.is_expired]

    def remove_expired(self) -> int:
        expired = [pid for pid, p in self._panels.items() if p.is_expired]
        for pid in expired:
            del self._panels[pid]
        return len(expired)

    @property
    def stats(self) -> dict[str, Any]:
        return {
            "total_panels": len(self._panels),
            "active_panels": len(self.get_active_panels()),
            "panel_types": list(set(p.panel_type.value for p in self._panels.values())),
        }
