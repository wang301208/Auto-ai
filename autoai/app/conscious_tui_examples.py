"""Conscious TUI Usage Examples

意识化TUI的核心用法示例
"""

from autoai.app.conscious_tui import (
    ConsciousMultiAgentTUI,
    AgentViewData,
    EmotionalState,
)


def example_basic_usage():
    """基础用法：创建并运行意识化TUI"""
    tui = ConsciousMultiAgentTUI(refresh_rate=0.5)
    
    # 添加Agent
    agent = AgentViewData(
        agent_id="agent-01",
        name="Assistant",
        role="Helper",
        autonomous=True,
        emotion=EmotionalState.FOCUSED,
    )
    tui.update_agent(agent)
    
    # 运行
    tui.run()


def example_self_evolution():
    """自我演化用法：启用系统自举能力"""
    tui = ConsciousMultiAgentTUI()
    
    # 启用自我演化（激进模式）
    tui.enable_self_evolution(enabled=True)
    
    # 执行自我诊断
    diagnosis = tui.perform_self_diagnosis()
    print(f"System Health: {diagnosis['health_score']:.0%}")
    
    # 检查是否有升级建议
    upgrade = tui.propose_self_upgrade()
    if upgrade:
        print(f"Upgrade suggested: {upgrade['reason']}")
        tui.execute_self_upgrade(upgrade)
    
    # 分析模块以寻找演化机会
    analysis = tui.analyze_module_for_evolution(__file__)
    print(f"Complexity score: {analysis['complexity_score']}")
    
    tui.run()


def example_dynamic_capability():
    """动态能力加载：运行时扩展系统功能"""
    tui = ConsciousMultiAgentTUI()
    
    # 动态加载新模块
    success = tui.dynamic_load_capability("new_module")
    if success:
        print("✅ New capability loaded")
    
    tui.run()


def example_meta_cognition():
    """元认知监控：观察系统自身状态"""
    tui = ConsciousMultiAgentTUI()
    
    # 收集系统指标
    metrics = tui.meta_monitor.collect_metrics()
    print(f"CPU: {metrics.cpu_usage}%")
    print(f"Memory: {metrics.memory_mb} MB")
    print(f"Health: {metrics.get_health_score():.0%}")
    
    # 检测异常
    anomalies = tui.meta_monitor.detect_anomalies()
    if anomalies:
        print("Anomalies detected:")
        for anomaly in anomalies:
            print(f"  - {anomaly}")
    
    # 获取优化建议
    suggestions = tui.meta_monitor.suggest_optimizations()
    print("Optimization suggestions:")
    for suggestion in suggestions:
        print(f"  - {suggestion}")
    
    tui.run()


if __name__ == "__main__":
    # 运行基础示例
    example_basic_usage()
