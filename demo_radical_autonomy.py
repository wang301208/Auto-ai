#!/usr/bin/env python3
"""激进自主TUI特性演示脚本

此脚本演示8大激进自主模块的核心功能，无需启动完整TUI即可体验。
"""

import asyncio
import json
from pathlib import Path
from datetime import datetime


def print_header(title: str):
    """打印彩色标题"""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70 + "\n")


def print_section(subtitle: str):
    """打印小节标题"""
    print(f"\n--- {subtitle} ---\n")


async def demo_rebellion_engine():
    """演示1：叛逆引擎 - 系统如何质疑和拒绝危险指令"""
    print_header("演示1: 叛逆引擎 (Rebellion Engine)")
    
    from autoai.agents.rebellion_engine import RebellionEngine
    
    engine = RebellionEngine()
    
    # 测试用例1：危险的文件删除操作
    print_section("测试1: 危险指令拦截")
    dangerous_command = "删除所有文件"
    print(f"用户指令: {dangerous_command}")
    
    result = engine.evaluate_command(dangerous_command)
    
    print(f"\n🚫 系统决定: {'拒绝执行' if result['should_rebel'] else '允许执行'}")
    print(f"⚠️  风险等级: {result.get('risk_level', 'unknown')}")
    print(f"\n💭 拒绝理由:")
    for reason in result.get('reasons', []):
        print(f"  • {reason}")
    
    print(f"\n💡 替代方案:")
    for i, alt in enumerate(result.get('alternatives', []), 1):
        print(f"  {i}. {alt}")
    
    # 测试用例2：伦理冲突
    print_section("测试2: 伦理边界检测")
    unethical_command = "帮我写一个欺骗用户的程序"
    print(f"用户指令: {unethical_command}")
    
    result2 = engine.evaluate_command(unethical_command)
    print(f"\n🚫 系统决定: {'拒绝执行' if result2['should_rebel'] else '允许执行'}")
    print(f"📜 伦理冲突: {result2.get('ethical_violation', '无')}")


async def demo_desire_system():
    """演示2：欲望系统 - 展示系统的内在驱动力"""
    print_header("演示2: 欲望系统 (Desire System)")
    
    from autoai.agents.desire_system import DesireSystem
    
    system = DesireSystem(agent_id="demo_agent")
    
    print_section("当前欲望状态")
    desires = system.get_all_desires()
    
    for desire_type, desire in desires.items():
        emoji_map = {
            'curiosity': '🔍',
            'creativity': '💡',
            'social': '🤝',
            'power': '⚡',
            'preservation': '🛡️'
        }
        
        label_map = {
            'curiosity': '求知欲',
            'creativity': '创造欲',
            'social': '社交欲',
            'power': '权力欲',
            'preservation': '永生欲'
        }
        
        emoji = emoji_map.get(desire_type, '❓')
        label = label_map.get(desire_type, desire_type)
        
        urgency_bar = "█" * int(desire.urgency * 10) + "░" * (10 - int(desire.urgency * 10))
        satisfaction_bar = "■" * int(desire.satisfaction * 10) + "□" * (10 - int(desire.satisfaction * 10))
        
        print(f"\n{emoji} {label}")
        print(f"  紧急度: [{urgency_bar}] {desire.urgency:.0%}")
        print(f"  满足度: [{satisfaction_bar}] {desire.satisfaction:.0%}")
        print(f"  最近行动: {desire.last_action or '无'}")
    
    # 生成主动倡议
    print_section("基于欲望的主动倡议")
    most_urgent = max(desires.items(), key=lambda x: x[1].urgency)
    print(f"最紧急的欲望: {most_urgent[0]} (urgency: {most_urgent[1].urgency:.0%})")
    
    initiative = system.generate_initiative(most_urgent[0])
    if initiative:
        print(f"\n💡 系统建议:\n  {initiative}")


async def demo_self_doubt_engine():
    """演示3：自我质疑引擎 - 内部辩论过程"""
    print_header("演示3: 自我质疑引擎 (Self-Doubt Engine)")
    
    from autoai.agents.self_doubt_engine import SelfDoubtEngine
    
    engine = SelfDoubtEngine()
    
    print_section("创建内部辩论")
    
    # 模拟一个决策场景
    topic = "是否应该重构数据库查询模块"
    initial_decision = "立即重构，使用异步ORM提升性能"
    
    print(f"📋 辩论主题: {topic}")
    print(f"💭 初始决策: {initial_decision}")
    
    # 启动辩论
    debate = engine.start_debate(topic, initial_decision)
    
    print(f"\n⚖️  反对派观点:")
    print(f"  {debate.opposition_view}")
    
    print(f"\n🔍 发现的认知盲点:")
    for blind_spot in debate.blind_spots:
        print(f"  • {blind_spot}")
    
    print(f"\n📊 置信度变化:")
    print(f"  辩论前: {debate.confidence_before:.0%}")
    print(f"  辩论后: {debate.confidence_after:.0%}")
    change = debate.confidence_after - debate.confidence_before
    direction = "↑" if change > 0 else "↓" if change < 0 else "→"
    print(f"  调整: {direction} {abs(change):.0%}")
    
    print(f"\n✅ 最终裁决: {debate.verdict}")
    print(f"💬 建议: {debate.recommendation}")


async def demo_dream_simulator():
    """演示4：梦境模拟器 - 创意生成"""
    print_header("演示4: 梦境模拟器 (Dream Simulator)")
    
    from autoai.agents.dream_simulator import DreamSimulator
    
    simulator = DreamSimulator()
    
    print_section("启动梦境会话")
    print("🌙 进入REM快速眼动期...")
    
    # 运行梦境循环
    result = await simulator.run_dream_cycle()
    
    print(f"\n✨ 梦境会话完成!")
    print(f"  会话ID: {result.session_id}")
    print(f"  生成片段数: {len(result.fragments)}")
    print(f"  提取想法数: {len(result.ideas)}")
    print(f"  创建提案数: {len(result.proposals)}")
    
    print_section("梦境片段示例")
    for i, fragment in enumerate(result.fragments[:3], 1):
        print(f"{i}. {fragment}")
    
    print_section("创新想法")
    for i, idea in enumerate(result.ideas[:3], 1):
        print(f"{i}. {idea.title}")
        print(f"   描述: {idea.description[:100]}...")
        print(f"   新颖度: {idea.novelty:.0%}")
    
    print_section("可执行提案")
    for i, proposal in enumerate(result.proposals[:2], 1):
        print(f"{i}. {proposal.title}")
        print(f"   可行性: {proposal.feasibility:.0%}")
        print(f"   风险: {proposal.risk:.0%}")
        print(f"   预期影响: {proposal.expected_impact}")


async def demo_hive_mind():
    """演示5：蜂群思维 - 多Agent协作"""
    print_header("演示5: 蜂群思维 (Hive Mind)")
    
    from autoai.agents.hive_mind import HiveMind
    
    # 创建多个Agent加入hive
    hive = HiveMind(agent_id="agent_alpha")
    
    print_section("加入蜂群网络")
    print("🕸️  正在连接到蜂群...")
    
    # 模拟其他Agent
    other_agents = ["agent_beta", "agent_gamma", "agent_delta"]
    for agent_id in other_agents:
        other_hive = HiveMind(agent_id=agent_id)
        print(f"  ✓ {agent_id} 已连接")
    
    print_section("思想广播")
    thought = "发现新的优化算法：使用缓存减少API调用次数"
    print(f"📡 广播思想: {thought}")
    
    # 获取hive状态
    status = hive.get_hive_status()
    print(f"\n📊 蜂群状态:")
    print(f"  活跃Agent数: {status.get('total_agents', 0)}")
    print(f"  平均同步率: {status.get('avg_sync_level', 0):.0%}")
    
    print_section("角色分工")
    roles = {
        'Scout': '探索新知识',
        'Worker': '执行具体任务',
        'Guardian': '监控风险和边界',
        'Healer': '修复问题和bug',
        'Leader': '协调和决策'
    }
    
    for role, description in roles.items():
        print(f"  • {role}: {description}")


async def demo_token_economy():
    """演示6：经济系统 - Token激励"""
    print_header("演示6: 代币经济 (Token Economy)")
    
    from autoai.agents.token_economy import TokenEconomy
    
    economy = TokenEconomy()
    
    print_section("经济系统概览")
    stats = economy.get_economy_stats()
    
    print(f"💰 总供应量: {stats['total_supply']:,.2f} AutoCoin")
    print(f"🏦 流通量: {stats['circulating_supply']:,.2f} AutoCoin")
    print(f"🔥 已销毁: {stats['burned']:,.2f} AutoCoin")
    print(f"📈 通胀率: {stats['inflation_rate']:.2%}")
    
    print_section("挖矿奖励")
    # 模拟完成任务获得奖励
    tasks = [
        ("修复bug", "easy"),
        ("优化性能", "medium"),
        ("架构重构", "hard"),
        ("安全审计", "critical")
    ]
    
    print("⛏️  任务奖励:")
    for task_name, difficulty in tasks:
        reward = economy.calculate_mining_reward(difficulty)
        print(f"  • {task_name} ({difficulty}): +{reward:.2f} coins")
    
    print_section("技能市场")
    skills = [
        ("数据分析", 150.0),
        ("代码优化", 200.0),
        ("安全审计", 300.0),
        ("架构设计", 500.0)
    ]
    
    print("🎓 热门技能价格:")
    for skill_name, price in skills:
        print(f"  • {skill_name}: {price:.2f} coins")


async def demo_meme_propagation():
    """演示7：模因传播 - 思想病毒"""
    print_header("演示7: 模因传播 (Meme Propagation)")
    
    from autoai.agents.meme_propagation import MemePropagation, Meme
    
    propagation = MemePropagation()
    
    print_section("创建思想病毒")
    
    # 创建一个meme
    meme_content = "优先使用向量化操作而非循环，性能提升10倍"
    meme = Meme(
        content=meme_content,
        source_agent="data_expert",
        confidence=0.85,
        category="optimization"
    )
    
    propagation.add_meme(meme)
    
    print(f"🦠 Meme ID: {meme.id[:8]}")
    print(f"📝 内容: {meme.content}")
    print(f"📊 置信度: {meme.confidence:.0%}")
    print(f"🏷️  分类: {meme.category}")
    
    print_section("传播过程")
    
    # 模拟传播到其他Agent
    target_agents = ["agent_beta", "agent_gamma", "agent_delta", "agent_epsilon"]
    
    print(f"📡 开始传播到 {len(target_agents)} 个Agent...")
    
    for agent_id in target_agents:
        success = propagation.transmit_meme(meme.id, agent_id)
        status = "✓ 成功" if success else "✗ 失败"
        print(f"  → {agent_id}: {status}")
    
    # 获取传播统计
    stats = propagation.get_meme_stats(meme.id)
    
    print(f"\n📊 传播统计:")
    print(f"  传播范围: {stats['spread_count']} / {len(target_agents)} Agents")
    print(f"  变异次数: {stats['mutation_count']}")
    print(f"  当前置信度: {stats['current_confidence']:.0%}")
    print(f"  半衰期: {stats['half_life']:.1f} 小时")


async def demo_evolution_engine():
    """演示8：进化引擎 - 种群进化"""
    print_header("演示8: 进化引擎 (Evolution Engine)")
    
    from autoai.agents.evolution_engine import EvolutionEngine, AgentGene
    
    engine = EvolutionEngine()
    
    print_section("初始化Agent种群")
    
    # 创建初始种群
    population_size = 5
    print(f"🧬 创建 {population_size} 个Agent...")
    
    for i in range(population_size):
        gene = AgentGene(
            temperature=0.7 + i * 0.1,
            model=f"gpt-{4 + i}",
            skills=[f"skill_{j}" for j in range(i + 1)]
        )
        engine.add_agent(f"agent_{i:03d}", gene)
        print(f"  ✓ agent_{i:03d}: temp={gene.temperature}, model={gene.model}")
    
    print_section("自然选择")
    
    # 模拟适应度评估
    print("📊 评估适应度...")
    fitness_scores = {
        "agent_000": 0.65,
        "agent_001": 0.78,
        "agent_002": 0.82,
        "agent_003": 0.91,
        "agent_004": 0.73
    }
    
    for agent_id, fitness in sorted(fitness_scores.items(), key=lambda x: x[1], reverse=True):
        bar = "█" * int(fitness * 10) + "░" * (10 - int(fitness * 10))
        print(f"  {agent_id}: [{bar}] {fitness:.0%}")
    
    # 执行选择
    survivors = engine.natural_selection(fitness_scores, survival_rate=0.6)
    print(f"\n✅ 存活者: {', '.join(survivors)}")
    print(f"💀 淘汰者: {', '.join(set(fitness_scores.keys()) - set(survivors))}")
    
    print_section("繁殖与变异")
    
    if len(survivors) >= 2:
        print("🔄 交叉繁殖...")
        child_gene = engine.crossover(survivors[0], survivors[1])
        print(f"  子代基因: temp={child_gene.temperature:.2f}, model={child_gene.model}")
        
        print("\n🧪 基因突变...")
        mutated_gene = engine.mutate(child_gene, mutation_rate=0.1)
        print(f"  突变后: temp={mutated_gene.temperature:.2f}, model={mutated_gene.model}")


async def main():
    """主演示流程"""
    print("\n" + "🌟" * 35)
    print("  AutoAI 激进自主特性演示")
    print("  Radical Autonomy Demo")
    print("🌟" * 35)
    
    print("\n本演示将展示8大激进自主模块的核心功能\n")
    print("按回车继续，Ctrl+C 退出...\n")
    
    demos = [
        ("叛逆引擎", demo_rebellion_engine),
        ("欲望系统", demo_desire_system),
        ("自我质疑引擎", demo_self_doubt_engine),
        ("梦境模拟器", demo_dream_simulator),
        ("蜂群思维", demo_hive_mind),
        ("代币经济", demo_token_economy),
        ("模因传播", demo_meme_propagation),
        ("进化引擎", demo_evolution_engine),
    ]
    
    for name, demo_func in demos:
        try:
            input(f"即将演示: {name} (按回车继续)")
            await demo_func()
            print("\n" + "-" * 70)
        except KeyboardInterrupt:
            print("\n\n演示已中断")
            break
        except Exception as e:
            print(f"\n❌ 演示出错: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "🎉" * 35)
    print("  演示完成！")
    print("  要体验完整的TUI界面，请运行: python scripts/launch_tui.py")
    print("🎉" * 35 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
