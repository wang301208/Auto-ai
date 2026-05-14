"""Immutable modification chain for Agent self-modification auditing.

Every self-modification (code patch, config change, strategy adjustment)
is recorded as a cryptographically linked block in an append-only chain.
This provides tamper-evident audit trail: any modification to a past
block invalidates all subsequent hashes.

Architecture:
    ModificationBlock: single block with SHA256 link to predecessor
    ModificationChain: append-only chain with persistence + verification

Usage:
    chain = ModificationChain(workspace=Path("."))
    block = chain.append(
        agent_id="auto-ai",
        patch_diff="--- a/foo.py\n+++ b/foo.py\n...",
        target_files=["foo.py"],
        test_result=TestResult(passed=True, output="5 passed"),
        autonomy_level=2,
    )
    assert chain.verify_integrity()
"""

from __future__ import annotations

import hashlib
import json
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any


class ModificationType(Enum):
    CODE_PATCH = "code_patch"
    CONFIG_CHANGE = "config_change"
    STRATEGY_ADJUST = "strategy_adjust"
    ARCHITECTURE_REFACTOR = "architecture_refactor"
    MODEL_SWITCH = "model_switch"
    AGENT_CREATE = "agent_create"
    AGENT_DESTROY = "agent_destroy"
    SELF_REWRITE = "self_rewrite"


class ModificationStatus(Enum):
    PENDING = "pending"
    APPLIED = "applied"
    TEST_PASSED = "test_passed"
    TEST_FAILED = "test_failed"
    REVERTED = "reverted"
    HOT_RELOADED = "hot_reloaded"


@dataclass
class TestResult:
    passed: bool
    output: str = ""
    test_count: int = 0
    fail_count: int = 0
    duration_seconds: float = 0.0


@dataclass
class ModificationBlock:
    index: int
    timestamp: str
    prev_hash: str
    hash: str
    agent_id: str
    mod_type: ModificationType
    status: ModificationStatus
    patch_diff: str
    target_files: list[str]
    test_result: TestResult | None
    autonomy_level: int
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        d = {
            "index": self.index,
            "timestamp": self.timestamp,
            "prev_hash": self.prev_hash,
            "hash": self.hash,
            "agent_id": self.agent_id,
            "mod_type": self.mod_type.value,
            "status": self.status.value,
            "patch_diff": self.patch_diff,
            "target_files": self.target_files,
            "autonomy_level": self.autonomy_level,
            "metadata": self.metadata,
        }
        if self.test_result is not None:
            d["test_result"] = {
                "passed": self.test_result.passed,
                "output": self.test_result.output,
                "test_count": self.test_result.test_count,
                "fail_count": self.test_result.fail_count,
                "duration_seconds": self.test_result.duration_seconds,
            }
        return d

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> ModificationBlock:
        tr = None
        if "test_result" in d and d["test_result"] is not None:
            tr_data = d["test_result"]
            tr = TestResult(
                passed=tr_data["passed"],
                output=tr_data.get("output", ""),
                test_count=tr_data.get("test_count", 0),
                fail_count=tr_data.get("fail_count", 0),
                duration_seconds=tr_data.get("duration_seconds", 0.0),
            )
        return cls(
            index=d["index"],
            timestamp=d["timestamp"],
            prev_hash=d["prev_hash"],
            hash=d["hash"],
            agent_id=d["agent_id"],
            mod_type=ModificationType(d["mod_type"]),
            status=ModificationStatus(d["status"]),
            patch_diff=d["patch_diff"],
            target_files=d["target_files"],
            test_result=tr,
            autonomy_level=d["autonomy_level"],
            metadata=d.get("metadata", {}),
        )


GENESIS_HASH = "0" * 64


class ModificationChain:
    """Append-only, tamper-evident modification log chain.

    Each block's hash = SHA256(prev_hash + index + timestamp + agent_id
                                + mod_type + patch_diff + target_files).
    Any alteration to a past block invalidates all subsequent hashes.
    """

    def __init__(self, workspace: Path | None = None, chain_file: str = "modification_chain.jsonl") -> None:
        self._blocks: list[ModificationBlock] = []
        self._lock = threading.Lock()
        self._workspace = workspace
        self._chain_file = chain_file
        if workspace is not None:
            self._chain_path = workspace / chain_file
            self._load()
        else:
            self._chain_path = None

    def _compute_hash(self, index: int, timestamp: str, prev_hash: str,
                      agent_id: str, mod_type: str, patch_diff: str,
                      target_files: list[str]) -> str:
        content = f"{index}:{timestamp}:{prev_hash}:{agent_id}:{mod_type}:{patch_diff}:{','.join(target_files)}"
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def append(
        self,
        agent_id: str,
        patch_diff: str,
        target_files: list[str],
        mod_type: ModificationType = ModificationType.CODE_PATCH,
        test_result: TestResult | None = None,
        autonomy_level: int = 1,
        status: ModificationStatus = ModificationStatus.PENDING,
        metadata: dict[str, Any] | None = None,
    ) -> ModificationBlock:
        with self._lock:
            index = len(self._blocks)
            prev_hash = self._blocks[-1].hash if self._blocks else GENESIS_HASH
            timestamp = datetime.now(timezone.utc).isoformat()

            hash_ = self._compute_hash(
                index, timestamp, prev_hash, agent_id,
                mod_type.value, patch_diff, target_files,
            )

            block = ModificationBlock(
                index=index,
                timestamp=timestamp,
                prev_hash=prev_hash,
                hash=hash_,
                agent_id=agent_id,
                mod_type=mod_type,
                status=status,
                patch_diff=patch_diff,
                target_files=target_files,
                test_result=test_result,
                autonomy_level=autonomy_level,
                metadata=metadata or {},
            )

            if test_result and test_result.passed:
                block.status = ModificationStatus.TEST_PASSED
            elif test_result and not test_result.passed:
                block.status = ModificationStatus.TEST_FAILED

            self._blocks.append(block)
            self._persist(block)
            return block

    def mark_reverted(self, index: int) -> None:
        with self._lock:
            if 0 <= index < len(self._blocks):
                block = self._blocks[index]
                self._blocks[index] = ModificationBlock(
                    index=block.index,
                    timestamp=block.timestamp,
                    prev_hash=block.prev_hash,
                    hash=block.hash,
                    agent_id=block.agent_id,
                    mod_type=block.mod_type,
                    status=ModificationStatus.REVERTED,
                    patch_diff=block.patch_diff,
                    target_files=block.target_files,
                    test_result=block.test_result,
                    autonomy_level=block.autonomy_level,
                    metadata=block.metadata,
                )
                self._rewrite_file()

    def mark_hot_reloaded(self, index: int) -> None:
        with self._lock:
            if 0 <= index < len(self._blocks):
                block = self._blocks[index]
                self._blocks[index] = ModificationBlock(
                    index=block.index,
                    timestamp=block.timestamp,
                    prev_hash=block.prev_hash,
                    hash=block.hash,
                    agent_id=block.agent_id,
                    mod_type=block.mod_type,
                    status=ModificationStatus.HOT_RELOADED,
                    patch_diff=block.patch_diff,
                    target_files=block.target_files,
                    test_result=block.test_result,
                    autonomy_level=block.autonomy_level,
                    metadata=block.metadata,
                )
                self._rewrite_file()

    def verify_integrity(self) -> tuple[bool, int]:
        with self._lock:
            for i, block in enumerate(self._blocks):
                expected_prev = GENESIS_HASH if i == 0 else self._blocks[i - 1].hash
                if block.prev_hash != expected_prev:
                    return False, i

                expected_hash = self._compute_hash(
                    block.index, block.timestamp, block.prev_hash,
                    block.agent_id, block.mod_type.value,
                    block.patch_diff, block.target_files,
                )
                if block.hash != expected_hash:
                    return False, i

            return True, -1

    @property
    def length(self) -> int:
        return len(self._blocks)

    @property
    def blocks(self) -> list[ModificationBlock]:
        return list(self._blocks)

    def get_block(self, index: int) -> ModificationBlock | None:
        if 0 <= index < len(self._blocks):
            return self._blocks[index]
        return None

    def recent_blocks(self, n: int = 10) -> list[ModificationBlock]:
        return list(self._blocks[-n:])

    def stats(self) -> dict[str, Any]:
        by_type: dict[str, int] = {}
        by_status: dict[str, int] = {}
        for b in self._blocks:
            by_type[b.mod_type.value] = by_type.get(b.mod_type.value, 0) + 1
            by_status[b.status.value] = by_status.get(b.status.value, 0) + 1
        return {
            "total": len(self._blocks),
            "by_type": by_type,
            "by_status": by_status,
            "integrity_ok": self.verify_integrity()[0],
        }

    def _persist(self, block: ModificationBlock) -> None:
        if self._chain_path is None:
            return
        self._chain_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._chain_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(block.to_dict(), ensure_ascii=False) + "\n")

    def _rewrite_file(self) -> None:
        if self._chain_path is None:
            return
        self._chain_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._chain_path, "w", encoding="utf-8") as f:
            for block in self._blocks:
                f.write(json.dumps(block.to_dict(), ensure_ascii=False) + "\n")

    def _load(self) -> None:
        if self._chain_path is None or not self._chain_path.exists():
            return
        with open(self._chain_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    d = json.loads(line)
                    self._blocks.append(ModificationBlock.from_dict(d))
                except (json.JSONDecodeError, KeyError, ValueError):
                    break


__all__ = [
    "ModificationType",
    "ModificationStatus",
    "TestResult",
    "ModificationBlock",
    "ModificationChain",
    "GENESIS_HASH",
]
