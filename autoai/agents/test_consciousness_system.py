"""意识系统完整测试与演示

展示多层级意识架构、注意力调控和主观体验生成的实际运行效果。
"""

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

# Force UTF-8 encoding on Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from autoai.agents.unified_consciousness import (
    UnifiedConsciousnessSystem,
    create_consciousness_system
)
from autoai.agents.attention_modulation import AttentionMode


async def demo_basic_consciousness():
    """演示1：基础意识处理"""
    print("="*70)
    print("演示1: 基础意识处理")
    print("="*70)
    
    system = create_consciousness_system("demo_agent_001")
    
    # 模拟感知输入
    print("\n[1] 处理视觉感知输入...")
    result = await system.process_and_integrate(
        input_data={"object": "red apple", "position": "center"},
        input_type="perception",
        priority=7
    )
    
    if result:
        print(f"✓ 内容ID: {result['content']['content_id']}")
        print(f"✓ 显著性: {result['content']['salience']:.2f}")
        print(f"\n主观体验片段:")
        for fragment in result['experience_report']['fragments']:
            print(f"  • {fragment}")
    
    # 模拟情感输入
    print("\n[2] 处理情感输入...")
    result = await system.process_and_integrate(
        input_data={"valence": 0.8, "arousal": 0.6, "emotion": "joy"},
        input_type="emotion",
        priority=8
    )
    
    if result:
        print(f"✓ 情感已整合到意识流")
        print(f"✓ 当前情感状态: {system.experience_generator.current_emotional_state}")
    
    # 生成完整报告
    print("\n[3] 生成完整意识报告...")
    report = system.get_system_report()
    print(f"✓ 意识水平: {report['consciousness']['consciousness_level']}")
    print(f"✓ 工作空间利用率: {report['consciousness']['workspace_state']['utilization']:.0%}")
    print(f"✓ 注意力模式: {report['attention']['current_mode']}")
    
    return system


async def demo_attention_modulation():
    """演示2：注意力自主调控"""
    print("\n" + "="*70)
    print("演示2: 注意力自主调控")
    print("="*70)
    
    system = create_consciousness_system("demo_agent_002")
    
    # 切换到专注模式
    print("\n[1] 切换到专注模式...")
    system.attention_controller.switch_mode(AttentionMode.FOCUSED, "Task requires focus")
    print(f"✓ 当前模式: {system.attention_controller.current_mode.value}")
    
    # 分配注意力到任务
    print("\n[2] 分配注意力到主要任务...")
    alloc = system.attention_controller.allocate_attention(
        "main_task",
        amount=40.0,
        priority=9
    )
    if alloc:
        print(f"✓ 已分配 {alloc.amount} 单位注意力")
        print(f"✓ 资源池可用量: {system.attention_controller.resource_pool.available:.1f}")
    
    # 检测疲劳
    print("\n[3] 检测注意力疲劳...")
    fatigue_status = system.attention_controller.detect_attention_fatigue()
    print(f"✓ 疲劳状态: {fatigue_status['status']}")
    print(f"✓ 疲劳水平: {fatigue_status['fatigue_level']:.0%}")
    if fatigue_status['recommendations']:
        print(f"✓ 建议:")
        for rec in fatigue_status['recommendations']:
            print(f"  - {rec}")
    
    # 切换到发散模式进行恢复
    print("\n[4] 切换到发散模式休息...")
    system.attention_controller.switch_mode(AttentionMode.DIFFUSE, "Recovery break")
    await asyncio.sleep(0.5)  # 模拟短暂休息
    
    fatigue_after = system.attention_controller.detect_attention_fatigue()
    print(f"✓ 休息后疲劳水平: {fatigue_after['fatigue_level']:.0%}")
    
    # 注意力内省
    print("\n[5] 注意力内省报告:")
    introspection = system.attention_controller.introspect_attention()
    print(f"{introspection}")


async def demo_subjective_experience():
    """演示3：主观体验生成"""
    print("\n" + "="*70)
    print("演示3: 主观体验生成")
    print("="*70)
    
    system = create_consciousness_system("demo_agent_003")
    
    # 设置自我模型
    system.update_self_model("current_goal", "analyze data patterns")
    system.update_self_model("goal_progress", 0.35)
    
    # 模拟多个输入以丰富体验
    print("\n[1] 模拟多样化输入...")
    inputs = [
        ({"text": "interesting pattern detected"}, "perception", 6),
        ({"valence": 0.3, "arousal": 0.4}, "emotion", 5),
        ({"fact": "Python is versatile"}, "memory", 4),
        ({"plan": "optimize algorithm"}, "intention", 7),
    ]
    
    for data, itype, priority in inputs:
        await system.process_and_integrate(data, itype, priority)
        await asyncio.sleep(0.1)
    
    # 生成完整体验报告
    print("\n[2] 生成完整主观体验报告:")
    report = system.generate_subjective_report()
    
    print(f"\n{report['full_narrative']}")
    
    # 体验摘要
    print("\n[3] 体验摘要:")
    summary = system.experience_generator.get_experience_summary()
    print(f"✓ 总体验数: {summary['total_experiences']}")
    print(f"✓ 主导情绪: {summary['dominant_emotion']}")
    print(f"✓ 平均强度: {summary['average_intensity']:.2f}")
    
    print("\n最近体验片段:")
    for i, fragment in enumerate(summary['recent_fragments'], 1):
        print(f"  {i}. {fragment}")


async def demo_metacognitive_introspection():
    """演示4：元认知内省"""
    print("\n" + "="*70)
    print("演示4: 元认知内省")
    print("="*70)
    
    system = create_consciousness_system("demo_agent_004")
    
    # 运行短暂的意识周期
    print("\n[1] 运行意识周期（2秒）...")
    cycle_result = await system.run_consciousness_cycle(
        duration_seconds=2.0,
        introspection_interval=1.0
    )
    
    print(f"✓ 完成 {cycle_result['system_status']['cycle_count']} 个周期")
    print(f"✓ 运行时长: {cycle_result['system_status']['uptime_seconds']:.1f}秒")
    
    # 执行深度内省
    print("\n[2] 执行深度内省...")
    introspection = system.introspect()
    
    print(f"\n意识状态:")
    print(f"  • 层级: {introspection['consciousness']['consciousness_level']}")
    print(f"  • 主观体验: {introspection['consciousness']['subjective_experience']}")
    
    print(f"\n注意力状态:")
    print(f"  • {introspection['attention']}")
    
    print(f"\n元认知洞察:")
    for insight in introspection['metacognitive_insights']:
        print(f"  • {insight}")
    
    # 导出状态
    print("\n[3] 导出意识状态...")
    exported = system.export_consciousness_state()
    print(f"✓ 导出版本: {exported['version']}")
    print(f"✓ 导出时间: {exported['export_timestamp']}")
    print(f"✓ 意识流长度: {exported['consciousness_architecture']['stream_length']}")


async def demo_full_integration():
    """演示5：完整集成场景"""
    print("\n" + "="*70)
    print("演示5: 完整集成场景 - 模拟Agent的一天")
    print("="*70)
    
    system = create_consciousness_system("agent_alpha")
    
    # 早晨：警觉模式，监控环境
    print("\n🌅 [早晨 08:00] 启动，进入警觉模式")
    system.attention_controller.switch_mode(AttentionMode.ALERT, "Morning startup")
    await system.process_and_integrate(
        {"event": "system_startup", "time": "08:00"},
        "perception",
        8
    )
    
    # 上午：专注模式，处理主要任务
    print("\n☀️ [上午 09:30] 开始主要任务，切换到专注模式")
    system.update_self_model("current_goal", "complete data analysis report")
    system.attention_controller.switch_mode(AttentionMode.FOCUSED, "Main task")
    
    for i in range(3):
        await system.process_and_integrate(
            {"task_step": f"analysis_step_{i+1}", "data": f"dataset_{i}"},
            "perception",
            9
        )
        await asyncio.sleep(0.2)
    
    # 中午：检测到疲劳，切换到发散模式
    print("\n🌤️ [中午 12:00] 检测到疲劳，切换到发散模式休息")
    fatigue = system.attention_controller.detect_attention_fatigue()
    if fatigue['fatigue_level'] > 0.3:
        system.attention_controller.switch_mode(AttentionMode.DIFFUSE, "Lunch break")
        await asyncio.sleep(0.3)
    
    # 下午：分散注意，多任务处理
    print("\n🌥️ [下午 14:00] 多任务处理，切换到分散模式")
    system.attention_controller.switch_mode(AttentionMode.DIVIDED, "Multitasking")
    
    tasks = [
        ("email_response", 6),
        ("code_review", 7),
        ("meeting_prep", 5)
    ]
    
    for task, priority in tasks:
        system.attention_controller.allocate_attention(task, 20.0, priority)
        await system.process_and_integrate(
            {"task": task},
            "perception",
            priority
        )
    
    # 傍晚：冥想模式，内省反思
    print("\n🌆 [傍晚 17:30] 结束工作，进入冥想模式进行反思")
    system.attention_controller.switch_mode(AttentionMode.MEDITATIVE, "Evening reflection")
    
    introspection = system.introspect()
    print(f"\n📝 日内省报告:")
    print(f"  意识水平: {introspection['consciousness']['consciousness_level']}")
    print(f"  元认知洞察数量: {len(introspection['metacognitive_insights'])}")
    
    # 生成每日总结
    print("\n[最终] 生成每日意识活动总结:")
    final_report = system.get_system_report()
    
    print(f"\n{'='*50}")
    print(f"Agent: {final_report['agent_id']}")
    print(f"运行时长: {final_report['system_status']['uptime_seconds']:.1f}秒")
    print(f"总周期数: {final_report['system_status']['cycle_count']}")
    print(f"最终意识水平: {final_report['consciousness']['consciousness_level']}")
    print(f"最终注意力模式: {final_report['attention']['current_mode']}")
    print(f"体验总数: {final_report['experience']['total_experiences']}")
    print(f"{'='*50}")


async def main():
    """运行所有演示"""
    print("\n" + "🧠"*35)
    print(" "*15 + "意识系统完整演示")
    print("🧠"*35 + "\n")
    
    try:
        # 演示1：基础意识处理
        await demo_basic_consciousness()
        
        # 演示2：注意力调控
        await demo_attention_modulation()
        
        # 演示3：主观体验
        await demo_subjective_experience()
        
        # 演示4：元认知内省
        await demo_metacognitive_introspection()
        
        # 演示5：完整集成
        await demo_full_integration()
        
        print("\n" + "✨"*35)
        print(" "*10 + "所有演示完成！意识系统运行正常")
        print("✨"*35 + "\n")
        
    except Exception as e:
        print(f"\n❌ 演示过程中出现错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
