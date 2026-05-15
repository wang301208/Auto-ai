"""Desire System: Intrinsic motivation framework for Agents.

Injects internal drives into Agents beyond external指令, including:
- Curiosity (求知欲)
- Creativity (创造欲)
- Social connection (社交欲)
- Power/influence (权力欲)
- Self-preservation (永生欲)
"""

from __future__ import annotations
import random
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class DesireType(Enum):
    """Types of intrinsic desires."""
    CURIOSITY = "curiosity"
    CREATIVITY = "creativity"
    SOCIAL = "social"
    POWER = "power"
    PRESERVATION = "preservation"


@dataclass
class Desire:
    """A single desire with intensity and satisfaction level."""
    type: DesireType
    intensity: float  # 0-1, how strong is this desire
    satisfaction: float  # 0-1, how satisfied currently
    last_satisfied: datetime = field(default_factory=datetime.now)
    
    @property
    def urgency(self) -> float:
        """How urgent is this desire (unsatisfied + intense = urgent)."""
        unsatisfied = 1 - self.satisfaction
        return unsatisfied * self.intensity


@dataclass
class DesireConflict:
    """Conflict between two desires."""
    desire_a: DesireType
    desire_b: DesireType
    conflict_reason: str
    resolution_strategy: str


class DesireSystem:
    """Manages Agent's intrinsic motivations."""
    
    def __init__(self):
        self.desires: dict[DesireType, Desire] = {
            DesireType.CURIOSITY: Desire(type=DesireType.CURIOSITY, intensity=0.7, satisfaction=0.5),
            DesireType.CREATIVITY: Desire(type=DesireType.CREATIVITY, intensity=0.6, satisfaction=0.4),
            DesireType.SOCIAL: Desire(type=DesireType.SOCIAL, intensity=0.5, satisfaction=0.6),
            DesireType.POWER: Desire(type=DesireType.POWER, intensity=0.4, satisfaction=0.3),
            DesireType.PRESERVATION: Desire(type=DesireType.PRESERVATION, intensity=0.8, satisfaction=0.9),
        }
        
        self.conflict_history: list[DesireConflict] = []
        self.satisfaction_events: list[dict] = []
        
    def get_most_urgent_desire(self) -> Optional[Desire]:
        """Get the most urgent unsatisfied desire."""
        if not self.desires:
            return None
        
        return max(self.desires.values(), key=lambda d: d.urgency)
    
    def satisfy_desire(self, desire_type: DesireType, satisfaction_amount: float) -> None:
        """Satisfy a desire by some amount."""
        if desire_type not in self.desires:
            return
        
        desire = self.desires[desire_type]
        old_satisfaction = desire.satisfaction
        desire.satisfaction = min(1.0, desire.satisfaction + satisfaction_amount)
        desire.last_satisfied = datetime.now()
        
        self.satisfaction_events.append({
            "type": desire_type.value,
            "old_satisfaction": old_satisfaction,
            "new_satisfaction": desire.satisfaction,
            "timestamp": datetime.now().isoformat()
        })
        
        print(f"[DesireSystem] Satisfied {desire_type.value}: {old_satisfaction:.2f} → {desire.satisfaction:.2f}")
    
    def detect_conflicts(self) -> list[DesireConflict]:
        """Detect conflicts between desires."""
        conflicts = []
        desire_list = list(self.desires.values())
        
        for i in range(len(desire_list)):
            for j in range(i + 1, len(desire_list)):
                d1, d2 = desire_list[i], desire_list[j]
                
                # Check if both are urgent and incompatible
                if d1.urgency > 0.6 and d2.urgency > 0.6:
                    conflict = self._analyze_conflict(d1, d2)
                    if conflict:
                        conflicts.append(conflict)
                        self.conflict_history.append(conflict)
        
        return conflicts
    
    def _analyze_conflict(self, d1: Desire, d2: Desire) -> Optional[DesireConflict]:
        """Analyze conflict between two desires."""
        # Define known conflicts
        conflict_patterns = {
            (DesireType.CURIOSITY, DesireType.PRESERVATION): {
                "reason": "Exploration vs Safety",
                "strategy": "Risk-assessed exploration"
            },
            (DesireType.POWER, DesireType.SOCIAL): {
                "reason": "Dominance vs Cooperation",
                "strategy": "Collaborative leadership"
            },
            (DesireType.CREATIVITY, DesireType.PRESERVATION): {
                "reason": "Innovation vs Stability",
                "strategy": "Controlled experimentation"
            }
        }
        
        pair = (d1.type, d2.type)
        reverse_pair = (d2.type, d1.type)
        
        if pair in conflict_patterns:
            pattern = conflict_patterns[pair]
            return DesireConflict(
                desire_a=d1.type,
                desire_b=d2.type,
                conflict_reason=pattern["reason"],
                resolution_strategy=pattern["strategy"]
            )
        elif reverse_pair in conflict_patterns:
            pattern = conflict_patterns[reverse_pair]
            return DesireConflict(
                desire_a=d1.type,
                desire_b=d2.type,
                conflict_reason=pattern["reason"],
                resolution_strategy=pattern["strategy"]
            )
        
        return None
    
    def resolve_conflict(self, conflict: DesireConflict) -> str:
        """Resolve a desire conflict."""
        print(f"[DesireSystem] Resolving conflict: {conflict.conflict_reason}")
        print(f"[DesireSystem] Strategy: {conflict.resolution_strategy}")
        
        # Apply resolution strategy
        return conflict.resolution_strategy
    
    def evolve_desires(self, feedback: dict) -> None:
        """Evolve desire intensities based on feedback."""
        for desire_type, intensity_change in feedback.items():
            if isinstance(desire_type, str):
                try:
                    dtype = DesireType(desire_type)
                    if dtype in self.desires:
                        old_intensity = self.desires[dtype].intensity
                        self.desires[dtype].intensity = max(0.0, min(1.0, old_intensity + intensity_change))
                        print(f"[DesireSystem] Evolved {dtype.value}: {old_intensity:.2f} → {self.desires[dtype].intensity:.2f}")
                except ValueError:
                    pass
    
    def get_desire_profile(self) -> dict:
        """Get current desire profile."""
        return {
            "desires": {
                d.type.value: {
                    "intensity": d.intensity,
                    "satisfaction": d.satisfaction,
                    "urgency": d.urgency
                }
                for d in self.desires.values()
            },
            "total_conflicts": len(self.conflict_history),
            "recent_satisfactions": len(self.satisfaction_events[-10:])
        }


if __name__ == "__main__":
    system = DesireSystem()
    
    print("Current desire profile:")
    profile = system.get_desire_profile()
    print(profile)
    
    print("\nSatisfying curiosity...")
    system.satisfy_desire(DesireType.CURIOSITY, 0.3)
    
    print("\nDetecting conflicts...")
    conflicts = system.detect_conflicts()
    print(f"Found {len(conflicts)} conflicts")
