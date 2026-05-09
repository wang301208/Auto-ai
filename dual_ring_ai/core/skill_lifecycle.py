"""
Controlled lifecycle for generated skills.

Generated skills must be validated before they are published into the shared
skill library. This module keeps that path separate from git deployment so
the system can approve capabilities without merging arbitrary branches.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import ast
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .event_bus import EventBus, EventTypes


REQUIRED_SKILL_FILES = ("skill.json", "test_main.py", "main.py")


@dataclass
class SkillValidationResult:
    """Result from validating a proposed skill directory."""

    passed: bool
    skill_dir: Path
    missing_files: list[str]
    metadata: dict[str, Any]
    pytest_return_code: int | None
    output: str


@dataclass
class SandboxPolicy:
    """Security policy for generated skill execution."""

    network: bool
    shell: bool
    filesystem: dict[str, list[str]]
    environment: dict[str, list[str]] = field(default_factory=dict)

    @classmethod
    def from_metadata(cls, metadata: dict[str, Any]) -> tuple["SandboxPolicy | None", list[str]]:
        raw_policy = metadata.get("security_policy")
        if raw_policy is None:
            return None, ["security_policy is required"]
        if not isinstance(raw_policy, dict):
            return None, ["security_policy must be an object"]

        filesystem = raw_policy.get("filesystem", {})
        if not isinstance(filesystem, dict):
            return None, ["security_policy.filesystem must be an object"]
        environment = raw_policy.get("environment", {})
        if not isinstance(environment, dict):
            return None, ["security_policy.environment must be an object"]

        policy = cls(
            network=bool(raw_policy.get("network", False)),
            shell=bool(raw_policy.get("shell", False)),
            filesystem={
                "read": [str(path) for path in filesystem.get("read", [])],
                "write": [str(path) for path in filesystem.get("write", [])],
            },
            environment={
                "allow": [str(name) for name in environment.get("allow", [])],
                "request": [str(name) for name in environment.get("request", [])],
            },
        )
        return policy, policy.validate()

    def validate(self) -> list[str]:
        errors: list[str] = []
        allowed_env = set(self.environment.get("allow", []))
        for requested_env in self.environment.get("request", []):
            if "*" not in allowed_env and requested_env not in allowed_env:
                errors.append(f"environment variable not allowed: {requested_env}")

        return errors

    def to_dict(self) -> dict[str, Any]:
        return {
            "network": self.network,
            "shell": self.shell,
            "filesystem": self.filesystem,
            "environment": self.environment,
        }


@dataclass
class PublishedSkill:
    """Metadata for a skill published into the shared library."""

    skill_name: str
    version: str
    target_dir: Path
    lifecycle_path: Path


class SkillLifecycleManager:
    """Validate and publish approved generated skills."""

    def __init__(
        self,
        skill_library_path: str | Path,
        event_bus: EventBus,
        audit_log_path: str | Path = "logs/skill_lifecycle_audit.jsonl",
    ) -> None:
        self.skill_library_path = Path(skill_library_path)
        self.event_bus = event_bus
        self.audit_log_path = Path(audit_log_path)
        self.skill_library_path.mkdir(parents=True, exist_ok=True)
        self.audit_log_path.parent.mkdir(parents=True, exist_ok=True)

    def validate_proposal(self, skill_dir: str | Path) -> SkillValidationResult:
        """Validate required files and run the skill's local pytest suite."""
        skill_dir = Path(skill_dir)
        missing_files = [
            file_name
            for file_name in REQUIRED_SKILL_FILES
            if not (skill_dir / file_name).exists()
        ]
        metadata = self._load_metadata(skill_dir) if "skill.json" not in missing_files else {}

        if missing_files:
            validation = SkillValidationResult(
                passed=False,
                skill_dir=skill_dir,
                missing_files=missing_files,
                metadata=metadata,
                pytest_return_code=None,
                output=f"Missing required files: {', '.join(missing_files)}",
            )
            self._write_audit("validate_proposal", "failure", metadata, validation.output)
            return validation

        policy, policy_errors = SandboxPolicy.from_metadata(metadata)
        if policy_errors:
            validation = SkillValidationResult(
                passed=False,
                skill_dir=skill_dir,
                missing_files=[],
                metadata=metadata,
                pytest_return_code=None,
                output="; ".join(policy_errors),
            )
            self._write_audit("validate_proposal", "failure", metadata, validation.output)
            return validation

        static_scan_errors = self._scan_static_security(skill_dir, policy)
        if static_scan_errors:
            validation = SkillValidationResult(
                passed=False,
                skill_dir=skill_dir,
                missing_files=[],
                metadata=metadata,
                pytest_return_code=None,
                output="; ".join(static_scan_errors),
            )
            self._write_audit("validate_proposal", "failure", metadata, validation.output)
            return validation

        result = subprocess.run(
            [sys.executable, "-m", "pytest", "test_main.py", "-q"],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=str(skill_dir),
            shell=False,
        )
        output = result.stdout + result.stderr

        validation = SkillValidationResult(
            passed=result.returncode == 0,
            skill_dir=skill_dir,
            missing_files=[],
            metadata=metadata,
            pytest_return_code=result.returncode,
            output=output,
        )
        self._write_audit(
            "validate_proposal",
            "success" if validation.passed else "failure",
            metadata,
            validation.output,
        )
        return validation

    def publish_approved_skill(
        self,
        skill_dir: str | Path,
        approved_by: str,
        source_request_id: str,
    ) -> PublishedSkill:
        """Publish a validated skill into the skill library and emit SKILL_CREATED."""
        skill_dir = Path(skill_dir)
        validation = self.validate_proposal(skill_dir)
        if not validation.passed:
            raise ValueError(f"Skill proposal failed validation: {validation.output}")

        metadata = validation.metadata
        skill_name = str(metadata["skill_name"])
        version = str(metadata.get("version", "1.0.0"))
        target_dir = self.skill_library_path / f"{skill_name}_{version}"
        if target_dir.exists():
            shutil.rmtree(target_dir)
        shutil.copytree(skill_dir, target_dir)

        lifecycle_payload = {
            "skill_name": skill_name,
            "version": version,
            "approved_by": approved_by,
            "source_request_id": source_request_id,
            "published_at": datetime.now(UTC).isoformat(),
            "validation": {
                "pytest_return_code": validation.pytest_return_code,
                "output": validation.output,
            },
            "security_policy": validation.metadata["security_policy"],
        }
        lifecycle_path = target_dir / "lifecycle.json"
        lifecycle_path.write_text(
            json.dumps(lifecycle_payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        self.event_bus.publish(
            EventTypes.SKILL_CREATED,
            {
                "skill_name": skill_name,
                "version": version,
                "description": metadata.get("description"),
                "tags": metadata.get("tags", []),
                "parameters": metadata.get("parameters", {}),
                "path": str(target_dir),
                "source_request_id": source_request_id,
            },
            "skill_lifecycle_manager",
        )

        self._write_audit(
            "publish_approved_skill",
            "success",
            metadata,
            f"Published to {target_dir}",
            actor=approved_by,
        )

        return PublishedSkill(
            skill_name=skill_name,
            version=version,
            target_dir=target_dir,
            lifecycle_path=lifecycle_path,
        )

    def _load_metadata(self, skill_dir: Path) -> dict[str, Any]:
        metadata = json.loads((skill_dir / "skill.json").read_text(encoding="utf-8"))
        if not metadata.get("skill_name"):
            raise ValueError("skill.json must include skill_name")
        return metadata

    def _scan_static_security(
        self,
        skill_dir: Path,
        policy: SandboxPolicy,
    ) -> list[str]:
        errors: list[str] = []
        for python_file in sorted(skill_dir.glob("*.py")):
            if python_file.name.startswith("test_"):
                continue
            try:
                tree = ast.parse(python_file.read_text(encoding="utf-8"))
            except SyntaxError as exc:
                errors.append(f"syntax error in {python_file.name}: {exc.msg}")
                continue
            scanner = _DangerousPatternScanner(
                python_file.name,
                allow_shell=policy.shell,
            )
            scanner.visit(tree)
            errors.extend(scanner.errors)
        return errors

    def _write_audit(
        self,
        action: str,
        result: str,
        metadata: dict[str, Any],
        message: str,
        actor: str = "skill_lifecycle_manager",
    ) -> None:
        payload = {
            "timestamp": datetime.now(UTC).isoformat(),
            "action": action,
            "result": result,
            "actor": actor,
            "skill_name": metadata.get("skill_name"),
            "version": metadata.get("version"),
            "message": message,
        }
        with self.audit_log_path.open("a", encoding="utf-8") as audit_file:
            audit_file.write(json.dumps(payload, ensure_ascii=False) + "\n")


class _DangerousPatternScanner(ast.NodeVisitor):
    """Small static guardrail for generated skills before tests execute."""

    always_blocked_calls = {
        "eval",
        "exec",
        "__import__",
        "yaml.load",
        "pickle.load",
        "pickle.loads",
        "pickle.dump",
        "pickle.dumps",
    }
    shell_blocked_calls = {
        "os.system",
        "os.popen",
        "subprocess.run",
        "subprocess.Popen",
        "subprocess.call",
        "subprocess.check_call",
        "subprocess.check_output",
    }
    blocked_imports = {"pickle"}

    def __init__(self, file_name: str, allow_shell: bool = False) -> None:
        self.file_name = file_name
        self.allow_shell = allow_shell
        self.errors: list[str] = []

    def visit_Call(self, node: ast.Call) -> Any:
        call_name = self._call_name(node.func)
        blocked_calls = set(self.always_blocked_calls)
        if not self.allow_shell:
            blocked_calls.update(self.shell_blocked_calls)
        if call_name in blocked_calls:
            self.errors.append(
                f"dangerous static pattern: {call_name} in {self.file_name}:{node.lineno}"
            )
        self.generic_visit(node)

    def visit_Import(self, node: ast.Import) -> Any:
        for alias in node.names:
            root_name = alias.name.split(".", maxsplit=1)[0]
            if root_name in self.blocked_imports:
                self.errors.append(
                    f"dangerous static pattern: import {root_name} in {self.file_name}:{node.lineno}"
                )
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> Any:
        root_name = (node.module or "").split(".", maxsplit=1)[0]
        if root_name in self.blocked_imports:
            self.errors.append(
                f"dangerous static pattern: import {root_name} in {self.file_name}:{node.lineno}"
            )
        self.generic_visit(node)

    def _call_name(self, func: ast.expr) -> str:
        if isinstance(func, ast.Name):
            return func.id
        if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name):
            return f"{func.value.id}.{func.attr}"
        return ""
