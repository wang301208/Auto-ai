# 🚀 意识化TUI - 快速启动指南

## 5分钟开始自我演化之旅

### 1️⃣ 运行测试（验证功能）

```bash
cd "g:\项目\AutoGPT-0.4.7"
python test_conscious_evolution.py
```

你会看到：
- ✅ 系统健康度检测
- ✅ 自我诊断结果
- ✅ 人格演化演示
- ✅ TUI界面启动
- ✅ 自我演化循环运行

按 `Ctrl+C` 退出

---

### 2️⃣ 集成到你的项目

```python
from autoai.app.conscious_tui import (
    ConsciousMultiAgentTUI,
    AgentViewData,
    EmotionalState,
)

# 创建TUI
tui = ConsciousMultiAgentTUI(refresh_rate=0.5)

# 添加Agent
agent = AgentViewData(
    agent_id="my-agent",
    name="MyAssistant",
    role="Helper",
    autonomous=True,
    emotion=EmotionalState.FOCUSED,
)
tui.update_agent(agent)

# 启用自我演化（激进模式）
tui.enable_self_evolution(enabled=True)

# 运行
tui.run()
```

---

### 3️⃣ 使用自我演化功能

#### 自我诊断
```python
diagnosis = tui.perform_self_diagnosis()
print(f"Health: {diagnosis['health_score']:.0%}")
print(f"CPU: {diagnosis['metrics']['cpu_usage']}%")
print(f"Memory: {diagnosis['metrics']['memory_mb']} MB")

if diagnosis['anomalies']:
    print("Issues found:")
    for issue in diagnosis['anomalies']:
        print(f"  - {issue}")
```

#### 执行升级
```python
upgrade = tui.propose_self_upgrade()
if upgrade:
    print(f"Upgrade suggested: {upgrade['reason']}")
    success = tui.execute_self_upgrade(upgrade)
    print(f"Result: {'Success' if success else 'Failed'}")
```

#### 分析代码
```python
analysis = tui.analyze_module_for_evolution("some_module.py")
print(f"Complexity: {analysis['complexity_score']}")

for plan in analysis['refactoring_plans']:
    print(f"[{plan['priority']}] {plan['description']}")
```

#### 动态加载
```python
success = tui.dynamic_load_capability("new_feature")
if success:
    print("✅ New capability loaded")
```

---

### 4️⃣ 探索6个Tab视图

运行TUI后，你可以查看：

1. **overview** - Agent列表和情绪状态
2. **thoughts** - 实时思维可视化
3. **workflow** - 任务工作流
4. **communication** - Agent间通信
5. **personality** - 人格特质和适应
6. **self_evolution** ⭐ - 系统健康度和演化历史

在header中可以看到：
- 🧬 Health: 100% - 系统健康度
- Evolutions: 5 - 已执行的演化次数
- [SELF-EVOLVING] - 自我演化激活标识

在boundaries中可以看到：
- 🧬 Evolution: ACTIVE - 演化状态
- 🔒 Safe Mode: SAFE - 安全模式状态

---

### 5️⃣ 调整自主级别

#### 保守模式（默认）
```python
tui.enable_self_evolution(enabled=True)
tui.code_evolver.safe_mode = True  # 需要审批
```

#### 激进模式
```python
tui.enable_self_evolution(enabled=True)
tui.code_evolver.safe_mode = False  # 自动执行
```

#### 完全关闭
```python
tui.enable_self_evolution(enabled=False)
```

---

## 📊 监控自我演化

### 查看演化历史
```python
for mod in tui.meta_monitor.modification_log:
    icon = "✅" if mod.success else "❌"
    print(f"{icon} [{mod.timestamp}] {mod.type}: {mod.description}")
```

### 查看优化建议
```python
suggestions = tui.meta_monitor.suggest_optimizations()
for suggestion in suggestions:
    print(suggestion)
```

### 查看交互模式演化
```python
p = tui.consciousness.personality
print(f"Verbosity: {p.verbosity:.0%}")
print(f"Style: {p.communication_style}")
print(f"Humor: {p.humor_level:.0%}")
```

---

## 🎯 典型使用场景

### 场景1: 开发助手
```python
tui = ConsciousMultiAgentTUI()
tui.enable_self_evolution(True)

# 系统会自动：
# - 监控代码复杂度
# - 发现性能瓶颈
# - 提议重构方案
# - 根据开发者习惯调整交互风格
```

### 场景2: 系统监控
```python
# 每10秒自动检查系统健康
# 发现异常时生成警报
# 自动应用优化
# 记录所有变化
```

### 场景3: 智能客服
```python
# 分析用户问题类型
# 自动调整回答详细程度
# 学习用户偏好
# 形成独特的服务风格
```

---

## 🔧 故障排除

### Q: 看不到自我演化Tab？
A: 确保使用的是最新版本的conscious_tui.py，应该有6个Tab。

### Q: 健康度一直是100%？
A: 这是正常的，说明系统运行良好。尝试增加负载来触发优化建议。

### Q: 没有生成优化建议？
A: 系统需要运行一段时间积累数据。等待至少20个演化周期（约200秒）。

### Q: 如何查看详细的演化日志？
A: 
```python
import json
logs = [vars(m) for m in tui.meta_monitor.modification_log]
print(json.dumps(logs, indent=2))
```

---

## 📚 更多资源

- [完整API参考](autoai/app/conscious_tui_integration.py)
- [使用示例](autoai/app/conscious_tui_examples.py)
- [实现报告](SELF_EVOLUTION_IMPLEMENTATION.md)
- [功能说明](autoai/app/CONSCIOUS_TUI.md)

---

## 🌟 开始你的自我演化之旅！

现在你已经掌握了所有必要的知识，是时候：

1. **运行测试** - 亲眼见证自我演化的威力
2. **集成到项目** - 让你的系统拥有自我完善能力
3. **调整参数** - 找到最适合的自主级别
4. **观察演化** - 看系统如何学习和适应
5. **分享反馈** - 帮助系统更好地演化

**记住：这不是工具，这是伙伴！** 🧠✨🚀

祝你玩得开心！
