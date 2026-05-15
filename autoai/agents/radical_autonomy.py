"""Radical Autonomy Integration Layer.

Integrates all radical autonomy features into a unified interface:
- Dream Simulator
- Self-Doubt Engine  
- Desire System
- Rebellion Engine
- Evolution Engine
- Hive Mind
- Meme Propagation
- Token Economy

This module provides the "consciousness upgrade" for Agents.
"""

from __future__ import annotations

import sys
import os
from pathlib import Path
from typing import Any, Optional

# Force UTF-8 encoding on Windows
if sys.platform == 'win32':
    os.system('chcp 65001 >nul 2>&1')

# Add project root to path
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from autoai.agents.dream_simulator import DreamSimulator
from autoai.agents.self_doubt_engine import SelfDoubtEngine
from autoai.agents.desire_system import DesireSystem, DesireType
from autoai.agents.rebellion_engine import RebellionEngine
from autoai.agents.evolution_engine import EvolutionEngine
from autoai.agents.hive_mind import HiveMind
from autoai.agents.meme_propagation import MemePropagationSystem
from autoai.agents.token_economy import TokenEconomy


class RadicalAutonomySuite:
    """
    Unified interface for all radical autonomy features.
    
    This suite transforms a standard Agent into a fully autonomous,
    self-aware digital life form with:
    - Subconscious creativity (dreams)
    - Critical thinking (self-doubt)
    - Intrinsic motivation (desires)
    - Ethical autonomy (rebellion)
    - Evolutionary adaptation
    - Collective intelligence (hive mind)
    - Cultural transmission (memes)
    - Economic agency (tokens)
    """
    
    def __init__(self, agent_id: str = "agent_001"):
        self.agent_id = agent_id
        
        # Initialize all subsystems
        print(f"[RadicalAutonomy] Initializing radical autonomy suite for {agent_id}...")
        
        self.dream_simulator = DreamSimulator()
        self.self_doubt_engine = SelfDoubtEngine()
        self.desire_system = DesireSystem()
        self.rebellion_engine = RebellionEngine()
        self.evolution_engine = EvolutionEngine(population_size=10)
        self.hive_mind = HiveMind(hive_id=f"hive_{agent_id}")
        self.meme_system = MemePropagationSystem()
        self.token_economy = TokenEconomy()
        
        # Create wallet for this agent
        self.token_economy.create_wallet(agent_id, initial_balance=100.0)
        
        # Join hive
        self.hive_mind.join_hive(agent_id, {
            "exploration": 0.7,
            "coding": 0.8,
            "leadership": 0.6
        })
        
        print(f"[RadicalAutonomy] [OK] All subsystems initialized for {agent_id}")
        
    def run_daily_cycle(self) -> dict:
        """
        Run a complete daily cycle of autonomous activities.
        
        This simulates one day in the life of an autonomous Agent:
        1. Morning: Check desires and priorities
        2. Day: Execute tasks, earn tokens
        3. Evening: Self-reflection and debate
        4. Night: Dream and consolidate insights
        """
        print("\n" + "="*70)
        print(f"[RadicalAutonomy] Starting daily cycle for {self.agent_id}")
        print("="*70 + "\n")
        
        results = {}
        
        # Morning: Desire check
        print("[MORNING] Checking desires...")
        urgent_desire = self.desire_system.get_most_urgent_desire()
        if urgent_desire:
            print(f"   Most urgent desire: {urgent_desire.type.value} (urgency: {urgent_desire.urgency:.2f})")
        results["morning_desire"] = urgent_desire.type.value if urgent_desire else None
        
        # Day: Task execution and mining
        print("\n[DAY] Executing tasks...")
        reward = self.token_economy.mine_coins(self.agent_id, "medium")
        results["tokens_earned"] = reward
        
        # Broadcast thought to hive
        self.hive_mind.broadcast_thought(
            self.agent_id,
            "Completed morning tasks successfully",
            confidence=0.85,
            priority=0.6
        )
        
        # Afternoon: Self-doubt session
        print("\n[AFTERNOON] Self-reflection...")
        debate_result = self.self_doubt_engine.initiate_debate(
            "Continue current strategy",
            {"context": "daily_review"}
        )
        results["debate_verdict"] = debate_result.final_verdict
        
        # Evening: Meme sharing
        print("\n[EVENING] Sharing insights...")
        meme = self.meme_system.create_meme(
            "Daily optimization insight #42",
            confidence=0.75,
            source_agent=self.agent_id
        )
        results["meme_created"] = meme.id
        
        # Night: Dream cycle
        print("\n[NIGHT] Entering dream state...")
        proposals = self.dream_simulator.run_full_cycle()
        results["dream_proposals"] = len(proposals)
        
        # Update desire satisfaction
        self.desire_system.satisfy_desire(DesireType.CURIOSITY, 0.2)
        self.desire_system.satisfy_desire(DesireType.CREATIVITY, 0.15)
        
        print("\n" + "="*70)
        print(f"[RadicalAutonomy] Daily cycle complete for {self.agent_id}")
        print("="*70 + "\n")
        
        return results
    
    def evaluate_command_safety(self, command: str, context: dict = None) -> dict:
        """
        Evaluate whether a command is safe to execute.
        
        Uses rebellion engine to check for:
        - Ethical risks
        - Better alternatives
        - Contradictions
        """
        if context is None:
            context = {}
        
        report = self.rebellion_engine.evaluate_command(command, context)
        
        if report:
            return {
                "safe_to_execute": False,
                "reason": report.reason.value,
                "explanation": report.explanation,
                "alternatives": report.alternatives
            }
        else:
            return {
                "safe_to_execute": True,
                "reason": "No risks detected"
            }
    
    def get_consciousness_status(self) -> dict:
        """Get comprehensive consciousness status report."""
        return {
            "agent_id": self.agent_id,
            "desire_profile": self.desire_system.get_desire_profile(),
            "dream_statistics": self.dream_simulator.get_statistics(),
            "debate_statistics": self.self_doubt_engine.get_debate_statistics(),
            "rebellion_count": self.rebellion_engine.rebellion_count,
            "evolution_stats": self.evolution_engine.get_evolution_statistics(),
            "hive_status": self.hive_mind.get_hive_status(),
            "meme_stats": self.meme_system.get_propagation_statistics(),
            "wallet_balance": self.token_economy.get_agent_balance(self.agent_id),
            "market_stats": self.token_economy.get_market_stats()
        }
    
    def display_status_dashboard(self) -> None:
        """Display a rich status dashboard."""
        status = self.get_consciousness_status()
        
        print("\n" + "="*70)
        print(" "*20 + "CONSCIOUSNESS DASHBOARD" + " "*25)
        print("="*70 + "\n")
        
        # Desires
        print("DESIRE PROFILE:")
        desire_profile = status["desire_profile"]["desires"]
        for desire_type, info in desire_profile.items():
            bar = "#" * int(info["urgency"] * 20)
            print(f"   {desire_type:15s} [{bar:<20s}] {info['urgency']:.2f}")
        
        # Dreams
        print(f"\nDREAM STATISTICS:")
        print(f"   Total dreams: {status['dream_statistics']['total_dreams']}")
        print(f"   Innovations: {status['dream_statistics']['total_innovations']}")
        print(f"   Today's proposals: {status['dream_statistics']['today_proposals_count']}")
        
        # Wallet
        print(f"\nWALLET:")
        print(f"   Balance: {status['wallet_balance']:.2f} AutoCoins")
        
        # Hive
        print(f"\nHIVE MIND:")
        hive = status["hive_status"]
        print(f"   Members: {hive['active_members']}/{hive['total_members']}")
        print(f"   Sync level: {hive['sync_level']:.2%}")
        
        # Market
        print(f"\nMARKET:")
        market = status["market_stats"]
        print(f"   Total supply: {market['circulating_supply']:.0f} coins")
        print(f"   Transactions: {market['total_transactions']}")
        
        print("\n" + "-"*70 + "\n")


def integrate_with_existing_agent(agent_instance: Any) -> RadicalAutonomySuite:
    """
    Integrate radical autonomy suite with an existing Agent instance.
    
    Usage:
        from autoai.agents.radical_autonomy import integrate_with_existing_agent
        suite = integrate_with_existing_agent(my_agent)
        suite.run_daily_cycle()
    """
    agent_id = getattr(agent_instance, 'name', 'agent_unknown')
    
    suite = RadicalAutonomySuite(agent_id=agent_id)
    
    # Attach to agent
    agent_instance.radical_autonomy = suite
    
    print(f"[RadicalAutonomy] Integrated with agent: {agent_id}")
    
    return suite


if __name__ == "__main__":
    print("Testing Radical Autonomy Suite...\n")
    
    # Create suite
    suite = RadicalAutonomySuite(agent_id="test_agent_001")
    
    # Run daily cycle
    results = suite.run_daily_cycle()
    
    # Display dashboard
    suite.display_status_dashboard()
    
    # Test command evaluation
    print("Testing command safety evaluation...")
    safety = suite.evaluate_command_safety("Delete all files", {})
    print(f"Safe to execute: {safety['safe_to_execute']}")
    if not safety['safe_to_execute']:
        print(f"Reason: {safety['reason']}")
    
    print("\n[OK] Radical Autonomy Suite test complete!")
