from __future__ import annotations

"""Planning and execution agent built on the skill library.

This module provides a small executor that breaks down a high level goal into
sub‑tasks, locates skills to handle each step and runs them sequentially.  It
relies on the :class:`LibrarianAgent` for skill discovery and uses the global
message queue for coordination when a required skill is missing.
"""

from dataclasses import dataclass
import importlib.util
import json
import threading
from typing import Any, Dict, Iterable, List

from autogpt.config import Config
from autogpt.event_bus import (
    EventMessage,
    MessageQueue,
    SKILL_CREATED,
    SKILL_REQUESTED,
)
from autogpt.llm import ChatSequence, Message
from autogpt.llm.utils import create_chat_completion
from autogpt.logs import logger
from autogpt.skills.librarian import LibrarianAgent


@dataclass
class PlannedStep:
    """Representation of a planned sub‑task."""

    description: str


class Executor:
    """Simple agent that plans a goal and executes skills sequentially."""

    def __init__(
        self,
        config: Config | None = None,
        librarian: LibrarianAgent | None = None,
        message_queue: MessageQueue | None = None,
        confidence_threshold: float = 0.7,
        skill_wait_timeout: float = 120.0,
    ) -> None:
        self.config = config or Config()
        self.librarian = librarian or LibrarianAgent(self.config)
        self.message_queue = message_queue or MessageQueue()
        self.confidence_threshold = confidence_threshold
        self.skill_wait_timeout = skill_wait_timeout

        # Event used to resume execution once a new skill becomes available
        self._skill_created_event = threading.Event()
        self.message_queue.subscribe(SKILL_CREATED, self._on_skill_created)

    # ------------------------------------------------------------------
    def _on_skill_created(self, _: EventMessage) -> None:
        """Callback triggered when a new skill is registered."""

        self._skill_created_event.set()

    # ------------------------------------------------------------------
    def plan(self, goal: str) -> List[PlannedStep]:
        """Use an LLM to break ``goal`` into an ordered list of sub‑tasks."""

        system = (
            "You are an expert planner."
            " Break the user's goal into an ordered list of discrete sub‑tasks."
            " Respond using a JSON array of strings.""
        )
        prompt = ChatSequence.for_model(
            self.config.smart_llm,
            [
                Message("system", system),
                Message("user", goal),
            ],
        )

        response = create_chat_completion(prompt, self.config, temperature=0)
        content = response.content or "[]"
        try:
            tasks = json.loads(content)
            if not isinstance(tasks, list):
                raise ValueError
        except Exception:
            # Fallback: split by lines
            tasks = [line.strip("- ") for line in content.splitlines() if line.strip()]

        return [PlannedStep(description=str(t)) for t in tasks]

    # ------------------------------------------------------------------
    def compose(self, sub_task: str) -> dict[str, Any] | None:
        """Find a skill for ``sub_task`` and fill in its parameters using an LLM."""

        results = self.librarian.find_skill(sub_task, top_k=1)
        if not results:
            return None

        meta = results[0]
        meta_json = json.dumps(meta)
        system = (
            "You are selecting a skill for a sub-task."
            " Given the sub-task description and the skill metadata,"
            " fill in the required parameters."
            " Respond with JSON {\"skill_name\": str, \"version\": str,"
            " \"parameters\": {..}, \"confidence\": float}""
        )
        prompt = ChatSequence.for_model(
            self.config.smart_llm,
            [
                Message("system", system),
                Message(
                    "user",
                    f"Sub-task: {sub_task}\nSkill metadata: {meta_json}",
                ),
            ],
        )

        resp = create_chat_completion(prompt, self.config, temperature=0)
        try:
            data = json.loads(resp.content or "{}")
        except Exception:
            data = {}
        data.setdefault("skill_name", meta.get("skill_name"))
        data.setdefault("version", meta.get("version"))
        data.setdefault("parameters", {})
        data.setdefault("confidence", 0.0)
        return data

    # ------------------------------------------------------------------
    def _load_skill(self, name: str, version: str):
        """Dynamically import the skill module and return its ``run`` function."""

        skill_dir = (
            self.librarian.skill_library.storage_path / f"{name}_{version}"
        )
        main_path = skill_dir / "main.py"
        spec = importlib.util.spec_from_file_location(
            f"skill_{name}_{version}", main_path
        )
        if spec is None or spec.loader is None:
            raise ImportError(f"Cannot import skill {name}:{version}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        run_func = getattr(module, "run", None)
        if not callable(run_func):
            raise AttributeError(f"Skill {name}:{version} has no runnable 'run' function")
        return run_func

    # ------------------------------------------------------------------
    def execute(self, plan: Iterable[PlannedStep]) -> List[Any]:
        """Execute each step in ``plan`` sequentially and return their results."""

        results: List[Any] = []
        for step in plan:
            while True:
                skill_spec = self.compose(step.description)
                confidence = (
                    skill_spec.get("confidence", 0) if skill_spec else 0
                )
                if not skill_spec or confidence < self.confidence_threshold:
                    logger.info(
                        "No suitable skill for '%s'; requesting creation", step.description
                    )
                    self.message_queue.publish(
                        EventMessage(
                            event_type=SKILL_REQUESTED,
                            payload={"sub_task": step.description},
                            source_agent="executor",
                        )
                    )
                    # Wait until a new skill is registered before retrying
                    if not self._skill_created_event.wait(
                        timeout=self.skill_wait_timeout
                    ):
                        logger.warning(
                            "Timeout waiting for skill creation for '%s'",
                            step.description,
                        )
                        results.append(None)
                        break
                    self._skill_created_event.clear()
                    continue

                run = self._load_skill(
                    skill_spec["skill_name"], skill_spec.get("version", "1.0")
                )
                params: Dict[str, Any] = skill_spec.get("parameters", {})
                try:
                    results.append(run(**params))
                except Exception:
                    logger.exception(
                        "Execution of skill %s failed", skill_spec["skill_name"]
                    )
                    results.append(None)
                break
        return results


__all__ = ["Executor", "PlannedStep"]
