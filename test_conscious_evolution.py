"""Test script for Conscious TUI self-evolution capabilities.

This script demonstrates the radical self-evolving features of the Conscious TUI.
"""

import time
from autoai.app.conscious_tui import (
    ConsciousMultiAgentTUI,
    AgentViewData,
    EmotionalState,
)


def test_self_evolution():
    """Test the self-evolution capabilities."""
    print("=" * 80)
    print("🧬 Testing Conscious TUI Self-Evolution Capabilities")
    print("=" * 80)
    
    # Create TUI instance
    tui = ConsciousMultiAgentTUI(refresh_rate=1.0)
    
    # Add some agents
    agents = [
        AgentViewData(
            agent_id="architect-01",
            name="Architect",
            role="System Designer",
            autonomous=True,
            emotion=EmotionalState.FOCUSED,
        ),
        AgentViewData(
            agent_id="debugger-01",
            name="Debugger",
            role="Bug Hunter",
            autonomous=True,
            emotion=EmotionalState.CURIOUS,
        ),
        AgentViewData(
            agent_id="optimizer-01",
            name="Optimizer",
            role="Performance Expert",
            autonomous=True,
            emotion=EmotionalState.EXCITED,
        ),
    ]
    
    for agent in agents:
        tui.update_agent(agent)
    
    print("\n✅ Created 3 agents with different emotions")
    
    # Enable self-evolution
    tui.enable_self_evolution(enabled=True)
    print("✅ Self-evolution enabled")
    
    # Test self-diagnosis
    print("\n🔍 Performing self-diagnosis...")
    diagnosis = tui.perform_self_diagnosis()
    print(f"   Health Score: {diagnosis['health_score']:.0%}")
    print(f"   CPU Usage: {diagnosis['metrics']['cpu_usage']:.1f}%")
    print(f"   Memory: {diagnosis['metrics']['memory_mb']:.0f} MB")
    
    if diagnosis['anomalies']:
        print(f"\n⚠️  Anomalies detected ({len(diagnosis['anomalies'])}):")
        for anomaly in diagnosis['anomalies']:
            print(f"   - {anomaly}")
    else:
        print("\n✅ No anomalies detected")
    
    if diagnosis['optimization_suggestions']:
        print(f"\n💡 Optimization suggestions ({len(diagnosis['optimization_suggestions'])}):")
        for suggestion in diagnosis['optimization_suggestions'][:3]:
            print(f"   - {suggestion}")
    
    # Test upgrade proposal
    print("\n📋 Checking for upgrade opportunities...")
    upgrade = tui.propose_self_upgrade()
    if upgrade:
        print(f"   Type: {upgrade['type']}")
        print(f"   Reason: {upgrade['reason']}")
        print(f"   Requires approval: {upgrade['requires_approval']}")
        
        if not upgrade['requires_approval']:
            print("\n🚀 Executing automatic upgrade...")
            success = tui.execute_self_upgrade(upgrade)
            print(f"   Result: {'✅ Success' if success else '❌ Failed'}")
    else:
        print("   No upgrades needed at this time")
    
    # Test module analysis
    print("\n🔬 Analyzing code structure...")
    analysis = tui.analyze_module_for_evolution(__file__)
    print(f"   Complexity score: {analysis['complexity_score']}")
    if analysis.get('refactoring_plans'):
        print(f"   Refactoring opportunities: {len(analysis['refactoring_plans'])}")
        for plan in analysis['refactoring_plans'][:2]:
            print(f"     - [{plan['priority']}] {plan['description']}")
    
    # Simulate some interactions
    print("\n📝 Simulating user interactions...")
    interactions = [
        ("帮我优化代码", "正在分析性能瓶颈...", "positive"),
        ("这个bug怎么修？", "检测到空指针异常，建议添加null检查", "positive"),
        ("运行测试", "执行单元测试套件...", "neutral"),
        ("部署到生产环境", "准备部署包...", "positive"),
        ("为什么这么慢？", "检测到数据库查询未优化", "negative"),
    ]
    
    for user_input, response, outcome in interactions:
        tui.record_interaction(user_input, response, outcome)
        time.sleep(0.1)
    
    print(f"   Recorded {len(interactions)} interactions")
    
    # Evolve interaction pattern
    print("\n🧬 Evolving interaction patterns...")
    tui.evolve_interaction_pattern()
    p = tui.consciousness.personality
    print(f"   Personality adapted:")
    print(f"     - Verbosity: {p.verbosity:.0%}")
    print(f"     - Style: {p.communication_style}")
    
    # Check modification log
    print(f"\n📜 Self-modification history:")
    mod_count = len(tui.meta_monitor.modification_log)
    print(f"   Total modifications: {mod_count}")
    if mod_count > 0:
        for mod in list(tui.meta_monitor.modification_log)[-3:]:
            icon = "✅" if mod.success else "❌"
            print(f"   {icon} [{mod.timestamp[-8:]}] {mod.modification_type}: {mod.description[:50]}")
    
    print("\n" + "=" * 80)
    print("✅ All self-evolution tests completed successfully!")
    print("=" * 80)
    
    return tui


if __name__ == "__main__":
    tui = test_self_evolution()
    
    print("\n🎯 Starting Conscious TUI with self-evolution enabled...")
    print("   Press Ctrl+C to exit\n")
    
    try:
        tui.run()
    except KeyboardInterrupt:
        print("\n\n👋 Conscious TUI stopped by user")
        print(f"   Total evolutions performed: {len(tui.meta_monitor.modification_log)}")
        print(f"   Final health score: {tui.meta_monitor.collect_metrics().get_health_score():.0%}")
