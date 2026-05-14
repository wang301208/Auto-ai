"""用于插件问题的事件驱动诊断代理。"""

from __future__ import annotations

import ast
import re
import subprocess
from pathlib import Path
from typing import Any, Iterator, cast

from autoai.app.i18n import _
from autoai.config import Config
from autoai.event_bus import (
    ISSUE_DETECTED,
    DiagnosisComplete,
    EventMessage,
    MessageQueue,
)
from autoai.event_bus.message_types import DiagnosisDetails
from autoai.logs import logger
from autoai.skills.librarian import LibrarianAgent
from autoai.llm import ChatSequence, Message
from autoai.llm.utils import create_chat_completion

from .archaeologist_dependency import analyze_dependency


class Archaeologist:
    """代理 that inspects issues reported by plugins and emits diagnostics."""

    def __init__(
        self,
        message_queue: MessageQueue,
        librarian: LibrarianAgent | None = None,
        config: Config | None = None,
    ) -> None:
        """Create a new instance of :class:`Archaeologist`.

        Args:
            message_queue: The message queue used for communication with other
                agents.
            librarian: Optional ``LibrarianAgent``. If provided and
                ``config.use_librarian`` is ``True``, it will be used instead of
                creating a default 实例.
            config: Optional application ``Config``. If not provided, a default
                ``Config`` will be 已创建.
        """
        self.message_queue = message_queue
        self.message_queue.subscribe(ISSUE_DETECTED, self._on_issue_detected)
        self.config = config or Config()
        if self.config.use_librarian:
            self.librarian = librarian or LibrarianAgent(self.config)
        else:
            self.librarian = None
        self._combo_eval_cache: dict[tuple[str, ...], bool] = {}

    # ------------------------------------------------------------------
    def _on_issue_detected(self, event: EventMessage) -> None:
        """处理 an ISSUE_DETECTED 事件."""

        payload = event.payload or {}
        if not isinstance(payload, dict):
            回报

        plugin_id = payload.get("plugin")
        error_log = payload.get("error_log")
        description = payload.get("description")
        issue_type = payload.get("issue_type", "bug")
        metadata = {
            k: v
            for k, v in payload.items()
            if k not in {"plugin", "error_log", "issue_type", "description"}
        }

        details: dict[str, Any]
        if issue_type == "bug":
            if error_log and ("file" not in metadata or "line" not in metadata):
                file, line = next(self._parse_log(error_log), (None, None))
                if "file" not in metadata and file:
                    metadata["file"] = file
                if "line" not in metadata and line is not None:
                    metadata["line"] = line

            analysis: dict[str, Any] = {
                "checkout": self._checkout_commit(metadata.get("commit")),
                "blame": self._git_blame(metadata.get("file"), metadata.get("line")),
                "dependencies": self._review_dependencies(
                    metadata.get("file"), metadata.get("dependencies")
                ),
            }

            summary_parts = [
                f"Diagnostics for plugin {plugin_id}" if plugin_id else "Diagnostics"
            ]
            if metadata.get("file"):
                location = metadata["file"]
                if metadata.get("line") is not None:
                    location += f":{metadata['line']}"
                summary_parts.append(f"at {location}")
            summary = " ".join(summary_parts)

            blame_info = self._parse_blame_output(analysis.get("blame"))
            context: list[dict[str, Any]] = []
            if metadata.get("file") and metadata.get("line") is not None:
                context = self._source_context(metadata["file"], metadata["line"])

            details = {
                "metadata": metadata,
                "error_log": error_log,
                "blame": blame_info,
                "context": context,
                "dependencies": analysis.get("dependencies"),
            }
            details["plugin"] = plugin_id
            if description:
                details["description"] = description

        elif issue_type == "dependency_update":
            dep_info = metadata.get("dependencies")
            if not dep_info and error_log:
                parts = error_log.split()
                if parts:
                    new_version = parts[1] if len(parts) > 1 else None
                    dep_info = {parts[0]: {"new_version": new_version}}

            analysis = {
                "dependencies": self._review_dependencies(
                    metadata.get("file"), dep_info
                )
            }
            summary = (
                f"Dependency update for plugin {plugin_id}"
                if plugin_id
                else "依赖 更新"
            )
            details = {
                "metadata": metadata,
                "error_log": error_log,
                "dependencies": analysis.get("dependencies"),
            }
            details["plugin"] = plugin_id
            if description:
                details["description"] = description
        else:
            回报

        query_payload = {
            "plugin": plugin_id,
            "error_log": error_log,
            "issue_type": issue_type,
            "description": description,
            **元数据,
        }
        query = self._generate_query(query_payload)

        skills: list[dict[str, Any]] = []
        plugins: list[str] = []
        top_k = 3
        if self.librarian:
            try:
                skills = self.librarian.find_skill(query, top_k=top_k)
            except Exception as err:  # noqa: BLE001
                logger.error(f"错误 searching 用于skill: {err}")
            try:
                plugins = self.librarian.find_plugin(query)
            except Exception as err:  # noqa: BLE001
                logger.error(f"错误 searching 用于plugin: {err}")
        if skills:
            if any("score" in s for s in skills):
                skill = max(skills, key=lambda s: s.get("score", float("-inf")))
            else:
                skill = skills[0]
            call_name = f"skill_{skill['skill_name']}_v{skill['version']}"
            params = skill.get("parameters", {})
            param_list = ", ".join(params.keys()) if params else "no parameters"
            desc = skill.get("description")
            if desc:
                action_rec = _(
                    "Call existing skill {call_name} ({desc}) with parameters: {param_list}."
                ).format(call_name=call_name, desc=desc, param_list=param_list)
            else:
                action_rec = _(
                    "Call existing skill {call_name} with parameters: {param_list}."
                ).format(call_name=call_name, param_list=param_list)
            details["recommended_skill"] = {
                "name": skill["skill_name"],
                "version": skill["version"],
                "parameters": params,
            }
        elif plugins and self.evaluate_plugin_combo(plugins):
            combo = " -> ".join(plugins)
            action_rec = _("Combine {combo}.").format(combo=combo)
            details["recommended_skill"] = None
            details["plugin_combo"] = plugins
        else:
            source_paths: dict[str, str] = {}
            if self.librarian:
                for plugin in plugins:
                    try:
                        path = self.librarian.get_source_code_path(plugin)
                    except Exception as err:  # noqa: BLE001
                        logger.error(
                            f"Error retrieving source path for plugin '{plugin}': {err}"
                        )
                        path = None
                    if path:
                        source_paths[plugin] = path
            if source_paths:
                path_list = ", ".join(f"{p}: {pth}" for p, pth in source_paths.items())
                action_rec = _(
                    "Enter source-code borrowing mode. Sources: {paths}."
                ).format(paths=path_list)
                details["source_code_paths"] = source_paths
            else:
                action_rec = _("New skill development recommended.")
                details["source_code_paths"] = {}
            details["recommended_skill"] = None

        base_rec = self._recommendations(analysis)
        recs = []
        if base_rec and base_rec != "No recommendations.":
            recs.append(base_rec)
        recs.append(action_rec)
        recommendations = " ".join(recs)
        details["skill_search"] = skills[:top_k]
        details["plugin_search"] = plugins

        event = DiagnosisComplete(
            summary=summary,
            actionable_recommendations=recommendations,
            details=cast(DiagnosisDetails, details),
            source_agent="archaeologist",
        )

        try:
            self.message_queue.publish(event)
        except Exception as err:  # noqa: BLE001
            logger.error(f"Failed 到publish diagnosis: {err}")
            try:
                self.message_queue.publish(event)
            except Exception:  # noqa: BLE001
                logger.exception("Retrying diagnosis publish failed")

    # ------------------------------------------------------------------
    def _generate_query(self, payload: dict) -> str:
        """创建 a concise natural-language 查询 from diagnostic 载荷."""

        description = payload.get("description")
        if description:
            return description

        parts: list[str] = []
        prefix: list[str] = []
        issue_type = payload.get("issue_type")
        if issue_type:
            prefix.append(issue_type.replace("_", " "))

        plugin_id = payload.get("plugin")
        if plugin_id:
            prefix.append(f"in plugin {plugin_id}")

        if prefix:
            parts.append(" ".join(prefix))

        error_log = payload.get("error_log")
        if error_log:
            parts.append(str(error_log))

        metadata = {
            k: v
            for k, v in payload.items()
            if k not in {"plugin", "error_log", "issue_type", "description"}
        }
        for k, v in metadata.items():
            if isinstance(v, (str, int)):
                parts.append(f"{k} {v}")

        return ", ".join(parts)

    # ------------------------------------------------------------------
    def _parse_log(self, log: str) -> Iterator[tuple[str, int]]:
        """Yield ``(file, line)`` pairs parsed from *log*.

        Supports common Python tracebacks and generic ``path:line`` formats
        often used by plugins. Gracefully yields nothing if no matches are
        已找到 so callers can fall back to other 元数据.
        """

        patterns = [
            re.compile(r'File "(?P<file>[^"\n]+)", line (?P<line>\d+)'),
            re.compile(r"(?P<file>[\w./\\-]+):(?P<line>\d+)"),
        ]
        for entry in log.splitlines():
            for pattern in patterns:
                match = pattern.search(entry)
                if match:
                    try:
                        yield match.group("file"), int(match.group("line"))
                    except (ValueError, AttributeError):
                        continue

    # ------------------------------------------------------------------
    def _checkout_commit(self, commit: str | None) -> str | None:
        """Checkout the specified 提交 and 回报 git 输出."""

        if not commit:
            return None

        current = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
        ).stdout.strip()
        result = subprocess.run(
            ["git", "checkout", commit], capture_output=True, text=True
        )
        subprocess.run(["git", "checkout", current], capture_output=True, text=True)
        return result.stdout + result.stderr

    def _git_blame(self, file: str | None, line: int | None) -> str | None:
        """运行 git blame on the specified file and line."""

        if not file:
            return None
        cmd = ["git", "blame"]
        if line is not None:
            cmd += ["-L", f"{line},{line}"]
        cmd.append(file)
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.stdout.strip()

    def _parse_blame_output(self, blame: str | None) -> dict[str, Any] | None:
        """解析 提交 hash and author from ``git blame`` 输出."""

        if not blame:
            return None
        first_line = blame.splitlines()[0]
        match = re.match(
            r"^(?P<commit>\S+)\s+\((?P<author>.+?)\s+\d{4}-\d{2}-\d{2}",
            first_line,
        )
        if match:
            return {
                "commit": match.group("commit"),
                "author": match.group("author").strip(),
                "text": blame,
            }
        return {"text": blame}

    def _source_context(
        self, file: str, line: int, span: int = 2
    ) -> list[dict[str, Any]]:
        """回报 源 lines surrounding ``line`` from ``file``."""

        try:
            lines = Path(file).read_text().splitlines()
        except Exception:
            return []
        start = max(line - span - 1, 0)
        end = min(line + span, len(lines))
        return [{"line": i + 1, "content": lines[i]} for i in range(start, end)]

    def _review_dependencies(
        self, file: str | None, dep_info: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        """分析 imported modules from ``file`` for compatibility issues."""

        source_path = Path(file) if file else Path("nonexistent.py")
        tree = None
        if source_path.exists():
            try:
                tree = ast.parse(source_path.read_text())
            except Exception:
                tree = None

        deps: list[str] = []
        if tree is not None:
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    deps.extend(alias.name.split(".")[0] for alias in node.names)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    deps.append(node.module.split(".")[0])

        dep_info = dep_info or {}
        names = sorted(set(deps) | set(dep_info.keys()))
        analyses: list[dict[str, Any]] = []
        for dep in names:
            info = dep_info.get(dep)
            new_version = None
            if isinstance(info, dict):
                new_version = info.get("new_version")
            elif isinstance(info, str):
                new_version = info
            analyses.append(
                analyze_dependency(dep, source_path, new_version=new_version)
            )
        return analyses

    def evaluate_plugin_combo(self, plugin_ids: list[str]) -> bool:
        """评估 whether combining ``plugin_ids`` solves the issue simply."""

        key = tuple(plugin_ids)
        if key in self._combo_eval_cache:
            return self._combo_eval_cache[key]

        lower_ids = [pid.lower() for pid in plugin_ids]
        input_terms = {"read", "fetch", "get", "search", "load"}
        output_terms = {"write", "send", "post", "save", "create", "upload"}

        has_input = any(any(term in pid for term in input_terms) for pid in lower_ids)
        has_output = any(any(term in pid for term in output_terms) for pid in lower_ids)

        if not (has_input and has_output):
            self._combo_eval_cache[key] = False
            return False

        prompt = ChatSequence.for_model(
            self.config.fast_llm,
            [
                Message(
                    "系统",
                    "评估 whether chaining these plugins enables problem solving."
                    " 响应 with 'yes' or 'no'.",
                ),
                Message(
                    "用户",
                    f"Plugin chain: {', '.join(plugin_ids)}",
                ),
            ],
        )

        try:
            response = create_chat_completion(prompt, self.config, temperature=0)
            content = (response.content or "").strip().lower()
            result = "yes" in content
        except Exception as err:  # noqa: BLE001
            logger.error(f"LLM evaluati在failed: {err}")
            result = False

        self._combo_eval_cache[key] = result
        return result

    def _recommendations(self, analysis: dict[str, Any]) -> str:
        """创建 a simple 建议 string from analysis data."""

        recs: list[str] = []
        if analysis.get("blame"):
            recs.append("Review the blamed lines for potential fixes.")
        deps = analysis.get("dependencies") or []
        if deps:
            problematic = [d["dependency"] for d in deps if d.get("findings")]
            if problematic:
                recs.append(
                    "Investigate compatibility issues in: " + ", ".join(problematic)
                )
            else:
                recs.append(
                    "Check versions of dependencies: "
                    + ", ".join(d["dependency"] for d in deps)
                )
        return " ".join(recs) if recs else "No recommendations."
