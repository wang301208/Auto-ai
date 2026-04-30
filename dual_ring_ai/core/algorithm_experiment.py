"""Deterministic local algorithm experiment runner."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path


@dataclass
class ExperimentSpec:
    proposal_id: str
    baseline_engine: str
    candidate_engine: str
    dataset_path: Path
    thresholds: dict[str, float]


@dataclass
class ExperimentReport:
    proposal_id: str
    baseline_engine: str
    candidate_engine: str
    metric_deltas: dict[str, float]
    recommendation: str
    report_path: Path
    created_at: str


class AlgorithmExperimentRunner:
    """Compare baseline and candidate metrics from a local JSON dataset."""

    def __init__(self, output_path: str | Path = "algorithm_experiments") -> None:
        self.output_path = Path(output_path)
        self.output_path.mkdir(parents=True, exist_ok=True)

    def run(self, spec: ExperimentSpec) -> ExperimentReport:
        dataset = json.loads(Path(spec.dataset_path).read_text(encoding="utf-8"))
        metric_deltas: dict[str, float] = {}

        for metric in spec.thresholds:
            baseline_values = [float(item["baseline"][metric]) for item in dataset]
            candidate_values = [float(item["candidate"][metric]) for item in dataset]
            baseline_avg = sum(baseline_values) / len(baseline_values)
            candidate_avg = sum(candidate_values) / len(candidate_values)
            metric_deltas[metric] = candidate_avg - baseline_avg

        recommendation = (
            "promote_candidate"
            if self._thresholds_pass(metric_deltas, spec.thresholds)
            else "keep_baseline"
        )
        created_at = datetime.now(UTC).isoformat()
        report_path = self.output_path / f"{spec.proposal_id}_report.json"
        report = ExperimentReport(
            proposal_id=spec.proposal_id,
            baseline_engine=spec.baseline_engine,
            candidate_engine=spec.candidate_engine,
            metric_deltas=metric_deltas,
            recommendation=recommendation,
            report_path=report_path,
            created_at=created_at,
        )
        payload = asdict(report)
        payload["report_path"] = str(report_path)
        report_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return report

    def _thresholds_pass(
        self, metric_deltas: dict[str, float], thresholds: dict[str, float]
    ) -> bool:
        for metric, threshold in thresholds.items():
            delta = metric_deltas[metric]
            if threshold >= 0 and delta < threshold:
                return False
            if threshold < 0 and delta > threshold:
                return False
        return True
