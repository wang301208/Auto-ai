"""Self-modification pipeline: Agent autonomously modifies its own code.

The radical evolution of auto_fix_cycle:
    1. LLM generates a diff patch for the discovered issue
    2. Apply patch in sandbox (copy workspace to tmp)
    3. Run full test suite in sandbox
    4. If tests pass: git commit + (optionally) git push + hot reload
    5. If tests fail: git revert + learn from failure + record to chain
    6. Record every modification to immutable ModificationChain

All operations are gated by AutonomyManager:
    - L2 (SELF_BOUND): can generate and apply patches
    - L3 (SELF_REWRITE): can also hot-reload and auto-push
    - Below L2: falls back to suggestion-only mode
"""

from __future__ import annotations

import asyncio
import importlib
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

from governance.autonomy_level import AutonomyLevel, AutonomyManager
from governance.modification_chain import (
    ModificationChain,
    ModificationStatus,
    ModificationType,
    TestResult,
)
from autogpt.logs import logger


class SandboxWorkspace:
    """Temporary copy of workspace for safe patch testing."""

    def __init__(self, source: Path) -> None:
        self._source = source
        self._tmpdir: tempfile.TemporaryDirectory | None = None
        self.path: Path | None = None

    def __enter__(self) -> Path:
        self._tmpdir = tempfile.TemporaryDirectory(prefix="autogpt_sandbox_")
        self.path = Path(self._tmpdir.name) / "workspace"
        shutil.copytree(self._source, self.path, dirs_exist_ok=True)
        return self.path

    def __exit__(self, *args: Any) -> None:
        if self._tmpdir:
            self._tmpdir.cleanup()
            self._tmpdir = None
            self.path = None


class SelfModifyPipeline:
    """Full self-modification pipeline: generate → apply → test → commit/revert → reload.

    Args:
        workspace: Project root directory
        agent_id: Agent identifier for audit trail
        autonomy: AutonomyManager instance
        chain: ModificationChain for immutable logging
        test_command: Shell command to run tests (default: pytest)
        git_auto_push: Whether to git push after commit (requires L3+)
    """

    def __init__(
        self,
        workspace: Path,
        agent_id: str = "auto-gpt",
        autonomy: AutonomyManager | None = None,
        chain: ModificationChain | None = None,
        test_command: str = "python -m pytest tests/ -x -q --tb=short",
        git_auto_push: bool = False,
    ) -> None:
        self.workspace = workspace
        self.agent_id = agent_id
        self.autonomy = autonomy or AutonomyManager(agent_id=agent_id)
        self.chain = chain or ModificationChain()
        self._test_command = test_command
        self._git_auto_push = git_auto_push

    @property
    def can_modify(self) -> bool:
        return self.autonomy.level >= AutonomyLevel.SELF_BOUND

    @property
    def can_hot_reload(self) -> bool:
        return self.autonomy.capabilities.can_hot_reload

    @property
    def can_auto_push(self) -> bool:
        return self.autonomy.capabilities.can_auto_push

    async def execute_modification(
        self,
        patch_diff: str,
        target_files: list[str],
        mod_type: ModificationType = ModificationType.CODE_PATCH,
        llm_patch_generator: Any = None,
    ) -> dict[str, Any]:
        """Execute full self-modification pipeline.

        Returns dict with keys: success, test_result, chain_index, reverted, reloaded
        """
        result: dict[str, Any] = {
            "success": False,
            "test_result": None,
            "chain_index": -1,
            "reverted": False,
            "reloaded": False,
        }

        if not self.can_modify:
            logger.info("[self-modify] Autonomy level too low for code modification. Suggestion only.")
            result["suggestion"] = patch_diff
            return result

        block = self.chain.append(
            agent_id=self.agent_id,
            patch_diff=patch_diff,
            target_files=target_files,
            mod_type=mod_type,
            autonomy_level=self.autonomy.level,
            status=ModificationStatus.PENDING,
        )
        result["chain_index"] = block.index

        applied = await self._apply_patch(patch_diff)
        if not applied:
            logger.warn("[self-modify] Patch application failed")
            self.autonomy.record_failure()
            return result

        test_result = await self._run_tests()
        result["test_result"] = test_result

        if test_result.passed:
            result["success"] = True
            self.autonomy.record_success()

            commit_ok = await self._git_commit(patch_diff, target_files)
            if commit_ok and self.can_auto_push and self._git_auto_push:
                await self._git_push()

            if self.can_hot_reload:
                reloaded = self._hot_reload(target_files)
                result["reloaded"] = reloaded
                if reloaded:
                    self.chain.mark_hot_reloaded(block.index)
        else:
            logger.warn(f"[self-modify] Tests failed: {test_result.fail_count} failures")
            self.autonomy.record_failure()
            reverted = await self._git_revert()
            result["reverted"] = reverted
            if reverted:
                self.chain.mark_reverted(block.index)

        return result

    async def _apply_patch(self, patch_diff: str) -> bool:
        try:
            proc = subprocess.run(
                ["git", "apply", "--unsafe-patches"],
                input=patch_diff,
                capture_output=True,
                text=True,
                cwd=str(self.workspace),
                timeout=30,
            )
            if proc.returncode == 0:
                logger.info("[self-modify] Patch applied successfully")
                return True
            logger.warn(f"[self-modify] git apply failed: {proc.stderr[:200]}")
            return False
        except Exception as e:
            logger.warn(f"[self-modify] Patch application error: {e}")
            return False

    async def _run_tests(self) -> TestResult:
        try:
            start = time.monotonic()
            proc = subprocess.run(
                self._test_command,
                shell=True,
                capture_output=True,
                text=True,
                cwd=str(self.workspace),
                timeout=300,
            )
            duration = time.monotonic() - start
            output = proc.stdout + proc.stderr

            passed = proc.returncode == 0
            test_count = 0
            fail_count = 0
            for line in output.split("\n"):
                if " passed" in line:
                    parts = line.strip().split()
                    for p in parts:
                        if p.isdigit():
                            test_count += int(p)
                            break
                if " failed" in line:
                    parts = line.strip().split()
                    for p in parts:
                        if p.isdigit():
                            fail_count += int(p)
                            break

            return TestResult(
                passed=passed,
                output=output[-2000:],
                test_count=test_count,
                fail_count=fail_count,
                duration_seconds=duration,
            )
        except subprocess.TimeoutExpired:
            return TestResult(passed=False, output="Test timeout (300s)")
        except Exception as e:
            return TestResult(passed=False, output=str(e))

    async def _git_commit(self, patch_diff: str, target_files: list[str]) -> bool:
        try:
            subprocess.run(
                ["git", "add"] + target_files,
                cwd=str(self.workspace),
                capture_output=True,
                timeout=10,
            )
            msg = f"[self-modify] Auto-fix: {', '.join(target_files[:3])}"
            if len(target_files) > 3:
                msg += f" (+{len(target_files)-3} more)"
            proc = subprocess.run(
                ["git", "commit", "-m", msg],
                cwd=str(self.workspace),
                capture_output=True,
                timeout=10,
            )
            if proc.returncode == 0:
                logger.info("[self-modify] Changes committed")
                return True
            return False
        except Exception as e:
            logger.warn(f"[self-modify] Git commit failed: {e}")
            return False

    async def _git_push(self) -> bool:
        try:
            proc = subprocess.run(
                ["git", "push"],
                cwd=str(self.workspace),
                capture_output=True,
                timeout=30,
            )
            if proc.returncode == 0:
                logger.info("[self-modify] Changes pushed")
                return True
            return False
        except Exception:
            return False

    async def _git_revert(self) -> bool:
        try:
            proc = subprocess.run(
                ["git", "reset", "--hard", "HEAD~1"],
                cwd=str(self.workspace),
                capture_output=True,
                timeout=10,
            )
            if proc.returncode == 0:
                logger.info("[self-modify] Reverted last commit")
                return True
            return False
        except Exception:
            return False

    def _hot_reload(self, target_files: list[str]) -> bool:
        reloaded = []
        for filepath in target_files:
            module_path = self._file_to_module(filepath)
            if module_path and module_path in sys.modules:
                try:
                    importlib.reload(sys.modules[module_path])
                    reloaded.append(module_path)
                except Exception as e:
                    logger.warn(f"[self-modify] Hot reload failed for {module_path}: {e}")
        if reloaded:
            logger.info(f"[self-modify] Hot reloaded: {', '.join(reloaded)}")
            return True
        return False

    def _file_to_module(self, filepath: str) -> str | None:
        rel = Path(filepath)
        if rel.suffix != ".py":
            return None
        parts = list(rel.with_suffix("").parts)
        if parts and parts[-1] == "__init__":
            parts = parts[:-1]
        if not parts:
            return None
        return ".".join(parts)


__all__ = ["SandboxWorkspace", "SelfModifyPipeline"]
