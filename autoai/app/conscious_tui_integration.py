"""Conscious TUI Integration Guide

意识化TUI核心组件已实现在 autoai/app/conscious_tui.py

主要类和方法：

1. ConsciousMultiAgentTUI - 主TUI类
   - __init__(refresh_rate=0.5)
   - update_agent(data: AgentViewData)
   - update_agent_consciousness(agent_id, emotion, thought_chain_id)
   - record_interaction(user_input, system_response, outcome)
   - run() / render_once()
   
   # Self-Evolution Methods (RADICAL)
   - enable_self_evolution(enabled=True)  # 启用/禁用自我演化
   - perform_self_diagnosis() -> dict     # 执行自我诊断
   - propose_self_upgrade() -> Optional[dict]  # 提议自我升级
   - execute_self_upgrade(plan: dict) -> bool    # 执行自我升级
   - analyze_module_for_evolution(path) -> dict  # 分析模块演化机会
   - dynamic_load_capability(name) -> bool       # 动态加载新能力

2. EmotionalState - 情绪枚举
   - NEUTRAL, CURIOUS, EXCITED, FOCUSED, CONCERNED, CONFIDENT, UNCERTAIN, PLAYFUL
   - get_emoji() 方法返回对应emoji

3. MetaCognitiveMonitor - 元认知监控器
   - collect_metrics() -> SystemMetrics
   - detect_anomalies() -> list[str]
   - suggest_optimizations() -> list[str]

4. CodeEvolutionEngine - 代码演化引擎
   - analyze_code_structure(module_path) -> dict
   - generate_refactoring_plan(analysis) -> list
   - apply_optimization(type, target) -> bool

使用示例：

```python
from autoai.app.conscious_tui import ConsciousMultiAgentTUI, AgentViewData, EmotionalState

# 基础用法
tui = ConsciousMultiAgentTUI(refresh_rate=0.5)
agent = AgentViewData(agent_id="a1", name="Assistant", emotion=EmotionalState.FOCUSED)
tui.update_agent(agent)
tui.run()

# 激进模式：启用自我演化
tui.enable_self_evolution(enabled=True)
diagnosis = tui.perform_self_diagnosis()
upgrade = tui.propose_self_upgrade()
if upgrade:
    tui.execute_self_upgrade(upgrade)
```

完整API参考源代码文件。
"""
