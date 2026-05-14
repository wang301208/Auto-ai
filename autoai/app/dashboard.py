"""Terminal Dashboard — pure Rich TUI system observation dashboard.

Replaces any web-based dashboard. All rendering happens in the terminal.

Layout (4 quadrants):
  ┌─────────────────┬─────────────────┐
  │  System Overview │  Model Router   │
  │  (agents/status) │  (models/cost)  │
  ├─────────────────┼─────────────────┤
  │  Task Scheduler  │  Governance     │
  │  (queue/phases)  │  (audit/policy) │
  └─────────────────┴─────────────────┘

  + Bottom bar: Live Stream + hotkeys

Usage:
    dashboard = TerminalDashboard(system)
    dashboard.run()  # 块ing

Hotkeys:
    q  - Quit
    r  - Refresh now
    1-4 - Focus quadrant
"""

from __future__ import annotations

import time
from collections import deque
from datetime import datetime
from typing import Any

from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.layout import Layout
from rich.align import Align
from rich import box


class TerminalDashboard:
    """用于监控多代理系统的纯终端仪表盘。"""

    def __init__(
        self,
        system: Any | None = None,
        refresh_rate: float = 1.0,
        max_log: int = 50,
    ) -> None:
        self._system = system
        self._refresh_rate = refresh_rate
        self._console = Console()
        self._start_time = time.time()
        self._event_log: deque[dict] = deque(maxlen=max_log)
        self._focused: int = 0

    def attach_system(self, system: Any) -> None:
        self._system = system

    def log_event(self, message: str, level: str = "info") -> None:
        self._event_log.append({
            "time": datetime.now().strftime("%H:%M:%S"),
            "level": level,
            "message": message[:80],
        })

    def _build_overview(self) -> Panel:
        table = Table(show_header=True, header_style="bold", expand=True, box=box.SIMPLE)
        table.add_column("Agent", width=16)
        table.add_column("Role", width=12)
        table.add_column("Status", width=10)
        table.add_column("Tasks", width=8, justify="right")
        table.add_column("Budget", width=10)

        if self._system and hasattr(self._system, "agent_factory") and self._system.agent_factory:
            agents_data = self._system.agent_factory.created_agents
            if isinstance(agents_data, dict):
                for aid, info in agents_data.items():
                    role = info.get("role", "?") if isinstance(info, dict) else "?"
                    table.add_row(aid[:16], str(role)[:12], "[green]active[/]", "-", "-")
            elif isinstance(agents_data, list):
                for aid in agents_data:
                    table.add_row(str(aid)[:16], "?", "[green]active[/]", "-", "-")

        if not table.rows:
            table.add_row("[dim]No agents[/]", "", "", "", "")

        uptime = int(time.time() - self._start_time)
        h, r = divmod(uptime, 3600)
        m, s = divmod(r, 60)

        return Panel(
            table,
            title=f"[bold]System Overview[/]  [dim]uptime {h}h{m:02d}m{s:02d}s[/]",
            border_style="blue",
        )

    def _build_model_panel(self) -> Panel:
        table = Table(show_header=True, header_style="bold", expand=True, box=box.SIMPLE)
        table.add_column("Model", width=24)
        table.add_column("Provider", width=10)
        table.add_column("Tier", width=8)
        table.add_column("Cost/1k", width=8, justify="right")
        table.add_column("Local", width=5)

        if self._system and self._system.model_registry:
            models = self._system.model_registry.list_models()
            for m in models[:12]:
                local = "[green]Y[/]" if m.is_local else "[dim]N[/]"
                cost = f"${m.prompt_token_cost_per_1k:.4f}" if m.prompt_token_cost_per_1k else "[dim]free[/]"
                table.add_row(
                    m.model_id[:24],
                    m.provider_name[:10],
                    m.tier.value,
                    cost,
                    local,
                )

        if not table.rows:
            table.add_row("[dim]No models registered[/]", "", "", "", "")

        daily_remaining = ""
        if self._system and self._system.model_router:
            daily_remaining = f"  [dim]budget: ${self._system.model_router.policy.daily_remaining:.2f}[/]"

        return Panel(
            table,
            title=f"[bold]Model Router[/]{daily_remaining}",
            border_style="cyan",
        )

    def _build_scheduler_panel(self) -> Panel:
        table = Table(show_header=True, header_style="bold", expand=True, box=box.SIMPLE)
        table.add_column("Task", width=20)
        table.add_column("Category", width=10)
        table.add_column("Status", width=12)
        table.add_column("Agent", width=12)
        table.add_column("Phase", width=8, justify="right")

        if self._system and self._system.task_scheduler:
            for tid, task in list(self._system.task_scheduler.completed_tasks.items())[:8]:
                table.add_row(
                    task.name[:20] or tid[:12],
                    task.category.value,
                    task.status.value,
                    (task.assigned_agent or "-")[:12],
                    f"{task.current_phase_index}/{len(task.phases)}" if task.phases else "-",
                )
            pending = self._system.task_scheduler.pending_count
            stats = self._system.task_scheduler.stats
            footer = (
                f"[dim]pending:{pending} "
                f"dispatched:{stats.total_dispatched} "
                f"ok:{stats.total_succeeded} "
                f"fail:{stats.total_failed}[/]"
            )
        else:
            footer = "[dim]No scheduler[/]"

        if not table.rows:
            table.add_row("[dim]No tasks yet[/]", "", "", "", "")

        content = table
        return Panel(content, title="[bold]Task Scheduler[/]", border_style="green", subtitle=footer)

    def _build_governance_panel(self) -> Panel:
        lines = []

        if self._system and self._system.governance_gate:
            gate = self._system.governance_gate
            lines.append("Mode: [bold green]AUTONOMOUS[/] (boundary-managed)")
            lines.append(f"Hard boundaries: {', '.join(sorted(gate.hard_boundaries))}")
            if gate.boundary and gate.boundary.constraints:
                bm = gate.boundary
                lines.append(f"Autonomy: L{bm.autonomy.level} ({bm.autonomy.level.name})")
                lines.append(f"Breaks: {bm.stats()['break_count']}")

        if self._system and self._system.policy_evolver:
            lines.append("Policy evolver: [green]active[/]")

        if self._system and self._system.health_monitor:
            all_health = self._system.health_monitor.get_all_status()
            healthy = sum(1 for s in all_health.values() if str(s) == "healthy" or (isinstance(s, dict) and s.get("status") == "healthy"))
            total = len(all_health) if all_health else 0
            lines.append(f"Health: [green]{healthy}[/]/{total} agents healthy")

        if self._system and self._system.checkpoint_mgr:
            lines.append("Checkpoints: [green]enabled[/]")

        if not lines:
            lines.append("[dim]Not initialized[/]")

        content = "\n".join(lines)
        return Panel(content, title="[bold]Governance[/]", border_style="yellow")

    def _build_event_bar(self) -> Panel:
        entries = list(self._event_log)[-5:]
        if not entries:
            return Panel("[dim]No events[/]", title="Events", border_style="dim", height=3)

        lines = []
        for e in entries:
            level_color = {"info": "dim", "warn": "yellow", "error": "red"}.get(e["level"], "dim")
            lines.append(f"[{level_color}]{e['time']} {e['message']}[/]")

        return Panel("\n".join(lines), title="Events", border_style="dim", height=3)

    def _build_hotkey_bar(self) -> Text:
        return Text("  [q]uit  [r]efresh  [1-4]focus  ", style="dim")

    def render(self) -> Layout:
        layout = Layout()
        layout.split_column(
            Layout(name="top", ratio=1),
            Layout(name="bottom", ratio=1),
            Layout(self._build_event_bar(), size=4),
        )
        layout["top"].split_row(
            Layout(self._build_overview()),
            Layout(self._build_model_panel()),
        )
        layout["bottom"].split_row(
            Layout(self._build_scheduler_panel()),
            Layout(self._build_governance_panel()),
        )
        return layout

    def run(self) -> None:
        """启动实时仪表盘（阻塞）。按q退出。"""
        with Live(
            self.render(),
            console=self._console,
            refresh_per_second=int(1 / self._refresh_rate),
            screen=True,
        ) as live:
            try:
                while True:
                    time.sleep(self._refresh_rate)
                    live.update(self.render())
            except KeyboardInterrupt:
                pass

    def render_once(self) -> None:
        """渲染单帧（非阻塞）。"""
        self._console.print(self.render())


def create_dashboard(system: Any) -> TerminalDashboard:
    """工厂：创建绑定到MultiAgentSystem的TerminalDashboard。"""
    return TerminalDashboard(system=system)


__all__ = ["TerminalDashboard", "create_dashboard"]
