"""TUI Observation Window for AutoAI Self-Evolving Agent.

A read-only terminal dashboard using Rich Live display that shows:
- Agent status and autonomous mode indicator
- Task queue progress
- Command execution log
- Self-evolution history
- Boundary alerts (budget, sandbox, architecture)
- Performance metrics
- Live streaming think/exec tokens

This is an OBSERVATION window, not a control panel.
The agent runs autonomously; the user only watches.
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
from rich.columns import Columns
from rich.progress import Progress, BarColumn, TextColumn

from autoai.core.planning.schema import TaskStatus


class TUIObservationWindow:
    """Terminal observation window for monitoring autonomous agent execution."""

    def __init__(
        self,
        agent_name: str = "AutoAI",
        max_log_entries: int = 50,
        max_evolution_entries: int = 20,
        refresh_rate: float = 0.5,
    ):
        self.agent_name = agent_name
        self._refresh_rate = refresh_rate
        self._console = Console()

        self._start_time = time.time()
        self._total_tasks_done = 0
        self._total_issues_fixed = 0
        self._autonomous = False
        self._cycle_count = 0

        self._tasks: list[dict] = []
        self._command_log: deque[dict] = deque(maxlen=max_log_entries)
        self._evolution_log: deque[dict] = deque(maxlen=max_evolution_entries)
        self._boundaries: dict[str, str] = {}
        self._budget_used: float = 0.0
        self._budget_total: float = 0.0

        self._stream_buffer: Any = None
        self._think_lines: deque[str] = deque(maxlen=100)
        self._exec_lines: deque[str] = deque(maxlen=100)
        self._current_think: str = ""
        self._current_exec: str = ""
        self._stream_stats_display: str = ""

    def attach_stream_buffer(self, buffer: Any) -> None:
        self._stream_buffer = buffer

    def on_stream_event(self, event: Any) -> None:
        from autoai.llm.model_router.streaming import StreamEventType
        if event.type == StreamEventType.THINK_TOKEN:
            self._current_think += event.content
        elif event.type == StreamEventType.THINK_END:
            if self._current_think:
                self._think_lines.append(self._current_think)
            self._current_think = ""
            if event.completion_tokens > 0:
                self._stream_stats_display = (
                    f"tokens: {event.prompt_tokens}+{event.completion_tokens} "
                    f"cost: ${event.total_cost:.6f}"
                )
        elif event.type == StreamEventType.EXEC_TOKEN:
            self._current_exec += event.content
        elif event.type == StreamEventType.EXEC_END:
            if self._current_exec:
                self._exec_lines.append(self._current_exec)
            self._current_exec = ""

    def _flush_stream_buffer(self) -> None:
        if self._stream_buffer:
            events = self._stream_buffer.recent_events
            self._stream_buffer.clear()
            for event in events:
                self.on_stream_event(event)

    def set_autonomous(self, enabled: bool) -> None:
        self._autonomous = enabled

    def update_tasks(self, task_queue: list, completed: list, current: Any = None) -> None:
        self._tasks = []
        for t in task_queue:
            self._tasks.append({
                "objective": t.objective[:60],
                "type": str(t.type),
                "priority": t.priority,
                "status": str(t.context.status) if hasattr(t, "context") else "?",
            })
        if current is not None:
            self._tasks.insert(0, {
                "objective": current.objective[:60],
                "type": str(current.type),
                "priority": current.priority,
                "status": ">> IN_PROGRESS",
            })
        self._total_tasks_done = len(completed)

    def log_command(self, command: str, result_summary: str, duration: float = 0.0) -> None:
        entry = {
            "time": datetime.now().strftime("%H:%M:%S"),
            "command": command[:30],
            "result": result_summary[:40],
            "duration": f"{duration:.1f}s" if duration else "-",
        }
        self._command_log.appendleft(entry)

    def log_evolution(self, message: str) -> None:
        entry = {
            "time": datetime.now().strftime("%H:%M:%S"),
            "message": message[:80],
        }
        self._evolution_log.appendleft(entry)
        self._total_issues_fixed += 1

    def update_boundaries(self, budget_ok: bool, sandbox_ok: bool, arch_ok: bool) -> None:
        self._boundaries = {
            "Budget": "[green]OK[/]" if budget_ok else "[red]ALERT[/]",
            "Sandbox": "[green]OK[/]" if sandbox_ok else "[red]ALERT[/]",
            "Architecture": "[green]OK[/]" if arch_ok else "[red]ALERT[/]",
        }

    def update_budget(self, used: float, total: float) -> None:
        self._budget_used = used
        self._budget_total = total

    def increment_cycle(self) -> None:
        self._cycle_count += 1

    def _build_header(self) -> Panel:
        uptime = time.time() - self._start_time
        hours, remainder = divmod(int(uptime), 3600)
        minutes, seconds = divmod(remainder, 60)
        uptime_str = f"{hours}h{minutes:02d}m{seconds:02d}s"

        mode = "[bold green]AUTONOMOUS[/]" if self._autonomous else "[yellow]MANUAL[/]"

        budget_pct = (
            f"{self._budget_used/self._budget_total*100:.1f}%"
            if self._budget_total > 0
            else "N/A"
        )

        header = Text()
        header.append(f" {self.agent_name} ", style="bold white on blue")
        header.append(f"  Mode: ")
        header.append(f"{mode}")
        header.append(f"  Uptime: {uptime_str}")
        header.append(f"  Cycle: {self._cycle_count}")
        header.append(f"  Tasks done: {self._total_tasks_done}")
        header.append(f"  Self-fixed: {self._total_issues_fixed}")
        header.append(f"  Budget: {budget_pct}")

        return Panel(header, title="AutoAI Self-Evolving", border_style="blue")

    def _build_task_table(self) -> Panel:
        table = Table(show_header=True, header_style="bold", expand=True)
        table.add_column("Status", width=16)
        table.add_column("Type", width=10)
        table.add_column("Priority", width=8, justify="right")
        table.add_column("Objective")

        for t in self._tasks[:10]:
            status = t["status"]
            if "IN_PROGRESS" in status:
                status_style = "bold yellow"
            elif status == str(TaskStatus.DONE):
                status_style = "green"
            elif status == str(TaskStatus.READY):
                status_style = "cyan"
            else:
                status_style = "dim"
            table.add_row(
                f"[{status_style}]{status}[/]",
                t["type"],
                str(t["priority"]),
                t["objective"],
            )

        if not self._tasks:
            table.add_row("[dim]No tasks[/]", "", "", "")

        return Panel(table, title=f"Tasks ({len(self._tasks)} pending)", border_style="cyan")

    def _build_command_log(self) -> Panel:
        table = Table(show_header=True, header_style="bold", expand=True)
        table.add_column("Time", width=8)
        table.add_column("Command", width=30)
        table.add_column("Result", width=40)
        table.add_column("Dur", width=6)

        for entry in list(self._command_log)[:8]:
            table.add_row(
                entry["time"],
                entry["command"],
                entry["result"],
                entry["duration"],
            )

        if not self._command_log:
            table.add_row("[dim]...[/]", "", "", "")

        return Panel(table, title="Command Log", border_style="green")

    def _build_evolution_log(self) -> Panel:
        lines = []
        for entry in list(self._evolution_log)[:8]:
            lines.append(f"[dim]{entry['time']}[/] {entry['message']}")

        if not lines:
            lines.append("[dim]No self-evolution events yet[/]")

        content = "\n".join(lines)
        return Panel(content, title="Self-Evolution Log", border_style="magenta")

    def _build_boundaries(self) -> Panel:
        parts = []
        for name, status in self._boundaries.items():
            parts.append(f"{name}: {status}")

        if not parts:
            parts.append("[dim]Not initialized[/]")

        content = "  ".join(parts)
        return Panel(content, title="Boundaries", border_style="yellow")

    def _build_stream_panel(self) -> Panel:
        self._flush_stream_buffer()
        lines = []
        for think in list(self._think_lines)[-3:]:
            snippet = think[:200] + ("..." if len(think) > 200 else "")
            lines.append(f"[cyan]THINK:[/] {snippet}")
        if self._current_think:
            snippet = self._current_think[-200:]
            lines.append(f"[bold cyan]>> THINK:[/] {snippet}")
        for exec_txt in list(self._exec_lines)[-3:]:
            snippet = exec_txt[:200] + ("..." if len(exec_txt) > 200 else "")
            lines.append(f"[green]EXEC:[/] {snippet}")
        if self._current_exec:
            snippet = self._current_exec[-200:]
            lines.append(f"[bold green]>> EXEC:[/] {snippet}")
        if self._stream_stats_display:
            lines.append(f"[dim]{self._stream_stats_display}[/]")
        if not lines:
            lines.append("[dim]No streaming output yet[/]")
        content = "\n".join(lines)
        return Panel(content, title="Live Stream", border_style="bright_blue")

    def render(self) -> Layout:
        layout = Layout()
        layout.split_column(
            Layout(self._build_header(), size=3),
            Layout(name="body"),
            Layout(self._build_boundaries(), size=3),
        )
        layout["body"].split_row(
            Layout(name="left"),
            Layout(name="right"),
        )
        layout["left"].split_column(
            Layout(self._build_task_table()),
            Layout(self._build_command_log()),
        )
        layout["right"].split_column(
            Layout(self._build_stream_panel()),
            Layout(self._build_evolution_log()),
        )
        return layout

    def run(self) -> None:
        """Start the live TUI display (blocking)."""
        with Live(
            self.render(),
            console=self._console,
            refresh_per_second=int(1 / self._refresh_rate),
            screen=True,
        ) as live:
            while True:
                time.sleep(self._refresh_rate)
                live.update(self.render())

    def render_once(self) -> None:
        """Render a single frame (non-blocking, for integration into external loops)."""
        self._console.print(self.render())


def create_tui_for_agent(agent: Any) -> TUIObservationWindow:
    """Factory: create a TUI window bound to an AsyncAgent."""
    window = TUIObservationWindow(agent_name=agent.ai_config.ai_name)
    window.set_autonomous(agent.autonomous_mode)
    return window
