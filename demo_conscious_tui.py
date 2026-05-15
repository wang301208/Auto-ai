"""Demo script for Conscious TUI - showing the autonomous, self-aware terminal.

This demonstrates:
1. Terminal with emotional states and personality
2. Real-time thought visualization
3. Autonomous initiatives
4. Resource negotiation
5. Personality evolution

Run with: python demo_conscious_tui.py
"""

import asyncio
import time
import random
from pathlib import Path

# Add project root to path
import sys
sys.path.insert(0, str(Path(__file__).parent))

from autoai.app.conscious_tui import (
    ConsciousMultiAgentTUI,
    AgentViewData,
    EmotionalState,
    ThoughtNode,
    AutonomousInitiative,
)


def simulate_agent_activity(tui: ConsciousMultiAgentTUI):
    """Simulate realistic agent activities to showcase consciousness features."""
    
    # Create some agents with different personalities
    agents = [
        AgentViewData(
            agent_id="architect-01",
            name="Architect",
            role="Designer",
            autonomous=True,
            status="running",
            current_task="Optimizing system architecture",
            emotion=EmotionalState.FOCUSED,
        ),
        AgentViewData(
            agent_id="debugger-02",
            name="Debugger",
            role="Fixer",
            autonomous=True,
            status="success",
            tasks_done=42,
            issues_fixed=15,
            emotion=EmotionalState.CONFIDENT,
        ),
        AgentViewData(
            agent_id="researcher-03",
            name="Researcher",
            role="Explorer",
            autonomous=True,
            status="running",
            current_task="Searching for optimization patterns",
            emotion=EmotionalState.CURIOUS,
        ),
    ]
    
    for agent in agents:
        tui.update_agent(agent)
        
    # Simulate thought processes
    print("🧠 Initializing thought processes...")
    
    # Architect's thinking chain
    architect_chain = "chain_arch_001"
    root_node = ThoughtNode(
        id="n1",
        level=1,
        description="Analyzing current architecture",
        status="completed",
        confidence=0.95,
        start_time=time.time() - 5,
        end_time=time.time() - 3,
    )
    root_node.children = [
        ThoughtNode(
            id="n2",
            level=2,
            description="Identifying bottleneck: Module coupling",
            status="completed",
            confidence=0.88,
            start_time=time.time() - 3,
            end_time=time.time() - 1,
        ),
        ThoughtNode(
            id="n3",
            level=2,
            description="Generating refactoring plan",
            status="active",
            confidence=0.75,
            start_time=time.time() - 1,
        ),
    ]
    tui.thought_renderer.add_thought_chain(architect_chain, root_node)
    tui.update_agent_consciousness("architect-01", EmotionalState.FOCUSED, architect_chain)
    
    # Researcher's thinking chain
    researcher_chain = "chain_res_001"
    res_root = ThoughtNode(
        id="r1",
        level=1,
        description="Exploring optimization strategies",
        status="active",
        confidence=0.60,
        start_time=time.time() - 2,
    )
    res_root.children = [
        ThoughtNode(
            id="r2",
            level=2,
            description="Option A: Caching layer (est. +30% perf)",
            status="pending",
            confidence=0.70,
        ),
        ThoughtNode(
            id="r3",
            level=2,
            description="Option B: Parallel processing (est. +50% perf)",
            status="pending",
            confidence=0.65,
        ),
        ThoughtNode(
            id="r4",
            level=2,
            description="Option C: Algorithm redesign (est. +80% perf, high risk)",
            status="pending",
            confidence=0.45,
        ),
    ]
    tui.thought_renderer.add_thought_chain(researcher_chain, res_root)
    tui.update_agent_consciousness("researcher-03", EmotionalState.CURIOUS, researcher_chain)
    
    # Generate some autonomous initiatives
    print("💡 Generating autonomous initiatives...")
    
    initiatives = [
        AutonomousInitiative(
            action_type="suggest",
            message="I noticed the Debugger agent could benefit from caching. Want me to implement it?",
            priority=0.7,
            requires_approval=True,
        ),
        AutonomousInitiative(
            action_type="warn",
            message="⚠️ High memory usage detected (85%). Consider optimizing data structures.",
            priority=0.8,
            requires_approval=False,
        ),
        AutonomousInitiative(
            action_type="share",
            message="🔍 Interesting pattern found: Similar bugs fixed 3x this week. Root cause analysis needed.",
            priority=0.5,
        ),
        AutonomousInitiative(
            action_type="request",
            message="I need 2 hours of GPU time to train a performance prediction model. Expected ROI: 40% speedup.",
            priority=0.6,
            requires_approval=True,
        ),
    ]
    
    for init in initiatives:
        tui.consciousness.initiatives.append(init)
        
    # Update agents with recent initiatives
    agents[0].recent_initiatives = ["Architecture optimization suggested"]
    agents[1].recent_initiatives = ["Caching opportunity identified"]
    agents[2].recent_initiatives = ["Pattern discovery: recurring bugs"]
    
    # Record some interactions for personality adaptation
    print("📈 Recording interaction history...")
    tui.record_interaction(
        user_input="Can you optimize the system?",
        system_response="Analyzing bottlenecks...",
        outcome="positive"
    )
    tui.record_interaction(
        user_input="Why is it so slow?",
        system_response="Detailed explanation of performance issues...",
        outcome="needs_more_detail"
    )
    tui.record_interaction(
        user_input="Great work!",
        system_response="Thank you! 😊",
        outcome="positive"
    )
    
    # Adapt personality based on interactions
    tui.consciousness.personality.adapt_from_feedback(True, "User appreciates concise responses")
    

def main():
    """Main demo entry point."""
    print("=" * 80)
    print("🧠 CONSCIOUS MULTI-AGENT TUI DEMO")
    print("=" * 80)
    print()
    print("This demo showcases:")
    print("  ✨ Terminal with emotions and personality")
    print("  🧠 Real-time thought visualization")
    print("  💡 Autonomous initiatives")
    print("  🎭 Personality evolution")
    print("  🤖 Resource negotiation")
    print()
    print("Starting in 2 seconds... Press Ctrl+C to exit")
    print("=" * 80)
    print()
    
    time.sleep(2)
    
    # Create conscious TUI
    tui = ConsciousMultiAgentTUI(refresh_rate=0.5)
    
    # Simulate activity
    simulate_agent_activity(tui)
    
    # Set initial tab to Thoughts (most impressive)
    tui.set_active_tab(ConsciousMultiAgentTUI.TAB_THOUGHTS)
    
    # Run the TUI
    try:
        tui.run()
    except KeyboardInterrupt:
        print("\n\nDemo ended. Thanks for experiencing consciousness! 🧠✨")


if __name__ == "__main__":
    main()
