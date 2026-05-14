from __future__ import annotations

"""Founder agent that analyzes system metrics and proposes org changes.

This agent runs at low frequency, gathers event statistics via a plugin,
asks an LLM to generate reorganization proposals as YAML blueprint diffs,
and raises a human architect approval event containing a branch/PR URL.
"""

import json
import logging
import os
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict

from git import Repo  # type: ignore[import-not-found]

from autoai.event_bus import MessageQueue
from autoai.event_bus.message_types import HumanArchitectApprovalRequired
from autoai.llm.utils import create_chat_completion
from autoai.llm.base import ChatSequence, Message
from autoai.config import ConfigBuilder


logger = logging.getLogger(__name__)


@dataclass
class FounderConfig:
    charter_repo_url: str
    run_interval_sec: int = 24 * 60 * 60
    workdir: str = "./founder_workspace"
    llm_model: str | None = None


class Plugin_SystemAnalytics:
    """Lightweight analytics plugin stub.

    In a full implementation, this would connect to Redis/Prometheus. Here we
    compute statistics from the SQLite-backed EventBus if available.
    """

    def __init__(self, events_db_path: str | Path):
        self.events_db_path = str(events_db_path)

    def get_event_frequency(self, event_type: str, time_window_sec: int) -> float:
        # Placeholder heuristic; real implementation would query metrics store
        return 0.0

    def calculate_task_success_rate(self, task_category: str) -> float:
        return 0.0

    def find_bottleneck_agent(self, time_window_sec: int) -> str | None:
        return None


class FounderAgent:
    def __init__(self, message_queue: MessageQueue, config: FounderConfig, events_db: str | Path = "events.db") -> None:
        self.message_queue = message_queue
        self.config = config
        self.events_db = str(events_db)
        self.analytics = Plugin_SystemAnalytics(self.events_db)
        self._running = False
        self._repo: Repo | None = None
        self._repo_path = Path(self.config.workdir) / "organizational_charter"

    @classmethod
    def from_blueprint(
        cls,
        *,
        blueprint,
        event_bus=None,
        message_queue: MessageQueue | None = None,
        events_db: str | Path = "events.db",
        **kwargs,
    ) -> "FounderAgent":
        """Factory used by the blueprint orchestrator.

        Expects blueprint.config to contain 'charter_repo_url'.
        """
        if message_queue is None and event_bus is not None:
            message_queue = MessageQueue(event_bus)
        config_dict: Dict[str, Any] = dict(getattr(blueprint, "config", {}) or {})
        repo_url = config_dict.get("charter_repo_url")
        if not repo_url:
            raise ValueError("Founder blueprint requires config.charter_repo_url")
        workdir = config_dict.get("workdir", "./founder_workspace")
        interval = int(config_dict.get("run_interval_sec", 24 * 60 * 60))
        cfg = FounderConfig(charter_repo_url=repo_url, run_interval_sec=interval, workdir=workdir)
        return cls(message_queue=message_queue or MessageQueue(EventBus(events_db)), config=cfg, events_db=events_db)

    # ------------------------------------------------------------------
    def _ensure_repo(self) -> None:
        if self._repo_path.exists():
            self._repo = Repo(str(self._repo_path))
            self._repo.git.checkout("main")
            self._repo.remotes.origin.pull("main")
        else:
            self._repo_path.parent.mkdir(parents=True, exist_ok=True)
            self._repo = Repo.clone_from(self.config.charter_repo_url, str(self._repo_path), branch="main")

    # ------------------------------------------------------------------
    def _render_prompt(self, stats: Dict[str, Any]) -> str:
        return (
            "你是一位顶级的AI系统架构师和组织动力学专家。以下是我们AI开发团队过去24小时的表现数据:\n"
            + json.dumps(stats, ensure_ascii=False, indent=2)
            + "\n根据这些数据，请分析当前组织结构是否存在瓶颈、冗余或能力缺口。\n"
            "如果存在，请提出一个具体的组织重组方案。你的方案必须以修改、创建或删除“代理蓝图YAML文件”的形式提出。"
            "请返回一个JSON对象: { 'diagnosis': string, 'changes': [ { 'file': 'tdd_developer.yaml', 'action': 'create|update|delete', 'content': 'YAML content if applicable' } ] }\n"
        )

    # ------------------------------------------------------------------
    def _collect_stats(self) -> Dict[str, Any]:
        # Placeholder metrics; wire to real analytics later
        return {
            "event_rates": {
                "DIAGNOSIS_COMPLETE": self.analytics.get_event_frequency("DIAGNOSIS_COMPLETE", 24 * 3600),
            },
            "success_rates": {
                "code_fixes": self.analytics.calculate_task_success_rate("code_fix"),
            },
            "bottleneck_agent": self.analytics.find_bottleneck_agent(24 * 3600),
        }

    # ------------------------------------------------------------------
    def _apply_changes_as_branch(self, response: Dict[str, Any]) -> tuple[str, str | None]:
        assert self._repo is not None
        branch = f"proposal/{int(time.time())}"
        self._repo.git.checkout("-b", branch)
        diagnosis = str(response.get("diagnosis", ""))
        for change in response.get("changes", []) or []:
            action = change.get("action")
            file_rel = change.get("file")
            content = change.get("content")
            if not file_rel or not isinstance(file_rel, str):
                continue
            file_path = self._repo_path / file_rel
            if action == "delete":
                if file_path.exists():
                    file_path.unlink()
            else:
                file_path.parent.mkdir(parents=True, exist_ok=True)
                Path(file_path).write_text(content or "", encoding="utf-8")
                self._repo.git.add(str(file_path.relative_to(self._repo_path)))
        self._repo.index.commit(diagnosis or "Organization change proposal")
        self._repo.git.push("--set-upstream", "origin", branch)
        # Branch URL discovery depends on remote; we cannot reliably compute here
        return branch, None

    # ------------------------------------------------------------------
    def start(self) -> None:
        self._running = True
        while self._running:
            try:
                self._ensure_repo()
                stats = self._collect_stats()
                prompt = self._render_prompt(stats)
                config = ConfigBuilder.build_config_from_env()
                seq = ChatSequence.for_model(
                    model_name=config.smart_llm,
                    messages=[Message("system", prompt)],
                )
                llm_resp = create_chat_completion(prompt=seq, config=config)
                # Expect model to return JSON; be defensive
                try:
                    parsed = json.loads(llm_resp.content) if hasattr(llm_resp, "content") else json.loads(str(llm_resp))
                except Exception:
                    parsed = {"diagnosis": str(llm_resp), "changes": []}
                branch, url = self._apply_changes_as_branch(parsed)
                self.message_queue.publish(
                    HumanArchitectApprovalRequired(
                        proposal_branch_name=branch,
                        proposal_branch_url=url,
                        rationale=str(parsed.get("diagnosis", "")),
                        changes_summary=json.dumps(parsed.get("changes", []), ensure_ascii=False),
                        source_agent="founder",
                    )
                )
            except Exception as e:
                logger.exception("Founder agent iteration failed: %s", e)

            time.sleep(self.config.run_interval_sec)

    def stop(self) -> None:
        self._running = False


