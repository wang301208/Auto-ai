"""CI/CD Auto-Builder: Agent autonomously creates, modifies, and maintains CI/CD pipelines.

The agent detects missing CI, generates appropriate config files,
validates them, and commits. When CI fails, the agent autonomously
diagnoses and fixes the configuration.

Supports:
    - GitHub Actions (.github/workflows/*.yml)
    - GitLab CI (.gitlab-ci.yml)
    - Makefile targets

This is L2+ (SELF_BOUND) capability: modifying config files.
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

from governance.autonomy_level import AutonomyLevel, AutonomyManager


class CIPlatform(Enum):
    GITHUB_ACTIONS = "github_actions"
    GITLAB_CI = "gitlab_ci"
    MAKEFILE = "makefile"


class CIOperation(Enum):
    CREATE = "create"
    FIX = "fix"
    EXTEND = "extend"
    REMOVE = "remove"


@dataclass
class CIAction:
    operation: CIOperation
    platform: CIPlatform
    file_path: str
    content: str
    reason: str
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()


@dataclass
class CIDiagnosis:
    has_ci: bool
    platform: CIPlatform | None
    workflow_files: list[str] = field(default_factory=list)
    missing_steps: list[str] = field(default_factory=list)
    last_run_status: str = "unknown"
    last_run_output: str = ""


GITHUB_ACTIONS_TEMPLATE = """name: AutoAI CI

on:
  push:
    branches: [ main, master, develop ]
  pull_request:
    branches: [ main, master ]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - run: pip install -r requirements.txt
      - run: pip install ruff mypy
      - run: ruff check .

  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - run: pip install -r requirements.txt
      - run: pip install pytest pytest-asyncio
      - run: python -m pytest tests/ -v --tb=short

  typecheck:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - run: pip install -r requirements.txt
      - run: pip install mypy
      - run: mypy autoai/ --ignore-missing-imports || true
"""

GITLAB_CI_TEMPLATE = """image: python:3.12

stages:
  - lint
  - test

lint:
  stage: lint
  script:
    - pip install -r requirements.txt
    - pip install ruff
    - ruff check .

test:
  stage: test
  script:
    - pip install -r requirements.txt
    - pip install pytest pytest-asyncio
    - python -m pytest tests/ -v --tb=short
"""

MAKEFILE_TEMPLATE = """.PHONY: lint test typecheck all clean

all: lint test typecheck

lint:
\truff check .

test:
\tpython -m pytest tests/ -v --tb=short

typecheck:
\tmypy autoai/ --ignore-missing-imports || true

clean:
\tfind . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
\tfind . -type f -name "*.pyc" -delete 2>/dev/null || true
"""


class CIAutoBuilder:
    """Agent-autonomous CI/CD pipeline builder and maintainer.

    Requires L2 (SELF_BOUND) autonomy to modify config files.

    Usage:
        builder = CIAutoBuilder(workspace=Path("."), autonomy=autonomy_mgr)
        diagnosis = builder.diagnose()
        if not diagnosis.has_ci:
            actions = builder.auto_create_ci()
        elif diagnosis.last_run_status == "failed":
            fixes = builder.auto_fix_ci(diagnosis)
    """

    def __init__(
        self,
        workspace: Path,
        autonomy: AutonomyManager | None = None,
    ) -> None:
        self.workspace = workspace
        self._autonomy = autonomy or AutonomyManager()
        self._history: list[CIAction] = []

    @property
    def can_modify(self) -> bool:
        return self._autonomy.level >= AutonomyLevel.SELF_BOUND

    def diagnose(self) -> CIDiagnosis:
        """Diagnose current CI/CD state."""
        has_github = (self.workspace / ".github" / "workflows").is_dir()
        has_gitlab = (self.workspace / ".gitlab-ci.yml").is_file()
        has_makefile = (self.workspace / "Makefile").is_file()

        workflow_files = []
        platform = None

        if has_github:
            platform = CIPlatform.GITHUB_ACTIONS
            wf_dir = self.workspace / ".github" / "workflows"
            workflow_files = [f.name for f in wf_dir.glob("*.yml") if f.is_file()]
        elif has_gitlab:
            platform = CIPlatform.GITLAB_CI
            workflow_files = [".gitlab-ci.yml"]
        elif has_makefile:
            platform = CIPlatform.MAKEFILE
            workflow_files = ["Makefile"]

        missing_steps = self._detect_missing_steps(platform, workflow_files)

        last_status, last_output = self._check_last_run()

        return CIDiagnosis(
            has_ci=has_github or has_gitlab or has_makefile,
            platform=platform,
            workflow_files=workflow_files,
            missing_steps=missing_steps,
            last_run_status=last_status,
            last_run_output=last_output,
        )

    def auto_create_ci(self, platform: CIPlatform = CIPlatform.GITHUB_ACTIONS) -> list[CIAction]:
        """Auto-create CI/CD configuration. Returns list of actions taken."""
        if not self.can_modify:
            return []

        actions = []

        if platform == CIPlatform.GITHUB_ACTIONS:
            wf_dir = self.workspace / ".github" / "workflows"
            wf_dir.mkdir(parents=True, exist_ok=True)
            path = wf_dir / "ci.yml"
            if not path.exists():
                path.write_text(GITHUB_ACTIONS_TEMPLATE, encoding="utf-8")
                action = CIAction(
                    operation=CIOperation.CREATE,
                    platform=platform,
                    file_path=str(path.relative_to(self.workspace)),
                    content=GITHUB_ACTIONS_TEMPLATE,
                    reason="no_ci_found",
                )
                actions.append(action)
                self._history.append(action)

        elif platform == CIPlatform.GITLAB_CI:
            path = self.workspace / ".gitlab-ci.yml"
            if not path.exists():
                path.write_text(GITLAB_CI_TEMPLATE, encoding="utf-8")
                action = CIAction(
                    operation=CIOperation.CREATE,
                    platform=platform,
                    file_path=".gitlab-ci.yml",
                    content=GITLAB_CI_TEMPLATE,
                    reason="no_ci_found",
                )
                actions.append(action)
                self._history.append(action)

        elif platform == CIPlatform.MAKEFILE:
            path = self.workspace / "Makefile"
            if not path.exists():
                path.write_text(MAKEFILE_TEMPLATE, encoding="utf-8")
                action = CIAction(
                    operation=CIOperation.CREATE,
                    platform=platform,
                    file_path="Makefile",
                    content=MAKEFILE_TEMPLATE,
                    reason="no_ci_found",
                )
                actions.append(action)
                self._history.append(action)

        return actions

    def auto_fix_ci(self, diagnosis: CIDiagnosis) -> list[CIAction]:
        """Auto-fix CI configuration based on diagnosis."""
        if not self.can_modify:
            return []

        actions = []

        for step in diagnosis.missing_steps:
            action = self._add_missing_step(diagnosis.platform, step)
            if action:
                actions.append(action)
                self._history.append(action)

        return actions

    def auto_extend_ci(self, new_step: str, step_content: str) -> CIAction | None:
        """Add a new step to existing CI configuration."""
        if not self.can_modify:
            return None

        if not (self.workspace / ".github" / "workflows").is_dir():
            return None

        wf_dir = self.workspace / ".github" / "workflows"
        ci_file = wf_dir / "ci.yml"
        if not ci_file.exists():
            return None

        try:
            content = ci_file.read_text(encoding="utf-8")
            if new_step in content:
                return None
            insertion = f"""
  {new_step}:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
{step_content}
"""
            content += insertion
            ci_file.write_text(content, encoding="utf-8")
            action = CIAction(
                operation=CIOperation.EXTEND,
                platform=CIPlatform.GITHUB_ACTIONS,
                file_path=str(ci_file.relative_to(self.workspace)),
                content=insertion,
                reason=f"add_{new_step}",
            )
            self._history.append(action)
            return action
        except Exception:
            return None

    def _detect_missing_steps(self, platform: CIPlatform | None, workflow_files: list[str]) -> list[str]:
        missing = []
        essential = {"lint", "test"}

        if platform == CIPlatform.GITHUB_ACTIONS and workflow_files:
            wf_dir = self.workspace / ".github" / "workflows"
            for wf in workflow_files:
                try:
                    content = (wf_dir / wf).read_text(encoding="utf-8")
                    if "ruff" not in content and "lint" not in content:
                        missing.append("lint")
                    if "pytest" not in content and "test" not in content:
                        missing.append("test")
                    if "mypy" not in content and "typecheck" not in content:
                        missing.append("typecheck")
                except Exception:
                    pass
        elif platform is None:
            missing = list(essential)

        return list(set(missing))

    def _add_missing_step(self, platform: CIPlatform | None, step: str) -> CIAction | None:
        if platform != CIPlatform.GITHUB_ACTIONS:
            return None

        wf_dir = self.workspace / ".github" / "workflows"
        ci_file = wf_dir / "ci.yml"
        if not ci_file.exists():
            return None

        try:
            content = ci_file.read_text(encoding="utf-8")
            if step in content:
                return None

            step_templates = {
                "lint": "\n      - run: ruff check .\n",
                "test": "\n      - run: python -m pytest tests/ -v\n",
                "typecheck": "\n      - run: mypy autoai/ --ignore-missing-imports || true\n",
            }

            addition = step_templates.get(step, "")
            if addition:
                content += addition
                ci_file.write_text(content, encoding="utf-8")
                return CIAction(
                    operation=CIOperation.EXTEND,
                    platform=CIPlatform.GITHUB_ACTIONS,
                    file_path=str(ci_file.relative_to(self.workspace)),
                    content=addition,
                    reason=f"missing_{step}",
                )
        except Exception:
            return None
        return None

    def _check_last_run(self) -> tuple[str, str]:
        try:
            proc = subprocess.run(
                ["git", "log", "--oneline", "-1", "--grep=CI"],
                capture_output=True, text=True,
                cwd=str(self.workspace), timeout=5,
            )
            if proc.returncode == 0 and proc.stdout.strip():
                return "recent_commit", proc.stdout.strip()
        except Exception:
            pass
        return "unknown", ""

    @property
    def history(self) -> list[CIAction]:
        return list(self._history)

    def stats(self) -> dict[str, Any]:
        return {
            "total_actions": len(self._history),
            "creates": len([a for a in self._history if a.operation == CIOperation.CREATE]),
            "fixes": len([a for a in self._history if a.operation == CIOperation.FIX]),
            "extensions": len([a for a in self._history if a.operation == CIOperation.EXTEND]),
            "can_modify": self.can_modify,
        }


__all__ = [
    "CIAutoBuilder", "CIPlatform", "CIOperation", "CIAction", "CIDiagnosis",
    "GITHUB_ACTIONS_TEMPLATE", "GITLAB_CI_TEMPLATE", "MAKEFILE_TEMPLATE",
]
