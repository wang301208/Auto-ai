"""Algorithm evolution proposal agent.

The Algorithmist does not deploy algorithms. It creates structured research
proposals that must go through experiment and human approval gates.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

from ..core.event_bus import EventBus, EventTypes


@dataclass
class AlgorithmResearchProposal:
    """Structured Algorithm Evolution Protocol proposal."""

    proposal_id: str
    target_agent: str
    current_engine: str
    candidate_engine: str
    bottleneck: str
    hypothesis: str
    experiment_design: str
    metrics: list[str]
    status: str
    requires_human_approval: bool
    created_at: str


class AlgorithmistAgent:
    """Create research proposals for thinking engine upgrades."""

    def __init__(self, event_bus: EventBus, workspace_path: str | Path = "workspace") -> None:
        self.event_bus = event_bus
        self.workspace_path = Path(workspace_path)
        self.proposal_dir = self.workspace_path / "algorithm_research_proposals"
        self.proposal_dir.mkdir(parents=True, exist_ok=True)

    def propose_research(
        self,
        target_agent: str,
        current_engine: str,
        candidate_engine: str,
        bottleneck: str,
        hypothesis: str,
        experiment_design: str,
        metrics: list[str],
    ) -> AlgorithmResearchProposal:
        created_at = datetime.now(UTC).isoformat()
        proposal_id = f"aep_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S_%f')}"
        proposal = AlgorithmResearchProposal(
            proposal_id=proposal_id,
            target_agent=target_agent,
            current_engine=current_engine,
            candidate_engine=candidate_engine,
            bottleneck=bottleneck,
            hypothesis=hypothesis,
            experiment_design=experiment_design,
            metrics=metrics,
            status="proposed",
            requires_human_approval=True,
            created_at=created_at,
        )

        proposal_path = self.proposal_dir / f"{proposal_id}.json"
        proposal_path.write_text(
            json.dumps(asdict(proposal), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        payload = asdict(proposal)
        payload["proposal_path"] = str(proposal_path)
        self.event_bus.publish(
            EventTypes.ALGORITHM_RESEARCH_PROPOSED,
            payload,
            "algorithmist_agent",
        )
        self.event_bus.publish(
            EventTypes.ALGORITHM_APPROVAL_REQUIRED,
            {
                "proposal_id": proposal_id,
                "proposal_path": str(proposal_path),
                "target_agent": target_agent,
                "candidate_engine": candidate_engine,
                "reason": "Algorithm research proposals require human approval.",
            },
            "algorithmist_agent",
        )

        return proposal
