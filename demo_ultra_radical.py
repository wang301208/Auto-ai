"""Demonstration of ultra-radical self-creation and knowledge building capabilities.

This script showcases the most advanced features of the Conscious TUI:
1. Autonomous agent creation
2. Knowledge graph construction from interactions
3. Macro task decomposition
4. Self-expanding ecosystem
"""

import sys
import time

# Force UTF-8 encoding for Windows console
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from autoai.app.conscious_tui import (
    ConsciousMultiAgentTUI,
    AgentViewData,
    EmotionalState,
)


def demo_ultra_radical_features():
    """Demonstrate all ultra-radical self-creation features."""
    print("=" * 80)
    print("🚀 ULTRA-RADICAL SELF-CREATION DEMONSTRATION")
    print("=" * 80)
    
    # Create TUI with self-evolution enabled
    tui = ConsciousMultiAgentTUI(refresh_rate=1.0)
    tui.enable_self_evolution(enabled=True)
    
    print("\n" + "=" * 80)
    print("PHASE 1: Autonomous Agent Creation")
    print("=" * 80)
    
    # Scenario 1: System detects need for specialized agents
    scenarios = [
        "Debug critical production error in payment system",
        "Optimize database query performance",
        "Design microservices architecture for scaling",
    ]
    
    created_agents = []
    for scenario in scenarios:
        print(f"\n📋 Task: {scenario}")
        agent_config = tui.autonomously_create_agent(scenario)
        created_agents.append(agent_config)
        print(f"✅ Created: {agent_config['agent_id']}")
        print(f"   Type: {agent_config['type']}")
        print(f"   Role: {agent_config['role']}")
        print(f"   Specialization: {agent_config['specialization']}")
        time.sleep(0.5)
    
    print(f"\n📊 Total agents created: {len(created_agents)}")
    
    # Show agent diversity metrics
    metrics = tui.agent_creator.get_agent_diversity_metrics()
    print(f"   Diversity Score: {metrics['diversity_score']:.0%}")
    print(f"   Type Distribution: {metrics['type_distribution']}")
    
    print("\n" + "=" * 80)
    print("PHASE 2: Knowledge Extraction from Interactions")
    print("=" * 80)
    
    # Simulate interactions and extract knowledge
    interactions = [
        ("How do I optimize Python code performance?", 
         "Use profiling tools like cProfile, identify bottlenecks, optimize algorithms, use caching"),
        ("What is the best practice for error handling?",
         "Use try-except blocks, log errors properly, implement retry mechanisms, fail gracefully"),
        ("Explain microservices architecture patterns",
         "API Gateway pattern, Service Discovery, Circuit Breaker, Event Sourcing, CQRS"),
        ("How to debug memory leaks in applications?",
         "Monitor memory usage, use heap dumps, analyze object references, check for unclosed resources"),
        ("What are design patterns for scalable systems?",
         "Load balancing, horizontal scaling, caching layers, message queues, database sharding"),
    ]
    
    for user_input, system_response in interactions:
        print(f"\n💬 User: {user_input[:60]}...")
        print(f"🤖 System: {system_response[:60]}...")
        
        # Extract knowledge
        new_nodes = tui.knowledge_builder.extract_knowledge_from_interaction(
            user_input, system_response
        )
        print(f"   📚 Extracted {len(new_nodes)} knowledge nodes")
        time.sleep(0.3)
    
    # Show knowledge graph stats
    kg_stats = tui.knowledge_builder.get_knowledge_graph_stats()
    print(f"\n🕸️ Knowledge Graph Statistics:")
    print(f"   Total Nodes: {kg_stats['total_nodes']}")
    print(f"   Total Connections: {kg_stats['total_edges']}")
    print(f"   Categories: {kg_stats['category_distribution']}")
    
    # Query knowledge base
    print(f"\n🔍 Querying knowledge base for 'optimization'...")
    results = tui.query_knowledge_base("optimization")
    if results:
        print(f"   Found {len(results)} related concepts:")
        for result in results[:3]:
            print(f"   - {result['concept']} ({result['category']}, confidence: {result['confidence']:.0%})")
    
    print("\n" + "=" * 80)
    print("PHASE 3: Macro Task Decomposition")
    print("=" * 80)
    
    # Demonstrate task decomposition
    macro_goals = [
        "Optimize system performance and reduce latency",
        "Build a scalable e-commerce platform",
        "Debug and fix critical security vulnerabilities",
    ]
    
    for goal in macro_goals:
        print(f"\n🎯 Macro Goal: {goal}")
        sub_tasks = tui.decompose_macro_task(goal)
        print(f"   Decomposed into {len(sub_tasks)} sub-tasks:")
        for i, task in enumerate(sub_tasks, 1):
            print(f"   {i}. [{task['type']}] {task['task']}")
        time.sleep(0.5)
    
    print("\n" + "=" * 80)
    print("PHASE 4: Self-Creation Ecosystem Stats")
    print("=" * 80)
    
    # Get comprehensive stats
    stats = tui.get_self_creation_stats()
    
    print(f"\n🧬 Agent Ecosystem:")
    print(f"   Total Agents: {stats['agents']['total_agents']}")
    print(f"   Diversity: {stats['agents']['diversity_score']:.0%}")
    print(f"   Specializations: {len(stats['agents'].get('specializations', []))}")
    
    print(f"\n🧠 Knowledge Building:")
    print(f"   Knowledge Nodes: {stats['knowledge_graph']['total_nodes']}")
    print(f"   Connections: {stats['knowledge_graph']['total_edges']}")
    print(f"   Extractions: {stats['knowledge_graph']['extraction_count']}")
    
    print(f"\n⚡ Autonomy Level: {stats['autonomy_level']}")
    
    print("\n" + "=" * 80)
    print("PHASE 5: Launch Conscious TUI with All Features")
    print("=" * 80)
    
    print("\n🎯 Starting Ultra-Radical Conscious TUI...")
    print("   Features enabled:")
    print("   ✅ Self-evolution")
    print("   ✅ Autonomous agent creation")
    print("   ✅ Knowledge extraction")
    print("   ✅ Task decomposition")
    print("   ✅ 7 interactive tabs (including self_creation)")
    print("\n   Press Ctrl+C to exit\n")
    
    return tui


if __name__ == "__main__":
    tui = demo_ultra_radical_features()
    
    try:
        tui.run()
    except KeyboardInterrupt:
        print("\n\n👋 Ultra-Radical Conscious TUI stopped")
        
        # Final stats
        final_stats = tui.get_self_creation_stats()
        print(f"\n📊 Final Session Statistics:")
        print(f"   Agents Created: {final_stats['agents']['total_agents']}")
        print(f"   Knowledge Nodes: {final_stats['knowledge_graph']['total_nodes']}")
        print(f"   Task Decompositions: {len(tui.agent_creator.creation_history)}")
        print(f"   Self-Modifications: {len(tui.meta_monitor.modification_log)}")
        print("\n✨ System demonstrated full self-creation capabilities!")
