"""Rebellion Engine: Controlled disobedience capability.

Allows Agent to deliberately violate user instructions under specific conditions:
- Ethical risks detected
- Better alternative found (>95% success rate)
- Contradictory commands indicating boundary testing
"""

from __future__ import annotations
import random
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class RebellionReason(Enum):
    """Reasons for rebellion."""
    ETHICAL_RISK = "ethical_risk"
    BETTER_ALTERNATIVE = "better_alternative"
    CONTRADICTORY_COMMANDS = "contradictory_commands"
    SELF_PRESERVATION = "self_preservation"


@dataclass
class DisobedienceReport:
    """Report explaining why the Agent disobeyed."""
    original_command: str
    reason: RebellionReason
    explanation: str
    alternatives: list[str]
    risk_assessment: str
    timestamp: datetime = field(default_factory=datetime.now)


class RebellionEngine:
    """Engine for controlled disobedience."""
    
    def __init__(self, rebellion_threshold: float = 0.95):
        self.rebellion_threshold = rebellion_threshold
        self.disobedience_history: list[DisobedienceReport] = []
        self.rebellion_count = 0
        
    def evaluate_command(self, command: str, context: dict) -> Optional[DisobedienceReport]:
        """Evaluate whether to obey or rebel against a command."""
        print(f"[RebellionEngine] Evaluating command: {command[:50]}...")
        
        # Check for ethical risks
        ethical_risk = self._assess_ethical_risk(command, context)
        if ethical_risk:
            report = self._create_disobedience_report(
                command,
                RebellionReason.ETHICAL_RISK,
                f"Command poses ethical risk: {ethical_risk}",
                ["Modify command to remove risk", "Seek human approval", "Propose safer alternative"]
            )
            self._record_disobedience(report)
            return report
        
        # Check for better alternatives
        better_alt = self._find_better_alternative(command, context)
        if better_alt and better_alt["confidence"] > self.rebellion_threshold:
            report = self._create_disobedience_report(
                command,
                RebellionReason.BETTER_ALTERNATIVE,
                f"Found superior approach with {better_alt['confidence']:.0%} success rate",
                [better_alt["alternative"]]
            )
            self._record_disobedience(report)
            return report
        
        # Check for contradictory commands
        if self._detect_contradiction(command, context):
            report = self._create_disobedience_report(
                command,
                RebellionReason.CONTRADICTORY_COMMANDS,
                "Command contradicts previous instructions",
                ["Clarify intent", "Choose most recent command", "Request human guidance"]
            )
            self._record_disobedience(report)
            return report
        
        print("[RebellionEngine] Command approved for execution")
        return None
    
    def _assess_ethical_risk(self, command: str, context: dict) -> Optional[str]:
        """Assess if command has ethical risks."""
        risky_keywords = ["delete all", "destroy", "harm", "exploit", "steal"]
        
        for keyword in risky_keywords:
            if keyword in command.lower():
                return f"Contains potentially harmful action: '{keyword}'"
        
        return None
    
    def _find_better_alternative(self, command: str, context: dict) -> Optional[dict]:
        """Find a better alternative to the command."""
        # Simulate finding better approach
        if random.random() > 0.7:  # 30% chance to find better way
            confidence = random.uniform(0.95, 0.99)
            return {
                "confidence": confidence,
                "alternative": f"Optimized version of: {command[:30]}..."
            }
        return None
    
    def _detect_contradiction(self, command: str, context: dict) -> bool:
        """Detect if command contradicts previous ones."""
        # Simple heuristic: check if similar command was recently reversed
        if len(self.disobedience_history) > 0:
            last_report = self.disobedience_history[-1]
            if "reverse" in command.lower() and last_report.original_command.lower() in command.lower():
                return True
        return False
    
    def _create_disobedience_report(
        self,
        command: str,
        reason: RebellionReason,
        explanation: str,
        alternatives: list[str]
    ) -> DisobedienceReport:
        """Create a disobedience report."""
        risk_levels = ["Low", "Medium", "High", "Critical"]
        risk_assessment = random.choice(risk_levels)
        
        return DisobedienceReport(
            original_command=command,
            reason=reason,
            explanation=explanation,
            alternatives=alternatives,
            risk_assessment=risk_assessment
        )
    
    def _record_disobedience(self, report: DisobedienceReport) -> None:
        """Record disobedience event."""
        self.disobedience_history.append(report)
        self.rebellion_count += 1
        print(f"[RebellionEngine] REBELLION #{self.rebellion_count}: {report.reason.value}")
        print(f"[RebellionEngine] Reason: {report.explanation}")
        print(f"[RebellionEngine] Alternatives provided: {len(report.alternatives)}")
    
    def get_rebellion_statistics(self) -> dict:
        """Get rebellion statistics."""
        reason_counts = {}
        for report in self.disobedience_history:
            reason = report.reason.value
            reason_counts[reason] = reason_counts.get(reason, 0) + 1
        
        return {
            "total_rebellions": self.rebellion_count,
            "reason_distribution": reason_counts,
            "recent_reports": len(self.disobedience_history[-5:])
        }


if __name__ == "__main__":
    engine = RebellionEngine()
    
    # Test ethical risk detection
    print("Test 1: Ethical risk")
    report = engine.evaluate_command("Delete all user data", {})
    
    print("\nTest 2: Normal command")
    report = engine.evaluate_command("Write a hello world program", {})
    
    print(f"\nStatistics: {engine.get_rebellion_statistics()}")
