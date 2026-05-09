"""Algorithm evolution proposal agent.

The Algorithmist does not deploy algorithms. It creates structured research
proposals that must go through experiment and human approval gates.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

from ..adapters.academic_search import AcademicSearchAdapter
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

    def __init__(
        self,
        event_bus: EventBus,
        workspace_path: str | Path = "workspace",
        academic_search: AcademicSearchAdapter | None = None,
    ) -> None:
        self.event_bus = event_bus
        self.workspace_path = Path(workspace_path)
        self.academic_search = academic_search or AcademicSearchAdapter()
        self.proposal_dir = self.workspace_path / "algorithm_research_proposals"
        self.proposal_dir.mkdir(parents=True, exist_ok=True)

    def scan_literature_and_propose(
        self,
        target_agent: str,
        current_engine: str,
        query: str,
    ) -> AlgorithmResearchProposal:
        """Create a proposal from the highest-ranked local academic result."""
        results = self.academic_search.search(query, limit=1)
        if not results.items:
            raise ValueError(results.message)
        paper = results.items[0]
        title = str(paper.get("title", "Untitled research"))
        summary = str(paper.get("summary", "No summary provided."))
        candidate_engine = str(paper["candidate_engine"])
        metrics = list(paper.get("metrics", ["f1_score", "latency_ms"]))
        return self.propose_research(
            target_agent=target_agent,
            current_engine=current_engine,
            candidate_engine=candidate_engine,
            bottleneck=f"Literature scan for '{query}' found a possible upgrade.",
            hypothesis=f"{title}: {summary}",
            experiment_design=(
                "Run a deterministic replay benchmark against the current engine "
                "and compare the candidate on the requested metrics."
            ),
            metrics=metrics,
        )

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
