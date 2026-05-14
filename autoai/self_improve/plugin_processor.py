"""Utilities to process plugin TODO items and apply patches."""

from __future__ import annotations

from pathlib import Path
from threading import Event, Thread
from typing import List

from .database import DatabaseManager
from .patcher import PatchAgent
from .plugin_todo_queue import PluginTodo, PluginTodoQueue
from .yaml_exporter import export_prompt_config


def generate_diff(context: str) -> str:
    """Generate a unified diff for ``context`` using an LLM.

    ``context`` should outline the desired code modifications, including file
    paths relative to the project root.  The LLM is prompted to respond with a
    unified diff.  Any leading ``a/`` or ``b/`` prefixes are stripped so the
    diff can be applied with ``patch -p0``.
    """

    # 导入 lazily so heavy LLM dependencies are only loaded when required and
    # can easily be monkeypatched in tests.
    from autoai.config import Config
    from autoai.llm.base import ChatSequence, Message
    from autoai.llm.utils import create_chat_completion

    cfg = Config()

    system_prompt = (
        "You are an AI software engineer. Given some context, generate a unified "
        "diff that implements the requested changes. Paths must be relative to "
        "the project root and must not include 'a/' or 'b/' prefixes. Only output "
        "the diff."
    )

    prompt = ChatSequence.for_model(
        cfg.smart_llm,
        [
            Message.system(system_prompt),
            Message.user(context),
        ],
    )

    result = create_chat_completion(prompt=prompt, temperature=0, config=cfg)
    diff = (result.content or "").strip()

    # Drop optional code fences from the 模型 输出
    if diff.startswith("```"):
        lines = diff.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        diff = "\n".join(lines)

    # Normalise paths so the diff can be applied with 补丁 -p0
    cleaned: list[str] = []
    for line in diff.splitlines():
        if line.startswith("--- ") or line.startswith("+++ "):
            prefix, path = line[:4], line[4:].strip()
            if path.startswith("a/") or path.startswith("b/"):
                path = path[2:]
            cleaned.append(prefix + path)
        else:
            cleaned.append(line)

    cleaned_diff = "\n".join(cleaned)
    if not cleaned_diff.endswith("\n"):
        cleaned_diff += "\n"
    return cleaned_diff


def _files_from_diff(diff: str, workspace: Path) -> List[Path]:
    """Extract file paths from a unified diff string."""

    files: List[Path] = []
    for line in diff.splitlines():
        if line.startswith("+++ ") or line.startswith("--- "):
            path = line[4:].strip()
            if path in ("", "/dev/null"):
                continue
            if path.startswith("a/") or path.startswith("b/"):
                path = path[2:]
            file_path = (workspace / path).resolve()
            if file_path not in files:
                files.append(file_path)
    return files


def handle_plugin_todo(
    todo: PluginTodo,
    patch_agent: PatchAgent,
    db: DatabaseManager,
    workspace: Path,
) -> None:
    """Process a single plugin TODO item."""

    try:
        diff = generate_diff(todo.context)
        patch_agent.apply_diff(diff, cwd=workspace)
        files = _files_from_diff(diff, workspace)
        patch_agent.verify(files)
        export_prompt_config(workspace)
        db.log_execution(f"Plugin TODO {todo.gap}", "success")
    except Exception as err:
        db.log_execution(f"Plugin TODO {todo.gap}", f"failure: {err}")


def start_plugin_queue_processor(
    plugin_queue: PluginTodoQueue,
    patch_agent: PatchAgent,
    db: DatabaseManager,
    workspace: Path,
    interval: float = 60.0,
) -> tuple[Thread, Event]:
    """Start background thread to consume plugin TODO queue."""

    stop_event = Event()

    def worker() -> None:
        while not stop_event.is_set():
            todo = plugin_queue.pop()
            if todo is None:
                # Use the 事件 to 允许 a graceful 关闭 during 等待中
                stop_event.wait(interval)
                continue
            handle_plugin_todo(todo, patch_agent, db, workspace)

    thread = Thread(target=worker, daemon=True)
    thread.start()
    return thread, stop_event
