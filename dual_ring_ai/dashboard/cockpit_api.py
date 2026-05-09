"""Minimal local Architect Cockpit API."""

from __future__ import annotations

from dataclasses import asdict

import json

from fastapi import APIRouter, FastAPI, HTTPException
from pydantic import BaseModel, Field

from ..runtime.local_runtime import LocalRuntime


class ApprovalDecisionRequest(BaseModel):
    decision: str
    decided_by: str
    comments: str = ""


class InteractionRequest(BaseModel):
    text: str


class BlueprintRollbackRequest(BaseModel):
    role_name: str | None = None
    requested_by: str
    reason: str = ""


class OperationalSmokeRequest(BaseModel):
    cycles: int = Field(default=1, ge=1, le=100)


class FinalAcceptanceRequest(BaseModel):
    desktop_root: str | None = None
    stress_cycles: int = Field(default=10, ge=1, le=100)


def create_cockpit_app(runtime: LocalRuntime) -> FastAPI:
    """Create a FastAPI app for terminal UI and local governance operations."""
    app = FastAPI(title="双环 AI 控制 API")
    router = APIRouter()

    @router.get("/status")
    def status():
        return runtime.status_snapshot()

    @router.get("/health")
    def health():
        return runtime.health_report()

    @router.post("/preflight")
    def preflight():
        report = runtime.preflight_report()
        runtime.write_preflight_report(report=report)
        return report

    @router.post("/host-integration-probe")
    def host_integration_probe():
        report = runtime.host_integration_probe()
        runtime.write_host_integration_probe(report=report)
        return report

    @router.post("/operational-smoke")
    def operational_smoke(request: OperationalSmokeRequest):
        try:
            report = runtime.run_operational_smoke(cycles=request.cycles)
            runtime.write_operational_smoke_report(cycles=request.cycles, report=report)
            return report
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @router.post("/final-acceptance")
    def final_acceptance(request: FinalAcceptanceRequest):
        try:
            report = runtime.final_acceptance_report(
                desktop_root=request.desktop_root,
                stress_cycles=request.stress_cycles,
            )
            runtime.write_final_acceptance_report(
                desktop_root=request.desktop_root,
                stress_cycles=request.stress_cycles,
                report=report,
            )
            return report
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @router.get("/adapters")
    def adapters():
        return runtime.adapter_health()

    @router.get("/blueprints")
    def blueprints():
        return runtime.list_agent_blueprints()

    def perform_blueprint_rollback(role_name: str, request: BlueprintRollbackRequest):
        try:
            return runtime.rollback_organization_change(
                role_name,
                requested_by=request.requested_by,
                reason=request.reason,
            )
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @router.post("/blueprints/rollback")
    def rollback_blueprint(request: BlueprintRollbackRequest):
        if not request.role_name or not request.role_name.strip():
            raise HTTPException(status_code=400, detail="role_name is required")
        return perform_blueprint_rollback(request.role_name, request)

    @router.post("/blueprints/{role_name}/rollback")
    def rollback_blueprint_by_path(role_name: str, request: BlueprintRollbackRequest):
        return perform_blueprint_rollback(role_name, request)

    @router.get("/approvals")
    def approvals(status: str | None = None):
        return [asdict(request) for request in runtime.governance.list_requests(status)]

    @router.post("/approvals/{request_id}/decision")
    def decide_approval(request_id: str, decision: ApprovalDecisionRequest):
        try:
            request = runtime.governance.decide(
                request_id,
                decision.decision,
                decision.decided_by,
                decision.comments,
            )
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail="approval request not found") from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return asdict(request)

    @router.get("/algorithm-proposals")
    def algorithm_proposals():
        proposal_dir = runtime.root_path / "workspace" / "algorithm_research_proposals"
        if not proposal_dir.exists():
            return []
        proposals = []
        for proposal_path in sorted(proposal_dir.glob("*.json")):
            try:
                payload = json.loads(proposal_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if isinstance(payload, dict):
                proposals.append(payload)
        return proposals

    @router.get("/events")
    def events(event_type: str | None = None):
        return [asdict(event) for event in runtime.event_bus.list_events(event_type)]

    @router.get("/skills")
    def skills():
        return runtime.list_published_skills()

    @router.get("/audit/skill-lifecycle")
    def skill_lifecycle_audit():
        return runtime.read_skill_lifecycle_audit()

    @router.get("/audit/algorithm-evolution")
    def algorithm_evolution_audit():
        return runtime.read_algorithm_evolution_audit()

    @router.get("/algorithms")
    def algorithms():
        return runtime.list_algorithms()

    @router.get("/algorithm-experiments")
    def algorithm_experiments():
        return runtime.list_algorithm_experiment_reports()

    @router.get("/algorithm-reviews")
    def algorithm_reviews():
        return runtime.list_algorithm_reviews()

    @router.post("/interaction")
    def interaction(request: InteractionRequest):
        if not request.text.strip():
            raise HTTPException(status_code=400, detail="text is required")
        return runtime.handle_interaction(request.text)

    @router.get("/avatar/latest")
    def latest_avatar():
        return runtime.get_latest_avatar_event()

    app.include_router(router)
    app.include_router(router, prefix="/api")

    return app
