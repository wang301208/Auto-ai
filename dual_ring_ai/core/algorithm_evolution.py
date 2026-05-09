"""Algorithm Evolution Protocol orchestration.

This module keeps algorithm research, sandbox experiment, human approval, and
agent-blueprint promotion as separate gates. It does not execute arbitrary
candidate code; experiments consume deterministic local benchmark datasets.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .agent_blueprint import AgentBlueprint, ThinkingEngineRef
from .algorithm_experiment import (
    AlgorithmExperimentRunner,
    ExperimentReport,
    ExperimentSpec,
)
from .algorithm_registry import AlgorithmManifest, AlgorithmRegistry
from .event_bus import EventBus, EventTypes
from .governance import ApprovalRequest, GovernanceStore


@dataclass
class AlgorithmResearchReport:
    """AEP research report prepared for AI peer review."""

    proposal_id: str
    hypothesis: str
    baseline_engine: str
    candidate_engine: str
    metric_deltas: dict[str, float]
    recommendation: str
    reviewer_agents: list[str]
    status: str
    report_path: Path
    created_at: str


class AlgorithmEvolutionProtocol:
    """Coordinate approved algorithm research and promotion workflows."""

    def __init__(
        self,
        root_path: str | Path,
        registry: AlgorithmRegistry,
        experiment_runner: AlgorithmExperimentRunner,
        governance: GovernanceStore,
        event_bus: EventBus,
        audit_log_path: str | Path | None = None,
    ) -> None:
        self.root_path = Path(root_path)
        self.registry = registry
        self.experiment_runner = experiment_runner
        self.governance = governance
        self.event_bus = event_bus
        self.audit_log_path = Path(
            audit_log_path
            if audit_log_path is not None
            else self.root_path / "logs" / "algorithm_evolution_audit.jsonl"
        )
        self.audit_log_path.parent.mkdir(parents=True, exist_ok=True)

    def create_research_request(
        self,
        proposal_path: str | Path,
        requested_by: str,
        title: str | None = None,
        risk_level: str = "high",
    ) -> ApprovalRequest:
        """Validate an Algorithmist proposal and enqueue human review."""
        proposal = self._read_json(proposal_path)
        self._require_keys(
            proposal,
            [
                "proposal_id",
                "target_agent",
                "current_engine",
                "candidate_engine",
                "bottleneck",
                "hypothesis",
                "experiment_design",
                "metrics",
            ],
        )
        candidate_name, candidate_version = self._split_engine_ref(
            proposal["candidate_engine"]
        )
        manifest = self.registry.get(candidate_name, candidate_version)

        request = self.governance.create_request(
            request_type="algorithm_research",
            title=title
            or f"Run AEP research for {proposal['target_agent']} -> {proposal['candidate_engine']}",
            payload={
                "proposal_path": str(Path(proposal_path)),
                "proposal_id": proposal["proposal_id"],
                "target_agent": proposal["target_agent"],
                "current_engine": proposal["current_engine"],
                "candidate_engine": proposal["candidate_engine"],
                "evaluation_suite": manifest.evaluation_suite,
                "metrics": proposal["metrics"],
            },
            requested_by=requested_by,
            risk_level=risk_level,
        )
        self.record_audit(
            "create_research_request",
            {
                "request_id": request.request_id,
                "proposal_id": proposal["proposal_id"],
                "candidate_engine": proposal["candidate_engine"],
            },
        )
        return request

    def run_experiment_from_approval(
        self,
        request_id: str,
        dataset_path: str | Path,
        thresholds: dict[str, float],
    ) -> ExperimentReport:
        """Run a deterministic experiment only after research approval."""
        request = self._require_approved_request(request_id, "algorithm_research")
        payload = request.payload
        report = self.experiment_runner.run(
            ExperimentSpec(
                proposal_id=payload["proposal_id"],
                baseline_engine=payload["current_engine"],
                candidate_engine=payload["candidate_engine"],
                dataset_path=Path(dataset_path),
                thresholds=thresholds,
            )
        )

        self.record_audit(
            "run_experiment",
            {
                "request_id": request_id,
                "proposal_id": report.proposal_id,
                "recommendation": report.recommendation,
                "report_path": str(report.report_path),
            },
        )
        self.event_bus.publish(
            EventTypes.ALGORITHM_EXPERIMENT_COMPLETED,
            {
                "proposal_id": report.proposal_id,
                "baseline_engine": report.baseline_engine,
                "candidate_engine": report.candidate_engine,
                "recommendation": report.recommendation,
                "report_path": str(report.report_path),
            },
            "algorithm_evolution_protocol",
        )
        return report

    def create_promotion_request(
        self,
        report_path: str | Path,
        blueprint_path: str | Path,
        requested_by: str,
        title: str | None = None,
        risk_level: str = "critical",
    ) -> ApprovalRequest:
        """Request human approval to bind a proven candidate to an agent."""
        report = self._read_json(report_path)
        self._require_keys(
            report,
            [
                "proposal_id",
                "baseline_engine",
                "candidate_engine",
                "recommendation",
            ],
        )
        if report["recommendation"] != "promote_candidate":
            raise ValueError("candidate report is not recommended for promotion")

        blueprint = AgentBlueprint.load(blueprint_path)
        candidate_name, candidate_version = self._split_engine_ref(
            report["candidate_engine"]
        )
        manifest = self.registry.get(candidate_name, candidate_version)

        request = self.governance.create_request(
            request_type="algorithm_promotion",
            title=title
            or f"Promote {report['candidate_engine']} for {blueprint.role_name}",
            payload={
                "report_path": str(Path(report_path)),
                "blueprint_path": str(Path(blueprint_path)),
                "proposal_id": report["proposal_id"],
                "target_agent": blueprint.role_name,
                "baseline_engine": report["baseline_engine"],
                "candidate_engine": report["candidate_engine"],
                "candidate_manifest": asdict(manifest),
            },
            requested_by=requested_by,
            risk_level=risk_level,
        )
        self.record_audit(
            "create_promotion_request",
            {
                "request_id": request.request_id,
                "proposal_id": report["proposal_id"],
                "target_agent": blueprint.role_name,
                "candidate_engine": report["candidate_engine"],
            },
        )
        return request

    def apply_promotion_from_approval(
        self,
        request_id: str,
        approved_by: str,
    ) -> AgentBlueprint:
        """Apply a thinking-engine upgrade only after promotion approval."""
        request = self._require_approved_request(request_id, "algorithm_promotion")
        payload = request.payload
        manifest_data = payload["candidate_manifest"]
        manifest = AlgorithmManifest(**manifest_data)
        blueprint_path = Path(payload["blueprint_path"])
        blueprint = AgentBlueprint.load(blueprint_path)
        previous_engine = asdict(blueprint.thinking_engine)

        blueprint.thinking_engine = ThinkingEngineRef(
            name=manifest.name,
            version=manifest.version,
            evaluation_suite=manifest.evaluation_suite,
        )
        blueprint.save(blueprint_path)

        promoted_manifest = AlgorithmManifest(
            name=manifest.name,
            version=manifest.version,
            description=manifest.description,
            source_module=manifest.source_module,
            status="active",
            metrics=manifest.metrics,
            rollback_to=manifest.rollback_to,
            evaluation_suite=manifest.evaluation_suite,
        )
        self.registry.register(promoted_manifest)

        audit_payload = {
            "request_id": request_id,
            "approved_by": approved_by,
            "proposal_id": payload["proposal_id"],
            "target_agent": blueprint.role_name,
            "previous_engine": previous_engine,
            "candidate_engine": payload["candidate_engine"],
            "blueprint_path": str(blueprint_path),
        }
        self.record_audit("apply_promotion", audit_payload)
        self.event_bus.publish(
            EventTypes.ALGORITHM_PROMOTED,
            audit_payload,
            "algorithm_evolution_protocol",
        )
        return blueprint

    def write_research_report(
        self,
        experiment_report_path: str | Path,
        hypothesis: str,
        reviewer_agents: list[str],
    ) -> AlgorithmResearchReport:
        """Create a peer-reviewable research report from an experiment report."""
        experiment_report = self._read_json(experiment_report_path)
        self._require_keys(
            experiment_report,
            [
                "proposal_id",
                "baseline_engine",
                "candidate_engine",
                "metric_deltas",
                "recommendation",
            ],
        )
        created_at = datetime.now(UTC).isoformat()
        report_path = (
            self.root_path
            / "algorithm_research_reports"
            / f"{experiment_report['proposal_id']}_research_report.json"
        )
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report = AlgorithmResearchReport(
            proposal_id=experiment_report["proposal_id"],
            hypothesis=hypothesis,
            baseline_engine=experiment_report["baseline_engine"],
            candidate_engine=experiment_report["candidate_engine"],
            metric_deltas={
                key: float(value)
                for key, value in experiment_report["metric_deltas"].items()
            },
            recommendation=experiment_report["recommendation"],
            reviewer_agents=reviewer_agents,
            status="ready_for_peer_review",
            report_path=report_path,
            created_at=created_at,
        )
        payload = asdict(report)
        payload["report_path"] = str(report_path)
        report_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        self.record_audit(
            "write_research_report",
            {
                "proposal_id": report.proposal_id,
                "report_path": str(report_path),
                "reviewer_agents": reviewer_agents,
            },
        )
        return report

    def peer_review_research_report(
        self,
        research_report_path: str | Path,
        required_reviewers: list[str],
    ) -> dict[str, Any]:
        """Run a deterministic AI peer-review gate for an AEP research report."""
        report = self._read_json(research_report_path)
        reviewer_agents = list(report.get("reviewer_agents", []))
        missing_reviewers = [
            reviewer for reviewer in required_reviewers if reviewer not in reviewer_agents
        ]
        metric_deltas = report.get("metric_deltas", {})
        promotes = report.get("recommendation") == "promote_candidate"
        has_positive_quality = any(
            metric in metric_deltas and float(metric_deltas[metric]) > 0
            for metric in ("f1_score", "accuracy", "quality_score")
        )
        has_efficiency_gain = any(
            metric in metric_deltas and float(metric_deltas[metric]) < 0
            for metric in ("latency_ms", "cost", "tokens")
        )
        decision = (
            "approved_for_human_promotion_review"
            if promotes and not missing_reviewers and (has_positive_quality or has_efficiency_gain)
            else "needs_revision"
        )
        review = {
            "proposal_id": report["proposal_id"],
            "decision": decision,
            "reviewers": required_reviewers,
            "missing_reviewers": missing_reviewers,
            "checks": {
                "promotes_candidate": promotes,
                "has_positive_quality": has_positive_quality,
                "has_efficiency_gain": has_efficiency_gain,
            },
        }
        review_path = (
            Path(research_report_path).parent
            / f"{report['proposal_id']}_peer_review.json"
        )
        review_path.write_text(
            json.dumps(review, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        self.record_audit(
            "peer_review_research_report",
            {
                "proposal_id": report["proposal_id"],
                "decision": decision,
                "review_path": str(review_path),
            },
        )
        return review

    def read_audit(self) -> list[dict[str, Any]]:
        """Read persisted algorithm evolution audit records."""
        if not self.audit_log_path.exists():
            return []
        return [
            json.loads(line)
            for line in self.audit_log_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

    def record_audit(self, action: str, payload: dict[str, Any]) -> None:
        """Append one audit record to the algorithm evolution log."""
        record = {
            "timestamp": datetime.now(UTC).isoformat(),
            "action": action,
            "payload": payload,
        }
        with self.audit_log_path.open("a", encoding="utf-8") as audit_file:
            audit_file.write(json.dumps(record, ensure_ascii=False) + "\n")

    def _require_approved_request(
        self, request_id: str, request_type: str
    ) -> ApprovalRequest:
        request = self.governance.get_request(request_id)
        if request.request_type != request_type:
            raise ValueError(f"approval request is not for {request_type}: {request_id}")
        if request.status != "approved":
            raise PermissionError(f"approval request is not approved: {request_id}")
        return request

    @staticmethod
    def _read_json(path: str | Path) -> dict[str, Any]:
        return json.loads(Path(path).read_text(encoding="utf-8"))

    @staticmethod
    def _require_keys(payload: dict[str, Any], keys: list[str]) -> None:
        missing = [key for key in keys if key not in payload]
        if missing:
            raise ValueError(f"missing required fields: {', '.join(missing)}")

    @staticmethod
    def _split_engine_ref(engine_ref: str) -> tuple[str, str]:
        if ":" not in engine_ref:
            raise ValueError("engine references must use '<name>:<version>'")
        name, version = engine_ref.split(":", 1)
        if not name or not version:
            raise ValueError("engine references must use '<name>:<version>'")
        return name, version
