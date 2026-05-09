"""Founder agent for organizational self-evolution proposals."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ..core.agent_blueprint import AgentBlueprint, ThinkingEngineRef
from ..core.event_bus import EventBus, EventTypes


@dataclass
class OrganizationChangeProposal:
    """A proposed constitutional change to the agent organization."""

    proposal_id: str
    change_type: str
    target_role: str
    rationale: str
    blueprint: dict[str, Any]
    status: str
    requires_human_approval: bool
    proposal_path: Path
    created_at: str


class FounderAgent:
    """Analyze organization-level metrics and propose blueprint changes."""

    def __init__(
        self,
        event_bus: EventBus,
        charter_path: str | Path,
        proposal_dir: str | Path | None = None,
    ) -> None:
        self.event_bus = event_bus
        self.charter_path = Path(charter_path)
        self.charter_path.mkdir(parents=True, exist_ok=True)
        self.proposal_dir = Path(proposal_dir) if proposal_dir else self.charter_path / "proposals"
        self.proposal_dir.mkdir(parents=True, exist_ok=True)

    def analyze_and_propose(self, metrics: dict[str, Any]) -> OrganizationChangeProposal:
        """Create a deterministic restructuring proposal from system metrics."""
        category_counts = metrics.get("task_category_counts", {})
        frontend_count = int(category_counts.get("frontend", 0))
        bottleneck_agent = str(metrics.get("bottleneck_agent", "unknown"))
        frontend_failure = float(metrics.get("failure_rates", {}).get("frontend", 0.0))

        if frontend_count >= 5 and frontend_failure >= 0.25:
            return self.propose_frontend_developer(
                rationale=(
                    "Frontend work is frequent and failure-prone; create a specialist "
                    f"role to reduce load on {bottleneck_agent}."
                )
            )

        return self.propose_observer(
            rationale="No specialist threshold was crossed; add a low-risk observer role."
        )

    def propose_frontend_developer(self, rationale: str) -> OrganizationChangeProposal:
        """Propose a frontend-specialist blueprint."""
        blueprint = AgentBlueprint(
            role_name="Frontend_Developer",
            version="1.0",
            agent_class="dual_ring_ai.genesis.tdd_developer.TDDDeveloperAgent",
            core_prompt=(
                "You are a Genesis frontend specialist. You handle UI work with "
                "strict tests, accessibility checks, and local cockpit contracts."
            ),
            thinking_engine=ThinkingEngineRef(
                name="thought_tree_reasoner",
                version="1.0.0",
                evaluation_suite="frontend_delivery_v1",
            ),
            authorized_plugins=[
                "Plugin_FileIO",
                "Plugin_PytestRunner",
                "Plugin_BrowserInspector",
            ],
            subscribed_events=[
                "UI_WORK_REQUESTED",
                "DIAGNOSIS_COMPLETE",
                "REFACTORING_REQUESTED",
            ],
            config={"max_parallel_tasks": 1, "specialty": "frontend"},
        )
        return self._write_proposal(
            change_type="create_blueprint",
            target_role=blueprint.role_name,
            rationale=rationale,
            blueprint=asdict(blueprint),
        )

    def propose_observer(self, rationale: str) -> OrganizationChangeProposal:
        """Propose a conservative observer blueprint when no clear gap dominates."""
        blueprint = AgentBlueprint(
            role_name="Organization_Observer",
            version="1.0",
            agent_class="dual_ring_ai.genesis.strategist.StrategistAgent",
            core_prompt="Observe organization metrics and report structural risks.",
            thinking_engine=ThinkingEngineRef(
                name="thought_tree_reasoner",
                version="1.0.0",
                evaluation_suite="organization_v1",
            ),
            authorized_plugins=["Plugin_SystemAnalytics"],
            subscribed_events=["EXECUTION_COMPLETED", "EXECUTION_FAILED"],
            config={"max_parallel_tasks": 1, "specialty": "organization_analysis"},
        )
        return self._write_proposal(
            change_type="create_blueprint",
            target_role=blueprint.role_name,
            rationale=rationale,
            blueprint=asdict(blueprint),
        )

    def _write_proposal(
        self,
        change_type: str,
        target_role: str,
        rationale: str,
        blueprint: dict[str, Any],
    ) -> OrganizationChangeProposal:
        created_at = datetime.now(UTC).isoformat()
        proposal_id = f"org_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S_%f')}"
        proposal_path = self.proposal_dir / f"{proposal_id}.json"
        proposal = OrganizationChangeProposal(
            proposal_id=proposal_id,
            change_type=change_type,
            target_role=target_role,
            rationale=rationale,
            blueprint=blueprint,
            status="proposed",
            requires_human_approval=True,
            proposal_path=proposal_path,
            created_at=created_at,
        )
        payload = asdict(proposal)
        payload["proposal_path"] = str(proposal_path)
        proposal_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        self.event_bus.publish(
            EventTypes.ORGANIZATION_CHANGE_PROPOSED,
            payload,
            "founder_agent",
        )
        self.event_bus.publish(
            EventTypes.ORGANIZATION_APPROVAL_REQUIRED,
            {
                "proposal_id": proposal_id,
                "proposal_path": str(proposal_path),
                "target_role": target_role,
                "reason": "Organization blueprint changes require architect approval.",
            },
            "founder_agent",
        )
        return proposal
