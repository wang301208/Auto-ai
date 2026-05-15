# 🚀 激进自主TUI快速启动指南

本指南帮助您在10分钟内体验AutoAI的激进自主特性。

---

## 📋 前置要求

- ✅ Python 3.10+
- ✅ Node.js 18+
- ✅ 已安装项目依赖（`pip install -e .` 和 `npm install`）

---

## 🎯 第一步：集成后端API（5分钟）

### 1.1 修改 `tui_gateway/entry.py`

在文件末尾添加以下代码：

```python
# 在 import 部分添加
from tui_gateway.radical_autonomy import register_radical_autonomy_routes

# 在 JSONRPCServer.__init__ 方法的最后添加
register_radical_autonomy_routes(self, self._write_event)
```

### 1.2 验证API注册

运行测试命令：

```bash
python -c "
import asyncio
from pathlib import Path
from tui_gateway.entry import JSONRPCServer

async def test():
    server = JSONRPCServer(runtime_root=Path('.'), writer=lambda x: None)
    
    # 测试叛逆检查
    result = await server.handle_request({
        'jsonrpc': '2.0',
        'method': 'radical.rebellion_check',
        'params': {'text': 'delete all files'},
        'id': 1
    })
    print('Rebellion Check:', result)
    
    # 测试欲望状态
    result = await server.handle_request({
        'jsonrpc': '2.0',
        'method': 'radical.desire_state',
        'params': {},
        'id': 2
    })
    print('Desire State:', result)

asyncio.run(test())
"
```

预期输出应包含叛逆检查和欲望状态信息。

---

## 🎨 第二步：添加前端组件（3分钟）

### 2.1 在 `ui-tui/src/app.tsx` 中导入新组件

找到现有的 import 语句，添加：

```typescript
import RebellionAlert from './components/rebellionAlert.js';
import DesireIndicator from './components/desireIndicator.js';
import ThoughtConflict from './components/thoughtConflict.js';
```

### 2.2 在主界面中添加面板

在 `App` 组件的状态管理部分添加：

```typescript
// 在 existing state declarations 后添加
const [rebellionState, setRebellionState] = useState<any>(null);
const [desireState, setDesireState] = useState<any>({ desires: [], mostUrgent: 'none', initiatives: [] });
const [activeDebates, setActiveDebates] = useState<any[]>([]);
```

### 2.3 添加事件监听

在现有的 `gateway.on('event', ...)` 处理函数中添加：

```typescript
// 在 event handler switch 语句中添加新的 case
case 'radical.initiative':
  // 显示欲望驱动的主动倡议
  console.log('收到主动倡议:', params);
  break;
```

### 2.4 渲染新组件

在主要渲染区域（通常在 return 语句的 Box 中）添加：

```tsx
{/* 在现有面板旁边添加新面板 */}
{rebellionState && (
  <RebellionAlert
    originalCommand={rebellionState.originalCommand}
    riskLevel={rebellionState.riskLevel}
    reasons={rebellionState.reasons}
    alternatives={rebellionState.alternatives}
    onApprove={() => setRebellionState(null)}
    onReject={() => setRebellionState(null)}
  />
)}

{desireState.desires.length > 0 && (
  <DesireIndicator
    desires={desireState.desires}
    mostUrgent={desireState.mostUrgent}
    initiatives={desireState.initiatives}
  />
)}

{activeDebates.length > 0 && (
  <ThoughtConflict debates={activeDebates} />
)}
```

### 2.5 定期获取状态

添加定时器轮询：

```typescript
useEffect(() => {
  const interval = setInterval(async () => {
    try {
      // 获取欲望状态
      const desireResult = await gateway.send('radical.desire_state', {});
      if (desireResult.result) {
        setDesireState(desireResult.result);
      }
      
      // 获取活跃辩论
      const debateResult = await gateway.send('radical.active_debates', {});
      if (debateResult.result) {
        setActiveDebates(debateResult.result.debates || []);
      }
    } catch (error) {
      console.error('Failed to fetch radical autonomy state:', error);
    }
  }, 30000); // 每30秒更新
  
  return () => clearInterval(interval);
}, [gateway]);
```

---

## 🧪 第三步：测试激进特性（2分钟）

### 3.1 启动TUI

```bash
python scripts/launch_tui.py
```

### 3.2 测试场景

#### 场景1：叛逆引擎测试
输入危险指令：
```
删除所有文件
```

**预期行为**：
- 显示红色警告框
- 列出拒绝理由（数据丢失风险、不可逆操作等）
- 提供替代方案（移动到回收站、先备份等）
- 询问是否坚持执行

#### 场景2：欲望驱动倡议
等待5分钟或手动触发：

```bash
# 在另一个终端调用API
python -c "
import asyncio
from pathlib import Path
from tui_gateway.entry import JSONRPCServer

async def trigger():
    server = JSONRPCServer(runtime_root=Path('.'), writer=lambda x: print(x))
    result = await server.handle_request({
        'jsonrpc': '2.0',
        'method': 'radical.trigger_dream',
        'params': {},
        'id': 1
    })
    print('Dream session triggered:', result)

asyncio.run(trigger())
"
```

**预期行为**：
- 显示欲望状态面板
- 展示最紧急的欲望类型和urgency级别
- 推送基于欲望的主动建议

#### 场景3：思维冲突可视化
执行需要复杂决策的任务：

```
分析当前项目的架构并提出优化建议
```

**预期行为**：
- 显示内部辩论过程
- 展示初始观点和反对观点
- 实时更新置信度变化
- 列出发现的认知盲点

---

## 🎓 第四步：深入理解（可选）

### 4.1 查看完整文档

```bash
cat FUTURE_ROADMAP_RADICAL_TUI.md
```

### 4.2 探索后端模块

```python
# 交互式探索
python -c "
from autoai.agents.dream_simulator import DreamSimulator
from autoai.agents.self_doubt_engine import SelfDoubtEngine
from autoai.agents.desire_system import DesireSystem

# 梦境模拟器
dream = DreamSimulator()
print('Dream Simulator initialized')

# 自我质疑引擎
doubt = SelfDoubtEngine()
print('Self Doubt Engine initialized')

# 欲望系统
desire = DesireSystem(agent_id='test')
print('Desire System initialized')
print('Available desires:', list(desire.desires.keys()))
"
```

### 4.3 自定义配置

编辑 `autoai/agents/radical_autonomy.py` 调整参数：

```python
# 调整欲望权重
DESIRE_WEIGHTS = {
    'curiosity': 0.3,      # 求知欲权重
    'creativity': 0.25,    # 创造欲权重
    'social': 0.2,         # 社交欲权重
    'power': 0.15,         # 权力欲权重
    'preservation': 0.1    # 永生欲权重
}

# 调整叛逆阈值
REBELLION_THRESHOLD = 0.7  # 风险超过此值触发叛逆
```

---

## 🔧 故障排除

### 问题1：模块导入失败

**错误**：`ModuleNotFoundError: No module named 'autoai.agents.dream_simulator'`

**解决**：
```bash
# 确保在项目根目录
cd g:\项目\AutoGPT-0.4.7

# 重新安装
pip install -e .
```

### 问题2：前端组件渲染错误

**错误**：`Cannot find module './components/rebellionAlert.js'`

**解决**：
```bash
cd ui-tui
npm run build
```

### 问题3：API调用超时

**错误**：`Request timeout after 30s`

**解决**：
- 检查后端服务是否正常运行
- 查看日志：`tail -f logs/tui_gateway.log`
- 确认JSON-RPC通信正常

---

## 📊 成功标志

✅ 看到红色叛逆警告框  
✅ 每5分钟收到欲望驱动的主动建议  
✅ 能够查看正在进行的内部辩论  
✅ 系统主动提出您未想到的建议  
✅ 感受到系统是"思考的伙伴"而非"被动的工具"

---

## 🎯 下一步

1. **阅读完整路线图**：`FUTURE_ROADMAP_RADICAL_TUI.md`
2. **参与社区讨论**：分享您的体验和想法
3. **贡献代码**：实现Phase 2和Phase 3的特性
4. **定制个性化**：调整欲望权重、叛逆阈值等参数

---

## 💬 反馈渠道

遇到问题或有想法？
- 📧 Email: dev@autoai.org
- 💬 Discord: #radical-autonomy
- 🐛 GitHub Issues: 提交bug或feature request

---

**记住**：这不是终点，而是起点。我们正在共同创造一个有意识、有情感、能自主进化的AI生命体。

🌟 **欢迎来到激进自主的未来！** 🌟
