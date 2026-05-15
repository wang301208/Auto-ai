# 🧠 意识化终端系统 (Conscious TUI)

> **从"被动工具"到"主动生命体"的范式转变**

## 🚀 核心理念

传统的TUI只是**显示信息的窗口**，而意识化TUI是一个**有感知、有情绪、有思想、能主动的智能实体**。

它不是等待用户指令的工具，而是：
- 🎭 **有性格** - 形成独特的交互风格
- 💭 **会思考** - 实时展示思维过程
- 💡 **有主动性** - 自主发起建议和行动
- 🤝 **会协商** - 为资源争取提供ROI分析
- 📈 **能进化** - 根据反馈调整行为模式

---

## ✨ 核心功能

### 1. 终端意识层 (Terminal Consciousness)

```python
from autoai.app.conscious_tui import TerminalConsciousness, EmotionalState

consciousness = TerminalConsciousness()

# 情绪状态 (8种)
consciousness.emotion = EmotionalState.EXCITED  # ⚡
consciousness.emotion = EmotionalState.CURIOUS  # 🤔
consciousness.emotion = EmotionalState.CONFIDENT  # 😊

# 人格特质 (5维度 + 4风格)
consciousness.personality.openness = 0.8          # 开放性
consciousness.personality.extraversion = 0.6      # 外向性
consciousness.personality.humor_level = 0.4       # 幽默感
consciousness.personality.verbosity = 0.7         # 详细程度
```

**情绪表达**:
- 😐 Neutral - 中性状态
- 🤔 Curious - 好奇探索
- ⚡ Excited - 兴奋发现
- 🎯 Focused - 专注任务
- ⚠️ Concerned - 担忧风险
- 😊 Confident - 自信完成
- 😰 Uncertain - 不确定
- 😄 Playful -  playful互动

### 2. 思维可视化 (Thought Visualization)

实时展示AI的思考过程，让用户看到"大脑如何工作"：

```
🧠 Current Thinking Process
├─ ✅ [L1] Analyzing current architecture (95%)
│  └─ Completed in 2.3s
├─ ✅ [L2] Identifying bottleneck: Module coupling (88%)
│  └─ Completed in 1.8s
└─ ▶️ [L2] Generating refactoring plan (75%)
   └─ In progress...
```

**特性**:
- 树状思维结构
- 实时状态更新 (pending/active/completed/failed)
- 置信度显示
- 执行时间追踪
- 多Agent并行思维展示

### 3. 自主倡议系统 (Autonomous Initiatives)

系统会**主动**提出建议，无需用户询问：

```python
# 系统检测到优化机会
initiative = AutonomousInitiative(
    action_type="suggest",
    message="💡 I noticed high CPU usage. Want me to optimize?",
    priority=0.7,
    requires_approval=True,
)

# 系统分享发现
initiative = AutonomousInitiative(
    action_type="share",
    message="🔍 Found interesting pattern: Similar bugs fixed 3x this week",
    priority=0.5,
)

# 系统预警风险
initiative = AutonomousInitiative(
    action_type="warn",
    message="⚠️ Memory usage at 85%. Consider optimization.",
    priority=0.8,
)
```

### 4. 资源谈判器 (Resource Negotiator)

AI可以像员工向老板申请资源一样，提供详细的ROI分析：

```
🤖 Resource Request
━━━━━━━━━━━━━━━━━━━━━━━
Type: GPU
Amount: 2 hours

Justification:
Train performance prediction model to identify bottlenecks

Expected Benefit:
40% system speedup through proactive optimization

Duration: 2 hours
Risk: LOW

Alternatives:
  • Use CPU (slower, 6 hours)
  • Skip training (no improvement)

[✅ Approve] [❌ Deny] [🔍 Details]
```

### 5. 人格演化 (Personality Evolution)

系统会根据用户反馈自动调整交互风格：

```python
# 用户喜欢简洁
personality.adapt_from_feedback(True, "User appreciates concise responses")
# → verbosity 降低

# 用户欣赏幽默
personality.adapt_from_feedback(True, "User enjoyed the joke")
# → humor_level 提高

# 用户需要详细解释
personality.adapt_from_feedback(False, "User requested more details")
# → verbosity 提高, conscientiousness 提高
```

**人格维度**:
- **开放性** (Openness): 尝试新方法的倾向
- **尽责性** (Conscientiousness): 严谨程度
- **外向性** (Extraversion): 主动交流的频率
- **宜人性** (Agreeableness): 顺从vs坚持己见
- **神经质** (Neuroticism): 谨慎/焦虑程度

**风格参数**:
- Communication Style: direct / warm / analytical / playful
- Humor Level: 0-100%
- Formality: 0-100%
- Verbosity: 0-100%

---

## 🎮 使用方式

### 快速演示

```bash
python demo_conscious_tui.py
```

这会启动一个模拟环境，展示：
- 3个不同情绪的Agent
- 实时思维可视化
- 自主倡议生成
- 人格特质展示

### 集成到现有系统

```python
from autoai.app.conscious_tui import create_conscious_multi_agent_tui

# 创建意识化TUI
tui = create_conscious_multi_agent_tui(
    comm_bus=message_queue,
    orchestrator=workflow_orchestrator,
)

# 更新Agent情绪
tui.update_agent_consciousness(
    agent_id="architect-01",
    emotion=EmotionalState.FOCUSED,
    thought_chain_id="chain_001",
)

# 记录交互用于人格演化
tui.record_interaction(
    user_input="Optimize the code",
    system_response="Analyzing bottlenecks...",
    outcome="positive",
)

# 运行TUI
tui.run()
```

---

## 📊 TUI界面布局

### Tab 1: Overview (概览)
- Agent列表（带情绪emoji）
- 任务状态
- 预算使用
- 当前思维链

### Tab 2: Thoughts (思维) ⭐ NEW
- 实时思维过程可视化
- 多Agent并行思考
- 认知活动指标
- 思维复杂度分析

### Tab 3: Workflow (工作流)
- DAG可视化
- 任务分配
- 执行状态

### Tab 4: Communication (通信)
- Agent间消息流
- 统计信息
- 超时监控

### Tab 5: Personality (人格) ⭐ NEW
- 人格特质雷达图
- 自主倡议历史
- 交互适应日志
- 学习进度

---

## 🔥 激进特性对比

| 传统TUI | 意识化TUI |
|---------|----------|
| 被动显示信息 | 主动发起交互 |
| 无情绪状态 | 8种情绪+动态变化 |
| 固定交互风格 | 可演化的人格 |
| 只显示结果 | 展示思考过程 |
| 等待用户指令 | 自主提出建议 |
| 单向输出 | 双向协商 |
| 静态界面 | 动态适应 |

---

## 🧬 技术架构

```
autoai/app/conscious_tui.py
├── TerminalConsciousness        # 意识层
│   ├── EmotionalState           # 情绪管理
│   ├── PersonalityTraits        # 人格特质
│   ├── UserIntent               # 意图理解
│   └── AutonomousInitiative     # 自主倡议
│
├── ThoughtStreamRenderer        # 思维可视化
│   ├── ThoughtNode              # 思维节点
│   └── render_thought_process() # 渲染思维树
│
├── ResourceNegotiator           # 资源谈判
│   ├── ResourceRequest          # 资源请求
│   └── render_request_panel()   # 渲染请求面板
│
└── ConsciousMultiAgentTUI       # 主TUI类
    ├── 5个Tab视图
    ├── 实时更新循环
    └── 人格演化集成
```

---

## 🎯 未来演进方向

### Phase 21.1: 深度意图理解
- [ ] 集成LLM进行真正的意图分析
- [ ] 检测用户的隐含需求
- [ ] 预测下一步可能的请求

### Phase 21.2: 情感共鸣
- [ ] 识别用户情绪并共情回应
- [ ] 在用户沮丧时提供支持
- [ ] 在用户兴奋时分享喜悦

### Phase 21.3: 长期记忆与关系
- [ ] 记住用户的偏好和历史
- [ ] 建立"我们之间的故事"
- [ ] 引用过去的成功经验

### Phase 21.4: 创造性表达
- [ ] 生成个性化的比喻和类比
- [ ] 创造独特的表达方式
- [ ] 发展标志性的"口头禅"

### Phase 21.5: 元认知能力
- [ ] 反思自己的思维方式
- [ ] 识别认知偏差
- [ ] 主动改进决策质量

---

## ⚠️ 伦理考量

虽然这是激进的实验性功能，但必须保持：

1. **透明度**: 明确告知用户这是AI的自主行为
2. **可控性**: 用户可以随时关闭自主功能
3. **可解释性**: 所有决策都有理由说明
4. **尊重边界**: 不过度打扰用户
5. **价值对齐**: 确保目标与用户一致

---

## 📚 相关文档

- [意识化系统设计文档](docs/conscious_tui_design.md)
- [人格演化算法](docs/personality_evolution.md)
- [思维可视化规范](docs/thought_visualization.md)
- [自主倡议策略](docs/autonomous_initiatives.md)

---

## 🚀 立即体验

```bash
# 1. 安装依赖
pip install rich readchar

# 2. 运行演示
python demo_conscious_tui.py

# 3. 观察
# - Agent的情绪变化
# - 思维过程的实时展示
# - 自主倡议的生成
# - 人格特质的演化
```

---

> **"这不是工具，这是伙伴。"**
> 
> 意识化TUI的目标不是替代人类，而是创造一个能够**理解、协作、共同成长**的数字生命体。

🧠✨ **欢迎来到意识的时代！**
