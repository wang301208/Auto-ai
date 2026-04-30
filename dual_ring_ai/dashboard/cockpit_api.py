"""Minimal local Architect Cockpit API."""

from __future__ import annotations

from dataclasses import asdict

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from ..runtime.local_runtime import LocalRuntime


class ApprovalDecisionRequest(BaseModel):
    decision: str
    decided_by: str
    comments: str = ""


def create_cockpit_app(runtime: LocalRuntime) -> FastAPI:
    """Create a FastAPI app for local governance operations."""
    app = FastAPI(title="Dual Ring AI Architect Cockpit")

    @app.get("/status")
    def status():
        return runtime.status_snapshot()

    @app.get("/approvals")
    def approvals(status: str | None = None):
        return [asdict(request) for request in runtime.governance.list_requests(status)]

    @app.post("/approvals/{request_id}/decision")
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

    @app.get("/algorithm-proposals")
    def algorithm_proposals():
        proposal_dir = runtime.root_path / "workspace" / "algorithm_research_proposals"
        if not proposal_dir.exists():
            return []
        proposals = []
        for proposal_path in sorted(proposal_dir.glob("*.json")):
            import json

            proposals.append(json.loads(proposal_path.read_text(encoding="utf-8")))
        return proposals

    return app
