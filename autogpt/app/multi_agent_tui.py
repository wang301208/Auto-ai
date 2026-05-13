"""Multi-Agent TUI Observation Window.

Extends the single-agent TUIObservationWindow to display multiple agents
in a tabbed/split terminal layout:

  - Overview tab: all agents at a glance (status, tasks, budget)
  - Per-agent detail: task queue, command log, evolution log
  - Workflow tab: DAG visualization, task assignment, agent utilization
  - Communication tab: inter-agent message flow

Uses Rich Layout with keyboard tab switching (via readchar if available).
"""

from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.layout import Layout
from rich.tree import Tree

from autogpt.core.planning.schema import TaskStatus


@dataclass
class AgentViewData:
    """Data snapshot for one agent in the multi-agent view."""

    agent_id: str
    name: str = ""
    role: str = ""
    autonomous: bool = False
    cycle_count: int = 0
    tasks_done: int = 0
    tasks_pending: int = 0
    issues_fixed: int = 0
    budget_used: float = 0.0
    budget_total: float = 0.0
    current_task: str = ""
    status: str = "idle"
    pending_messages: int = 0


@dataclass
class WorkflowViewData:
    """Data snapshot for workflow orchestration."""

    workflow_id: str = ""
    workflow_name: str = ""
    total_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    running_tasks: int = 0
    agent_assignments: dict[str, str] = field(default_factory=dict)
    task_states: dict[str, str] = field(default_factory=dict)


@dataclass
class CommViewData:
    """Data snapshot for inter-agent communication."""

    total_direct: int = 0
    total_broadcast: int = 0
    total_requests: int = 0
    total_responses: int = 0
    total_timeouts: int = 0
    active_agents: int = 0
    active_channels: int = 0
    pending_requests: int = 0
    recent_messages: list[dict[str, Any]] = field(default_factory=list)


class MultiAgentTUI:
    """Terminal UI for monitoring multiple autonomous agents."""

    TAB_OVERVIEW = "overview"
    TAB_WORKFLOW = "workflow"
    TAB_COMM = "communication"
    TABS = [TAB_OVERVIEW, TAB_WORKFLOW, TAB_COMM]

    def __init__(
        self,
        max_agents: int = 10,
        max_log_entries: int = 50,
        refresh_rate: float = 0.5,
    ) -> None:
        self._refresh_rate = refresh_rate
        self._console = Console()
        self._start_time = time.time()
        self._current_tab = 0

        self._agents: dict[str, AgentViewData] = {}
        self._command_logs: dict[str, deque[dict]] = {}
        self._evolution_logs: dict[str, deque[dict]] = {}
        self._workflow = WorkflowViewData()
        self._comm = CommViewData()
        self._boundaries: dict[str, str] = {}

        self._max_log = max_log_entries

    def set_active_tab(self, tab_name: str) -> None:
        if tab_name in self.TABS:
            self._current_tab = self.TABS.index(tab_name)

    def cycle_tab(self) -> None:
        self._current_tab = (self._current_tab + 1) % len(self.TABS)

    def update_agent(self, data: AgentViewData) -> None:
        self._agents[data.agent_id] = data

    def remove_agent(self, agent_id: str) -> None:
        self._agents.pop(agent_id, None)
        self._command_logs.pop(agent_id, None)
        self._evolution_logs.pop(agent_id, None)

    def log_command(self, agent_id: str, command: str, result_summary: str, duration: float = 0.0) -> None:
        if agent_id not in self._command_logs:
            self._command_logs[agent_id] = deque(maxlen=self._max_log)
        self._command_logs[agent_id].appendleft({
            "time": datetime.now().strftime("%H:%M:%S"),
            "command": command[:30],
            "result": result_summary[:40],
            "duration": f"{duration:.1f}s" if duration else "-",
        })

    def log_evolution(self, agent_id: str, message: str) -> None:
        if agent_id not in self._evolution_logs:
            self._evolution_logs[agent_id] = deque(maxlen=20)
        self._evolution_logs[agent_id].appendleft({
            "time": datetime.now().strftime("%H:%M:%S"),
            "message": message[:80],
        })

    def update_workflow(self, data: WorkflowViewData) -> None:
        self._workflow = data

    def update_comm(self, data: CommViewData) -> None:
        self._comm = data

    def update_boundaries(self, budget_ok: bool, sandbox_ok: bool, arch_ok: bool) -> None:
        self._boundaries = {
            "Budget": "[green]OK[/]" if budget_ok else "[red]ALERT[/]",
            "Sandbox": "[green]OK[/]" if sandbox_ok else "[red]ALERT[/]",
            "Architecture": "[green]OK[/]" if arch_ok else "[red]ALERT[/]",
        }

    def _build_header(self) -> Panel:
        uptime = time.time() - self._start_time
        hours, remainder = divmod(int(uptime), 3600)
        minutes, seconds = divmod(remainder, 60)
        uptime_str = f"{hours}h{minutes:02d}m{seconds:02d}s"

        tab_names = []
        for i, name in enumerate(self.TABS):
            if i == self._current_tab:
                tab_names.append(f"[bold white on blue] {name} [/]")
            else:
                tab_names.append(f"[dim] {name} [/]")
        tabs_str = " ".join(tab_names)

        header = Text()
        header.append(f" Multi-Agent ", style="bold white on blue")
        header.append(f"  Agents: {len(self._agents)}")
        header.append(f"  Uptime: {uptime_str}")

        return Panel(
            f"{header}\n{tabs_str}",
            title="AutoGPT Multi-Agent Orchestrator",
            border_style="blue",
        )

    def _build_overview(self) -> Layout:
        layout = Layout()
        layout.split_row(Layout(name="agent_list"), Layout(name="agent_detail"))

        agent_list = self._build_agent_list()
        layout["agent_list"].update(Panel(agent_list, title="Agents", border_style="cyan"))

        first_agent_id = next(iter(self._agents), None)
        if first_agent_id:
            detail = self._build_agent_detail(first_agent_id)
        else:
            detail = Panel("[dim]No agents registered[/]", title="Detail", border_style="dim")
        layout["agent_detail"].update(detail)

        return layout

    def _build_agent_list(self) -> Table:
        table = Table(show_header=True, header_style="bold", expand=True)
        table.add_column("ID", width=12)
        table.add_column("Role", width=10)
        table.add_column("Mode", width=10)
        table.add_column("Status", width=10)
        table.add_column("Tasks", width=10, justify="right")
        table.add_column("Budget", width=8, justify="right")
        table.add_column("Msgs", width=5, justify="right")

        for data in self._agents.values():
            mode = "[green]AUTO[/]" if data.autonomous else "[yellow]MAN[/]"
            budget_pct = (
                f"{data.budget_used / data.budget_total * 100:.0f}%"
                if data.budget_total > 0
                else "N/A"
            )
            status_style = {
                "idle": "dim",
                "running": "bold yellow",
                "success": "green",
                "failed": "red",
            }.get(data.status, "white")

            table.add_row(
                data.name[:12] or data.agent_id[:12],
                data.role[:10],
                mode,
                f"[{status_style}]{data.status}[/]",
                f"{data.tasks_done}/{data.tasks_done + data.tasks_pending}",
                budget_pct,
                str(data.pending_messages),
            )

        if not self._agents:
            table.add_row("[dim]No agents[/]", "", "", "", "", "", "")

        return table

    def _build_agent_detail(self, agent_id: str) -> Layout:
        layout = Layout()
        layout.split_column(Layout(name="tasks"), Layout(name="logs"))

        data = self._agents.get(agent_id)
        if data:
            task_info = Text()
            task_info.append(f"Current: {data.current_task or 'None'}\n", style="bold")
            task_info.append(f"Done: {data.tasks_done}  Pending: {data.tasks_pending}  ")
            task_info.append(f"Fixed: {data.issues_fixed}  Cycles: {data.cycle_count}")
            layout["tasks"].update(Panel(task_info, title=f"Tasks: {data.name}", border_style="cyan"))
        else:
            layout["tasks"].update(Panel("[dim]No data[/]", border_style="dim"))

        evo_log = self._evolution_logs.get(agent_id, deque())
        lines = []
        for entry in list(evo_log)[:8]:
            lines.append(f"[dim]{entry['time']}[/] {entry['message']}")
        content = "\n".join(lines) if lines else "[dim]No events[/]"
        layout["logs"].update(Panel(content, title="Evolution Log", border_style="magenta"))

        return layout

    def _build_workflow_view(self) -> Layout:
        layout = Layout()
        layout.split_column(Layout(name="wf_summary"), Layout(name="wf_assignments"))

        wf = self._workflow
        summary = Text()
        summary.append(f"Workflow: {wf.workflow_name or wf.workflow_id or 'None'}\n", style="bold")
        summary.append(f"Tasks: {wf.total_tasks}  ")
        summary.append(f"[green]Done: {wf.completed_tasks}[/]  ")
        summary.append(f"[yellow]Running: {wf.running_tasks}[/]  ")
        summary.append(f"[red]Failed: {wf.failed_tasks}[/]")
        layout["wf_summary"].update(Panel(summary, title="Workflow DAG", border_style="blue"))

        table = Table(show_header=True, header_style="bold", expand=True)
        table.add_column("Task", width=20)
        table.add_column("State", width=10)
        table.add_column("Agent", width=15)

        for task_id, state in wf.task_states.items():
            state_style = {
                "success": "green",
                "running": "bold yellow",
                "failed": "red",
                "pending": "dim",
            }.get(state, "white")
            agent = wf.agent_assignments.get(task_id, "-")
            table.add_row(task_id[:20], f"[{state_style}]{state}[/]", agent[:15])

        if not wf.task_states:
            table.add_row("[dim]No workflow[/]", "", "")

        layout["wf_assignments"].update(Panel(table, title="Task Assignments", border_style="cyan"))

        return layout

    def _build_comm_view(self) -> Layout:
        layout = Layout()
        layout.split_column(Layout(name="comm_stats"), Layout(name="comm_flow"))

        c = self._comm
        stats = Text()
        stats.append(f"Agents: {c.active_agents}  Channels: {c.active_channels}\n", style="bold")
        stats.append(f"Direct: {c.total_direct}  Broadcast: {c.total_broadcast}  ")
        stats.append(f"Requests: {c.total_requests}  Responses: {c.total_responses}  ")
        stats.append(f"Timeouts: {c.total_timeouts}\n")
        stats.append(f"Pending: {c.pending_requests}")
        layout["comm_stats"].update(Panel(stats, title="Communication Stats", border_style="green"))

        table = Table(show_header=True, header_style="bold", expand=True)
        table.add_column("Time", width=8)
        table.add_column("From", width=12)
        table.add_column("To", width=12)
        table.add_column("Type", width=10)
        table.add_column("Summary", width=30)

        for msg in c.recent_messages[:10]:
            table.add_row(
                msg.get("time", ""),
                str(msg.get("from", ""))[:12],
                str(msg.get("to", ""))[:12],
                msg.get("type", ""),
                str(msg.get("summary", ""))[:30],
            )

        if not c.recent_messages:
            table.add_row("[dim]No messages[/]", "", "", "", "")

        layout["comm_flow"].update(Panel(table, title="Message Flow", border_style="yellow"))

        return layout

    def _build_boundaries(self) -> Panel:
        parts = []
        for name, status in self._boundaries.items():
            parts.append(f"{name}: {status}")
        if not parts:
            parts.append("[dim]Not initialized[/]")
        return Panel("  ".join(parts), title="Boundaries", border_style="yellow")

    def render(self) -> Layout:
        layout = Layout()
        layout.split_column(
            Layout(self._build_header(), size=4),
            Layout(name="body"),
            Layout(self._build_boundaries(), size=3),
        )

        tab_name = self.TABS[self._current_tab]
        if tab_name == self.TAB_OVERVIEW:
            layout["body"].update(self._build_overview())
        elif tab_name == self.TAB_WORKFLOW:
            layout["body"].update(self._build_workflow_view())
        elif tab_name == self.TAB_COMM:
            layout["body"].update(self._build_comm_view())

        return layout

    def run(self) -> None:
        """Start the live multi-agent TUI display (blocking)."""
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
        """Render a single frame (non-blocking)."""
        self._console.print(self.render())


def create_multi_agent_tui(
    comm_bus: Any | None = None,
    orchestrator: Any | None = None,
) -> MultiAgentTUI:
    """Factory: create a MultiAgentTUI from a communication bus and orchestrator."""
    tui = MultiAgentTUI()

    if comm_bus is not None:
        stats = comm_bus.get_stats()
        comm_data = CommViewData(
            total_direct=stats.get("direct_sent", 0),
            total_broadcast=stats.get("broadcast_sent", 0),
            total_requests=stats.get("requests_sent", 0),
            total_responses=stats.get("responses_sent", 0),
            total_timeouts=stats.get("requests_timed_out", 0),
            active_agents=stats.get("registered_agents", 0),
            active_channels=stats.get("active_channels", 0),
            pending_requests=stats.get("pending_requests", 0),
        )
        tui.update_comm(comm_data)

    return tui


__all__ = [
    "AgentViewData",
    "WorkflowViewData",
    "CommViewData",
    "MultiAgentTUI",
    "create_multi_agent_tui",
]
