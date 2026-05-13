# AutoGPT-0.4.7 自主进化终端Agent系统

## 项目定位

基于LLM的**完全自主运行终端Agent系统**。核心理念：**高度自主，自我进化**——Agent默认自主运行，人只设边界、看结果。

纯终端TUI应用，**无GUI/无浏览器/无Web界面**，所有功能在终端运行和展示。

## 自主等级体系（L0→L5）

| 等级 | 名称 | 描述 | 能力 |
|------|------|------|------|
| L0 | MANUAL | 每步需人审批 | 无自主权限 |
| L1 | SUPERVISED | 人设边界内运行 | 可修改配置、切换模型 |
| L2 | SELF_BOUND | Agent自设边界 | 可修改代码、自动commit、热重载 |
| L3 | SELF_REWRITE | 可修改自身架构 | 可自改架构、自动push、跳过审批 |
| L4 | SELF_SPAWN | 可创建/销毁子Agent | 可创建销毁子Agent |
| L5 | AUTONOMOUS | 完全自治 | 全部能力，人只看结果 |

## 架构全景

```
autogpt/                          # Agent核心
├── agents/
│   ├── agent.py                  # V1 Agent主类
│   ├── async_agent.py            # V2 AsyncAgent核心（ModelRouter/Sandbox/Streaming接入）
│   ├── unified_task.py           # 统一任务模型（4类别+TaskScheduler+CircuitBreaker）
│   ├── self_think.py             # SelfThinkEngine（自我进化闭环：scan→fix→verify→policy_adjust）
│   ├── self_modify.py            # 代码自修改管道（patch→apply→test→commit→revert→reload）
│   ├── ability_adapter.py        # Command→Ability适配器
│   ├── memory_adapter.py         # V1→V2 Memory适配器
│   ├── subsystem_injection.py    # V2 Ability包装+注入
│   ├── agent_comm.py             # Agent通信总线
│   ├── workflow_orchestrator.py  # DAG编排+WorkflowOrchestrator
│   ├── health_monitor.py         # Agent健康监控
│   ├── workflow_checkpoint.py    # 检查点管理
│   ├── agent_pool.py             # Agent池
│   └── agent_factory.py          # Agent工厂+AgentSpec
├── app/
│   ├── main.py                   # 主入口（async_mode/autonomous/multi_agent集成）
│   ├── cli.py                    # CLI注册（--async-mode/--autonomous/--multi-agent）
│   ├── commands.py               # 统一CLI命令组（含doctor/model/dashboard/governance）
│   ├── async_loop.py             # 异步主循环（周期性策略调整+自进化触发）
│   ├── tui.py                    # 单Agent TUI（流式Live Stream面板）
│   ├── multi_agent_tui.py        # 多Agent TUI（3-Tab布局）
│   ├── dashboard.py              # 终端Dashboard（Rich 4象限仪表板）
│   ├── i18n.py                   # 多语言切换框架
│   ├── zh_CN.json / en.json      # 中英locale文件
│   └── __main__.py               # 入口（UTF-8终端强制）
├── llm/model_router/             # 统一模型层
│   ├── base_provider.py          # BaseProvider抽象+ChatMessage/ChatResponse
│   ├── model_spec.py             # ModelSpec+9个内置spec+_caps辅助
│   ├── model_registry.py         # ModelRegistry（注册+别名+fallback+YAML加载）
│   ├── model_router.py           # ModelRouter+5策略+降级链+预算感知
│   ├── openai_provider.py        # OpenAICompatProvider（含stream_chat）
│   ├── ollama_provider.py        # OllamaProvider（含stream_chat+自动检测）
│   ├── model_auto_selector.py    # 模型自选（Agent根据任务实时选模型）
│   ├── streaming.py              # StreamingEvent+StreamEmitter+StreamingChat+StreamBuffer
│   └── models.yaml               # 声明式模型配置（9个模型+3个别名）
├── sandbox/                      # 安全沙箱
│   ├── base.py                   # SandboxConfig+SandboxResult+ViolationType
│   ├── subprocess_sandbox.py     # SubprocessSandbox（跨平台）
│   └── seccomp_sandbox.py        # SeccompSandbox（Linux,非Linux降级）
├── distributed/                  # 分布式执行
│   ├── base.py                   # DistributedBackend+WorkerInfo+DispatchFuture
│   ├── local_backend.py          # LocalBackend（单进程asyncio）
│   └── ray_backend.py            # RayBackend（多节点Ray,Ray不可用时降级）
├── config/config.py              # Config（含language字段+ModelRouter别名桥接）
├── logs/logger.py                # 日志
├── event_bus/                    # 事件总线
├── self_improve/                 # 自我改进模块
├── memory/                       # 记忆系统
├── commands/                     # V1命令集
└── core/                         # V2核心（ability/planning/schema）

governance/                       # 治理引擎
├── policy.py                     # 声明式策略引擎
├── approval.py                   # 审批工作流
├── rate_limit.py                 # 令牌桶限速
├── audit.py                      # JSONL审计日志
├── quota.py                      # 配额管理
├── gate.py                       # 审计网门面（autonomous/supervised双模式）
├── policy_evolver.py             # 策略自演化引擎（含evolve_from_cycle）
├── autonomy_level.py             # 自主等级管理（L0-L5+自动晋升/降级）
├── modification_chain.py         # 不可变修改日志链（SHA256链式审计）
├── experience_store.py           # 经验库（修复模式存储+匹配+复用）
├── default_policy.json           # 默认策略
└── agents_fleet.json             # 默认舰队配置

algorithm_library/                # 算法库
├── base.py / registry.py / evaluation.py / lifecycle.py / catalog.py

tests/unit/                       # 测试套件（241个测试全部PASSED）
```

## 自我进化闭环

```
scan(发现) → fix(修复) → verify(验证) → policy_adjust(策略调整) → [下一周期]
     ↑                                                        |
     └──────────── 周期性触发(每50轮) ──────────────────────────┘
```

**激进版（Phase 11+）：**

```
scan → LLM生成patch → 沙箱apply → 全量test → 通过→commit+push+hot-reload
                                           → 失败→git-revert+学习+记录到链
```

每次修改记录到**不可变SHA256链式日志**，任何篡改可检测。

## 代码自修改管道

```
SelfModifyPipeline:
  1. 检查自主等级 >= L2（SELF_BOUND）
  2. git apply --unsafe-patches 应用补丁
  3. 跑全量测试（pytest）
  4. 通过 → git commit → (L3+则git push) → importlib.reload热重载
  5. 失败 → git reset --hard HEAD~1 自动回滚 → 记录失败 → 自主等级降级
```

## 模型自选机制

Agent根据任务特征实时决定用什么模型：

| 任务复杂度 | 层级 | 典型模型 |
|-----------|------|---------|
| TRIVIAL/SIMPLE | fast | qwen3-4b (本地, 免费) |
| MODERATE | balanced | qwen3-14b / gpt-4o-mini |
| COMPLEX/CRITICAL | smart | gpt-4o / qwen3-72b |
| embedding | embedding | text-embedding-3-small |

预算不足自动降级到fast，延迟敏感自动降级到balanced，记录历史性能下次选最优。

## 经验库

- 修复成功 → 抽象模式 → 存储 → 下次相似Issue → 直接复用
- 按issue_type/language/symptom_pattern匹配
- 成功率+置信度评分，失败自动降权
- **Agent越用越聪明**

## 快速开始

### 环境要求

- Python >= 3.10
- OpenAI API Key（或本地Ollama）

### 安装

```bash
pip install -r requirements.txt
```

### 配置

```bash
cp .env.template .env
# 编辑 .env 填入 OPENAI_API_KEY
```

### 运行

```bash
# 标准模式
python -m autogpt

# 异步模式
python -m autogpt --async-mode

# 自主模式（无人值守）
python -m autogpt --async-mode --autonomous

# 多Agent模式
python -m autogpt --async-mode --multi-agent

# 中文化
python -m autogpt --lang zh_CN
```

### 诊断

```bash
python -m autogpt doctor
```

检测项：Python版本、openai/chromadb/rich/click/httpx、governance/、model_router/、sandbox/、distributed/、streaming/、self_think/、ray(可选)/seccomp(可选)

## CLI命令组

```bash
autogpt doctor                    # 健康诊断
autogpt model list               # 列出已注册模型
autogpt model route --tier fast  # 查看路由决策
autogpt model providers          # 列出可用Provider
autogpt dashboard                # 终端4象限仪表板
autogpt governance breaks        # 查看边界突破记录（事后审计）
autogpt governance audit         # 查看治理审计日志
autogpt governance policy        # 查看当前策略
autogpt governance evolve        # 触发策略自演化
autogpt stop                     # 终止Agent运行（唯一人类运行时干预）
autogpt orchestrate              # 多Agent编排
```

## 治理引擎

### Agent自主边界管理（核心哲学）

**Agent自己设定边界，Agent自己调整边界，Agent自己打破边界。人类角色：仅事后审视结果。**

三生命周期：
1. **autonomous_init()** — Agent根据任务目标+经验库+环境感知自主定义初始约束
2. **autonomous_adjust()** — Agent根据执行反馈动态调整约束（±30%梯度，连续3次同方向后扩大）
3. **autonomous_break()** — Agent突破阻碍目标的约束（风险乘子递增收敛，突破后自动补偿）

10种约束类型：token_budget / file_write_scope / file_read_scope / network_access / shell_execute / sandbox_strictness / time_budget / model_tier / self_modify / agent_spawn

人类交互入口仅三个：
- `agpt run` — 下达目标
- `agpt audit` — 事后审视审计日志
- `agpt breaks` — 事后审视边界突破记录
- `agpt stop` — 终止运行（唯一运行时干预，不影响边界决策）

### 策略自演化

`PolicyEvolver.evolve_from_cycle(fixed_count, failed_count)`：
- 修复全部成功 → 放宽限速（refill_rate × 1.05）
- 修复失败多于成功 → 收紧限速（refill_rate × 0.8）

### 自主等级自动调整

所有等级均为完全自主运行，等级差异仅影响约束松紧度，不涉及人类审批：
- 连续50次成功 → 自主等级+1（约束放宽）
- 连续3次失败 → 自主等级-1（约束收紧）
- 冷却期1小时（防止频繁升降级）

## 中文化

支持中文/英文切换，110+条翻译覆盖：

```bash
python -m autogpt --lang zh_CN    # 中文
python -m autogpt --lang en       # 英文
```

或在`.env`中设置`LANGUAGE=zh_CN`。

## 统一模型层

### 5种路由策略

1. **cost_optimal**：最低成本优先
2. **latency_optimal**：最低延迟优先
3. **quality_optimal**：最高质量优先
4. **round_robin**：轮询
5. **fallback_chain**：降级链

### 9个内置模型Spec

gpt-4o / gpt-4o-mini / gpt-3.5-turbo / claude-3-opus / claude-3-haiku / qwen3-4b / qwen3-14b / qwen3-72b / text-embedding-3-small

### 3个别名

fast→gpt-4o-mini / balanced→gpt-4o / smart→claude-3-opus

## 安全沙箱

- **SubprocessSandbox**：跨平台子进程隔离，白名单/黑名单命令控制，路径限制，资源限制（CPU/内存/超时）
- **SeccompSandbox**：Linux seccomp-bpf系统调用过滤，非Linux自动降级到SubprocessSandbox
- **ViolationType**：6种违规类型（BLOCKED_COMMAND/BLOCKED_PATH/RESOURCE_EXCEEDED/UNSAFE_SYSCALL/NETWORK_ACCESS/UNKNOWN）

## 分布式执行

- **LocalBackend**：单进程asyncio实现，零依赖
- **RayBackend**：多节点Ray实现，Ray不可用时自动降级到LocalBackend
- **延迟装饰器**：`@ray.remote`在模块级别不执行，延迟到`_get_ray_worker_class()`函数内

## 流式输出

纯终端TUI流式输出，**无SSE/WebSocket/HTTP**：

- **StreamingEvent**：11种事件类型（THINK_START/THINK_TOKEN/THINK_END/EXEC_START/EXEC_TOKEN/EXEC_END/TOOL_CALL/TOOL_RESULT/ERROR/DONE/META）
- **StreamEmitter**：缓冲发射器+统计追踪
- **StreamingChat**：高级流式聊天接口（支持provider.stream_chat和provider.chat降级）
- **StreamBuffer**：线程安全缓冲区，TUI消费端

## 测试

241个测试全部PASSED：

| 测试文件 | 用例数 | 覆盖范围 |
|---------|--------|---------|
| test_multi_agent_integration.py | 27 | 多Agent集成 |
| test_phase7_hardening.py | 19 | 健壮性增强 |
| test_phase8_e2e.py | 16 | 端到端 |
| test_unified_task_and_model_router.py | 39 | 统一任务+模型路由 |
| test_streaming_and_dashboard.py | 24 | 流式+仪表板 |
| test_sandbox_and_distributed.py | 30 | 沙箱+分布式 |
| test_runtime_integration.py | 11 | 运行时集成 |
| test_self_evolution_closed_loop.py | 13 | 自我进化闭环 |
| test_streaming_e2e.py | 10 | 流式端到端 |
| test_phase11_self_modify.py | 30 | 修改链+自主等级+自修改管道 |
| test_phase12_13_experience_model.py | 22 | 经验库+模型自选 |

运行测试：

```bash
python -m pytest tests/unit/ -v
```

## 已修复的16个漏洞

### 业务逻辑一致性（4个）
- `main.py`：cycles_remaining偏移修复、运算符优先级修复
- `agent.py`：assert→raise ValueError
- `executor.py`：死循环超时修复

### 代码逻辑安全性（6个）
- `execute_code.py`：命令注入/路径检查/工作区校验
- `file_operations.py`：KeyError修复
- `plugin_todo_queue.py`：线程安全
- `database.py`：SQLite线程安全
- `patcher.py`：路径遍历

### 数据流向正确性（5个）
- `long_term.py`：摘要重置修复
- `message_history.py`：遍历删除修复
- `self_develop.py`：事件索引修复
- `orchestrator.py`：进程重启竞争

### V2循环导入（1个）
- `ability/base.py`→`planning/schema.py`循环导入

## 项目统计

- 代码文件：215+ Python文件
- 代码行数：32,000+行
- 测试用例：241个（全部PASSED）
- 治理模块：11个文件
- 内置模型：9个Spec + 3个别名
- 中文化：93+条翻译

## 开发路线图

| Phase | 状态 | 描述 |
|-------|------|------|
| 1-3 | 已完成 | V1/V2架构合并+适配器 |
| 4.2 | 已完成 | SelfThink自进化闭环 |
| 4.3+5.3 | 已完成 | TUI观测窗 |
| 5 | 已完成 | Multi-Agent+通信总线 |
| 6-8 | 已完成 | 集成+运行时打通 |
| 9-10 | 已完成 | 收敛+CLI增强 |
| 11 | 已完成 | 代码自修改管道+修改日志链+自主等级 |
| 12 | 已完成 | 经验库+模型自选 |
| 13 | 已完成 | 策略自生成集成 |
| 14 | 规划中 | Agent自主创建子Agent |
| 15 | 规划中 | 跨项目经验迁移 |
| 16 | 规划中 | Agent自搭CI/CD |
| 17 | 规划中 | Agent自训练专属模型 |
| 18 | 规划中 | Agent重写自身架构 |
| 19 | 规划中 | 群体智能 |
| 20 | 规划中 | L5完全自治 |
