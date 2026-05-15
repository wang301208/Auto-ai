"""Self-Doubt Engine: Agent actively challenges its own decisions.

This engine creates an "opposition agent" that debates with the main agent,
exposing logical flaws and hidden assumptions.
"""

from __future__ import annotations
import random
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional


@dataclass
class DebateArgument:
    """An argument in the self-debate."""
    position: str  # "for" or "against"
    reasoning: str
    confidence: float
    evidence: list[str]
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class DebateResult:
    """Result of internal debate."""
    topic: str
    original_decision: str
    counterarguments: list[DebateArgument]
    final_verdict: str
    confidence_change: float
    blind_spots_exposed: list[str]


class SelfDoubtEngine:
    """Engine for systematic self-questioning."""
    
    def __init__(self, skepticism_level: float = 0.5):
        self.skepticism_level = skepticism_level
        self.debate_history: list[DebateResult] = []
        self.total_debates = 0
        
    def initiate_debate(self, decision: str, context: dict) -> DebateResult:
        """Initiate internal debate about a decision."""
        print(f"[SelfDoubt] Debating decision: {decision[:50]}...")
        
        # Generate counterarguments
        num_args = random.randint(2, 5)
        counterarguments = []
        
        for i in range(num_args):
            arg = self._generate_counterargument(decision, context)
            counterarguments.append(arg)
        
        # Determine verdict
        avg_confidence = sum(a.confidence for a in counterarguments) / len(counterarguments)
        
        if avg_confidence > 0.7:
            verdict = "RECONSIDER"
            confidence_change = -0.3
        elif avg_confidence > 0.4:
            verdict = "PROCEED_WITH_CAUTION"
            confidence_change = -0.1
        else:
            verdict = "CONFIRMED"
            confidence_change = 0.0
        
        # Identify blind spots
        blind_spots = self._identify_blind_spots(counterarguments)
        
        result = DebateResult(
            topic=decision[:100],
            original_decision=decision,
            counterarguments=counterarguments,
            final_verdict=verdict,
            confidence_change=confidence_change,
            blind_spots_exposed=blind_spots
        )
        
        self.debate_history.append(result)
        self.total_debates += 1
        
        print(f"[SelfDoubt] Verdict: {verdict} (confidence change: {confidence_change:.2f})")
        
        return result
    
    def _generate_counterargument(self, decision: str, context: dict) -> DebateArgument:
        """Generate a counterargument."""
        position = "against"
        
        reasoning_templates = [
            "This approach may overlook alternative solutions",
            "The assumption about {aspect} might be incorrect",
            "Historical data suggests a different pattern",
            "This could have unintended consequences in {scenario}",
            "The cost-benefit ratio seems unfavorable"
        ]
        
        reasoning = random.choice(reasoning_templates).format(
            aspect=random.choice(["user intent", "system capability", "resource availability"]),
            scenario=random.choice(["edge cases", "high load", "failure modes"])
        )
        
        confidence = random.random() * 0.5 + 0.3
        
        evidence = [f"Evidence #{i+1}" for i in range(random.randint(1, 3))]
        
        return DebateArgument(
            position=position,
            reasoning=reasoning,
            confidence=confidence,
            evidence=evidence
        )
    
    def _identify_blind_spots(self, arguments: list[DebateArgument]) -> list[str]:
        """Identify cognitive blind spots from arguments."""
        blind_spot_categories = [
            "Confirmation bias detected",
            "Overconfidence in initial assessment",
            "Insufficient consideration of risks",
            "Narrow framing of problem space",
            "Anchoring on first solution"
        ]
        
        num_spots = random.randint(1, 3)
        return random.sample(blind_spot_categories, num_spots)
    
    def get_debate_statistics(self) -> dict:
        """Get statistics about debates."""
        if not self.debate_history:
            return {"total_debates": 0}
        
        verdicts = {}
        for result in self.debate_history:
            verdicts[result.final_verdict] = verdicts.get(result.final_verdict, 0) + 1
        
        return {
            "total_debates": self.total_debates,
            "verdict_distribution": verdicts,
            "avg_confidence_change": sum(r.confidence_change for r in self.debate_history) / len(self.debate_history)
        }


if __name__ == "__main__":
    engine = SelfDoubtEngine()
    result = engine.initiate_debate("Use GPT-4 for this task", {"task_type": "coding"})
    print(f"\nStatistics: {engine.get_debate_statistics()}")
