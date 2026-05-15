"""Dream Simulator: Subconscious exploration and creative innovation.

The Dream Simulator allows Agents to enter a "dream state" during idle periods,
where they randomly combine historical experiences to generate innovative solutions.
"""

from __future__ import annotations

import random
import time
import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional
from pathlib import Path
from enum import Enum
import numpy as np


class DreamPhase(Enum):
    """Sleep cycle phases."""
    REM = "rem"
    DEEP = "deep"
    LIGHT = "light"
    AWAKE = "awake"


@dataclass
class DreamFragment:
    """A fragment of dream content - combination of experiences."""
    id: str
    components: list[str]
    novelty_score: float
    feasibility_score: float
    absurdity_level: float
    timestamp: datetime = field(default_factory=datetime.now)
    description: str = ""


@dataclass
class InnovationProposal:
    """A concrete innovation proposal from dreams."""
    title: str
    description: str
    source_dreams: list[str]
    expected_impact: str
    risk_level: str
    implementation_steps: list[str]
    confidence: float
    created_at: datetime = field(default_factory=datetime.now)


class DreamSimulator:
    """
    Simulates Agent subconscious exploration during idle periods.
    
    The simulator operates in cycles:
    1. Collect historical experiences and successful patterns
    2. Enter REM phase - randomly recombine elements
    3. Evaluate novelty and feasibility
    4. Consolidate promising ideas in deep sleep
    5. Present top innovations upon waking
    """
    
    def __init__(
        self,
        experience_db_path: str = "./experience",
        dream_log_path: str = "./dreams",
        innovation_threshold: float = 0.7,
        max_daily_proposals: int = 3
    ):
        self.experience_db_path = Path(experience_db_path)
        self.dream_log_path = Path(dream_log_path)
        self.dream_log_path.mkdir(parents=True, exist_ok=True)
        
        self.innovation_threshold = innovation_threshold
        self.max_daily_proposals = max_daily_proposals
        
        self.current_phase = DreamPhase.AWAKE
        self.active_dreams: list[DreamFragment] = []
        self.consolidated_ideas: list[InnovationProposal] = []
        self.today_proposals: list[InnovationProposal] = []
        
        # Load historical experiences
        self.experience_pool = self._load_experiences()
        
        # Dream statistics
        self.total_dreams = 0
        self.total_innovations = 0
        
    def _load_experiences(self) -> list[dict]:
        """Load historical experiences from database."""
        experiences = []
        
        if not self.experience_db_path.exists():
            return experiences
        
        for json_file in self.experience_db_path.glob("*.json"):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        experiences.extend(data)
                    elif isinstance(data, dict):
                        experiences.append(data)
            except Exception as e:
                print(f"[DreamSimulator] Warning: Failed to load {json_file}: {e}")
        
        return experiences
    
    def run_full_cycle(self) -> list[InnovationProposal]:
        """Run a complete sleep-wake cycle."""
        print("\n[DreamSimulator] Starting full dream cycle")
        self.enter_sleep_mode()
        self.start_rem_phase()
        self.enter_deep_sleep()
        proposals = self.wake_up()
        print(f"[DreamSimulator] Cycle complete. Generated {len(proposals)} proposals\n")
        return proposals

    def enter_sleep_mode(self) -> None:
        """Transition to sleep mode."""
        print("[DreamSimulator] Entering sleep mode...")
        self.current_phase = DreamPhase.LIGHT
        self.active_dreams.clear()

    def start_rem_phase(self) -> list[DreamFragment]:
        """Start REM phase - active dreaming."""
        print("[DreamSimulator] Starting REM phase - Active dreaming...")
        self.current_phase = DreamPhase.REM
        
        num_dreams = random.randint(10, 30)
        new_dreams = []
        
        for i in range(num_dreams):
            dream = self._generate_dream_fragment()
            if dream:
                new_dreams.append(dream)
                self.active_dreams.append(dream)
                self.total_dreams += 1
        
        print(f"[DreamSimulator] Generated {len(new_dreams)} dream fragments")
        return new_dreams

    def _generate_dream_fragment(self) -> Optional[DreamFragment]:
        """Generate a single dream fragment by combining experiences."""
        if not self.experience_pool:
            return None
        
        num_components = random.randint(2, min(5, len(self.experience_pool)))
        components = random.sample(self.experience_pool, num_components)
        
        component_ids = [str(hash(str(c))) for c in components]
        
        novelty = min(1.0, random.random() * 0.7 + 0.3)
        feasibility = min(1.0, random.random() * 0.6 + 0.2)
        absurdity = min(1.0, random.random() * 0.5 + 0.2)
        
        description = f"Dream combining {num_components} experiences"
        fragment_id = f"dream_{int(time.time())}_{random.randint(1000, 9999)}"
        
        return DreamFragment(
            id=fragment_id,
            components=component_ids,
            novelty_score=novelty,
            feasibility_score=feasibility,
            absurdity_level=absurdity,
            description=description
        )

    def enter_deep_sleep(self) -> None:
        """Enter deep sleep phase - consolidate promising ideas."""
        print("[DreamSimulator] Entering deep sleep - Consolidating ideas...")
        self.current_phase = DreamPhase.DEEP
        
        promising = [
            d for d in self.active_dreams
            if d.novelty_score > 0.5 and d.feasibility_score > 0.3
        ]
        
        for dream in promising[:10]:
            proposal = self._create_innovation_proposal(dream)
            if proposal:
                self.consolidated_ideas.append(proposal)
                self.total_innovations += 1

    def _create_innovation_proposal(self, dream: DreamFragment) -> Optional[InnovationProposal]:
        """Transform a dream fragment into a concrete innovation proposal."""
        combined_score = (
            dream.novelty_score * 0.4 + 
            dream.feasibility_score * 0.4 + 
            (1 - dream.absurdity_level) * 0.2
        )
        
        if combined_score < self.innovation_threshold:
            return None
        
        if dream.novelty_score > 0.8:
            impact = "High"
            risk = "High" if dream.feasibility_score < 0.5 else "Medium"
        elif dream.novelty_score > 0.6:
            impact = "Medium"
            risk = "Medium"
        else:
            impact = "Low"
            risk = "Low"
        
        steps = [f"Phase {i+1}" for i in range(7)]
        confidence = combined_score * 0.8 + random.random() * 0.2
        
        title = f"Innovation #{self.total_innovations + 1}"
        
        return InnovationProposal(
            title=title,
            description=dream.description,
            source_dreams=[dream.id],
            expected_impact=impact,
            risk_level=risk,
            implementation_steps=steps,
            confidence=confidence
        )

    def wake_up(self) -> list[InnovationProposal]:
        """Wake up and present today's top innovation proposals."""
        print("[DreamSimulator] Waking up...")
        self.current_phase = DreamPhase.AWAKE
        
        scored = [
            (
                p.confidence * 0.5 +
                (0.8 if p.expected_impact == "High" else 0.5) * 0.3,
                p
            )
            for p in self.consolidated_ideas
        ]
        
        scored.sort(key=lambda x: x[0], reverse=True)
        
        self.today_proposals = [
            p for _, p in scored[:self.max_daily_proposals]
        ]
        
        self._save_proposals()
        self.consolidated_ideas.clear()
        
        return self.today_proposals

    def _save_proposals(self) -> None:
        """Save today's proposals to file."""
        if not self.today_proposals:
            return
        
        proposals_file = self.dream_log_path / f"proposals_{datetime.now().strftime('%Y%m%d')}.json"
        
        try:
            data = [
                {"title": p.title, "confidence": p.confidence}
                for p in self.today_proposals
            ]
            with open(proposals_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[DreamSimulator] Warning: {e}")

    def get_statistics(self) -> dict:
        """Get dream simulator statistics."""
        return {
            "total_dreams": self.total_dreams,
            "total_innovations": self.total_innovations,
            "current_phase": self.current_phase.value,
            "today_proposals_count": len(self.today_proposals)
        }


if __name__ == "__main__":
    simulator = DreamSimulator()
    proposals = simulator.run_full_cycle()
    print(f"Statistics: {json.dumps(simulator.get_statistics(), indent=2)}")
