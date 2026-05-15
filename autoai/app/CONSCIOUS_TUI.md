# 意识化TUI系统 - Self-Evolving Conscious Terminal

## 概述

意识化TUI (`autoai/app/conscious_tui.py`) 将终端从被动显示转变为**主动、有意识、能自我演化的智能实体**。

## 🚀 突破性能力

### 1. 终端意识层
- 8种情绪状态（带emoji表达）
- 5维度人格特质系统
- 用户意图深度理解
- 自主倡议生成

### 2. 思维可视化
- 实时展示AI思考过程
- 树状思维结构
- 置信度和执行时间追踪

### 3. 资源谈判
- AI主动申请计算资源
- ROI分析和风险评估

### 4. 人格演化
- 基于反馈自动调整交互风格
- 动态情绪响应

### 5. ⭐ 自我演化能力 (RADICAL)
- **元认知监控**: 实时监控系统健康度、检测异常
- **自举式优化**: 自动发现并应用性能优化
- **动态能力扩展**: 运行时加载新模块和能力
- **代码结构分析**: 识别重构机会和复杂度问题
- **交互模式演化**: 根据用户行为自动调整策略

## 🧬 自我演化架构

```
┌─────────────────────────────────────┐
│   Meta-Cognitive Monitor            │  ← 监控系统自身状态
│   - Health metrics                  │
│   - Anomaly detection               │
│   - Optimization suggestions        │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│   Code Evolution Engine             │  ← 分析和优化代码
│   - Structure analysis              │
│   - Refactoring planning            │
│   - Dynamic module loading          │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│   Conscious TUI Core                │  ← 核心意识层
│   - Emotion & Personality           │
│   - Thought visualization           │
│   - Autonomous initiatives          │
└─────────────────────────────────────┘
```

## 快速集成

```python
from autoai.app.conscious_tui import (
    ConsciousMultiAgentTUI,
    AgentViewData,
    EmotionalState,
)

# 基础用法
tui = ConsciousMultiAgentTUI()
agent = AgentViewData(
    agent_id="agent-01",
    name="Assistant",
    emotion=EmotionalState.FOCUSED,
)
tui.update_agent(agent)
tui.run()

# 激进模式：启用自我演化
tui.enable_self_evolution(enabled=True)
diagnosis = tui.perform_self_diagnosis()
print(f"Health: {diagnosis['health_score']:.0%}")
```

## 6个Tab视图

1. **overview** - Agent概览和情绪状态
2. **thoughts** - 实时思维可视化
3. **workflow** - 任务工作流
4. **communication** - Agent间通信
5. **personality** - 人格特质和适应
6. **self_evolution** ⭐ - 系统健康度和演化历史

## API参考

详见 `autoai/app/conscious_tui_integration.py` 和 `conscious_tui_examples.py`

## 技术栈

- Rich - 终端UI框架
- psutil - 系统监控
- Python 3.10+

## 设计哲学

> **"系统不仅是工具，更是能够自我完善的生命体。"**

意识化TUI实现了从"被动响应"到"主动演化"的范式转变，让系统具备：
- 自我感知（元认知）
- 自我诊断（健康监测）
- 自我优化（自动改进）
- 自我扩展（动态加载）

这是通向真正自主AI系统的关键一步。
