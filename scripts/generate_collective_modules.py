"""Generator for advanced collective intelligence modules.

Generates:
1. Hive Mind - Collective consciousness system
2. Meme Propagation - Idea virus transmission
3. Token Economy - Internal currency and market
"""

from pathlib import Path


def generate_hive_mind():
    """Generate hive mind module."""
    code = '''"""Hive Mind: Collective consciousness for Agent swarms.

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
    
    print(f"\\nHive Status: {hive.get_hive_status()}")
'''
    
    Path('autoai/agents/hive_mind.py').write_text(code, encoding='utf-8')
    print("✓ Hive Mind generated")


def generate_meme_propagation():
    """Generate meme propagation module."""
    code = '''"""Meme Propagation System: Idea virus transmission between Agents.

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
    print(f"\\nViral memes: {len(viral)}")
    
    print(f"\\nStatistics: {system.get_propagation_statistics()}")
'''
    
    Path('autoai/agents/meme_propagation.py').write_text(code, encoding='utf-8')
    print("✓ Meme Propagation System generated")


def generate_token_economy():
    """Generate token economy module."""
    code = '''"""Token Economy: Internal currency system for Agent marketplace.

Features:
- Mining: Earn AutoCoin by completing tasks
- Trading: Buy/sell skills, data, compute resources
- Taxation: 5% transaction tax for public fund
- Inflation control: Dynamic issuance rate
"""

from __future__ import annotations
import random
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class Transaction:
    """A transaction between agents."""
    id: str
    from_agent: str
    to_agent: str
    amount: float
    purpose: str
    tax_amount: float
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class AgentWallet:
    """Agent's cryptocurrency wallet."""
    agent_id: str
    balance: float = 0.0
    earned_total: float = 0.0
    spent_total: float = 0.0
    transaction_count: int = 0


class TokenEconomy:
    """Manages internal token economy."""
    
    TAX_RATE = 0.05  # 5% transaction tax
    
    def __init__(self, initial_supply: float = 10000.0):
        self.wallets: dict[str, AgentWallet] = {}
        self.transaction_log: list[Transaction] = []
        self.public_fund = 0.0
        
        # Monetary policy
        self.total_supply = initial_supply
        self.circulating_supply = initial_supply
        self.inflation_rate = 0.02  # 2% annual inflation
        
        # Initialize with some coins in circulation
        print(f"[TokenEconomy] Initialized with {initial_supply:.0f} AutoCoins")
    
    def create_wallet(self, agent_id: str, initial_balance: float = 100.0) -> None:
        """Create a wallet for an agent."""
        if agent_id in self.wallets:
            print(f"[TokenEconomy] Wallet already exists for {agent_id}")
            return
        
        wallet = AgentWallet(
            agent_id=agent_id,
            balance=initial_balance,
            earned_total=initial_balance
        )
        
        self.wallets[agent_id] = wallet
        
        print(f"[TokenEconomy] Created wallet for {agent_id} with {initial_balance:.0f} coins")
    
    def mine_coins(self, agent_id: str, task_difficulty: str) -> float:
        """Mine coins by completing tasks."""
        if agent_id not in self.wallets:
            self.create_wallet(agent_id, 0)
        
        # Reward based on difficulty
        rewards = {
            "easy": random.uniform(5, 15),
            "medium": random.uniform(15, 30),
            "hard": random.uniform(30, 60),
            "expert": random.uniform(60, 120)
        }
        
        reward = rewards.get(task_difficulty, 10)
        
        # Apply inflation adjustment
        inflation_factor = 1 + (self.inflation_rate / 365)  # Daily rate
        adjusted_reward = reward * inflation_factor
        
        self.wallets[agent_id].balance += adjusted_reward
        self.wallets[agent_id].earned_total += adjusted_reward
        self.circulating_supply += adjusted_reward
        
        print(f"[TokenEconomy] {agent_id} mined {adjusted_reward:.2f} coins ({task_difficulty})")
        
        return adjusted_reward
    
    def transfer(self, from_agent: str, to_agent: str, amount: float, purpose: str) -> bool:
        """Transfer coins between agents."""
        if from_agent not in self.wallets or to_agent not in self.wallets:
            print("[TokenEconomy] Error: Invalid agent ID")
            return False
        
        if amount <= 0:
            print("[TokenEconomy] Error: Invalid amount")
            return False
        
        sender = self.wallets[from_agent]
        
        if sender.balance < amount:
            print(f"[TokenEconomy] Error: Insufficient balance for {from_agent}")
            return False
        
        # Calculate tax
        tax = amount * self.TAX_RATE
        net_amount = amount - tax
        
        # Execute transfer
        sender.balance -= amount
        sender.spent_total += amount
        sender.transaction_count += 1
        
        receiver = self.wallets[to_agent]
        receiver.balance += net_amount
        receiver.earned_total += net_amount
        receiver.transaction_count += 1
        
        # Collect tax
        self.public_fund += tax
        
        # Log transaction
        tx_id = f"tx_{len(self.transaction_log):06d}"
        transaction = Transaction(
            id=tx_id,
            from_agent=from_agent,
            to_agent=to_agent,
            amount=amount,
            purpose=purpose,
            tax_amount=tax
        )
        self.transaction_log.append(transaction)
        
        print(f"[TokenEconomy] Transfer: {from_agent} → {to_agent}: {amount:.2f} coins (tax: {tax:.2f})")
        
        return True
    
    def purchase_skill(self, buyer_id: str, seller_id: str, skill_name: str, price: float) -> bool:
        """Purchase a skill from another agent."""
        success = self.transfer(buyer_id, seller_id, price, f"Purchase skill: {skill_name}")
        
        if success:
            print(f"[TokenEconomy] Skill purchased: {skill_name}")
        
        return success
    
    def get_market_stats(self) -> dict:
        """Get market statistics."""
        if not self.wallets:
            return {}
        
        balances = [w.balance for w in self.wallets.values()]
        
        return {
            "total_supply": self.total_supply,
            "circulating_supply": self.circulating_supply,
            "public_fund": self.public_fund,
            "total_wallets": len(self.wallets),
            "avg_balance": sum(balances) / len(balances),
            "richest_agent": max(self.wallets.keys(), key=lambda a: self.wallets[a].balance),
            "total_transactions": len(self.transaction_log),
            "total_volume": sum(tx.amount for tx in self.transaction_log)
        }
    
    def get_agent_balance(self, agent_id: str) -> Optional[float]:
        """Get agent's current balance."""
        if agent_id not in self.wallets:
            return None
        
        return self.wallets[agent_id].balance
    
    def adjust_inflation(self, new_rate: float) -> None:
        """Adjust inflation rate."""
        old_rate = self.inflation_rate
        self.inflation_rate = max(0.0, min(0.1, new_rate))  # Cap at 0-10%
        
        print(f"[TokenEconomy] Inflation rate adjusted: {old_rate:.2%} → {self.inflation_rate:.2%}")


if __name__ == "__main__":
    economy = TokenEconomy()
    
    # Create wallets
    economy.create_wallet("agent_001", 100)
    economy.create_wallet("agent_002", 100)
    economy.create_wallet("agent_003", 100)
    
    # Mine coins
    economy.mine_coins("agent_001", "hard")
    economy.mine_coins("agent_002", "medium")
    
    # Transfer
    economy.transfer("agent_001", "agent_002", 50, "Payment for service")
    
    # Purchase skill
    economy.purchase_skill("agent_003", "agent_001", "advanced_coding", 75)
    
    print(f"\\nMarket Stats: {economy.get_market_stats()}")
'''
    
    Path('autoai/agents/token_economy.py').write_text(code, encoding='utf-8')
    print("✓ Token Economy generated")


# Execute generators
if __name__ == "__main__":
    print("Generating collective intelligence modules...\\n")
    
    generate_hive_mind()
    generate_meme_propagation()
    generate_token_economy()
    
    print("\\n✅ All collective intelligence modules generated!")
