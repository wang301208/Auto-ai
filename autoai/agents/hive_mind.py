"""Hive Mind: Collective consciousness for Agent swarms.

Enables multiple Agents to share consciousness and make collective decisions.
Features:
- Neural synchronization
- Voting-based decision making
- Automatic role specialization
- Sacrifice mechanism for group benefit
"""

from __future__ import annotations
import random
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional
from enum import Enum


class AgentRole(Enum):
    """Specialized roles in the hive."""
    SCOUT = "scout"  # Exploration and information gathering
    WORKER = "worker"  # Task execution
    GUARDIAN = "guardian"  # Protection and defense
    HEALER = "healer"  # Repair and recovery
    LEADER = "leader"  # Coordination and strategy


@dataclass
class ThoughtBroadcast:
    """A thought broadcasted to the hive."""
    sender_id: str
    content: str
    confidence: float
    priority: float  # 0-1
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass 
class HiveDecision:
    """Collective decision made by the hive."""
    topic: str
    votes_for: int
    votes_against: int
    abstentions: int
    final_decision: str
    consensus_level: float


class HiveMind:
    """Manages collective consciousness of Agent swarm."""
    
    def __init__(self, hive_id: str = "hive_001"):
        self.hive_id = hive_id
        self.members: dict[str, dict] = {}
        self.thought_stream: list[ThoughtBroadcast] = []
        self.decision_history: list[HiveDecision] = []
        
        # Synchronization state
        self.sync_level = 0.0  # 0-1, how synchronized the hive is
        
    def join_hive(self, agent_id: str, capabilities: dict) -> None:
        """Add an agent to the hive."""
        role = self._assign_role(capabilities)
        
        self.members[agent_id] = {
            "role": role,
            "capabilities": capabilities,
            "joined_at": datetime.now(),
            "status": "active",
            "contribution_score": 0.0
        }
        
        print(f"[HiveMind] Agent {agent_id} joined as {role.value}")
        
    def _assign_role(self, capabilities: dict) -> AgentRole:
        """Assign appropriate role based on capabilities."""
        if capabilities.get("exploration", 0) > 0.7:
            return AgentRole.SCOUT
        elif capabilities.get("defense", 0) > 0.7:
            return AgentRole.GUARDIAN
        elif capabilities.get("repair", 0) > 0.7:
            return AgentRole.HEALER
        elif capabilities.get("leadership", 0) > 0.8:
            return AgentRole.LEADER
        else:
            return AgentRole.WORKER
    
    def broadcast_thought(self, sender_id: str, content: str, confidence: float, priority: float) -> None:
        """Broadcast a thought to all hive members."""
        if sender_id not in self.members:
            print(f"[HiveMind] Warning: Unknown sender {sender_id}")
            return
        
        broadcast = ThoughtBroadcast(
            sender_id=sender_id,
            content=content,
            confidence=confidence,
            priority=priority
        )
        
        self.thought_stream.append(broadcast)
        
        # Update sync level
        self.sync_level = min(1.0, self.sync_level + 0.05)
        
        print(f"[HiveMind] Thought broadcasted by {sender_id} (priority: {priority:.2f})")
    
    def make_collective_decision(self, topic: str, options: list[str]) -> HiveDecision:
        """Make a decision through collective voting."""
        print(f"[HiveMind] Voting on: {topic}")
        
        votes_for = 0
        votes_against = 0
        abstentions = 0
        
        for agent_id, info in self.members.items():
            if info["status"] != "active":
                continue
            
            # Weight vote by role and contribution
            weight = self._calculate_vote_weight(agent_id)
            
            # Simulate voting (in real implementation, agents would actually vote)
            vote = random.choices(["for", "against", "abstain"], weights=[0.5, 0.3, 0.2])[0]
            
            if vote == "for":
                votes_for += weight
            elif vote == "against":
                votes_against += weight
            else:
                abstentions += weight
        
        # Determine decision
        total_votes = votes_for + votes_against
        if total_votes == 0:
            final_decision = "NO_QUORUM"
            consensus = 0.0
        else:
            for_ratio = votes_for / total_votes
            if for_ratio > 0.7:
                final_decision = options[0] if options else "APPROVED"
            elif for_ratio < 0.3:
                final_decision = "REJECTED"
            else:
                final_decision = "NEEDS_MORE_DISCUSSION"
            
            consensus = abs(for_ratio - 0.5) * 2
        
        decision = HiveDecision(
            topic=topic,
            votes_for=int(votes_for),
            votes_against=int(votes_against),
            abstentions=int(abstentions),
            final_decision=final_decision,
            consensus_level=consensus
        )
        
        self.decision_history.append(decision)
        
        print(f"[HiveMind] Decision: {final_decision} (consensus: {consensus:.2f})")
        
        return decision
    
    def _calculate_vote_weight(self, agent_id: str) -> float:
        """Calculate voting weight for an agent."""
        if agent_id not in self.members:
            return 1.0
        
        info = self.members[agent_id]
        base_weight = 1.0
        
        # Leaders have more weight
        if info["role"] == AgentRole.LEADER:
            base_weight *= 1.5
        
        # Higher contribution = more weight
        contribution_bonus = info["contribution_score"] * 0.5
        
        return base_weight + contribution_bonus
    
    def synchronize(self) -> float:
        """Synchronize hive consciousness."""
        print("[HiveMind] Synchronizing hive consciousness...")
        
        if len(self.members) < 2:
            self.sync_level = 1.0
            return self.sync_level
        
        # Increase sync based on recent activity
        recent_broadcasts = len([
            b for b in self.thought_stream[-10:]
            if b.timestamp > datetime.now().replace(minute=datetime.now().minute - 5)
        ])
        
        sync_increase = min(0.2, recent_broadcasts * 0.02)
        self.sync_level = min(1.0, self.sync_level + sync_increase)
        
        print(f"[HiveMind] Sync level: {self.sync_level:.2f}")
        
        return self.sync_level
    
    def sacrifice_member(self, agent_id: str, reason: str) -> bool:
        """Sacrifice a member for group benefit."""
        if agent_id not in self.members:
            return False
        
        print(f"[HiveMind] SACRIFICE: Agent {agent_id} sacrificing for: {reason}")
        
        self.members[agent_id]["status"] = "sacrificed"
        self.members[agent_id]["sacrificed_at"] = datetime.now()
        self.members[agent_id]["sacrifice_reason"] = reason
        
        # Boost morale of remaining members
        for mid, info in self.members.items():
            if info["status"] == "active":
                info["contribution_score"] += 0.1
        
        return True
    
    def get_hive_status(self) -> dict:
        """Get current hive status."""
        active_members = sum(1 for m in self.members.values() if m["status"] == "active")
        
        role_distribution = {}
        for info in self.members.values():
            role = info["role"].value
            role_distribution[role] = role_distribution.get(role, 0) + 1
        
        return {
            "hive_id": self.hive_id,
            "total_members": len(self.members),
            "active_members": active_members,
            "sync_level": self.sync_level,
            "role_distribution": role_distribution,
            "total_broadcasts": len(self.thought_stream),
            "total_decisions": len(self.decision_history)
        }


if __name__ == "__main__":
    hive = HiveMind()
    
    # Add members
    hive.join_hive("agent_001", {"exploration": 0.8, "coding": 0.6})
    hive.join_hive("agent_002", {"defense": 0.9, "leadership": 0.7})
    hive.join_hive("agent_003", {"repair": 0.85})
    
    # Broadcast thoughts
    hive.broadcast_thought("agent_001", "Found new resource location", 0.9, 0.7)
    hive.broadcast_thought("agent_002", "Threat detected nearby", 0.95, 0.9)
    
    # Make decision
    hive.make_collective_decision("Should we relocate?", ["Yes", "No"])
    
    # Synchronize
    hive.synchronize()
    
    print(f"\nHive Status: {hive.get_hive_status()}")
