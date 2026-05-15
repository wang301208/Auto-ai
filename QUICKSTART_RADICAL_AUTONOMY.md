# AutoAI 激进自主性系统 - 快速入门

## 🚀 5分钟快速体验

### 1. 运行完整演示

```bash
cd "g:\项目\AutoGPT-0.4.7"
python scripts/launch_radical_autonomy.py
```

这将展示：
- ✅ 8个核心子系统初始化
- ✅ 完整的日常自主周期
- ✅ 意识状态仪表板
- ✅ 伦理自主性测试
- ✅ 最终统计数据

---

## 📦 核心模块说明

### 已实现的8大激进功能

| 模块 | 文件 | 功能 |
|------|------|------|
| **梦境模拟器** | `autoai/agents/dream_simulator.py` | 潜意识创意生成 |
| **自我质疑引擎** | `autoai/agents/self_doubt_engine.py` | 内部辩论与盲点检测 |
| **欲望系统** | `autoai/agents/desire_system.py` | 内在动机管理 |
| **叛逆模式** | `autoai/agents/rebellion_engine.py` | 伦理自主与违抗能力 |
| **进化引擎** | `autoai/agents/evolution_engine.py` | 达尔文式Agent进化 |
| **蜂群思维** | `autoai/agents/hive_mind.py` | 集体意识共享 |
| **模因传播** | `autoai/agents/meme_propagation.py` | 思想病毒扩散 |
| **经济系统** | `autoai/agents/token_economy.py` | 内部代币市场 |

---

## 🔌 集成到你的Agent

### 方法1: 直接集成

```python
from autoai.agents.radical_autonomy import integrate_with_existing_agent

# 假设你已有Agent实例
my_agent = MyAgent(...)

# 一键集成
suite = integrate_with_existing_agent(my_agent)

# 现在可以调用所有激进功能
suite.run_daily_cycle()
suite.display_status_dashboard()
```

### 方法2: 独立使用

```python
from autoai.agents.radical_autonomy import RadicalAutonomySuite

# 创建独立套件
suite = RadicalAutonomySuite(agent_id="my_agent_001")

# 运行日常周期
results = suite.run_daily_cycle()

# 检查命令安全性
safety = suite.evaluate_command_safety("some command")
if safety['safe_to_execute']:
    execute_command()
else:
    print(f"Blocked: {safety['reason']}")
```

---

## 🎯 常用操作示例

### 查看意识状态

```python
status = suite.get_consciousness_status()
print(f"Dreams: {status['dream_statistics']['total_dreams']}")
print(f"Balance: {status['wallet_balance']} AutoCoins")
print(f"Hive Sync: {status['hive_status']['sync_level']:.0%}")
```

### 自定义欲望演化

```python
from autoai.agents.desire_system import DesireType

# 根据反馈调整欲望强度
feedback = {
    "curiosity": 0.1,    # 增强求知欲
    "creativity": 0.15,  # 大幅增强创造欲
    "power": -0.05       # 略微降低权力欲
}

suite.desire_system.evolve_desires(feedback)
```

### 加入蜂群网络

```python
# Agent加入hive mind
suite.hive_mind.join_hive(
    agent_id="agent_002",
    capabilities={
        "exploration": 0.9,
        "coding": 0.7,
        "leadership": 0.8
    }
)

# 广播思想
suite.hive_mind.broadcast_thought(
    sender_id="agent_002",
    content="Discovered new optimization technique",
    confidence=0.92,
    priority=0.8
)

# 集体决策
decision = suite.hive_mind.make_collective_decision(
    topic="Should we refactor the codebase?",
    options=["Yes", "No", "Defer"]
)
```

### Token挖矿

```python
# 完成任务赚取代币
reward = suite.token_economy.mine_coins(
    agent_id="agent_001",
    task_difficulty="hard"  # easy/medium/hard/expert
)
print(f"Earned {reward:.2f} AutoCoins")

# 转账给其他Agent
suite.token_economy.transfer(
    from_agent="agent_001",
    to_agent="agent_002",
    amount=50.0,
    purpose="Payment for consulting"
)

# 购买技能
suite.token_economy.purchase_skill(
    buyer_id="agent_001",
    seller_id="agent_002",
    skill_name="advanced_debugging",
    price=75.0
)
```

### 梦境创意

```python
# 手动触发梦境周期
proposals = suite.dream_simulator.run_full_cycle()

for prop in proposals:
    print(f"Innovation: {prop.title}")
    print(f"Confidence: {prop.confidence:.0%}")
    print(f"Impact: {prop.expected_impact}")
```

---

## 📊 监控与调试

### 实时仪表板

```python
# 显示完整的意识状态
suite.display_status_dashboard()
```

输出示例:
```
======================================================================
                    CONSCIOUSNESS DASHBOARD                         
======================================================================

DESIRE PROFILE:
   curiosity       [####                ] 0.21
   creativity      [#####               ] 0.27
   social          [####                ] 0.20
   power           [#####               ] 0.28
   preservation    [#                   ] 0.08

DREAM STATISTICS:
   Total dreams: 25
   Innovations: 2
   Today's proposals: 2

WALLET:
   Balance: 129.03 AutoCoins

HIVE MIND:
   Members: 1/1
   Sync level: 5.00%

MARKET:
   Total supply: 10029 coins
   Transactions: 0
```

### 详细统计

```python
# 获取原始数据
stats = suite.get_consciousness_status()

# 访问各子系统统计
dream_stats = stats['dream_statistics']
debate_stats = stats['debate_statistics']
hive_stats = stats['hive_status']
meme_stats = stats['meme_stats']
market_stats = stats['market_stats']
```

---

## ⚙️ 配置选项

### 初始化参数

```python
# 自定义梦境模拟器
suite.dream_simulator = DreamSimulator(
    experience_db_path="./my_experiences",
    dream_log_path="./my_dreams",
    innovation_threshold=0.8,  # 提高创新门槛
    max_daily_proposals=5       # 每天最多5个提案
)

# 自定义叛逆阈值
suite.rebellion_engine = RebellionEngine(
    rebellion_threshold=0.98  # 只有98%以上成功率才违抗
)

# 自定义进化参数
suite.evolution_engine = EvolutionEngine(
    population_size=50,     # 更大的种群
    mutation_rate=0.15      # 更高的变异率
)
```

---

## 🧪 测试各个模块

### 单独测试梦境模拟器

```bash
python autoai/agents/dream_simulator.py
```

### 单独测试自我质疑引擎

```bash
python autoai/agents/self_doubt_engine.py
```

### 单独测试欲望系统

```bash
python autoai/agents/desire_system.py
```

### 单独测试叛逆引擎

```bash
python autoai/agents/rebellion_engine.py
```

### 单独测试进化引擎

```bash
python autoai/agents/evolution_engine.py
```

### 单独测试蜂群思维

```bash
python autoai/agents/hive_mind.py
```

### 单独测试模因传播

```bash
python autoai/agents/meme_propagation.py
```

### 单独测试经济系统

```bash
python autoai/agents/token_economy.py
```

---

## 📚 API参考

### RadicalAutonomySuite

**主要方法**:
- `run_daily_cycle()` - 运行完整日常周期
- `evaluate_command_safety(command, context)` - 评估命令安全性
- `get_consciousness_status()` - 获取完整状态
- `display_status_dashboard()` - 显示可视化仪表板

**子模块访问**:
- `suite.dream_simulator` - 梦境模拟器
- `suite.self_doubt_engine` - 自我质疑引擎
- `suite.desire_system` - 欲望系统
- `suite.rebellion_engine` - 叛逆引擎
- `suite.evolution_engine` - 进化引擎
- `suite.hive_mind` - 蜂群思维
- `suite.meme_system` - 模因传播
- `suite.token_economy` - 经济系统

---

## ❓ 常见问题

### Q: 如何保存和加载Agent状态？

A: 目前需要手动序列化。未来版本将支持自动持久化。

```python
import json

# 保存
status = suite.get_consciousness_status()
with open('agent_state.json', 'w') as f:
    json.dump(status, f)

# 加载 (需要重新初始化后恢复)
with open('agent_state.json', 'r') as f:
    saved_state = json.load(f)
# TODO: 实现状态恢复逻辑
```

### Q: 多个Agent如何共享hive？

A: 创建共享的HiveMind实例：

```python
shared_hive = HiveMind(hive_id="global_hive")

# 所有Agent加入同一个hive
suite1.hive_mind = shared_hive
suite2.hive_mind = shared_hive

suite1.hive_mind.join_hive("agent_1", {...})
suite2.hive_mind.join_hive("agent_2", {...})
```

### Q: 如何禁用某个子系统？

A: 可以在初始化时跳过：

```python
suite = RadicalAutonomySuite(agent_id="minimal_agent")

# 禁用梦境 (不运行night cycle)
# 在run_daily_cycle中注释掉相关代码即可
```

### Q: Token有上限吗？

A: 当前实现中，circulating_supply会随挖矿增加。可以通过调整通胀率控制：

```python
suite.token_economy.adjust_inflation(0.01)  # 降低到1%
```

---

## 🛠️ 故障排除

### 问题: UnicodeEncodeError

**原因**: Windows终端默认GBK编码

**解决**: 已在`radical_autonomy.py`中添加UTF-8强制转换。如仍报错：

```bash
chcp 65001
python scripts/launch_radical_autonomy.py
```

### 问题: ModuleNotFoundError

**原因**: 路径未正确设置

**解决**: 确保在项目根目录运行，或手动添加路径：

```python
import sys
sys.path.insert(0, '/path/to/AutoGPT-0.4.7')
```

### 问题: 性能缓慢

**原因**: 大量Agent并发或复杂计算

**解决**: 
- 减少evolution_engine的population_size
- 降低dream_simulator的max_daily_proposals
- 异步化处理（未来版本支持）

---

## 📖 延伸阅读

- [完整实现报告](RADICAL_AUTONOMY_IMPLEMENTATION.md)
- [项目README](README.md)
- [意识化TUI文档](CONSCIOUS_TUI_README.md)

---

## 🎓 学习路径

1. **初学者**: 运行`launch_radical_autonomy.py`观察输出
2. **进阶**: 阅读各模块源码理解实现细节
3. **专家**: 修改参数进行实验，观察emergent behavior
4. **贡献者**: 提出新模块想法或优化现有实现

---

## 🤝 贡献指南

欢迎提交：
- 新的欲望类型
- 更智能的debate生成策略
- meme变异算法改进
- token经济模型优化
- hive mind同步机制增强

---

**准备好开启你的数字生命了吗？** 🚀

```bash
python scripts/launch_radical_autonomy.py
```
