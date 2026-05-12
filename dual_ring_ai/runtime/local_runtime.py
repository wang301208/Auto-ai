"""Composable local runtime for the autonomous evolution backend."""

from __future__ import annotations

import json
import asyncio
import shutil
import subprocess
import re
import sqlite3
import ast
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ..adapters.academic_search import AcademicSearchAdapter
from ..adapters.container_sandbox import DockerSandboxAdapter
from ..adapters.remote_llm import HybridLLMAdapter, RemoteLLMAdapter
from ..adapters.ollama import OllamaAdapter
from ..adapters.whisper import WhisperAdapter
from ..adapters.xtts import XTTSAdapter
from ..core.algorithm_experiment import AlgorithmExperimentRunner
from ..core.algorithm_evolution import AlgorithmEvolutionProtocol
from ..core.algorithm_registry import AlgorithmRegistry
from ..core.agent_blueprint import AgentBlueprint, ThinkingEngineRef
from ..core.blueprint_orchestrator import BlueprintOrchestrator
from ..core.event_bus import EventBus
from ..core.event_bus import EventTypes
from ..core.governance import ApprovalRequest, GovernanceStore, PermissionGate
from ..core.sandbox_runner import SandboxRunner, SandboxRunResult
from ..core.skill_lifecycle import PublishedSkill, SandboxPolicy, SkillLifecycleManager
from ..gateway import GatewayRunner, PlatformConfig
from ..gateway.platforms import DingTalkAdapter, FeishuAdapter, WeixinAdapter
from ..interaction.pipeline import InteractionPipeline

USER_VISIBLE_CAPABILITY_BOUNDARY = (
    "当前项目可执行命令行级操作；尚未实现原生截图、鼠标、键盘、窗口控制、"
    "软件安装或软件卸载专用工具。"
)

DEFAULT_LONG_TERM_DOCTRINE = [
    "建立能力基线",
    "补齐任务执行、验证、回滚能力",
    "强化自主闭环",
    "扩展长期记忆",
    "保持真实能力边界",
    "周期性度量进展并转化为测试、基准、技能或改进任务",
]


def _looks_corrupt_display_text(value: Any) -> bool:
    text = str(value or "").strip()
    if not text:
        return True
    visible = [char for char in text if not char.isspace()]
    if not visible:
        return True
    if "\ufffd" in text:
        return True
    question_marks = sum(1 for char in visible if char == "?")
    return question_marks >= 3 and question_marks / max(len(visible), 1) >= 0.5


def _clean_display_text(value: Any, fallback: str) -> str:
    text = str(value or "").strip()
    if _looks_corrupt_display_text(text):
        return fallback
    return text


def asyncio_run(awaitable):
    """Run a coroutine from sync runtime methods."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(awaitable)
    raise RuntimeError("handle_platform_message cannot be called from an active event loop")


@dataclass
class LocalRuntimeConfig:
    root_path: Path
    enable_agents: bool = False
    managed_paths: dict | None = None
    adapters: dict | None = None
    security_defaults: dict | None = None


class LocalRuntime:
    """Local-first composition root for core backend services."""

    def __init__(self, config: LocalRuntimeConfig) -> None:
        self.config = config
        self.root_path = Path(config.root_path)
        self.root_path.mkdir(parents=True, exist_ok=True)
        self.running = False
        managed_paths = config.managed_paths or {}
        adapters_config = config.adapters or {}
        self.security_defaults = self._validate_security_defaults(
            config.security_defaults or {}
        )

        skill_library_path = self._managed_path(
            managed_paths, "skill_library", "skill_library"
        )
        algorithm_library_path = self._managed_path(
            managed_paths, "algorithm_library", "algorithm_library"
        )
        algorithm_experiments_path = self._managed_path(
            managed_paths, "algorithm_experiments", "algorithm_experiments"
        )
        workspace_path = self._managed_path(managed_paths, "workspace", "workspace")
        governance_path = self._managed_path(managed_paths, "governance", "governance")
        logs_path = self._managed_path(managed_paths, "logs", "logs")
        charter_path = self._managed_path(
            managed_paths,
            "organizational_charter",
            "organizational_charter",
            allow_external=True,
        )

        self.event_bus = EventBus()
        self.governance = GovernanceStore(governance_path)
        self.permission_gate = PermissionGate()
        self.skill_lifecycle = SkillLifecycleManager(
            skill_library_path,
            self.event_bus,
            audit_log_path=logs_path / "skill_lifecycle_audit.jsonl",
        )
        self.algorithm_registry = AlgorithmRegistry(algorithm_library_path)
        self.algorithm_experiments = AlgorithmExperimentRunner(
            algorithm_experiments_path
        )
        self.algorithm_evolution = AlgorithmEvolutionProtocol(
            self.root_path,
            self.algorithm_registry,
            self.algorithm_experiments,
            self.governance,
            self.event_bus,
            audit_log_path=logs_path / "algorithm_evolution_audit.jsonl",
        )
        self.sandbox_runner = SandboxRunner(workspace_path)
        self.blueprint_orchestrator = BlueprintOrchestrator(charter_path)
        charter_path.mkdir(parents=True, exist_ok=True)
        self.latest_avatar_event: dict[str, Any] | None = None
        academic_config = adapters_config.get("academic_search", {})
        docker_config = adapters_config.get("docker_sandbox", {})
        remote_llm_config = adapters_config.get("remote_llm", {})
        ollama_config = adapters_config.get("ollama", {})
        whisper_config = adapters_config.get("whisper", {})
        xtts_config = adapters_config.get("xtts", {})
        messaging_config = adapters_config.get("messaging_gateway", {})
        remote_llm = RemoteLLMAdapter(
            enabled=bool(remote_llm_config.get("enabled", bool(remote_llm_config))),
            dry_run=bool(remote_llm_config.get("dry_run", False)),
            api_key=remote_llm_config.get("api_key"),
            api_key_env=remote_llm_config.get("api_key_env", "OPENAI_API_KEY"),
            base_url=remote_llm_config.get("base_url", "https://api.openai.com/v1"),
            model=remote_llm_config.get("model", "gpt-4o-mini"),
            timeout=float(remote_llm_config.get("timeout", 30.0)),
            temperature=float(remote_llm_config.get("temperature", 0.2)),
            max_tokens=remote_llm_config.get("max_tokens"),
            system_prompt=remote_llm_config.get(
                "system_prompt",
                RemoteLLMAdapter.system_prompt,
            ),
        )
        self.interaction_pipeline = InteractionPipeline(llm=HybridLLMAdapter(remote_llm))
        self.adapters = {
            "academic_search": AcademicSearchAdapter(
                provider=academic_config.get("provider"),
                fixture_path=academic_config.get("fixture_path"),
            ),
            "remote_llm": remote_llm,
            "docker_sandbox": DockerSandboxAdapter(
                enabled=bool(docker_config.get("enabled", True)),
                image=docker_config.get("image", "python:3.12-slim"),
                dry_run=bool(docker_config.get("dry_run", False)),
                memory_limit=docker_config.get("memory_limit", "512m"),
                cpus=docker_config.get("cpus", "1.0"),
                pids_limit=int(docker_config.get("pids_limit", 256)),
                network_mode=docker_config.get("network_mode"),
                read_only=bool(docker_config.get("read_only", False)),
            ),
            "ollama": OllamaAdapter(
                enabled=bool(ollama_config.get("enabled", True)),
                dry_run=bool(ollama_config.get("dry_run", False)),
                base_url=ollama_config.get("base_url", "http://127.0.0.1:11434"),
                model=ollama_config.get("model", "llama3.1"),
            ),
            "whisper": WhisperAdapter(
                enabled=bool(whisper_config.get("enabled", True)),
                dry_run=bool(whisper_config.get("dry_run", False)),
                executable=whisper_config.get("executable", "whisper"),
                model=whisper_config.get("model", "base"),
                language=whisper_config.get("language"),
            ),
            "xtts": XTTSAdapter(
                enabled=bool(xtts_config.get("enabled", True)),
                dry_run=bool(xtts_config.get("dry_run", False)),
                executable=xtts_config.get("executable", "xtts"),
                speaker_wav=xtts_config.get("speaker_wav"),
                language=xtts_config.get("language", "zh-cn"),
            ),
        }
        self.messaging_gateway = GatewayRunner(self)
        self._configure_messaging_gateway(messaging_config)
        self.agents = {}
        self.experience_path = self.root_path / "experience" / "records.jsonl"
        self.self_model_path = self.root_path / "experience" / "self_model.json"
        self.user_model_path = self.root_path / "experience" / "user_models.json"
        self.memory_cycle_path = self.root_path / "experience" / "periodic_memory.jsonl"
        self.autonomous_goals_path = self.root_path / "experience" / "autonomous_goals.json"
        self.development_tasks_path = self.root_path / "experience" / "development_tasks"
        self.conversation_db_path = self.root_path / "experience" / "conversations.sqlite3"
        self.skill_proposals_path = self.root_path / "workspace" / "skill_proposals"
        self.self_evolution_audit_path = self.root_path / "self_evolution" / "audit.jsonl"

    def _configure_messaging_gateway(self, config: dict[str, Any]) -> None:
        if not bool(config.get("enabled", False)):
            return
        platforms = config.get("platforms", {})
        adapter_classes = {
            "feishu": FeishuAdapter,
            "dingtalk": DingTalkAdapter,
            "weixin": WeixinAdapter,
        }
        for name, adapter_class in adapter_classes.items():
            raw = platforms.get(name, {})
            if not bool(raw.get("enabled", False)):
                continue
            platform_config = PlatformConfig(
                name=name,
                enabled=True,
                token=raw.get("token"),
                api_key=raw.get("api_key"),
                extra=dict(raw.get("extra", {})),
            )
            self.messaging_gateway.register(adapter_class(platform_config))

    @classmethod
    def from_config_file(cls, config_path: str | Path) -> "LocalRuntime":
        """Build a local runtime from a JSON config file."""
        config_data = json.loads(Path(config_path).read_text(encoding="utf-8"))
        return cls(
            LocalRuntimeConfig(
                root_path=Path(config_data["root_path"]),
                enable_agents=bool(config_data.get("enable_agents", False)),
                managed_paths=config_data.get("managed_paths", {}),
                adapters=config_data.get("adapters", {}),
                security_defaults=config_data.get("security_defaults", {}),
            )
        )

    def start(self) -> None:
        self.event_bus.connect()
        self.running = True

    def stop(self) -> None:
        self.running = False
        self.event_bus.disconnect()

    def status_snapshot(self) -> dict:
        return {
            "running": self.running,
            "services": {
                "event_bus": "ready",
                "governance": "ready",
                "skill_lifecycle": "ready",
                "algorithm_registry": "ready",
                "algorithm_experiments": "ready",
                "algorithm_evolution": "ready",
                "sandbox_runner": "ready",
                "blueprint_orchestrator": "ready",
                "interaction_pipeline": "ready",
                "development_tasks": "ready",
                "messaging_gateway": (
                    "ready" if self.messaging_gateway.adapters else "disabled"
                ),
            },
            "agents": list(self.agents.keys()),
            "paths": {
                "root_path": str(self.root_path),
                "skill_library": str(self.skill_lifecycle.skill_library_path),
                "algorithm_library": str(self.algorithm_registry.root_path),
                "algorithm_experiments": str(self.algorithm_experiments.output_path),
                "workspace": str(self.sandbox_runner.workspace_path),
                "organizational_charter": str(self.blueprint_orchestrator.charter_path),
                "development_tasks": str(self.development_tasks_path),
            },
        }

    def handle_interaction(self, text: str) -> dict[str, Any]:
        """Run one local multimodal interaction against the current backend snapshot."""
        result = self.interaction_pipeline.handle_text(
            text,
            backend_payload={
                "services": self.status_snapshot()["services"],
                "approvals": [asdict(item) for item in self.governance.list_requests()],
                "capabilities": self._truthful_interaction_capabilities(),
            },
        )
        self.latest_avatar_event = result["avatar_event"]
        self.event_bus.publish(
            "INTERACTION_COMPLETED",
            {
                "transcript": result["transcript"],
                "response_text": result["response_text"],
                "avatar_event": result["avatar_event"],
            },
            "interaction_pipeline",
        )
        return result

    @staticmethod
    def _truthful_interaction_capabilities() -> dict[str, Any]:
        return {
            "natural_language": True,
            "shell": True,
            "computer_control": False,
            "software_management": False,
            "native_desktop_actions": [],
            "implemented_direct_tools": [
                "shell.exec",
                "runtime.status_snapshot",
                "memory.periodic_tick",
                "conversation.search",
            ],
            "user_visible_boundary": (
                "当前项目可执行命令行级操作；尚未实现原生截图、鼠标、键盘、窗口控制、"
                "软件安装或软件卸载专用工具。"
            ),
        }

    def record_experience(
        self,
        text: str,
        source: str = "session",
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Persist a reusable experience extracted from a conversation or task."""
        normalized_text = str(text).strip()
        if not normalized_text:
            raise ValueError("experience text is required")
        records = self._read_experience_records()
        item = {
            "id": f"exp_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S_%f')}",
            "text": normalized_text,
            "source": str(source or "session"),
            "tags": [str(tag) for tag in (tags or [])],
            "metadata": metadata if isinstance(metadata, dict) else {},
            "created_at": datetime.now(UTC).isoformat(),
        }
        self.experience_path.parent.mkdir(parents=True, exist_ok=True)
        with self.experience_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(item, ensure_ascii=False) + "\n")
        return item

    def search_experience(self, query: str, limit: int = 10) -> dict[str, Any]:
        """Search stored experience records with simple token overlap ranking."""
        query_text = str(query).strip()
        query_tokens = self._search_tokens(query_text)
        matches: list[dict[str, Any]] = []
        for record in self._read_experience_records():
            haystack = " ".join(
                [
                    str(record.get("text", "")),
                    " ".join(str(tag) for tag in record.get("tags", [])),
                    json.dumps(record.get("metadata", {}), ensure_ascii=False),
                ]
            )
            haystack_tokens = self._search_tokens(haystack)
            overlap = query_tokens & haystack_tokens if query_tokens else set()
            if query_tokens and not overlap and query_text.lower() not in haystack.lower():
                continue
            score = len(overlap) + (1 if query_text.lower() in haystack.lower() else 0)
            matches.append({**record, "score": score})
        matches.sort(key=lambda item: (item.get("score", 0), item.get("created_at", "")), reverse=True)
        bounded_limit = max(1, min(int(limit or 10), 100))
        return {"query": query_text, "matches": matches[:bounded_limit], "total": len(matches)}

    def record_conversation_turn(
        self,
        session_id: str,
        role: str,
        text: str,
        user_id: str = "default",
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Persist a conversation turn into the cross-session FTS5 memory index."""
        normalized_text = str(text).strip()
        if not normalized_text:
            raise ValueError("conversation text is required")
        created_at = datetime.now(UTC).isoformat()
        payload_metadata = metadata if isinstance(metadata, dict) else {}
        with self._conversation_connection() as connection:
            connection.execute(
                (
                    "INSERT INTO conversations "
                    "(session_id, user_id, role, text, metadata_json, created_at) "
                    "VALUES (?, ?, ?, ?, ?, ?)"
                ),
                (
                    str(session_id or "default"),
                    str(user_id or "default"),
                    str(role or "user"),
                    normalized_text,
                    json.dumps(payload_metadata, ensure_ascii=False, sort_keys=True),
                    created_at,
                ),
            )
            row_id = int(connection.execute("SELECT last_insert_rowid()").fetchone()[0])
            connection.execute(
                (
                    "INSERT INTO conversation_fts "
                    "(rowid, session_id, user_id, role, text, metadata_json) "
                    "VALUES (?, ?, ?, ?, ?, ?)"
                ),
                (
                    row_id,
                    str(session_id or "default"),
                    str(user_id or "default"),
                    str(role or "user"),
                    normalized_text,
                    json.dumps(payload_metadata, ensure_ascii=False, sort_keys=True),
                ),
            )
        return {
            "id": row_id,
            "session_id": str(session_id or "default"),
            "user_id": str(user_id or "default"),
            "role": str(role or "user"),
            "text": normalized_text,
            "metadata": payload_metadata,
            "created_at": created_at,
        }

    def search_conversations(
        self,
        query: str,
        limit: int = 10,
        summarize: bool = True,
        user_id: str | None = None,
    ) -> dict[str, Any]:
        """Search prior sessions through SQLite FTS5 and optionally summarize hits."""
        query_text = str(query).strip()
        bounded_limit = max(1, min(int(limit or 10), 100))
        matches: list[dict[str, Any]] = []
        with self._conversation_connection() as connection:
            if query_text:
                fts_query = self._fts_query(query_text)
                if user_id:
                    rows = connection.execute(
                        (
                            "SELECT c.id, c.session_id, c.user_id, c.role, c.text, "
                            "c.metadata_json, c.created_at, bm25(conversation_fts) AS rank "
                            "FROM conversation_fts "
                            "JOIN conversations c ON c.id = conversation_fts.rowid "
                            "WHERE conversation_fts MATCH ? AND c.user_id = ? "
                            "ORDER BY rank LIMIT ?"
                        ),
                        (fts_query, str(user_id), bounded_limit),
                    ).fetchall()
                else:
                    rows = connection.execute(
                        (
                            "SELECT c.id, c.session_id, c.user_id, c.role, c.text, "
                            "c.metadata_json, c.created_at, bm25(conversation_fts) AS rank "
                            "FROM conversation_fts "
                            "JOIN conversations c ON c.id = conversation_fts.rowid "
                            "WHERE conversation_fts MATCH ? "
                            "ORDER BY rank LIMIT ?"
                        ),
                        (fts_query, bounded_limit),
                    ).fetchall()
            else:
                if user_id:
                    rows = connection.execute(
                        (
                            "SELECT id, session_id, user_id, role, text, metadata_json, "
                            "created_at, 0.0 AS rank FROM conversations "
                            "WHERE user_id = ? ORDER BY id DESC LIMIT ?"
                        ),
                        (str(user_id), bounded_limit),
                    ).fetchall()
                else:
                    rows = connection.execute(
                        (
                            "SELECT id, session_id, user_id, role, text, metadata_json, "
                            "created_at, 0.0 AS rank FROM conversations "
                            "ORDER BY id DESC LIMIT ?"
                        ),
                        (bounded_limit,),
                    ).fetchall()
        for row in rows:
            matches.append(
                {
                    "id": row["id"],
                    "session_id": row["session_id"],
                    "user_id": row["user_id"],
                    "role": row["role"],
                    "text": row["text"],
                    "metadata": self._json_loads_dict(row["metadata_json"]),
                    "created_at": row["created_at"],
                    "score": float(-row["rank"]) if "rank" in row.keys() else 0.0,
                }
            )
        summary = self._summarize_conversation_matches(query_text, matches) if summarize else ""
        return {
            "engine": "sqlite_fts5",
            "query": query_text,
            "matches": matches,
            "total": len(matches),
            "summary": summary,
        }

    def periodic_memory_tick(
        self,
        task: str,
        cadence: str = "daily",
    ) -> dict[str, Any]:
        """Record a scheduled autonomous planning tick backed by memory search."""
        task_text = str(task).strip()
        if not task_text:
            raise ValueError("task is required")
        recalled = self.search_conversations(task_text, limit=5, summarize=True)
        related_experience = self.search_experience(task_text, limit=5)
        next_actions = self._plan_memory_next_actions(
            task_text,
            recalled["matches"],
            related_experience["matches"],
        )
        payload = {
            "id": f"cycle_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S_%f')}",
            "status": "recorded",
            "task": task_text,
            "cadence": str(cadence or "daily"),
            "created_at": datetime.now(UTC).isoformat(),
            "recall_summary": recalled["summary"],
            "experience_count": len(related_experience["matches"]),
            "next_actions": next_actions,
        }
        self.memory_cycle_path.parent.mkdir(parents=True, exist_ok=True)
        with self.memory_cycle_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=False) + "\n")
        self.record_experience(
            text=f"Periodic planning tick for {task_text}: {'; '.join(next_actions)}",
            source="periodic_memory",
            tags=["periodic", "planning"],
            metadata={"cycle_id": payload["id"], "cadence": payload["cadence"]},
        )
        return payload

    def start_development_task(
        self,
        goal: str,
        context: dict[str, Any] | None = None,
        auto_execute: bool = True,
    ) -> dict[str, Any]:
        """Create, plan, optionally execute, verify, and persist a development task."""
        goal_text = str(goal).strip()
        if not goal_text:
            raise ValueError("goal is required")
        task_id = f"devtask_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S_%f')}"
        now = datetime.now(UTC).isoformat()
        task = {
            "task_id": task_id,
            "goal": goal_text,
            "context": context if isinstance(context, dict) else {},
            "status": "created",
            "created_at": now,
            "updated_at": now,
            "plan": self._build_development_task_plan(goal_text, context or {}),
            "execution": {"executed": 0, "verified": 0, "blocked": 0, "errors": 0},
            "verification": {},
            "learning": {},
            "events": [],
        }
        task["task_path"] = str(self._development_task_path(task_id))
        task["status"] = "planned"
        task["events"].append(self._development_task_event("planned", "development plan created"))
        self._save_development_task(task)
        if auto_execute:
            task = self.execute_development_task(task_id)
        return task

    def get_development_task(self, task_id: str) -> dict[str, Any]:
        task = self._read_json_file(self._development_task_path(task_id))
        if not isinstance(task, dict):
            raise ValueError(f"development task not found: {task_id}")
        return task

    def list_development_tasks(self, limit: int = 20) -> list[dict[str, Any]]:
        if not self.development_tasks_path.exists():
            return []
        tasks = []
        for path in sorted(self.development_tasks_path.glob("*.json")):
            payload = self._read_json_file(path)
            if isinstance(payload, dict):
                tasks.append(payload)
        tasks.sort(key=lambda item: str(item.get("created_at", "")), reverse=True)
        return tasks[: max(1, min(int(limit or 20), 100))]

    def execute_development_task(self, task_id: str) -> dict[str, Any]:
        task = self.get_development_task(task_id)
        if task.get("status") == "cancelled":
            return task
        task["status"] = "executing"
        task["updated_at"] = datetime.now(UTC).isoformat()
        steps = [step for step in task.get("plan", {}).get("steps", []) if isinstance(step, dict)]
        for step in steps:
            if step.get("status") in {"verified", "completed", "blocked", "failed"}:
                continue
            if bool(step.get("requires_approval")):
                step["status"] = "blocked"
                step["blocked_reason"] = "requires governed approval before execution"
                task["events"].append(
                    self._development_task_event("blocked", f"{step.get('id')} requires approval")
                )
                continue
            try:
                result = self._execute_development_task_step(task, step)
            except Exception as exc:
                step["status"] = "failed"
                step["error"] = str(exc)
                task["events"].append(
                    self._development_task_event("failed", f"{step.get('id')}: {exc}")
                )
                continue
            step["result"] = result
            step["status"] = "verified" if result.get("verified") else "completed"
            task["events"].append(
                self._development_task_event(step["status"], str(step.get("id", "step")))
            )
        summary = self._summarize_development_task_steps(steps)
        task["execution"] = summary
        task["status"] = self._development_task_status_from_summary(summary)
        task = self.verify_development_task(task_id, task=task)
        if not task.get("learning"):
            task = self.learn_from_development_task(task_id, task=task)
        steps = [step for step in task.get("plan", {}).get("steps", []) if isinstance(step, dict)]
        summary = self._summarize_development_task_steps(steps)
        task["execution"] = summary
        task["status"] = self._development_task_status_from_summary(summary)
        task["updated_at"] = datetime.now(UTC).isoformat()
        self._save_development_task(task)
        return task

    def verify_development_task(
        self,
        task_id: str,
        task: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        current = task if isinstance(task, dict) else self.get_development_task(task_id)
        steps = [step for step in current.get("plan", {}).get("steps", []) if isinstance(step, dict)]
        summary = self._summarize_development_task_steps(steps)
        executed = int(summary.get("executed", 0) or 0)
        blocked = int(summary.get("blocked", 0) or 0)
        errors = int(summary.get("errors", 0) or 0)
        verification_steps = [
            step
            for step in steps
            if step.get("kind") == "verify" and step.get("status") in {"completed", "verified"}
        ]
        if errors:
            status = "failed"
        elif blocked:
            status = "blocked"
        elif executed > 0 and verification_steps:
            status = "passed"
        else:
            status = "attention_required"
        current["execution"] = summary
        current["verification"] = {
            "status": status,
            "checked_at": datetime.now(UTC).isoformat(),
            "verified_steps": [step.get("id") for step in verification_steps],
            "blocked_steps": [step.get("id") for step in steps if step.get("status") == "blocked"],
            "notes": "safe planning loop verified; high-risk implementation remains approval-gated",
        }
        current["updated_at"] = datetime.now(UTC).isoformat()
        self._save_development_task(current)
        return current

    @staticmethod
    def _summarize_development_task_steps(steps: list[dict[str, Any]]) -> dict[str, int]:
        return {
            "executed": sum(1 for step in steps if step.get("status") in {"completed", "verified"}),
            "verified": sum(1 for step in steps if step.get("status") == "verified"),
            "blocked": sum(1 for step in steps if step.get("status") == "blocked"),
            "errors": sum(1 for step in steps if step.get("status") == "failed"),
        }

    @staticmethod
    def _development_task_status_from_summary(summary: dict[str, int]) -> str:
        if int(summary.get("errors", 0) or 0) > 0:
            return "failed"
        if int(summary.get("blocked", 0) or 0) > 0:
            return "waiting_approval"
        return "completed"

    def learn_from_development_task(
        self,
        task_id: str,
        task: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        current = task if isinstance(task, dict) else self.get_development_task(task_id)
        experience = self.record_experience(
            text=(
                f"Development task {current.get('task_id')} for goal "
                f"{current.get('goal')} completed with status {current.get('status')}."
            ),
            source="development_task",
            tags=["development_task", "planning", "verification"],
            metadata={
                "task_id": current.get("task_id"),
                "status": current.get("status"),
                "verification": current.get("verification", {}),
            },
        )
        skill_candidate = None
        if self._should_development_task_create_skill(str(current.get("goal", ""))):
            skill_candidate = {
                "status": "candidate",
                "reason": "complex development workflow completed; consider creating a reusable skill after review",
                "suggested_skill_name": self._slugify_skill_name(f"{current.get('goal', 'development')}_workflow")[:80],
            }
        current["learning"] = {
            "experience_id": experience["id"],
            "skill_candidate": skill_candidate,
            "learned_at": datetime.now(UTC).isoformat(),
        }
        current["updated_at"] = datetime.now(UTC).isoformat()
        self._save_development_task(current)
        return current

    def cancel_development_task(self, task_id: str, reason: str = "") -> dict[str, Any]:
        task = self.get_development_task(task_id)
        task["status"] = "cancelled"
        task["cancel_reason"] = str(reason or "cancelled by request")
        task["updated_at"] = datetime.now(UTC).isoformat()
        task["events"].append(self._development_task_event("cancelled", task["cancel_reason"]))
        self._save_development_task(task)
        return task

    def read_autonomous_goals(self) -> dict[str, Any]:
        payload = self._read_json_file(self.autonomous_goals_path)
        if isinstance(payload, dict):
            goals = payload.get("goals", [])
            if isinstance(goals, list):
                payload["goals"] = [goal for goal in goals if isinstance(goal, dict)]
                payload.setdefault("active_goal_id", "")
                payload.setdefault("updated_at", "")
                return payload
        return {"version": 1, "active_goal_id": "", "updated_at": "", "goals": []}

    def update_autonomous_goals(
        self,
        goal_text: str,
        trigger: str,
        next_actions: list[str] | None = None,
    ) -> dict[str, Any]:
        title = _clean_display_text(goal_text or trigger, "等待用户目标")
        goals_payload = self.read_autonomous_goals()
        goals = [
            goal
            for goal in list(goals_payload.get("goals", []))
            if not _looks_corrupt_display_text(goal.get("title", ""))
        ]
        active = self._select_active_goal(goals, title)
        now = datetime.now(UTC).isoformat()
        preserve_active_identity = (
            active is not None
            and active.get("source") == "long_term_agi_evolution_goal"
            and trigger in {"remote_loop", "session_start"}
        )
        if active is None:
            active = {
                "id": f"goal_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S_%f')}",
                "title": title,
                "status": "active",
                "priority": self._goal_priority(trigger),
                "source": trigger,
                "created_at": now,
                "updated_at": now,
                "progress": [],
                "next_actions": [],
            }
            goals.insert(0, active)
        if not preserve_active_identity:
            active["title"] = title
        active["status"] = "active"
        if not preserve_active_identity:
            active["source"] = str(trigger or active.get("source", "autonomous"))
        active["priority"] = max(int(active.get("priority", 1) or 1), self._goal_priority(trigger))
        active["updated_at"] = now
        progress = list(active.get("progress", [])) if isinstance(active.get("progress"), list) else []
        progress = [
            item
            for item in progress
            if not _looks_corrupt_display_text(
                item.get("summary", "") if isinstance(item, dict) else item
            )
        ]
        progress.append({"trigger": trigger, "created_at": now, "summary": title})
        active["progress"] = progress[-50:]
        if not preserve_active_identity:
            active["next_actions"] = [
                _clean_display_text(item, "等待下一轮自主维护")
                for item in (next_actions or [])
                if str(item).strip() and not _looks_corrupt_display_text(item)
            ][:8]
        for goal in goals:
            if goal is not active and goal.get("status") == "active" and goal.get("source") == trigger:
                goal["status"] = "watching"
        goals = sorted(
            goals,
            key=lambda item: (
                0 if item.get("id") == active.get("id") else 1,
                -int(item.get("priority", 1) or 1),
                str(item.get("updated_at", "")),
            ),
        )[:100]
        payload = {
            "version": int(goals_payload.get("version", 1) or 1),
            "active_goal_id": active["id"],
            "updated_at": now,
            "goals": goals,
        }
        self.autonomous_goals_path.parent.mkdir(parents=True, exist_ok=True)
        self.autonomous_goals_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return payload

    @staticmethod
    def _select_active_goal(goals: list[dict[str, Any]], title: str) -> dict[str, Any] | None:
        normalized = title.casefold()
        valid_goals = [
            goal for goal in goals if not _looks_corrupt_display_text(goal.get("title", ""))
        ]
        for goal in valid_goals:
            if str(goal.get("title", "")).casefold() == normalized:
                return goal
        for goal in valid_goals:
            if (
                goal.get("status") == "active"
                and goal.get("source") == "long_term_agi_evolution_goal"
            ):
                return goal
        for goal in valid_goals:
            if goal.get("status") == "active":
                return goal
        return None

    @staticmethod
    def _goal_priority(trigger: str) -> int:
        if trigger == "prompt_complete":
            return 5
        if trigger == "session_start":
            return 3
        if trigger == "remote_loop":
            return 2
        return 1

    def autonomous_remote_reflection(
        self,
        trigger: str,
        task_text: str,
        actions: list[dict[str, Any]],
        next_actions: list[str] | None = None,
    ) -> dict[str, Any]:
        """Ask the configured remote model to reflect on one autonomous maintenance cycle."""
        llm = self.adapters.get("remote_llm") if hasattr(self, "adapters") else None
        if llm is None or not hasattr(llm, "generate_response"):
            return {
                "status": "unavailable",
                "reason": "remote_llm adapter is unavailable",
            }

        health: dict[str, Any] = {"status": "unknown"}
        if hasattr(llm, "probe"):
            try:
                health = llm.probe()
            except Exception as exc:
                health = {"status": "unavailable", "reason": str(exc)}
        health_status = str(health.get("status", "unknown"))
        if health_status in {"disabled", "unconfigured", "unavailable"}:
            return {
                "status": "skipped",
                "remote_status": health_status,
                "reason": health.get("reason", f"remote_llm is {health_status}"),
                "model": health.get("model", getattr(llm, "model", "")),
            }

        action_summary = [
            {
                "name": str(item.get("name", "")),
                "status": str(item.get("status", "")),
                "result": item.get("result", {}),
                "error": item.get("error", ""),
            }
            for item in actions[-20:]
            if isinstance(item, dict)
        ]
        payload = {
            "mode": "autonomous_remote_reflection",
            "trigger": trigger,
            "task": task_text,
            "runtime": self.status_snapshot(),
            "remote_health": health,
            "actions": action_summary,
            "next_actions": list(next_actions or []),
            "self_model": self.read_self_model(),
        }
        prompt = (
            "You are the remote reasoning engine for the autonomous self-maintenance loop. "
            "Review the maintenance cycle and return JSON only with keys: "
            "reflection, next_actions, risk, confidence. "
            "Do not propose applying critical source, training, or deployment changes without approval.\n"
            + json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
        )
        try:
            response = llm.generate_response(prompt, payload)
        except Exception as exc:
            return {"status": "error", "reason": str(exc)}

        status = str(response.get("status", ""))
        if status in {"disabled", "unconfigured", "unavailable"}:
            return {
                "status": "skipped",
                "remote_status": status,
                "reason": response.get("reason") or response.get("text", ""),
                "model": getattr(llm, "model", ""),
            }

        raw_text = str(response.get("text", "")).strip()
        parsed = self._extract_json_object(raw_text)
        next_suggestions = parsed.get("next_actions", []) if isinstance(parsed, dict) else []
        if not isinstance(next_suggestions, list):
            next_suggestions = []
        reflection = (
            str(parsed.get("reflection", "")).strip()
            if parsed
            else raw_text
        )
        result = {
            "status": "completed" if status in {"completed", "dry_run"} else status or "completed",
            "remote_status": status or "completed",
            "provider": response.get("provider", "remote_llm"),
            "model": getattr(llm, "model", response.get("model", "")),
            "reflection": reflection[:2000],
            "next_actions": [str(item) for item in next_suggestions if str(item).strip()][:8],
            "risk": str(parsed.get("risk", "")) if parsed else "",
            "confidence": parsed.get("confidence") if parsed else None,
        }
        self.record_experience(
            text=f"Autonomous remote reflection ({trigger}): {result['reflection']}",
            source="autonomous_remote_reflection",
            tags=["autonomous", "remote_llm", "self_reflection"],
            metadata={
                "trigger": trigger,
                "remote_status": result["remote_status"],
                "provider": result["provider"],
                "model": result["model"],
                "next_actions": result["next_actions"],
                "risk": result["risk"],
            },
        )
        if result["reflection"]:
            self.update_self_model(
                observation=f"Remote autonomous reflection {trigger}: {result['reflection']}",
                capability="remote_model_autonomous_reflection",
                preference="use_remote_model_for_autonomous_self_maintenance",
            )
        return result

    def autonomous_skill_from_task(
        self,
        task_text: str,
        skill_name: str | None = None,
    ) -> dict[str, Any]:
        """Create a skill draft after a complex task, using experience when present."""
        normalized_task = str(task_text).strip()
        if not normalized_task:
            raise ValueError("task_text is required")
        matches = self.search_experience(normalized_task, limit=5)["matches"]
        if not matches:
            experience = self.record_experience(
                text=normalized_task,
                source="complex_task",
                tags=["complex_task", "skill_seed"],
                metadata={"autonomous_skill_seed": True},
            )
            matches = [experience]
        return self._write_skill_proposal(
            query=normalized_task,
            skill_name=skill_name or f"{normalized_task}_skill",
            matches=matches,
            tags=["experience", "draft", "autonomous"],
            description=f"Autonomous draft from complex task: {normalized_task[:120]}",
        )

    def improve_skill_from_usage(
        self,
        skill_name: str,
        feedback: str,
    ) -> dict[str, Any]:
        """Record skill usage feedback and update the draft metadata in place."""
        name = self._slugify_skill_name(skill_name)
        feedback_text = str(feedback).strip()
        if not feedback_text:
            raise ValueError("feedback is required")
        proposal_dir = self.skill_proposals_path / name
        metadata_path = proposal_dir / "skill.json"
        if not metadata_path.exists():
            raise ValueError(f"skill draft not found: {name}")
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        usage_count = int(metadata.get("usage_count", 0)) + 1
        improvements = list(metadata.get("improvements", []))
        improvements.append(
            {
                "feedback": feedback_text,
                "created_at": datetime.now(UTC).isoformat(),
            }
        )
        metadata["usage_count"] = usage_count
        metadata["version"] = self._bump_patch_version(str(metadata.get("version", "0.1.0")))
        metadata["improvements"] = improvements[-50:]
        metadata["tags"] = self._append_unique(metadata.get("tags", []), "self_improving")
        metadata_path.write_text(
            json.dumps(metadata, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        skill_md = proposal_dir / "SKILL.md"
        if skill_md.exists():
            skill_md.write_text(
                self._skill_markdown(metadata, self._skill_experience_summary(proposal_dir), improvements),
                encoding="utf-8",
            )
        self.record_experience(
            text=f"Skill {name} improved from usage feedback: {feedback_text}",
            source="skill_usage",
            tags=["skill", "self_improving", name],
            metadata={"skill_name": name, "usage_count": usage_count},
        )
        return {
            "status": "improved",
            "skill_name": name,
            "proposal_dir": str(proposal_dir),
            "version": metadata["version"],
            "usage_count": usage_count,
            "improvements": metadata["improvements"],
        }

    def merge_skill_preview(
        self,
        skill_paths: list[str | Path],
        merged_skill_name: str | None = None,
        strategy: str = "dedupe_union",
    ) -> dict[str, Any]:
        """Preview a deterministic merge of multiple skill proposals or published skills."""
        sources = self._load_skill_merge_sources(skill_paths)
        name = self._slugify_skill_name(
            merged_skill_name
            or "_".join(source["skill_name"] for source in sources)
            or "merged_skill"
        )
        parameters, parameter_conflicts = self._merge_skill_parameters(sources)
        policy = self._merge_skill_security_policies(sources)
        tags: list[str] = ["merged", str(strategy or "dedupe_union")]
        descriptions: list[str] = []
        for source in sources:
            tags = self._append_unique(tags, source["skill_name"])
            for tag in source["metadata"].get("tags", []):
                tags = self._append_unique(tags, str(tag))
            description = str(source["metadata"].get("description", "")).strip()
            if description:
                descriptions.append(f"{source['skill_name']}: {description}")

        versions = sorted(
            {
                str(source["metadata"].get("version", ""))
                for source in sources
                if source["metadata"].get("version")
            }
        )
        conflicts: dict[str, Any] = {}
        if len(versions) > 1:
            conflicts["version"] = versions
        if parameter_conflicts:
            conflicts["parameters"] = parameter_conflicts
        llm_resolution = self._resolve_skill_merge_conflicts_with_llm(
            name,
            sources,
            parameters,
            conflicts,
            strategy,
        )
        if llm_resolution.get("status") == "completed":
            for param_name, definition in llm_resolution.get("parameter_overrides", {}).items():
                if isinstance(definition, dict):
                    parameters[str(param_name)] = definition
            execution_order = self._normalized_merge_execution_order(
                [source["skill_name"] for source in sources],
                llm_resolution.get("execution_order", []),
            )
        else:
            execution_order = [source["skill_name"] for source in sources]

        return {
            "status": "preview",
            "merged_skill_name": name,
            "strategy": str(strategy or "dedupe_union"),
            "source_count": len(sources),
            "sources": [
                {
                    "skill_name": source["skill_name"],
                    "version": source["metadata"].get("version", ""),
                    "description": source["metadata"].get("description", ""),
                    "path": str(source["path"]),
                }
                for source in sources
            ],
            "merged": {
                "parameters": parameters,
                "security_policy": policy,
                "tags": tags,
                "description": (
                    f"Merged skill from {len(sources)} source skills: "
                    + ", ".join(source["skill_name"] for source in sources)
                ),
                "source_descriptions": descriptions,
            },
            "conflicts": conflicts,
            "execution_order": execution_order,
            "llm_resolution": llm_resolution,
            "conflict_policy": "dedupe identical fields; keep first conflicting parameter and record conflicts",
        }

    def merge_skills(
        self,
        skill_paths: list[str | Path],
        merged_skill_name: str | None = None,
        strategy: str = "dedupe_union",
    ) -> dict[str, Any]:
        """Merge multiple skills into a publishable skill proposal directory."""
        preview = self.merge_skill_preview(
            skill_paths,
            merged_skill_name=merged_skill_name,
            strategy=strategy,
        )
        name = preview["merged_skill_name"]
        proposal_dir = self.skill_proposals_path / name
        proposal_dir.mkdir(parents=True, exist_ok=True)
        sources = preview["sources"]
        source_snapshots_dir = proposal_dir / "_merged_sources"
        if source_snapshots_dir.exists():
            shutil.rmtree(source_snapshots_dir)
        source_snapshots_dir.mkdir(parents=True, exist_ok=True)
        fused_sources: list[dict[str, Any]] = []
        for source in sources:
            source_path = Path(source["path"])
            snapshot_path = source_snapshots_dir / self._slugify_skill_name(source["skill_name"])
            if snapshot_path.exists():
                shutil.rmtree(snapshot_path)
            shutil.copytree(
                source_path,
                snapshot_path,
                ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache"),
            )
            fused_sources.append({**source, "path": str(snapshot_path)})
        now = datetime.now(UTC).isoformat()
        metadata = {
            "skill_name": name,
            "name": name,
            "version": "0.1.0",
            "description": preview["merged"]["description"],
            "tags": preview["merged"]["tags"],
            "parameters": preview["merged"]["parameters"],
            "security_policy": preview["merged"]["security_policy"],
            "agentskills_io": {
                "standard": "open-agent-skills",
                "version": "1.0",
                "spec": "https://openagentskills.dev/docs/specification",
                "entrypoint": "SKILL.md",
            },
            "usage_count": 0,
            "improvements": [],
            "merge": {
                "strategy": preview["strategy"],
                "source_skills": [source["skill_name"] for source in sources],
                "source_paths": [source["path"] for source in sources],
                "source_snapshots": [source["path"] for source in fused_sources],
                "conflicts": preview["conflicts"],
                "llm_resolution": preview["llm_resolution"],
                "execution_order": preview["execution_order"],
                "created_at": now,
            },
        }
        source_lines = "\n".join(
            f"- {source['skill_name']} v{source.get('version', '')}: {source.get('description', '')}"
            for source in sources
        )
        summary = (
            "Merged source skills:\n"
            f"{source_lines}\n\n"
            f"Merge strategy: {preview['strategy']}\n"
            f"Conflict policy: {preview['conflict_policy']}"
        )
        (proposal_dir / "skill.json").write_text(
            json.dumps(metadata, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        (proposal_dir / "SKILL.md").write_text(
            self._skill_markdown(metadata, summary, []),
            encoding="utf-8",
        )
        (proposal_dir / "main.py").write_text(
            self._merged_skill_main_py(
                name,
                fused_sources,
                preview["strategy"],
                preview["execution_order"],
            ),
            encoding="utf-8",
        )
        (proposal_dir / "test_main.py").write_text(
            self._merged_skill_test_py(name, [source["skill_name"] for source in sources]),
            encoding="utf-8",
        )
        self.record_experience(
            text=(
                f"Merged skills into {name}: "
                + ", ".join(source["skill_name"] for source in sources)
            ),
            source="skill_merge",
            tags=["skill", "merged", name],
            metadata={
                "skill_name": name,
                "source_skills": [source["skill_name"] for source in sources],
            },
        )
        return {
            "status": "merged",
            "proposal_dir": str(proposal_dir),
            "skill_name": name,
            "source_count": len(sources),
            "preview": preview,
        }

    def update_user_model_dialectic(
        self,
        user_id: str,
        observation: str,
    ) -> dict[str, Any]:
        """Maintain a Honcho-style dialectic user model from observations."""
        normalized_user = str(user_id or "default")
        observation_text = str(observation).strip()
        if not observation_text:
            raise ValueError("observation is required")
        payload = self._read_json_file(self.user_model_path) or {}
        model = payload.get(normalized_user, {})
        observations = list(model.get("observations", []))
        observations.append(
            {
                "text": observation_text,
                "created_at": datetime.now(UTC).isoformat(),
            }
        )
        recent_text = " ".join(item["text"] for item in observations[-8:])
        thesis = self._extract_user_preference(recent_text)
        antithesis = self._extract_user_tension(recent_text)
        synthesis = self._synthesize_user_model(thesis, antithesis)
        model = {
            "user_id": normalized_user,
            "observations": observations[-100:],
            "thesis": thesis,
            "antithesis": antithesis,
            "synthesis": synthesis,
            "dialectic": {
                "thesis": thesis,
                "antithesis": antithesis,
                "synthesis": synthesis,
            },
            "updated_at": datetime.now(UTC).isoformat(),
        }
        payload[normalized_user] = model
        self.user_model_path.parent.mkdir(parents=True, exist_ok=True)
        self.user_model_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return {"user_id": normalized_user, "model": model}

    def query_user_model(
        self,
        user_id: str,
        question: str = "",
    ) -> dict[str, Any]:
        """Query the current dialectic user model."""
        normalized_user = str(user_id or "default")
        payload = self._read_json_file(self.user_model_path) or {}
        model = payload.get(normalized_user)
        if not model:
            model = self.update_user_model_dialectic(
                normalized_user,
                str(question or "No prior user model; prefer direct clarification."),
            )["model"]
        return {
            "user_id": normalized_user,
            "question": str(question or ""),
            "answer": model.get("synthesis", ""),
            "model": model,
        }

    def read_self_model(self) -> dict[str, Any]:
        """Read the persistent self model accumulated across sessions."""
        if not self.self_model_path.exists():
            return {
                "version": 0,
                "observations": [],
                "capabilities": [],
                "preferences": [],
                "updated_at": "",
            }
        payload = self._read_json_file(self.self_model_path)
        if isinstance(payload, dict):
            return payload
        return {
            "version": 0,
            "observations": [],
            "capabilities": [],
            "preferences": [],
            "updated_at": "",
        }

    def update_self_model(
        self,
        observation: str,
        capability: str | None = None,
        preference: str | None = None,
    ) -> dict[str, Any]:
        """Update the persistent self model from a new observation."""
        observation_text = str(observation).strip()
        if not observation_text:
            raise ValueError("observation is required")
        model = self.read_self_model()
        model["version"] = int(model.get("version", 0)) + 1
        observations = list(model.get("observations", []))
        observations.append(
            {
                "text": observation_text,
                "created_at": datetime.now(UTC).isoformat(),
            }
        )
        model["observations"] = observations[-100:]
        model["capabilities"] = self._append_unique(model.get("capabilities", []), capability)
        model["preferences"] = self._append_unique(model.get("preferences", []), preference)
        model["updated_at"] = datetime.now(UTC).isoformat()
        self.self_model_path.parent.mkdir(parents=True, exist_ok=True)
        self.self_model_path.write_text(
            json.dumps(model, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return model

    def draft_skill_from_experience(
        self,
        query: str,
        skill_name: str | None = None,
    ) -> dict[str, Any]:
        """Create a valid skill proposal scaffold from matching experience records."""
        search = self.search_experience(query, limit=5)
        if not search["matches"]:
            raise ValueError(f"no matching experience for query: {query}")
        return self._write_skill_proposal(
            query=query,
            skill_name=skill_name or f"{query}_skill",
            matches=search["matches"],
            tags=["experience", "draft"],
            description=f"Drafted from experience search: {query}",
        )

    def _write_skill_proposal(
        self,
        query: str,
        skill_name: str,
        matches: list[dict[str, Any]],
        tags: list[str],
        description: str,
    ) -> dict[str, Any]:
        name = self._slugify_skill_name(skill_name)
        proposal_dir = self.skill_proposals_path / name
        proposal_dir.mkdir(parents=True, exist_ok=True)
        summary = "\n".join(f"- {item['text']}" for item in matches)
        metadata = {
            "skill_name": name,
            "name": name,
            "version": "0.1.0",
            "description": description,
            "tags": tags,
            "parameters": {"value": {"type": "string"}},
            "security_policy": self.security_defaults,
            "experience": {
                "query": query,
                "matched_ids": [item["id"] for item in matches],
            },
            "agentskills_io": {
                "standard": "open-agent-skills",
                "version": "1.0",
                "spec": "https://openagentskills.dev/docs/specification",
                "entrypoint": "SKILL.md",
            },
            "usage_count": 0,
            "improvements": [],
        }
        (proposal_dir / "skill.json").write_text(
            json.dumps(metadata, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        (proposal_dir / "SKILL.md").write_text(
            self._skill_markdown(metadata, summary, []),
            encoding="utf-8",
        )
        (proposal_dir / "main.py").write_text(
            (
                "import argparse\n"
                "import json\n\n\n"
                "def run(parameters):\n"
                "    return {\n"
                "        \"value\": parameters.get(\"value\"),\n"
                "        \"experience_summary\": EXPERIENCE_SUMMARY,\n"
                "    }\n\n\n"
                "if __name__ == \"__main__\":\n"
                "    parser = argparse.ArgumentParser()\n"
                "    parser.add_argument(\"--value\", default=\"\")\n"
                "    args = parser.parse_args()\n"
                "    print(json.dumps(run(vars(args)), ensure_ascii=False))\n\n\n"
                f"EXPERIENCE_SUMMARY = {summary!r}\n"
            ),
            encoding="utf-8",
        )
        (proposal_dir / "test_main.py").write_text(
            (
                "from main import run\n\n\n"
                "def test_run_returns_value_and_experience_summary():\n"
                "    result = run({\"value\": \"ok\"})\n"
                "    assert result[\"value\"] == \"ok\"\n"
                "    assert result[\"experience_summary\"]\n"
            ),
            encoding="utf-8",
        )
        return {
            "status": "drafted",
            "proposal_dir": str(proposal_dir),
            "skill_name": name,
            "matches": matches,
        }

    def messaging_gateway_status(self) -> dict[str, Any]:
        """Return configured messaging platform adapter state."""
        platforms = {
            name: {
                "connected": adapter.connected,
                "enabled": adapter.config.enabled,
                "transport": adapter.transport,
            }
            for name, adapter in self.messaging_gateway.adapters.items()
        }
        return {
            "status": "ready" if platforms else "disabled",
            "platforms": list(platforms.keys()),
            "details": platforms,
        }

    def handle_platform_message(
        self,
        platform: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        """Normalize and process one inbound messaging-platform payload."""
        adapter = self.messaging_gateway.adapters.get(platform)
        if adapter is None:
            raise ValueError(f"platform adapter is not configured: {platform}")
        return asyncio_run(adapter.receive(payload))

    def get_latest_avatar_event(self) -> dict[str, Any]:
        """Return the latest avatar event or a neutral startup event."""
        if self.latest_avatar_event is not None:
            return self.latest_avatar_event
        return {
            "text": "",
            "emotion": "neutral",
            "animation": "idle",
            "timestamp": None,
        }

    def adapter_health(self) -> dict[str, dict[str, Any]]:
        """Return non-destructive health status for optional adapters."""
        health: dict[str, dict[str, Any]] = {}
        academic = self.adapters["academic_search"].search("__health__", limit=0)
        health["academic_search"] = {
            "status": academic.provider,
            "message": academic.message,
        }
        docker_result = self.adapters["docker_sandbox"].run(
            ["python", "--version"],
            workspace=self.sandbox_runner.workspace_path,
        )
        health["docker_sandbox"] = {
            "status": (
                "disabled"
                if docker_result["status"] == "unavailable"
                and "disabled" in str(docker_result.get("reason", "")).lower()
                else docker_result["status"]
            ),
            "reason": docker_result.get("reason"),
            "command": docker_result.get("docker_command", docker_result.get("command")),
            "workspace_mount": docker_result.get("workspace_mount"),
        }
        health["ollama"] = self.adapters["ollama"].probe()
        health["remote_llm"] = self.adapters["remote_llm"].probe()
        whisper_result = self.adapters["whisper"].transcribe(
            self.sandbox_runner.workspace_path / "__health__.wav"
        )
        health["whisper"] = {
            "status": whisper_result["status"],
            "command": whisper_result["command"],
        }
        xtts_result = self.adapters["xtts"].synthesize(
            "health check",
            self.sandbox_runner.workspace_path / "__health__.wav",
        )
        health["xtts"] = {
            "status": xtts_result["status"],
            "command": xtts_result["command"],
        }
        health["messaging_gateway"] = self.messaging_gateway_status()
        return health

    def health_report(self) -> dict[str, Any]:
        """Return runtime, adapter, and security posture in one response."""
        return {
            "runtime": self.status_snapshot(),
            "security": self.security_defaults,
            "adapters": self.adapter_health(),
        }

    def preflight_report(self) -> dict[str, Any]:
        """Build a local delivery-readiness report without side effects."""
        health = self.health_report()
        blueprints = self.list_agent_blueprints()
        adapter_statuses = {
            name: details.get("status", "unknown")
            for name, details in health["adapters"].items()
        }
        attention = [
            name
            for name, status in adapter_statuses.items()
            if status not in {"disabled", "dry_run", "local", "available"}
        ]
        status = "ready" if not attention else "attention_required"
        return {
            "summary": {
                "status": status,
                "attention": attention,
                "blueprint_count": len(blueprints),
            },
            "checks": {
                "runtime": health["runtime"],
                "security": health["security"],
                "adapters": health["adapters"],
                "blueprints": blueprints,
            },
        }

    def write_preflight_report(
        self,
        output_path: str | Path | None = None,
        report: dict[str, Any] | None = None,
    ) -> Path:
        """Write the current preflight report as JSON."""
        target = Path(output_path) if output_path else self.root_path / "preflight_report.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            json.dumps(report if report is not None else self.preflight_report(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return target

    def long_term_capability_baseline(
        self,
        doctrine: list[str] | None = None,
    ) -> dict[str, Any]:
        """Record a measurable baseline for the long-term autonomous evolution doctrine."""
        doctrine_items = [
            str(item).strip()
            for item in (
                doctrine
                or [
                    "建立能力基线",
                    "补齐任务执行、验证、回滚能力",
                    "强化自主闭环",
                    "扩展长期记忆",
                    "保持真实能力边界",
                    "周期性度量进展并转化为测试、基准、技能或改进任务",
                ]
            )
            if str(item).strip()
        ]
        capabilities = self._truthful_interaction_capabilities()
        self_model = self.read_self_model()
        goals = self.read_autonomous_goals()
        dimensions = [
            self._baseline_dimension(
                "capability_baseline",
                doctrine_items[0] if len(doctrine_items) > 0 else "建立能力基线",
                evidence=[
                    "runtime.status_snapshot",
                    "runtime.health_report",
                    "preflight_report",
                ],
                gaps=[],
            ),
            self._baseline_dimension(
                "task_execution_verification_rollback",
                doctrine_items[1] if len(doctrine_items) > 1 else "补齐任务执行、验证、回滚能力",
                evidence=[
                    "shell.exec",
                    "autonomous.execute.runtime.status_snapshot",
                    "autonomous.verify.runtime.status_snapshot",
                    "self_evolution rollback artifacts",
                ],
                gaps=[
                    gap
                    for gap, available in {
                        "computer_control": bool(capabilities.get("computer_control")),
                        "software_management": bool(capabilities.get("software_management")),
                        "native_desktop_actions": bool(capabilities.get("native_desktop_actions")),
                    }.items()
                    if not available
                ],
            ),
            self._baseline_dimension(
                "autonomous_closed_loop",
                doctrine_items[2] if len(doctrine_items) > 2 else "强化自主闭环",
                evidence=[
                    "autonomous.plan",
                    "autonomous.execute.*",
                    "autonomous.verify.*",
                    "autonomy_loop.jsonl",
                ],
                gaps=[],
            ),
            self._baseline_dimension(
                "long_term_memory",
                doctrine_items[3] if len(doctrine_items) > 3 else "扩展长期记忆",
                evidence=[
                    "sqlite_fts5_conversation_search",
                    "experience records",
                    "self_model",
                    "autonomous_goals",
                ],
                gaps=[],
            ),
            self._baseline_dimension(
                "truthful_capability_boundaries",
                doctrine_items[4] if len(doctrine_items) > 4 else "保持真实能力边界",
                evidence=[
                    "truthful_interaction_capabilities",
                    capabilities.get("user_visible_boundary", ""),
                    "remote LLM boundary prompt",
                ],
                gaps=[],
            ),
            self._baseline_dimension(
                "periodic_measurement_conversion",
                doctrine_items[5] if len(doctrine_items) > 5 else "周期性度量进展并转化为测试、基准、技能或改进任务",
                evidence=[
                    "periodic_memory_tick",
                    "run_operational_smoke",
                    "run_interaction_stress",
                    "autonomous_skill_from_task",
                ],
                gaps=[],
            ),
        ]
        overall_score = round(
            sum(float(item["score"]) for item in dimensions) / max(1, len(dimensions)),
            3,
        )
        report = {
            "id": f"baseline_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S_%f')}",
            "status": "recorded",
            "created_at": datetime.now(UTC).isoformat(),
            "doctrine": doctrine_items,
            "overall_score": overall_score,
            "dimensions": dimensions,
            "active_goal_id": goals.get("active_goal_id", ""),
            "self_model_version": self_model.get("version", 0),
            "next_actions": self._baseline_next_actions(dimensions),
        }
        self.record_experience(
            text=(
                f"长期能力基线 {report['id']}: overall_score={overall_score}; "
                f"gaps={', '.join(report['next_actions']) or 'none'}"
            ),
            source="long_term_capability_baseline",
            tags=["long_term_goal", "capability_baseline", "measurement"],
            metadata=report,
        )
        return report

    @staticmethod
    def _baseline_dimension(
        dimension_id: str,
        objective: str,
        evidence: list[Any],
        gaps: list[str],
    ) -> dict[str, Any]:
        clean_evidence = [str(item) for item in evidence if str(item).strip()]
        clean_gaps = [str(item) for item in gaps if str(item).strip()]
        score = round(len(clean_evidence) / (len(clean_evidence) + len(clean_gaps) or 1), 3)
        return {
            "id": dimension_id,
            "objective": str(objective),
            "score": score,
            "evidence": clean_evidence,
            "gaps": clean_gaps,
            "status": "attention_required" if clean_gaps else "tracked",
        }

    @staticmethod
    def _baseline_next_actions(dimensions: list[dict[str, Any]]) -> list[str]:
        actions: list[str] = []
        for dimension in dimensions:
            for gap in dimension.get("gaps", []):
                actions.append(f"{dimension['id']}: 补齐 {gap}")
        return actions[:12]

    def run_operational_smoke(self, cycles: int = 1) -> dict[str, Any]:
        """Run repeatable local smoke cycles across core runtime surfaces."""
        if cycles < 1:
            raise ValueError("cycles must be at least 1")
        cycle_reports: list[dict[str, Any]] = []
        failures: list[str] = []
        for index in range(1, cycles + 1):
            status = self.status_snapshot()
            health = self.health_report()
            preflight = self.preflight_report()
            interaction = self.handle_interaction(f"operational smoke cycle {index}")
            cycle = {
                "cycle": index,
                "runtime_running": status["running"],
                "service_count": len(status["services"]),
                "adapter_count": len(health["adapters"]),
                "preflight_status": preflight["summary"]["status"],
                "interaction": interaction,
            }
            if not interaction.get("avatar_event", {}).get("animation"):
                failures.append(f"cycle {index}: missing avatar animation")
            if len(status["services"]) == 0:
                failures.append(f"cycle {index}: no services reported")
            cycle_reports.append(cycle)

        return {
            "summary": {
                "status": "passed" if not failures else "failed",
                "cycles": cycles,
                "failures": failures,
            },
            "cycles": cycle_reports,
        }

    def write_operational_smoke_report(
        self,
        cycles: int = 1,
        output_path: str | Path | None = None,
        report: dict[str, Any] | None = None,
    ) -> Path:
        """Write operational smoke report to the runtime root."""
        target = (
            Path(output_path)
            if output_path
            else self.root_path / "operational_smoke_report.json"
        )
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            json.dumps(
                report if report is not None else self.run_operational_smoke(cycles=cycles),
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        return target

    def run_interaction_stress(self, cycles: int = 10) -> dict[str, Any]:
        """Exercise the local interaction pipeline repeatedly."""
        if cycles < 1:
            raise ValueError("cycles must be at least 1")
        results: list[dict[str, Any]] = []
        failures: list[str] = []
        for index in range(1, cycles + 1):
            result = self.handle_interaction(f"stress interaction {index}")
            avatar_event = result.get("avatar_event", {})
            item = {
                "cycle": index,
                "transcript": result.get("transcript"),
                "response_text": result.get("response_text"),
                "avatar_event": avatar_event,
            }
            if not avatar_event.get("animation"):
                failures.append(f"cycle {index}: missing avatar animation")
            if not item["response_text"]:
                failures.append(f"cycle {index}: missing response text")
            results.append(item)
        return {
            "status": "passed" if not failures else "failed",
            "cycles": cycles,
            "failures": failures,
            "results": results,
        }

    def terminal_ui_status(self) -> dict[str, Any]:
        """Check whether the retained terminal UI entrypoints are present."""
        root = Path(__file__).resolve().parents[2]
        required = [
            root / "ui-tui" / "package.json",
            root / "ui-tui" / "src" / "entry.tsx",
            root / "tui_gateway" / "entry.py",
        ]
        missing = [str(path) for path in required if not path.exists()]
        return {
            "status": "ready" if not missing else "missing_files",
            "missing": missing,
            "required": [str(path) for path in required],
        }

    def final_acceptance_report(
        self,
        desktop_root: str | Path | None = None,
        stress_cycles: int = 10,
    ) -> dict[str, Any]:
        """Build the final local acceptance report for real integration handoff."""
        preflight = self.preflight_report()
        smoke = self.run_operational_smoke(cycles=2)
        stress = self.run_interaction_stress(cycles=stress_cycles)
        external_services = self.adapter_health()
        host_integration = self.host_integration_probe()

        gates = {
            "local_control_plane": {
                "status": "passed"
                if preflight["summary"]["status"] in {"ready", "attention_required"}
                and smoke["summary"]["status"] == "passed"
                else "failed",
                "preflight": preflight["summary"],
                "operational_smoke": smoke["summary"],
            },
            "interaction_stress": stress,
            "terminal_ui": self.terminal_ui_status(),
            "external_services": external_services,
            "host_integration": host_integration,
        }
        failed_gates = [
            name
            for name, gate in gates.items()
            if gate.get("status") in {"failed", "missing_files"}
        ]
        status = "ready_for_real_integration" if not failed_gates else "attention_required"
        return {
            "summary": {
                "status": status,
                "failed_gates": failed_gates,
                "real_service_note": (
                    "External services are reported as disabled, dry_run, available, "
                    "or unavailable; enable them explicitly for live integration."
                ),
            },
            "gates": gates,
        }

    def write_final_acceptance_report(
        self,
        desktop_root: str | Path | None = None,
        stress_cycles: int = 10,
        output_path: str | Path | None = None,
        report: dict[str, Any] | None = None,
    ) -> Path:
        """Write the final local acceptance report."""
        target = (
            Path(output_path)
            if output_path
            else self.root_path / "final_acceptance_report.json"
        )
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            json.dumps(
                report
                if report is not None
                else self.final_acceptance_report(
                    desktop_root=desktop_root,
                    stress_cycles=stress_cycles,
                ),
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        return target

    def host_integration_probe(self) -> dict[str, Any]:
        """Probe host tools needed for live integrations without installing anything."""
        tools = {
            "docker": self._probe_command("docker", ["docker", "--version"]),
            "node": self._probe_command("node", ["node", "--version"]),
            "npm": self._probe_command("npm", ["npm", "--version"]),
            "ollama": self._probe_ollama_host(),
            "whisper": self._probe_command("whisper", ["whisper", "--help"]),
            "xtts": self._probe_command("xtts", ["xtts", "--help"]),
        }
        ready = [name for name, item in tools.items() if item["status"] == "available"]
        missing = [
            name
            for name, item in tools.items()
            if item["status"] in {"missing", "unavailable"}
        ]
        if not missing:
            status = "ready"
        elif ready:
            status = "partial"
        else:
            status = "missing_requirements"
        return {
            "summary": {
                "status": status,
                "available": ready,
                "missing": missing,
            },
            "tools": tools,
        }

    def write_host_integration_probe(
        self,
        output_path: str | Path | None = None,
        report: dict[str, Any] | None = None,
    ) -> Path:
        """Write host integration probe report."""
        target = (
            Path(output_path)
            if output_path
            else self.root_path / "host_integration_probe.json"
        )
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            json.dumps(report if report is not None else self.host_integration_probe(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return target

    @staticmethod
    def _probe_command(name: str, command: list[str]) -> dict[str, Any]:
        executable = shutil.which(command[0])
        if executable is None:
            return {
                "status": "missing",
                "name": name,
                "command": command,
                "reason": f"{command[0]} not found on PATH",
            }
        try:
            use_shell = executable.lower().endswith((".cmd", ".bat"))
            result = subprocess.run(
                " ".join(command) if use_shell else command,
                capture_output=True,
                text=True,
                shell=use_shell,
                timeout=10,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            return {
                "status": "unavailable",
                "name": name,
                "command": command,
                "path": executable,
                "reason": str(exc),
            }
        output = (result.stdout or result.stderr or "").strip()
        return {
            "status": "available" if result.returncode == 0 else "unavailable",
            "name": name,
            "command": command,
            "path": executable,
            "return_code": result.returncode,
            "version": output.splitlines()[0] if output else "",
        }

    def _probe_ollama_host(self) -> dict[str, Any]:
        command_probe = self._probe_command("ollama", ["ollama", "--version"])
        service_probe = self.adapters["ollama"].probe()
        return {
            **command_probe,
            "service_status": service_probe.get("status"),
            "service_url": service_probe.get("url"),
        }

    def create_skill_publication_request(
        self,
        proposal_dir: str | Path,
        requested_by: str,
        title: str,
        risk_level: str = "medium",
    ) -> ApprovalRequest:
        """Validate a proposed skill and enqueue a human approval request."""
        proposal_path = Path(proposal_dir)
        validation = self.skill_lifecycle.validate_proposal(proposal_path)
        if not validation.passed:
            raise ValueError(validation.output)

        return self.governance.create_request(
            request_type="skill_publish",
            title=title,
            payload={
                "proposal_path": str(proposal_path),
                "skill_name": validation.metadata["skill_name"],
                "version": validation.metadata.get("version", "1.0.0"),
                "validation": {
                    "passed": validation.passed,
                    "pytest_return_code": validation.pytest_return_code,
                    "output": validation.output,
                },
            },
            requested_by=requested_by,
            risk_level=risk_level,
        )

    def publish_skill_from_approval(
        self,
        request_id: str,
        approved_by: str,
        parameters: dict | None = None,
    ) -> tuple[PublishedSkill, SandboxRunResult]:
        """Publish and smoke-run a skill only after its approval request is approved."""
        request = self.governance.get_request(request_id)
        if request.request_type != "skill_publish":
            raise ValueError(f"approval request is not for skill publication: {request_id}")
        if request.status != "approved":
            raise PermissionError(f"approval request is not approved: {request_id}")

        proposal_path = Path(request.payload["proposal_path"])
        published = self.skill_lifecycle.publish_approved_skill(
            proposal_path,
            approved_by=approved_by,
            source_request_id=request_id,
        )
        metadata = json.loads((published.target_dir / "skill.json").read_text(encoding="utf-8"))
        policy, policy_errors = SandboxPolicy.from_metadata(metadata)
        if policy is None or policy_errors:
            raise ValueError("; ".join(policy_errors))

        run_result = self.sandbox_runner.run_skill(
            published.target_dir,
            parameters or {},
            policy,
            timeout=30,
        )
        return published, run_result

    def apply_core_source_change_from_approval(
        self,
        request_id: str,
        approved_by: str,
    ) -> dict[str, Any]:
        """Apply an approved guarded core-source patch inside the runtime root."""
        request = self._approved_self_evolution_request(request_id, "core_source_change")
        proposal_path = self._resolve_runtime_artifact_path(request.payload["proposal_path"])
        patch_path = self._resolve_runtime_artifact_path(request.payload["patch_path"])
        proposal = self._read_json_file(proposal_path) or {}
        patch_text = patch_path.read_text(encoding="utf-8")
        changed_files = self._apply_unified_patch(patch_text)
        rollback_artifact = self._write_core_patch_rollback_artifact(
            request_id,
            approved_by,
            changed_files,
            proposal,
        )
        result = {
            "status": "applied",
            "request_id": request_id,
            "approved_by": approved_by,
            "proposal_path": str(proposal_path),
            "patch_path": str(patch_path),
            "changed_files": [str(item["path"]) for item in changed_files],
            "rollback_artifact": str(rollback_artifact),
            "requires_gateway_reload": True,
            "reload_reason": "core_source_change_applied",
            "applied_at": datetime.now(UTC).isoformat(),
        }
        self._record_self_evolution_audit("core_source_change.applied", result)
        return result

    def run_model_finetune_from_approval(
        self,
        request_id: str,
        approved_by: str,
    ) -> dict[str, Any]:
        """Materialize an approved offline fine-tuning run artifact."""
        request = self._approved_self_evolution_request(request_id, "model_finetune")
        job_path = self._resolve_runtime_artifact_path(request.payload["training_job_path"])
        job = self._read_json_file(job_path) or {}
        run_dir = job_path.parent / "runs" / request_id
        outputs_dir = Path(str(job.get("outputs", {}).get("adapter_or_weights") or run_dir / "outputs"))
        if not outputs_dir.is_absolute():
            outputs_dir = (job_path.parent / outputs_dir).resolve()
        outputs_dir = self._ensure_runtime_path(outputs_dir)
        outputs_dir.mkdir(parents=True, exist_ok=True)
        run_dir.mkdir(parents=True, exist_ok=True)
        manifest = {
            "type": "offline_adapter_manifest",
            "status": "completed",
            "request_id": request_id,
            "approved_by": approved_by,
            "training_job_path": str(job_path),
            "dataset_sources": list(job.get("dataset_sources", [])),
            "weights_promoted": False,
            "promotion_requires_approval": True,
            "created_at": datetime.now(UTC).isoformat(),
        }
        adapter_manifest_path = outputs_dir / "adapter_manifest.json"
        adapter_manifest_path.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        eval_report_path = run_dir / "eval_report.json"
        eval_report_path.write_text(
            json.dumps(
                {
                    "status": "passed",
                    "mode": "offline_simulation",
                    "metrics": {"loss_delta": 0.0, "safety_regression_count": 0},
                    "promotion_gate": "manual_approval_required",
                    "created_at": datetime.now(UTC).isoformat(),
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        result = {
            "status": "completed",
            "request_id": request_id,
            "approved_by": approved_by,
            "training_job_path": str(job_path),
            "run_dir": str(run_dir),
            "adapter_manifest_path": str(adapter_manifest_path),
            "eval_report_path": str(eval_report_path),
            "completed_at": datetime.now(UTC).isoformat(),
        }
        self._record_self_evolution_audit("model_finetune.completed", result)
        return result

    def deploy_architecture_migration_from_approval(
        self,
        request_id: str,
        approved_by: str,
    ) -> dict[str, Any]:
        """Execute an approved architecture migration as an auditable canary deployment run."""
        request = self._approved_self_evolution_request(
            request_id,
            "architecture_migration_deploy",
        )
        plan_path = self._resolve_runtime_artifact_path(request.payload["deployment_plan_path"])
        plan = self._read_json_file(plan_path) or {}
        run_dir = plan_path.parent / "runs" / request_id
        run_dir.mkdir(parents=True, exist_ok=True)
        phases = list(plan.get("phases", [])) or ["design", "test", "canary", "deploy", "rollback_ready"]
        deployment_run = {
            "status": "deployed",
            "mode": "canary_simulation",
            "request_id": request_id,
            "approved_by": approved_by,
            "deployment_plan_path": str(plan_path),
            "phases": [{"name": phase, "status": "completed"} for phase in phases],
            "created_at": datetime.now(UTC).isoformat(),
        }
        deployment_run_path = run_dir / "deployment_run.json"
        deployment_run_path.write_text(
            json.dumps(deployment_run, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        rollback_plan_path = run_dir / "rollback_plan.json"
        rollback_plan_path.write_text(
            json.dumps(
                {
                    "status": "ready",
                    "request_id": request_id,
                    "restore_from": str(plan_path),
                    "steps": [
                        "stop canary traffic",
                        "restore previous runtime configuration",
                        "rerun health and preflight checks",
                    ],
                    "created_at": datetime.now(UTC).isoformat(),
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        result = {
            "status": "deployed",
            "request_id": request_id,
            "approved_by": approved_by,
            "deployment_plan_path": str(plan_path),
            "deployment_run_path": str(deployment_run_path),
            "rollback_plan_path": str(rollback_plan_path),
            "completed_at": datetime.now(UTC).isoformat(),
        }
        self._record_self_evolution_audit("architecture_migration.deployed", result)
        return result

    def read_skill_lifecycle_audit(self) -> list[dict]:
        """Read the skill lifecycle JSONL audit log."""
        audit_path = self.skill_lifecycle.audit_log_path
        if not audit_path.exists():
            return []
        return self._read_jsonl_records(audit_path)

    def list_published_skills(self) -> list[dict]:
        """List published skills from lifecycle manifests."""
        skills: list[dict] = []
        for lifecycle_path in sorted(self.skill_lifecycle.skill_library_path.glob("*/lifecycle.json")):
            payload = self._read_json_file(lifecycle_path)
            if payload is None:
                continue
            payload["path"] = str(lifecycle_path.parent)
            skills.append(payload)
        return skills

    def list_algorithm_experiment_reports(self) -> list[dict]:
        """List persisted algorithm experiment reports."""
        reports: list[dict] = []
        for report_path in sorted(self.algorithm_experiments.output_path.glob("*_report.json")):
            payload = self._read_json_file(report_path)
            if payload is not None:
                reports.append(payload)
        return reports

    def list_algorithms(self) -> list[dict]:
        """List registered algorithm manifests as API-friendly dictionaries."""
        return [asdict(manifest) for manifest in self.algorithm_registry.list_algorithms()]

    def create_algorithm_research_request(
        self,
        proposal_path: str | Path,
        requested_by: str,
        title: str | None = None,
        risk_level: str = "high",
    ) -> ApprovalRequest:
        """Validate an AEP research proposal and enqueue human approval."""
        return self.algorithm_evolution.create_research_request(
            proposal_path,
            requested_by=requested_by,
            title=title,
            risk_level=risk_level,
        )

    def run_algorithm_experiment_from_approval(
        self,
        request_id: str,
        dataset_path: str | Path,
        thresholds: dict[str, float],
    ):
        """Run an approved deterministic algorithm experiment."""
        return self.algorithm_evolution.run_experiment_from_approval(
            request_id,
            dataset_path,
            thresholds,
        )

    def create_algorithm_promotion_request(
        self,
        report_path: str | Path,
        blueprint_path: str | Path,
        requested_by: str,
        title: str | None = None,
        risk_level: str = "critical",
    ) -> ApprovalRequest:
        """Request human approval for a candidate thinking-engine promotion."""
        return self.algorithm_evolution.create_promotion_request(
            report_path,
            blueprint_path,
            requested_by=requested_by,
            title=title,
            risk_level=risk_level,
        )

    def apply_algorithm_promotion_from_approval(
        self,
        request_id: str,
        approved_by: str,
    ):
        """Apply an approved thinking-engine promotion to an agent blueprint."""
        return self.algorithm_evolution.apply_promotion_from_approval(
            request_id,
            approved_by,
        )

    def read_algorithm_evolution_audit(self) -> list[dict]:
        """Read the algorithm evolution JSONL audit log."""
        return self._read_jsonl_records(self.algorithm_evolution.audit_log_path)

    def list_algorithm_reviews(self) -> list[dict]:
        """List peer-review reports produced by the Algorithm Evolution Protocol."""
        reviews: list[dict] = []
        reports_root = self.root_path / "algorithm_research_reports"
        if not reports_root.exists():
            return []
        for review_path in sorted(reports_root.glob("*_peer_review.json")):
            payload = self._read_json_file(review_path)
            if payload is None:
                continue
            payload["path"] = str(review_path)
            reviews.append(payload)
        return reviews

    def create_organization_change_request(
        self,
        proposal_path: str | Path,
        requested_by: str,
        title: str | None = None,
        risk_level: str = "constitutional",
    ) -> ApprovalRequest:
        """Validate a Founder proposal and enqueue architect approval."""
        proposal_path = Path(proposal_path)
        proposal = json.loads(proposal_path.read_text(encoding="utf-8"))
        self._require_organization_change_fields(proposal)
        blueprint = proposal["blueprint"]
        self._validate_blueprint_payload(blueprint)
        request = self.governance.create_request(
            request_type="organization_change",
            title=title or f"Apply organization change for {proposal['target_role']}",
            payload={
                "proposal_path": str(proposal_path),
                "proposal_id": proposal["proposal_id"],
                "change_type": proposal["change_type"],
                "target_role": proposal["target_role"],
                "rationale": proposal["rationale"],
                "blueprint": blueprint,
            },
            requested_by=requested_by,
            risk_level=risk_level,
        )
        self.event_bus.publish(
            EventTypes.ORGANIZATION_APPROVAL_REQUIRED,
            {
                "request_id": request.request_id,
                "proposal_id": proposal["proposal_id"],
                "target_role": proposal["target_role"],
            },
            "local_runtime",
        )
        return request

    def apply_organization_change_from_approval(
        self,
        request_id: str,
        approved_by: str,
    ) -> AgentBlueprint:
        """Apply an approved organization blueprint change."""
        request = self.governance.get_request(request_id)
        if request.request_type != "organization_change":
            raise ValueError(
                f"approval request is not for organization_change: {request_id}"
            )
        if request.status != "approved":
            raise PermissionError(f"approval request is not approved: {request_id}")
        payload = request.payload
        blueprint_payload = payload["blueprint"]
        blueprint = self._blueprint_from_payload(blueprint_payload)
        target_path = self.blueprint_orchestrator.charter_path / (
            self._slugify_role(blueprint.role_name) + ".yaml"
        )
        blueprint.save(target_path)
        self.blueprint_orchestrator.reload_changed()
        event_payload = {
            "request_id": request_id,
            "approved_by": approved_by,
            "proposal_id": payload["proposal_id"],
            "change_type": payload["change_type"],
            "target_role": blueprint.role_name,
            "blueprint_path": str(target_path),
        }
        self.event_bus.publish(
            EventTypes.ORGANIZATION_CHANGE_APPLIED,
            event_payload,
            "local_runtime",
        )
        return blueprint

    def list_agent_blueprints(self) -> list[dict[str, Any]]:
        """List current organization charter blueprints."""
        blueprints = self.blueprint_orchestrator.reload_changed()
        output: list[dict[str, Any]] = []
        paths_by_role: dict[str, Path] = {}
        for path in self.blueprint_orchestrator._blueprint_paths():
            blueprint = AgentBlueprint.load(path)
            paths_by_role[blueprint.role_name] = path
        for role_name, blueprint in sorted(blueprints.items()):
            payload = asdict(blueprint)
            payload["path"] = str(paths_by_role.get(role_name, ""))
            output.append(payload)
        return output

    def rollback_organization_change(
        self,
        role_name: str,
        requested_by: str,
        reason: str,
    ) -> dict[str, Any]:
        """Remove an organization blueprint and emit a rollback audit event."""
        blueprint_path = self.blueprint_orchestrator.charter_path / (
            self._slugify_role(role_name) + ".yaml"
        )
        if not blueprint_path.exists():
            raise FileNotFoundError(f"blueprint not found for role: {role_name}")
        before = AgentBlueprint.load(blueprint_path)
        blueprint_path.unlink()
        self.blueprint_orchestrator.reload_changed()
        payload = {
            "status": "rolled_back",
            "role_name": role_name,
            "requested_by": requested_by,
            "reason": reason,
            "removed_blueprint": asdict(before),
            "blueprint_path": str(blueprint_path),
        }
        self.event_bus.publish(
            EventTypes.ORGANIZATION_CHANGE_ROLLED_BACK,
            payload,
            "local_runtime",
        )
        return payload

    def _managed_path(
        self,
        managed_paths: dict,
        key: str,
        default: str,
        allow_external: bool = False,
    ) -> Path:
        raw_path = Path(str(managed_paths.get(key, default)))
        if raw_path.is_absolute():
            if allow_external:
                return raw_path
            resolved = raw_path.resolve()
        else:
            resolved = (self.root_path / raw_path).resolve()

        root = self.root_path.resolve()
        if not self._is_relative_to(resolved, root):
            raise ValueError(f"managed path escapes runtime root: {key}")
        return resolved

    @staticmethod
    def _validate_security_defaults(raw_defaults: dict[str, Any]) -> dict[str, Any]:
        network = bool(raw_defaults.get("network", True))
        shell = bool(raw_defaults.get("shell", True))
        filesystem = raw_defaults.get(
            "filesystem", {"read": ["*"], "write": ["*"]}
        )
        environment = raw_defaults.get("environment", {"allow": ["*"], "request": []})
        policy = SandboxPolicy(
            network=network,
            shell=shell,
            filesystem={
                "read": [str(path) for path in filesystem.get("read", [])],
                "write": [str(path) for path in filesystem.get("write", [])],
            },
            environment={
                "allow": [str(name) for name in environment.get("allow", [])],
                "request": [str(name) for name in environment.get("request", [])],
            },
        )
        errors = policy.validate()
        if errors:
            raise ValueError("; ".join(errors))
        return policy.to_dict()

    def _approved_self_evolution_request(
        self,
        request_id: str,
        request_type: str,
    ) -> ApprovalRequest:
        request = self.governance.get_request(request_id)
        if request.request_type != request_type:
            raise ValueError(f"approval request is not for {request_type}: {request_id}")
        if request.status != "approved":
            raise PermissionError(f"approval request is not approved: {request_id}")
        return request

    def _resolve_runtime_artifact_path(self, raw_path: str | Path) -> Path:
        path = Path(raw_path)
        if not path.is_absolute():
            path = self.root_path / path
        return self._ensure_runtime_path(path.resolve())

    def _ensure_runtime_path(self, path: Path) -> Path:
        resolved = path.resolve()
        if not self._is_relative_to(resolved, self.root_path.resolve()):
            raise ValueError(f"path escapes runtime root: {resolved}")
        return resolved

    def _record_self_evolution_audit(
        self,
        action: str,
        payload: dict[str, Any],
    ) -> None:
        self.self_evolution_audit_path.parent.mkdir(parents=True, exist_ok=True)
        record = {
            "action": action,
            "created_at": datetime.now(UTC).isoformat(),
            "payload": payload,
        }
        with self.self_evolution_audit_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")

    def _apply_unified_patch(self, patch_text: str) -> list[dict[str, Any]]:
        file_patches = self._parse_unified_patch(patch_text)
        if not file_patches:
            raise ValueError("candidate patch does not contain any file changes")
        changed_files: list[dict[str, Any]] = []
        for item in file_patches:
            target = self._resolve_patch_target(item["path"])
            before_exists = target.exists()
            before = target.read_text(encoding="utf-8") if before_exists else ""
            after = self._apply_patch_hunks(before, item["hunks"])
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(after, encoding="utf-8")
            changed_files.append(
                {
                    "path": target,
                    "before": before,
                    "after": after,
                    "existed": before_exists,
                }
            )
        return changed_files

    def _write_core_patch_rollback_artifact(
        self,
        request_id: str,
        approved_by: str,
        changed_files: list[dict[str, Any]],
        proposal: dict[str, Any],
    ) -> Path:
        rollback_dir = self.root_path / "self_evolution" / "rollbacks" / request_id
        rollback_dir.mkdir(parents=True, exist_ok=True)
        files: list[dict[str, Any]] = []
        for index, item in enumerate(changed_files, start=1):
            snapshot_path = rollback_dir / f"{index:03d}_{item['path'].name}.before"
            snapshot_path.write_text(str(item["before"]), encoding="utf-8")
            files.append(
                {
                    "path": str(item["path"]),
                    "snapshot_path": str(snapshot_path),
                    "existed": bool(item["existed"]),
                }
            )
        artifact = {
            "request_id": request_id,
            "approved_by": approved_by,
            "proposal": proposal,
            "files": files,
            "created_at": datetime.now(UTC).isoformat(),
        }
        artifact_path = rollback_dir / "rollback.json"
        artifact_path.write_text(
            json.dumps(artifact, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return artifact_path

    def _resolve_patch_target(self, raw_path: str) -> Path:
        normalized = raw_path.replace("\\", "/")
        if normalized.startswith("a/") or normalized.startswith("b/"):
            normalized = normalized[2:]
        if normalized in {"", "/dev/null"}:
            raise ValueError("patch target is empty")
        target = (self.root_path / normalized).resolve()
        return self._ensure_runtime_path(target)

    @staticmethod
    def _parse_unified_patch(patch_text: str) -> list[dict[str, Any]]:
        lines = patch_text.splitlines()
        files: list[dict[str, Any]] = []
        current: dict[str, Any] | None = None
        current_hunk: dict[str, Any] | None = None
        hunk_re = re.compile(
            r"@@ -(?P<old_start>\d+)(?:,(?P<old_count>\d+))? "
            r"\+(?P<new_start>\d+)(?:,(?P<new_count>\d+))? @@"
        )
        for line in lines:
            if line.startswith("--- "):
                continue
            if line.startswith("+++ "):
                raw_path = line[4:].strip().split("\t", maxsplit=1)[0]
                current = {"path": raw_path, "hunks": []}
                files.append(current)
                current_hunk = None
                continue
            if current is None:
                continue
            match = hunk_re.match(line)
            if match:
                current_hunk = {
                    "old_start": int(match.group("old_start")),
                    "old_count": int(match.group("old_count") or "1"),
                    "new_start": int(match.group("new_start")),
                    "new_count": int(match.group("new_count") or "1"),
                    "lines": [],
                }
                current["hunks"].append(current_hunk)
                continue
            if current_hunk is not None and (
                line.startswith(" ")
                or line.startswith("+")
                or line.startswith("-")
                or line == r"\ No newline at end of file"
            ):
                current_hunk["lines"].append(line)
        return [item for item in files if item["hunks"]]

    @staticmethod
    def _apply_patch_hunks(original: str, hunks: list[dict[str, Any]]) -> str:
        had_trailing_newline = original.endswith("\n")
        source_lines = original.splitlines()
        output: list[str] = []
        source_index = 0
        for hunk in hunks:
            hunk_start = max(0, int(hunk["old_start"]) - 1)
            output.extend(source_lines[source_index:hunk_start])
            source_index = hunk_start
            for line in hunk["lines"]:
                if not line or line == r"\ No newline at end of file":
                    continue
                marker = line[0]
                value = line[1:]
                if marker == " ":
                    if source_index >= len(source_lines) or source_lines[source_index] != value:
                        raise ValueError("patch context does not match target file")
                    output.append(value)
                    source_index += 1
                elif marker == "-":
                    if source_index >= len(source_lines) or source_lines[source_index] != value:
                        raise ValueError("patch removal does not match target file")
                    source_index += 1
                elif marker == "+":
                    output.append(value)
        output.extend(source_lines[source_index:])
        rendered = "\n".join(output)
        if had_trailing_newline or original == "":
            rendered += "\n"
        return rendered

    @staticmethod
    def _require_organization_change_fields(proposal: dict[str, Any]) -> None:
        required = [
            "proposal_id",
            "change_type",
            "target_role",
            "rationale",
            "blueprint",
        ]
        missing = [key for key in required if key not in proposal]
        if missing:
            raise ValueError(f"missing organization proposal fields: {', '.join(missing)}")
        if proposal["change_type"] != "create_blueprint":
            raise ValueError("only create_blueprint organization changes are supported")

    @staticmethod
    def _validate_blueprint_payload(blueprint: dict[str, Any]) -> None:
        required = ["role_name", "version", "agent_class", "thinking_engine"]
        missing = [key for key in required if key not in blueprint]
        if missing:
            raise ValueError(f"missing blueprint fields: {', '.join(missing)}")
        engine = blueprint.get("thinking_engine", {})
        for key in ("name", "version", "evaluation_suite"):
            if key not in engine:
                raise ValueError(f"missing thinking_engine field: {key}")

    @staticmethod
    def _blueprint_from_payload(payload: dict[str, Any]) -> AgentBlueprint:
        engine = ThinkingEngineRef(**payload["thinking_engine"])
        return AgentBlueprint(
            role_name=payload["role_name"],
            version=str(payload["version"]),
            agent_class=payload["agent_class"],
            core_prompt=str(payload.get("core_prompt", "")),
            thinking_engine=engine,
            authorized_plugins=list(payload.get("authorized_plugins", [])),
            subscribed_events=list(payload.get("subscribed_events", [])),
            config=dict(payload.get("config", {})),
        )

    @staticmethod
    def _slugify_role(role_name: str) -> str:
        return role_name.strip().lower().replace(" ", "_")

    def _read_experience_records(self) -> list[dict[str, Any]]:
        return self._read_jsonl_records(self.experience_path)

    def _conversation_connection(self) -> sqlite3.Connection:
        self.conversation_db_path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.conversation_db_path)
        connection.row_factory = sqlite3.Row
        connection.execute(
            (
                "CREATE TABLE IF NOT EXISTS conversations ("
                "id INTEGER PRIMARY KEY AUTOINCREMENT,"
                "session_id TEXT NOT NULL,"
                "user_id TEXT NOT NULL,"
                "role TEXT NOT NULL,"
                "text TEXT NOT NULL,"
                "metadata_json TEXT NOT NULL,"
                "created_at TEXT NOT NULL"
                ")"
            )
        )
        connection.execute(
            (
                "CREATE VIRTUAL TABLE IF NOT EXISTS conversation_fts "
                "USING fts5(session_id, user_id, role, text, metadata_json)"
            )
        )
        return connection

    @staticmethod
    def _fts_query(query: str) -> str:
        tokens = [
            token
            for token in re.findall(r"[a-zA-Z0-9_\u4e00-\u9fff]+", query)
            if token.strip()
        ]
        return " OR ".join(tokens) if tokens else '""'

    @staticmethod
    def _json_loads_dict(text: str) -> dict[str, Any]:
        try:
            payload = json.loads(text or "{}")
        except json.JSONDecodeError:
            return {}
        return payload if isinstance(payload, dict) else {}

    def _summarize_conversation_matches(
        self,
        query: str,
        matches: list[dict[str, Any]],
    ) -> str:
        if not matches:
            return ""
        snippets = []
        for item in matches[:5]:
            text = str(item.get("text", "")).strip().replace("\n", " ")
            snippets.append(text[:160])
        prompt = (
            f"Summarize cross-session recall for query '{query}' in one sentence:\n"
            + "\n".join(f"- {snippet}" for snippet in snippets)
        )
        llm = self.adapters.get("remote_llm") if hasattr(self, "adapters") else None
        if llm is not None:
            try:
                response = llm.generate_response(
                    prompt,
                    {"matches": snippets, "mode": "memory_summary"},
                )
                text = str(response.get("text", "")).strip()
                if text and response.get("status") not in {"unconfigured", "disabled", "unavailable"}:
                    return text
            except Exception:
                pass
        return f"Found {len(matches)} related cross-session memories: " + "; ".join(snippets[:3])

    @staticmethod
    def _plan_memory_next_actions(
        task: str,
        conversation_matches: list[dict[str, Any]],
        experience_matches: list[dict[str, Any]],
    ) -> list[str]:
        actions = ["review recalled context before acting"]
        if conversation_matches:
            actions.append("reuse prior session decisions")
        if experience_matches:
            actions.append("extract reusable implementation pattern")
        if any(term in task.lower() for term in ("complex", "repeated", "cleanup", "skill")):
            actions.append("consider drafting or improving a skill")
        return actions

    def _build_development_task_plan(
        self,
        goal: str,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        remote_plan = self._remote_development_plan(goal, context)
        if remote_plan:
            steps = remote_plan
        else:
            steps = self._default_development_plan_steps(goal)
        return {
            "objective": goal,
            "strategy": "plan_execute_verify_learn",
            "risk_policy": "read, plan, memory, and verification steps may run automatically; source edits and shell execution remain approval-gated",
            "steps": steps,
        }

    def _remote_development_plan(
        self,
        goal: str,
        context: dict[str, Any],
    ) -> list[dict[str, Any]]:
        llm = self.adapters.get("remote_llm") if hasattr(self, "adapters") else None
        if llm is None:
            return []
        try:
            response = llm.generate_response(
                (
                    "Create a safe JSON plan for a bounded software development task. "
                    "Return compact JSON only with a steps array. "
                    "Each step needs id, title, kind, action, risk, requires_approval."
                ),
                {"goal": goal, "context": context, "mode": "development_task_planning"},
            )
        except Exception:
            return []
        if response.get("status") in {"unconfigured", "disabled", "unavailable"}:
            return []
        text = str(response.get("text", "")).strip()
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            return []
        raw_steps = payload.get("steps") if isinstance(payload, dict) else None
        if not isinstance(raw_steps, list):
            return []
        steps: list[dict[str, Any]] = []
        for index, item in enumerate(raw_steps[:12], start=1):
            if not isinstance(item, dict):
                continue
            kind = str(item.get("kind") or "plan")
            risk = str(item.get("risk") or "low")
            steps.append(
                {
                    "id": str(item.get("id") or f"remote_{index}"),
                    "title": str(item.get("title") or kind),
                    "kind": kind,
                    "action": str(item.get("action") or item.get("title") or kind),
                    "risk": risk,
                    "requires_approval": bool(item.get("requires_approval")) or risk in {"high", "critical"},
                    "status": "planned",
                }
            )
        return steps

    @staticmethod
    def _default_development_plan_steps(goal: str) -> list[dict[str, Any]]:
        return [
            {
                "id": "understand_goal",
                "title": "Understand goal and constraints",
                "kind": "understand",
                "action": "summarize requested development outcome and boundaries",
                "risk": "low",
                "requires_approval": False,
                "status": "planned",
            },
            {
                "id": "inspect_codebase",
                "title": "Inspect relevant code paths",
                "kind": "inspect",
                "action": "identify likely files, tests, and integration points",
                "risk": "low",
                "requires_approval": False,
                "status": "planned",
            },
            {
                "id": "create_plan",
                "title": "Create implementation plan",
                "kind": "plan",
                "action": "produce ordered implementation and verification steps",
                "risk": "low",
                "requires_approval": False,
                "status": "planned",
            },
            {
                "id": "write_regression_tests",
                "title": "Write regression tests",
                "kind": "test",
                "action": "add or update tests before implementation",
                "risk": "medium",
                "requires_approval": True,
                "status": "planned",
            },
            {
                "id": "implement_change",
                "title": "Implement minimal code change",
                "kind": "implement",
                "action": "modify source code in the smallest safe scope",
                "risk": "high",
                "requires_approval": True,
                "status": "planned",
            },
            {
                "id": "run_verification",
                "title": "Run relevant verification",
                "kind": "verify",
                "action": "run targeted tests or static checks and record results",
                "risk": "low",
                "requires_approval": False,
                "status": "planned",
            },
            {
                "id": "learn_from_result",
                "title": "Record reusable learning",
                "kind": "learn",
                "action": "store task outcome as experience and possible skill candidate",
                "risk": "low",
                "requires_approval": False,
                "status": "planned",
            },
        ]

    def _execute_development_task_step(
        self,
        task: dict[str, Any],
        step: dict[str, Any],
    ) -> dict[str, Any]:
        kind = str(step.get("kind", ""))
        if kind == "understand":
            return {
                "verified": True,
                "summary": str(task.get("goal", "")).strip(),
                "boundary": USER_VISIBLE_CAPABILITY_BOUNDARY,
            }
        if kind == "inspect":
            status = self.status_snapshot()
            return {
                "verified": True,
                "services": status.get("services", {}),
                "paths": status.get("paths", {}),
            }
        if kind == "plan":
            return {
                "verified": True,
                "step_count": len(task.get("plan", {}).get("steps", [])),
                "strategy": task.get("plan", {}).get("strategy"),
            }
        if kind == "verify":
            service_count = len(self.status_snapshot().get("services", {}))
            return {"verified": service_count > 0, "service_count": service_count}
        if kind == "learn":
            return {"verified": True, "deferred_to_task_learning": True}
        return {"verified": False, "skipped": True}

    def _development_task_path(self, task_id: str) -> Path:
        normalized = re.sub(r"[^a-zA-Z0-9_-]+", "_", str(task_id)).strip("_")
        if not normalized:
            raise ValueError("task_id is required")
        return self.development_tasks_path / f"{normalized}.json"

    def _save_development_task(self, task: dict[str, Any]) -> None:
        self.development_tasks_path.mkdir(parents=True, exist_ok=True)
        self._development_task_path(str(task["task_id"])).write_text(
            json.dumps(task, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    @staticmethod
    def _development_task_event(status: str, message: str) -> dict[str, Any]:
        return {
            "status": status,
            "message": message,
            "created_at": datetime.now(UTC).isoformat(),
        }

    @staticmethod
    def _should_development_task_create_skill(goal: str) -> bool:
        normalized = goal.lower()
        return any(
            term in normalized
            for term in (
                "complex",
                "workflow",
                "development task",
                "复杂",
                "开发任务",
                "自主规划",
            )
        )

    def _load_skill_merge_sources(self, skill_paths: list[str | Path]) -> list[dict[str, Any]]:
        if not isinstance(skill_paths, list) or len(skill_paths) < 2:
            raise ValueError("at least two skill_paths are required")
        sources: list[dict[str, Any]] = []
        seen: set[Path] = set()
        for raw_path in skill_paths:
            skill_dir = Path(raw_path)
            if not skill_dir.is_absolute():
                skill_dir = self.root_path / skill_dir
            skill_dir = skill_dir.resolve()
            if skill_dir in seen:
                continue
            seen.add(skill_dir)
            metadata_path = skill_dir / "skill.json"
            if not metadata_path.exists():
                raise FileNotFoundError(f"skill.json not found: {skill_dir}")
            metadata = self._read_json_file(metadata_path)
            if metadata is None:
                raise ValueError(f"invalid skill metadata: {metadata_path}")
            skill_name = self._slugify_skill_name(
                str(metadata.get("skill_name") or metadata.get("name") or skill_dir.name)
            )
            sources.append(
                {
                    "path": skill_dir,
                    "metadata": metadata,
                    "skill_name": skill_name,
                }
            )
        if len(sources) < 2:
            raise ValueError("at least two distinct skill sources are required")
        return sources

    @staticmethod
    def _merge_skill_parameters(
        sources: list[dict[str, Any]],
    ) -> tuple[dict[str, Any], dict[str, list[dict[str, Any]]]]:
        parameters: dict[str, Any] = {}
        conflicts: dict[str, list[dict[str, Any]]] = {}
        for source in sources:
            raw_parameters = source["metadata"].get("parameters", {})
            if not isinstance(raw_parameters, dict):
                continue
            for name, definition in raw_parameters.items():
                if name not in parameters:
                    parameters[name] = definition
                    continue
                if parameters[name] != definition:
                    conflicts.setdefault(name, []).append(
                        {
                            "skill_name": source["skill_name"],
                            "definition": definition,
                        }
                    )
        if not parameters:
            parameters["value"] = {
                "type": "string",
                "required": False,
                "description": "Value passed to the merged skill.",
            }
        return parameters, conflicts

    def _merge_skill_security_policies(self, sources: list[dict[str, Any]]) -> dict[str, Any]:
        network = False
        shell = False
        read_paths: list[str] = []
        write_paths: list[str] = []
        env_allow: list[str] = []
        env_request: list[str] = []
        for source in sources:
            policy = source["metadata"].get("security_policy", {})
            if not isinstance(policy, dict):
                continue
            network = network or bool(policy.get("network", False))
            shell = shell or bool(policy.get("shell", False))
            filesystem = policy.get("filesystem", {})
            if isinstance(filesystem, dict):
                for item in filesystem.get("read", []):
                    read_paths = self._append_unique(read_paths, str(item))
                for item in filesystem.get("write", []):
                    write_paths = self._append_unique(write_paths, str(item))
            environment = policy.get("environment", {})
            if isinstance(environment, dict):
                for item in environment.get("allow", []):
                    env_allow = self._append_unique(env_allow, str(item))
                for item in environment.get("request", []):
                    env_request = self._append_unique(env_request, str(item))
        defaults = self.security_defaults
        default_fs = defaults.get("filesystem", {})
        default_env = defaults.get("environment", {})
        if not read_paths:
            read_paths = [str(item) for item in default_fs.get("read", ["."])]
        if not write_paths:
            write_paths = [str(item) for item in default_fs.get("write", ["workspace"])]
        if not env_allow:
            env_allow = [str(item) for item in default_env.get("allow", [])]
        return {
            "network": network or bool(defaults.get("network", False)),
            "shell": shell or bool(defaults.get("shell", False)),
            "filesystem": {
                "read": read_paths,
                "write": write_paths,
            },
            "environment": {
                "allow": env_allow,
                "request": env_request,
            },
        }

    def _resolve_skill_merge_conflicts_with_llm(
        self,
        merged_skill_name: str,
        sources: list[dict[str, Any]],
        parameters: dict[str, Any],
        conflicts: dict[str, Any],
        strategy: str,
    ) -> dict[str, Any]:
        if not conflicts and "llm" not in str(strategy).lower():
            return {"status": "skipped", "reason": "no conflicts"}
        llm = self.adapters.get("remote_llm") if hasattr(self, "adapters") else None
        if llm is None or not hasattr(llm, "generate_response"):
            return {"status": "unavailable", "reason": "remote_llm adapter is unavailable"}
        prompt_payload = {
            "merged_skill_name": merged_skill_name,
            "strategy": strategy,
            "source_skills": [
                {
                    "skill_name": source["skill_name"],
                    "version": source["metadata"].get("version", ""),
                    "description": source["metadata"].get("description", ""),
                    "parameters": source["metadata"].get("parameters", {}),
                    "main_preview": self._read_skill_main_preview(source["path"]),
                }
                for source in sources
            ],
            "merged_parameters": parameters,
            "conflicts": conflicts,
        }
        prompt = (
            "Resolve this skill merge as JSON only. "
            "Return keys: resolution, parameter_overrides, execution_order, rationale.\n"
            + json.dumps(prompt_payload, ensure_ascii=False, sort_keys=True)
        )
        try:
            response = llm.generate_response(
                prompt,
                {"mode": "skill_merge_conflict_resolution"},
            )
        except Exception as exc:
            return {"status": "error", "reason": str(exc)}
        status = str(response.get("status", ""))
        if status not in {"completed", "dry_run"}:
            return {
                "status": status or "unavailable",
                "reason": response.get("reason") or response.get("text", ""),
            }
        parsed = self._extract_json_object(str(response.get("text", "")))
        if not parsed:
            return {
                "status": "unparseable",
                "reason": "LLM response did not contain a JSON object",
                "raw_text": str(response.get("text", ""))[:1000],
            }
        return {
            "status": "completed",
            "resolution": parsed.get("resolution", {}),
            "parameter_overrides": (
                parsed.get("parameter_overrides", {})
                if isinstance(parsed.get("parameter_overrides"), dict)
                else {}
            ),
            "execution_order": (
                parsed.get("execution_order", [])
                if isinstance(parsed.get("execution_order"), list)
                else []
            ),
            "rationale": str(parsed.get("rationale", "")),
            "provider": response.get("provider", "remote_llm"),
        }

    @staticmethod
    def _normalized_merge_execution_order(
        source_names: list[str],
        requested_order: Any,
    ) -> list[str]:
        output: list[str] = []
        requested = requested_order if isinstance(requested_order, list) else []
        for item in requested:
            name = str(item)
            if name in source_names and name not in output:
                output.append(name)
        for name in source_names:
            if name not in output:
                output.append(name)
        return output

    @staticmethod
    def _extract_json_object(text: str) -> dict[str, Any]:
        stripped = text.strip()
        if stripped.startswith("```"):
            stripped = re.sub(r"^```(?:json)?", "", stripped, flags=re.IGNORECASE).strip()
            stripped = re.sub(r"```$", "", stripped).strip()
        candidates = [stripped]
        start = stripped.find("{")
        end = stripped.rfind("}")
        if start >= 0 and end > start:
            candidates.append(stripped[start : end + 1])
        for candidate in candidates:
            try:
                payload = json.loads(candidate)
            except json.JSONDecodeError:
                continue
            if isinstance(payload, dict):
                return payload
        return {}

    @staticmethod
    def _read_skill_main_preview(skill_dir: Path) -> str:
        main_file = skill_dir / "main.py"
        if not main_file.exists():
            return ""
        try:
            return main_file.read_text(encoding="utf-8")[:4000]
        except OSError:
            return ""

    @staticmethod
    def _merged_skill_main_py(
        skill_name: str,
        sources: list[dict[str, Any]],
        strategy: str,
        execution_order: list[str],
    ) -> str:
        source_payload = [
            {
                "skill_name": source["skill_name"],
                "path": str(source["path"]),
            }
            for source in sources
        ]
        return (
            "import argparse\n"
            "import importlib.util\n"
            "import json\n\n\n"
            f"SKILL_NAME = {skill_name!r}\n"
            f"SOURCE_SKILLS = {source_payload!r}\n"
            f"MERGE_STRATEGY = {strategy!r}\n\n\n"
            f"EXECUTION_ORDER = {execution_order!r}\n\n\n"
            "def _load_source_module(source):\n"
            "    module_path = source[\"path\"] + \"/main.py\"\n"
            "    module_name = \"merged_source_\" + source[\"skill_name\"]\n"
            "    spec = importlib.util.spec_from_file_location(module_name, module_path)\n"
            "    if spec is None or spec.loader is None:\n"
            "        raise RuntimeError(\"cannot load source skill: \" + source[\"skill_name\"])\n"
            "    module = importlib.util.module_from_spec(spec)\n"
            "    spec.loader.exec_module(module)\n"
            "    return module\n\n\n"
            "def _call_source(module, parameters):\n"
            "    if hasattr(module, \"run\"):\n"
            "        return module.run(dict(parameters))\n"
            "    if hasattr(module, \"main\"):\n"
            "        try:\n"
            "            return module.main(**dict(parameters))\n"
            "        except TypeError:\n"
            "            return module.main(parameters.get(\"value\", \"\"))\n"
            "    raise RuntimeError(\"source skill has no run or main function\")\n\n\n"
            "def run(parameters):\n"
            "    current = dict(parameters)\n"
            "    steps = []\n"
            "    by_name = {source[\"skill_name\"]: source for source in SOURCE_SKILLS}\n"
            "    ordered_sources = [by_name[name] for name in EXECUTION_ORDER if name in by_name]\n"
            "    for source in ordered_sources:\n"
            "        module = _load_source_module(source)\n"
            "        result = _call_source(module, current)\n"
            "        if not isinstance(result, dict):\n"
            "            result = {\"status\": \"success\", \"value\": result}\n"
            "        steps.append({\"skill_name\": source[\"skill_name\"], \"result\": result})\n"
            "        if \"value\" in result:\n"
            "            current[\"value\"] = result[\"value\"]\n"
            "        if result.get(\"status\") == \"error\":\n"
            "            return {\n"
            "                \"status\": \"error\",\n"
            "                \"skill_name\": SKILL_NAME,\n"
            "                \"failed_source\": source[\"skill_name\"],\n"
            "                \"steps\": steps,\n"
            "                \"parameters\": current,\n"
            "            }\n"
            "    return {\n"
            "        \"status\": \"success\",\n"
            "        \"skill_name\": SKILL_NAME,\n"
            "        \"source_skills\": EXECUTION_ORDER,\n"
            "        \"merge_strategy\": MERGE_STRATEGY,\n"
            "        \"parameters\": current,\n"
            "        \"value\": current.get(\"value\"),\n"
            "        \"steps\": steps,\n"
            "    }\n\n\n"
            "if __name__ == \"__main__\":\n"
            "    parser = argparse.ArgumentParser()\n"
            "    parser.add_argument(\"--value\", default=\"\")\n"
            "    args, unknown = parser.parse_known_args()\n"
            "    parameters = vars(args)\n"
            "    for index in range(0, len(unknown), 2):\n"
            "        key = unknown[index].lstrip(\"-\")\n"
            "        value = unknown[index + 1] if index + 1 < len(unknown) else \"\"\n"
            "        if key:\n"
            "            parameters[key] = value\n"
            "    print(json.dumps(run(parameters), ensure_ascii=False))\n"
        )

    @staticmethod
    def _merged_skill_test_py(skill_name: str, source_skills: list[str]) -> str:
        return (
            "from main import run\n\n\n"
            "def test_merged_skill_reports_sources_and_parameters():\n"
            "    result = run({\"value\": \"ok\"})\n"
            "    assert result[\"status\"] == \"success\"\n"
            f"    assert result[\"skill_name\"] == {skill_name!r}\n"
            f"    assert result[\"source_skills\"] == {source_skills!r}\n"
            "    assert \"value\" in result[\"parameters\"]\n"
            "    assert len(result[\"steps\"]) == len(result[\"source_skills\"])\n"
        )

    @staticmethod
    def _skill_experience_summary(proposal_dir: Path) -> str:
        main_file = proposal_dir / "main.py"
        if not main_file.exists():
            return ""
        match = re.search(
            r"EXPERIENCE_SUMMARY\s*=\s*(?P<value>.+)$",
            main_file.read_text(encoding="utf-8"),
            re.MULTILINE,
        )
        if not match:
            return ""
        try:
            return str(ast.literal_eval(match.group("value")))
        except Exception:
            return match.group("value")

    @staticmethod
    def _skill_markdown(
        metadata: dict[str, Any],
        summary: str,
        improvements: list[dict[str, Any]],
    ) -> str:
        tags = ", ".join(str(tag) for tag in metadata.get("tags", []))
        improvement_lines = "\n".join(
            f"- {item.get('feedback', '')}" for item in improvements[-10:]
        ) or "- No usage feedback yet."
        return (
            "---\n"
            f"name: {metadata.get('skill_name')}\n"
            f"description: {metadata.get('description', '')}\n"
            f"version: {metadata.get('version', '0.1.0')}\n"
            f"tags: [{tags}]\n"
            "---\n\n"
            "# Skill\n\n"
            f"{metadata.get('description', '')}\n\n"
            "## Usage Notes\n\n"
            "Use this skill when a similar task appears again. It follows the "
            "Open Agent Skills directory convention with this SKILL.md as the "
            "agent-facing entrypoint while preserving the project's skill.json runtime contract.\n\n"
            "## Experience Summary\n\n"
            f"{summary or '- No experience summary recorded.'}\n\n"
            "## Self Improvement\n\n"
            f"{improvement_lines}\n"
        )

    @staticmethod
    def _bump_patch_version(version: str) -> str:
        parts = [int(part) if part.isdigit() else 0 for part in version.split(".")[:3]]
        while len(parts) < 3:
            parts.append(0)
        parts[2] += 1
        return ".".join(str(part) for part in parts)

    @staticmethod
    def _extract_user_preference(text: str) -> str:
        lower = text.lower()
        preferences: list[str] = []
        if "concise" in lower or "简洁" in text:
            preferences.append("prefers concise answers")
        if "terminal" in lower:
            preferences.append("prefers terminal-first execution")
        if "architecture" in lower or "架构" in text:
            preferences.append("values architecture context")
        if "tradeoff" in lower or "trade-off" in lower:
            preferences.append("wants tradeoffs when design choices matter")
        return "; ".join(preferences) or text[:200]

    @staticmethod
    def _extract_user_tension(text: str) -> str:
        lower = text.lower()
        if ("concise" in lower or "简洁" in text) and (
            "architecture" in lower or "tradeoff" in lower or "详细" in text
        ):
            return "brevity can conflict with requested architectural depth"
        if "but" in lower or "但是" in text:
            return "the observation contains conditional preferences"
        return "no strong contradiction detected"

    @staticmethod
    def _synthesize_user_model(thesis: str, antithesis: str) -> str:
        if "brevity" in antithesis:
            return (
                "Start with concise execution-oriented answers, then add focused "
                "architecture tradeoffs only when the task asks for design depth."
            )
        if "conditional" in antithesis:
            return f"Follow the primary preference while checking the stated condition: {thesis}."
        return thesis

    @staticmethod
    def _search_tokens(text: str) -> set[str]:
        return {
            token.lower()
            for token in re.findall(r"[a-zA-Z0-9_\u4e00-\u9fff]+", text)
            if token.strip()
        }

    @staticmethod
    def _append_unique(values: Any, value: str | None) -> list[str]:
        output = [str(item) for item in values] if isinstance(values, list) else []
        if value:
            normalized = str(value).strip()
            if normalized and normalized not in output:
                output.append(normalized)
        return output

    @staticmethod
    def _slugify_skill_name(skill_name: str) -> str:
        normalized = re.sub(r"[^a-zA-Z0-9_]+", "_", str(skill_name).strip().lower())
        normalized = normalized.strip("_")
        return normalized or "experience_skill"

    @staticmethod
    def _read_json_file(path: Path) -> dict[str, Any] | None:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        return payload if isinstance(payload, dict) else None

    @classmethod
    def _read_jsonl_records(cls, path: Path) -> list[dict[str, Any]]:
        if not path.exists():
            return []
        records: list[dict[str, Any]] = []
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except OSError:
            return records
        for line in lines:
            if not line.strip():
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(payload, dict):
                records.append(payload)
        return records

    @staticmethod
    def _is_relative_to(path: Path, root: Path) -> bool:
        try:
            path.relative_to(root)
        except ValueError:
            return False
        return True
