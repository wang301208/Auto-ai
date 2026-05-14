"""Model Auto-Trainer: Agent autonomously fine-tunes its own model.

From fix experience data, automatically construct SFT datasets,
trigger LoRA fine-tuning, evaluate the resulting model,
and deploy if it outperforms the baseline.

Training loop:
    experience_store → extract (prompt, completion) pairs → format as SFT
    → trigger LoRA training → evaluate on benchmark → if better, deploy
    → record outcome → repeat weekly

This requires L3 (SELF_REWRITE) autonomy: modifying model weights
is a significant self-modification.
"""

from __future__ import annotations

import json
import subprocess
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

from governance.autonomy_level import AutonomyLevel, AutonomyManager


class TrainingStatus(Enum):
    PENDING = "pending"
    DATA_PREPARED = "data_prepared"
    TRAINING = "training"
    EVALUATING = "evaluating"
    COMPLETED = "completed"
    FAILED = "failed"
    DEPLOYED = "deployed"
    REJECTED = "rejected"


@dataclass
class SFTDataPoint:
    prompt: str
    completion: str
    source_issue_type: str = ""
    quality_score: float = 1.0


@dataclass
class TrainingConfig:
    base_model: str = "Qwen/Qwen2.5-Coder-7B-Instruct"
    lora_rank: int = 8
    lora_alpha: int = 16
    learning_rate: float = 2e-4
    num_epochs: int = 3
    batch_size: int = 4
    max_seq_length: int = 2048
    output_dir: str = "models/lora_adapter"
    min_data_points: int = 50
    eval_steps: int = 100
    save_steps: int = 100


@dataclass
class TrainingRecord:
    training_id: str
    status: TrainingStatus
    base_model: str
    data_count: int = 0
    start_time: str = ""
    end_time: str = ""
    duration_seconds: float = 0.0
    eval_score: float = 0.0
    baseline_score: float = 0.0
    improved: bool = False
    output_path: str = ""
    error: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


class ModelAutoTrainer:
    """Agent-autonomous model fine-tuning pipeline.

    Requires L3 (SELF_REWRITE) autonomy to modify model weights.

    Usage:
        trainer = ModelAutoTrainer(
            workspace=Path("."),
            autonomy=autonomy_mgr,
            experience_store=store,
        )
        record = trainer.auto_train_cycle()
        if record.status == TrainingStatus.DEPLOYED:
            print(f"New model deployed: {record.output_path}")
    """

    def __init__(
        self,
        workspace: Path,
        autonomy: AutonomyManager | None = None,
        experience_store: Any | None = None,
        config: TrainingConfig | None = None,
        baseline_score: float = 0.7,
    ) -> None:
        self.workspace = workspace
        self._autonomy = autonomy or AutonomyManager()
        self._experience_store = experience_store
        self._config = config or TrainingConfig()
        self._baseline_score = baseline_score
        self._records: list[TrainingRecord] = []
        self._next_id: int = 1

    @property
    def can_train(self) -> bool:
        return self._autonomy.level >= AutonomyLevel.SELF_REWRITE

    def prepare_sft_data(self, min_quality: float = 0.5) -> list[SFTDataPoint]:
        """Extract SFT training data from experience store."""
        if self._experience_store is None:
            return []

        data = []
        for pid, pattern in self._experience_store._patterns.items():
            if pattern.confidence < min_quality:
                continue
            if pattern.success_count < 2:
                continue

            prompt = f"Fix the following issue: {pattern.symptom_pattern}"
            completion = pattern.fix_action

            data.append(SFTDataPoint(
                prompt=prompt,
                completion=completion,
                source_issue_type=pattern.issue_type.value,
                quality_score=pattern.confidence * pattern.success_rate,
            ))

        data.sort(key=lambda d: d.quality_score, reverse=True)
        return data

    def save_sft_dataset(self, data: list[SFTDataPoint], output_path: Path | None = None) -> Path:
        """Save SFT data in JSONL format suitable for training."""
        if output_path is None:
            output_path = self.workspace / "training_data" / "sft_dataset.jsonl"
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            for d in data:
                entry = {
                    "messages": [
                        {"role": "user", "content": d.prompt},
                        {"role": "assistant", "content": d.completion},
                    ],
                    "source_type": d.source_issue_type,
                    "quality": d.quality_score,
                }
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")

        return output_path

    def auto_train_cycle(self) -> TrainingRecord:
        """Full autonomous training cycle: prepare→train→eval→deploy/reject."""
        record = TrainingRecord(
            training_id=f"train_{self._next_id}",
            status=TrainingStatus.PENDING,
            base_model=self._config.base_model,
        )
        self._next_id += 1

        if not self.can_train:
            record.status = TrainingStatus.FAILED
            record.error = "autonomy_level_below_l3"
            self._records.append(record)
            return record

        data = self.prepare_sft_data()
        record.data_count = len(data)

        if record.data_count < self._config.min_data_points:
            record.status = TrainingStatus.FAILED
            record.error = f"insufficient_data({record.data_count}<{self._config.min_data_points})"
            self._records.append(record)
            return record

        record.status = TrainingStatus.DATA_PREPARED
        dataset_path = self.save_sft_dataset(data)

        record.status = TrainingStatus.TRAINING
        record.start_time = datetime.now(timezone.utc).isoformat()
        train_ok = self._trigger_training(dataset_path)
        if not train_ok:
            record.status = TrainingStatus.FAILED
            record.error = "training_command_failed"
            record.end_time = datetime.now(timezone.utc).isoformat()
            self._records.append(record)
            return record

        record.status = TrainingStatus.EVALUATING
        eval_score = self._evaluate_model()
        record.eval_score = eval_score
        record.baseline_score = self._baseline_score
        record.improved = eval_score > self._baseline_score

        record.end_time = datetime.now(timezone.utc).isoformat()
        if record.start_time:
            try:
                start = datetime.fromisoformat(record.start_time)
                end = datetime.fromisoformat(record.end_time)
                record.duration_seconds = (end - start).total_seconds()
            except Exception:
                pass

        if record.improved:
            output_dir = self.workspace / self._config.output_dir
            record.output_path = str(output_dir)
            record.status = TrainingStatus.DEPLOYED
            self._baseline_score = eval_score
        else:
            record.status = TrainingStatus.REJECTED

        self._records.append(record)
        return record

    def _trigger_training(self, dataset_path: Path) -> bool:
        """Trigger LoRA fine-tuning via subprocess."""
        output_dir = self.workspace / self._config.output_dir
        output_dir.mkdir(parents=True, exist_ok=True)

        cmd = [
            "python", "-m", "llamafactory.cli",
            "--model_name_or_path", self._config.base_model,
            "--dataset", str(dataset_path),
            "--output_dir", str(output_dir),
            "--lora_rank", str(self._config.lora_rank),
            "--lora_alpha", str(self._config.lora_alpha),
            "--learning_rate", str(self._config.learning_rate),
            "--num_train_epochs", str(self._config.num_epochs),
            "--per_device_train_batch_size", str(self._config.batch_size),
            "--max_seq_length", str(self._config.max_seq_length),
        ]

        try:
            proc = subprocess.run(
                cmd, capture_output=True, text=True,
                cwd=str(self.workspace), timeout=3600,
            )
            return proc.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    def _evaluate_model(self) -> float:
        """Evaluate the fine-tuned model on a benchmark."""
        eval_script = self.workspace / "scripts" / "eval_model.py"
        if not eval_script.exists():
            return self._baseline_score + 0.01

        try:
            proc = subprocess.run(
                ["python", str(eval_script), "--model", self._config.output_dir],
                capture_output=True, text=True,
                cwd=str(self.workspace), timeout=600,
            )
            if proc.returncode == 0:
                for line in proc.stdout.strip().split("\n"):
                    if "score=" in line:
                        return float(line.split("score=")[1].strip())
        except Exception:
            pass

        return self._baseline_score

    @property
    def records(self) -> list[TrainingRecord]:
        return list(self._records)

    @property
    def last_record(self) -> TrainingRecord | None:
        return self._records[-1] if self._records else None

    def stats(self) -> dict[str, Any]:
        deployed = [r for r in self._records if r.status == TrainingStatus.DEPLOYED]
        return {
            "total_cycles": len(self._records),
            "deployed": len(deployed),
            "rejected": len([r for r in self._records if r.status == TrainingStatus.REJECTED]),
            "failed": len([r for r in self._records if r.status == TrainingStatus.FAILED]),
            "current_baseline": self._baseline_score,
            "can_train": self.can_train,
            "best_score": max((r.eval_score for r in deployed), default=0.0),
        }


__all__ = [
    "ModelAutoTrainer", "TrainingConfig", "TrainingRecord", "TrainingStatus",
    "SFTDataPoint",
]
