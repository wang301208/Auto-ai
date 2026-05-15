"""Meme Propagation System: Idea virus transmission between Agents.

Implements memetic evolution:
- Ideas packaged as memes with mutation history
- High-confidence memes spread faster
- Receivers can modify and version memes
- Immune system to reject harmful memes
"""

from __future__ import annotations
import random
import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional


@dataclass
class Meme:
    """A transmissible idea unit."""
    id: str
    content: str
    confidence: float
    source_agent: str
    generation: int
    mutation_history: list[str]
    infection_count: int = 0
    birth_time: datetime = field(default_factory=datetime.now)
    half_life_hours: float = 48.0  # Memes decay over time
    
    @property
    def age_hours(self) -> float:
        """Age of meme in hours."""
        delta = datetime.now() - self.birth_time
        return delta.total_seconds() / 3600
    
    @property
    def vitality(self) -> float:
        """Current vitality (decays with age)."""
        decay_factor = 0.5 ** (self.age_hours / self.half_life_hours)
        return self.confidence * decay_factor


@dataclass
class InfectionEvent:
    """Record of meme transmission."""
    meme_id: str
    from_agent: str
    to_agent: str
    success: bool
    timestamp: datetime = field(default_factory=datetime.now)


class MemePropagationSystem:
    """Manages meme transmission across Agent population."""
    
    def __init__(self):
        self.meme_pool: dict[str, Meme] = {}
        self.infection_log: list[InfectionEvent] = []
        self.agent_immunity: dict[str, set[str]] = {}  # agent -> set of blocked meme IDs
        
    def create_meme(self, content: str, confidence: float, source_agent: str) -> Meme:
        """Create a new meme."""
        meme_id = hashlib.md5(f"{content}{datetime.now()}".encode()).hexdigest()[:12]
        
        meme = Meme(
            id=meme_id,
            content=content,
            confidence=confidence,
            source_agent=source_agent,
            generation=1,
            mutation_history=[]
        )
        
        self.meme_pool[meme_id] = meme
        
        print(f"[MemeSystem] Created meme: {meme_id[:8]}... (confidence: {confidence:.2f})")
        
        return meme
    
    def transmit_meme(self, meme_id: str, from_agent: str, to_agent: str) -> bool:
        """Attempt to transmit a meme from one agent to another."""
        if meme_id not in self.meme_pool:
            print(f"[MemeSystem] Error: Unknown meme {meme_id}")
            return False
        
        meme = self.meme_pool[meme_id]
        
        # Check immunity
        if to_agent in self.agent_immunity:
            if meme_id in self.agent_immunity[to_agent]:
                print(f"[MemeSystem] Agent {to_agent} immune to meme {meme_id[:8]}")
                self._log_infection(meme_id, from_agent, to_agent, False)
                return False
        
        # Transmission probability based on meme vitality and receiver openness
        transmission_prob = meme.vitality * 0.8 + random.random() * 0.2
        
        success = random.random() < transmission_prob
        
        if success:
            meme.infection_count += 1
            
            # Chance of mutation during transmission
            if random.random() < 0.1:  # 10% mutation rate
                mutated_meme = self._mutate_meme(meme)
                print(f"[MemeSystem] Meme mutated during transmission: {mutated_meme.id[:8]}")
        
        self._log_infection(meme_id, from_agent, to_agent, success)
        
        return success
    
    def _mutate_meme(self, original_meme: Meme) -> Meme:
        """Create a mutated version of a meme."""
        # Simple mutation: slightly modify confidence
        mutated_confidence = max(0.0, min(1.0, original_meme.confidence + random.uniform(-0.1, 0.1)))
        
        mutated_id = hashlib.md5(f"{original_meme.content}{random.random()}".encode()).hexdigest()[:12]
        
        mutated = Meme(
            id=mutated_id,
            content=original_meme.content,
            confidence=mutated_confidence,
            source_agent=original_meme.source_agent,
            generation=original_meme.generation + 1,
            mutation_history=original_meme.mutation_history + [original_meme.id]
        )
        
        self.meme_pool[mutated_id] = mutated
        
        return mutated
    
    def immunize_agent(self, agent_id: str, meme_id: str) -> None:
        """Make an agent immune to a specific meme."""
        if agent_id not in self.agent_immunity:
            self.agent_immunity[agent_id] = set()
        
        self.agent_immunity[agent_id].add(meme_id)
        print(f"[MemeSystem] Agent {agent_id} immunized against meme {meme_id[:8]}")
    
    def clean_expired_memes(self) -> int:
        """Remove memes that have expired."""
        expired = []
        
        for meme_id, meme in self.meme_pool.items():
            if meme.vitality < 0.05:  # Very low vitality
                expired.append(meme_id)
        
        for meme_id in expired:
            del self.meme_pool[meme_id]
        
        if expired:
            print(f"[MemeSystem] Cleaned {len(expired)} expired memes")
        
        return len(expired)
    
    def _log_infection(self, meme_id: str, from_agent: str, to_agent: str, success: bool) -> None:
        """Log infection event."""
        event = InfectionEvent(
            meme_id=meme_id,
            from_agent=from_agent,
            to_agent=to_agent,
            success=success
        )
        self.infection_log.append(event)
    
    def get_viral_memes(self, top_n: int = 5) -> list[Meme]:
        """Get most viral memes."""
        sorted_memes = sorted(
            self.meme_pool.values(),
            key=lambda m: m.infection_count,
            reverse=True
        )
        
        return sorted_memes[:top_n]
    
    def get_propagation_statistics(self) -> dict:
        """Get propagation statistics."""
        total_infections = len([e for e in self.infection_log if e.success])
        total_attempts = len(self.infection_log)
        
        success_rate = total_infections / total_attempts if total_attempts > 0 else 0
        
        return {
            "total_memes": len(self.meme_pool),
            "total_infections": total_infections,
            "total_attempts": total_attempts,
            "success_rate": success_rate,
            "viral_memes": len([m for m in self.meme_pool.values() if m.infection_count > 5])
        }


if __name__ == "__main__":
    system = MemePropagationSystem()
    
    # Create memes
    meme1 = system.create_meme("Optimization technique #42", 0.85, "agent_001")
    meme2 = system.create_meme("Bug fix pattern Alpha", 0.92, "agent_002")
    
    # Transmit
    system.transmit_meme(meme1.id, "agent_001", "agent_003")
    system.transmit_meme(meme2.id, "agent_002", "agent_003")
    
    # Get viral memes
    viral = system.get_viral_memes()
    print(f"\nViral memes: {len(viral)}")
    
    print(f"\nStatistics: {system.get_propagation_statistics()}")
