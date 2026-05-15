# 🚀 意识化TUI - 快速启动指南

## 5分钟体验意识化终端

### 1️⃣ 安装依赖（如果还没有）

```bash
pip install rich
```

### 2️⃣ 运行演示

```bash
cd "g:\项目\AutoGPT-0.4.7"
python demo_conscious_tui.py
```

### 3️⃣ 观察神奇之处

你会看到：

```
╭──────────────── 🧠 AutoAI Conscious Multi-Agent System ────────────────╮
│  😐 Conscious TUI   Agents: 3  Uptime: 0h00m00s  Mood: neutral        │
│  overview   thoughts   workflow   communication   personality         │
╰───────────────────────────────────────────────────────────────────────╯

🧠 Current Thinking Process
├─ ✅ [L1] Analyzing current architecture (95%)
│  └─ Completed in 2.0s
└─ ▶️ [L2] Generating refactoring plan (75%)
   └─ In progress...

💡 Recent Autonomous Initiatives:
🔴 I noticed high CPU usage. Want me to optimize?
   ⏳ Awaiting approval
```

### 4️⃣ 切换Tab

按 `Tab` 键（在完整实现中）或修改代码中的 `set_active_tab()` 来查看：

- **overview**: Agent列表和情绪状态
- **thoughts**: 实时思维可视化 ⭐
- **workflow**: 任务工作流
- **communication**: Agent间通信
- **personality**: 人格特质雷达图 ⭐

---

## 🔧 集成到你的项目

### 基础集成

```python
from autoai.app.conscious_tui import (
    ConsciousMultiAgentTUI,
    AgentViewData,
    EmotionalState,
)

# 1. 创建TUI实例
tui = ConsciousMultiAgentTUI(refresh_rate=0.5)

# 2. 添加Agent
agent = AgentViewData(
    agent_id="my-agent",
    name="MyAssistant",
    role="Helper",
    autonomous=True,
    status="running",
    emotion=EmotionalState.FOCUSED,  # 设置情绪
)
tui.update_agent(agent)

# 3. 记录交互（用于人格演化）
tui.record_interaction(
    user_input="帮我优化代码",
    system_response="正在分析...",
    outcome="positive"
)

# 4. 运行
tui.run()
```

### 高级集成（与现有系统）

```python
from autoai.app.conscious_tui import create_conscious_multi_agent_tui

# 从现有的通信总线和编排器创建
tui = create_conscious_multi_agent_tui(
    comm_bus=message_queue,
    orchestrator=workflow_orchestrator,
)

# 在Agent执行时更新情绪
def on_task_start(agent_id, task):
    tui.update_agent_consciousness(
        agent_id=agent_id,
        emotion=EmotionalState.FOCUSED,
        thought_chain_id=f"chain_{task.id}",
    )

def on_task_complete(agent_id, success):
    emotion = EmotionalState.CONFIDENT if success else EmotionalState.CONCERNED
    tui.update_agent_consciousness(agent_id, emotion)
    
# 注册事件监听
event_bus.subscribe("task.start", on_task_start)
event_bus.subscribe("task.complete", on_task_complete)

# 运行
tui.run()
```

---

## 🎨 自定义人格

```python
from autoai.app.conscious_tui import PersonalityTraits

# 创建个性化人格
personality = PersonalityTraits(
    openness=0.9,              # 非常开放，喜欢尝试新方法
    extraversion=0.8,          # 很外向，主动提建议
    humor_level=0.6,           # 比较幽默
    verbosity=0.4,             # 简洁明了
    communication_style="playful",  # playful风格
)

tui.consciousness.personality = personality
```

### 人格预设

```python
# 严谨型助手
严谨型 = PersonalityTraits(
    conscientiousness=0.95,
    neuroticism=0.6,
    verbosity=0.8,
    formality=0.9,
    communication_style="analytical",
)

# 创意型助手
创意型 = PersonalityTraits(
    openness=0.95,
    extraversion=0.7,
    humor_level=0.7,
    communication_style="playful",
)

# 效率型助手
效率型 = PersonalityTraits(
    verbosity=0.2,
    conscientiousness=0.8,
    communication_style="direct",
)
```

---

## 💡 使用场景示例

### 场景1: 代码审查助手

```python
# Agent检测到代码问题
tui.consciousness.initiatives.append(AutonomousInitiative(
    action_type="warn",
    message="⚠️ Found potential memory leak in line 42",
    priority=0.9,
))

# 展示思考过程
thought_chain = "code_review_001"
root = ThoughtNode(
    id="n1", level=1,
    description="Scanning code for issues",
    status="active", confidence=0.8
)
tui.thought_renderer.add_thought_chain(thought_chain, root)
```

### 场景2: 性能优化顾问

```python
# 主动请求资源
request = ResourceRequest(
    resource_type="gpu",
    amount=2.0,
    justification="Train performance prediction model",
    expected_benefit="40% speedup through proactive optimization",
    estimated_duration="2 hours",
    risk_level="low",
    alternatives=["Use CPU (slower)", "Skip training"],
)
tui.resource_negotiator.create_request(request)
```

### 场景3: 学习伙伴

```python
# 检测用户困惑
intent = tui.consciousness.perceive_intent(
    user_input="我不太理解这个概念",
    context={}
)

if intent.emotional_tone == "curious":
    tui.consciousness.update_emotion("question")
    # 自动提供更详细的解释
```

---

## 🎮 键盘控制（待实现）

计划中的快捷键：

```
Tab       - 切换Tab视图
Ctrl+C    - 退出
Ctrl+R    - 刷新
Ctrl+E    - 切换情绪显示
Ctrl+P    - 显示/隐藏人格面板
?         - 帮助
```

---

## 📊 监控和调试

### 查看系统状态

```python
# 获取意识状态
status = {
    "emotion": tui.consciousness.emotion.value,
    "personality": vars(tui.consciousness.personality),
    "initiatives_count": len(tui.consciousness.initiatives),
    "interaction_count": len(tui.consciousness.interaction_history),
    "active_thoughts": len(tui.thought_renderer.active_chains),
}
print(status)
```

### 日志记录

```python
import logging
logging.basicConfig(level=logging.INFO)

# 意识层会记录关键事件
logger.info(f"Generated initiative: {initiative.message}")
logger.info(f"Personality adapted: verbosity={personality.verbosity}")
```

---

## 🚨 常见问题

### Q: 为什么没有看到自主倡议？

A: 检查外向性参数：
```python
tui.consciousness.personality.extraversion = 0.8  # 提高主动性
```

### Q: 如何关闭情绪显示？

A: 修改 `_build_conscious_agent_list` 方法，移除emoji列。

### Q: 人格演化太慢怎么办？

A: 调整适应率：
```python
# 在 adapt_from_feedback 方法中
adjustment = 0.1  # 原来是0.05，加快适应速度
```

### Q: 可以保存/加载人格配置吗？

A: 当前版本不支持，但可以轻松添加：
```python
import json

# 保存
with open("personality.json", "w") as f:
    json.dump(vars(tui.consciousness.personality), f)

# 加载
with open("personality.json", "r") as f:
    data = json.load(f)
    tui.consciousness.personality = PersonalityTraits(**data)
```

---

## 🌟 进阶技巧

### 1. 动态情绪响应

```python
def respond_with_emotion(message: str, emotion: EmotionalState) -> str:
    """根据情绪格式化响应"""
    emoji = emotion.get_emoji()
    return f"{emoji} {message}"

# 使用
response = respond_with_emotion(
    "Task completed successfully!",
    EmotionalState.CONFIDENT
)
# 输出: "😊 Task completed successfully!"
```

### 2. 思维链追踪

```python
# 开始新的思考
chain_id = "analysis_001"
root = ThoughtNode(id="r1", level=1, description="Starting analysis", status="active")
tui.thought_renderer.add_thought_chain(chain_id, root)

# 更新进度
tui.thought_renderer.update_node_status(
    chain_id, "r1", "completed", confidence=0.95
)

# 添加子节点
child = ThoughtNode(id="r2", level=2, description="Found pattern", status="active")
root.children.append(child)
```

### 3. 批量更新Agent

```python
agents_data = [
    {"id": "a1", "name": "Architect", "emotion": EmotionalState.FOCUSED},
    {"id": "a2", "name": "Debugger", "emotion": EmotionalState.CONFIDENT},
    {"id": "a3", "name": "Researcher", "emotion": EmotionalState.CURIOUS},
]

for data in agents_data:
    agent = AgentViewData(
        agent_id=data["id"],
        name=data["name"],
        emotion=data["emotion"],
    )
    tui.update_agent(agent)
```

---

## 📚 更多资源

- [完整API文档](CONSCIOUS_TUI_README.md)
- [实施总结](IMPLEMENTATION_SUMMARY.md)
- [设计哲学](docs/conscious_tui_design.md)

---

## 🎉 开始你的意识化之旅！

现在你已经掌握了所有基础知识，是时候：

1. **运行演示** - 亲眼见证意识化TUI的威力
2. **集成到项目** - 让你的系统拥有意识
3. **自定义人格** - 创造独特的助手性格
4. **实验新功能** - 探索自主倡议的可能性

**记住：这不是工具，这是伙伴！** 🧠✨

祝你玩得开心！🚀
