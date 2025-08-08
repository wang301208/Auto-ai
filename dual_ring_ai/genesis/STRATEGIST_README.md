# 策略师代理 (Strategist Agent) - 大脑的大脑

## 概述

策略师代理是一个元认知（Metacognition）代理，专门负责观察、反思和优化整个系统解决问题的"方法论"。它不参与任何具体任务的执行，而是专注于系统级别的战略优化。

## 核心功能

### 1. 观察与数据收集 (Observation & Data Collection)

策略师代理订阅事件总线上的所有关键事件：

- **任务开始事件**: 记录执行者收到的原始目标
- **计划生成事件**: 记录执行者为该目标制定的完整技能组合计划
- **任务结果事件**: 记录任务是成功、失败，以及执行的效率（耗时、API调用成本）
- **创世纪工单事件**: 记录任务失败是否由工具缺陷引起

它会将这些 (目标 -> 计划 -> 结果 -> 原因) 的数据对，作为一个个"战略案例"存入自己的知识库中。

### 2. 分析与复盘 (Analysis & Review)

在系统空闲时，策略师会启动它的核心分析引擎：

- **模式识别和聚类分析**: 对成百上千个"战略案例"进行模式识别
- **失败原因分析**: 识别常见的失败模式和原因
- **效率分析**: 分析执行时间和成本效益
- **技能组合分析**: 评估不同技能组合的成功率

### 3. 策略的"进化"与"演化" (Strategy Evolution & Generalization)

基于分析结果，策略师会提炼出新的、更优的"战略原则"或"启发式规则 (Heuristics)"：

**示例原则**:
- **原则#1（进化）**: "当一个网页抓取技能失败后，下一次重试时不应简单重复，而应切换到另一个备用的抓取插件"
- **原则#2（演化）**: "所有涉及写入文件的任务，在其计划的最后一步，都必须自动加入一个'文件内容校验'技能，以确保数据完整性"

### 4. 影响与赋能 (Influence & Empowerment)

策略师代理通过更新"执行者"代理的系统提示来应用战略原则：

**原始系统提示**:
```
你是一个AI助手，请为用户的目标制定一个计划。
```

**优化后的系统提示**:
```
你是一个AI助手，请为用户的目标制定一个计划。

在制定任何计划前，必须遵循以下战略原则：
1. 抓取失败后必须切换工具重试
2. 文件写入后必须进行校验
3. 数据分析任务优先进行数据清洗
...
```

## 架构设计

### 核心组件

1. **StrategicCase**: 战略案例 - 记录一个完整的任务执行周期
2. **StrategicPrinciple**: 战略原则 - 从案例分析中提炼出的指导方针
3. **StrategistAgent**: 策略师代理 - 元认知大脑
4. **StrategistMonitor**: 策略师监控组件 - 提供实时监控和可视化

### 数据流

```
事件总线 → 策略师代理 → 知识库 → 分析引擎 → 战略原则 → 系统优化
```

### 知识库结构

- **strategic_cases**: 存储所有战略案例
- **strategic_principles**: 存储提炼的战略原则
- **实时统计**: 成功率、平均执行时间、平均成本等

## 配置选项

```yaml
strategist:
  # 分析间隔（秒）
  analysis_interval: 3600
  
  # 最少案例数才开始分析
  min_cases_for_analysis: 10
  
  # 置信度阈值
  confidence_threshold: 0.7
  
  # 最大原则数量
  max_principles: 20
  
  # 数据库路径
  database_path: "strategist_knowledge.db"
  
  # 启用自动优化
  enable_auto_optimization: true
```

## 使用方法

### 1. 基本使用

```python
from dual_ring_ai.core.event_bus import EventBus
from dual_ring_ai.genesis.strategist import StrategistAgent, DEFAULT_STRATEGIST_CONFIG

# 初始化事件总线
event_bus = EventBus()
event_bus.connect()

# 初始化策略师代理
strategist = StrategistAgent(event_bus, DEFAULT_STRATEGIST_CONFIG)
strategist.start()

# 策略师会自动开始观察和分析
```

### 2. 监控策略师

```python
from dual_ring_ai.dashboard.strategist_monitor import StrategistMonitor

# 初始化监控组件
monitor = StrategistMonitor(event_bus, strategist)
monitor.start_monitoring()

# 获取战略仪表板
dashboard = monitor.get_strategic_dashboard()
print(f"成功率: {dashboard['overview']['success_rate']}")
print(f"平均执行时间: {dashboard['overview']['avg_execution_time']}")

# 获取性能报告
report = monitor.get_performance_report()
for rec in report['recommendations']:
    print(f"建议: {rec}")
```

### 3. 测试策略师

```python
# 运行测试脚本
python dual_ring_ai/test_strategist.py
```

## 监控指标

### 关键指标

1. **成功率**: 任务成功完成的比例
2. **平均执行时间**: 任务的平均执行时间
3. **平均成本**: 任务的平均API调用成本
4. **原则数量**: 已提炼的战略原则数量
5. **置信度分布**: 原则的置信度分布（高/中/低）

### 洞察报告

- **失败原因分析**: 最常见的失败原因和频率
- **效率建议**: 基于执行时间和成本的优化建议
- **技能组合分析**: 最有效的技能组合模式
- **趋势分析**: 系统性能的变化趋势

## 事件类型

### 订阅的事件

- `TASK_PLANNED`: 任务计划事件
- `EXECUTION_COMPLETED`: 执行完成事件
- `EXECUTION_FAILED`: 执行失败事件
- `ISSUE_DETECTED`: 问题检测事件
- `ISSUE_RESOLVED`: 问题解决事件

### 发布的事件

- `SYSTEM_OPTIMIZATION`: 系统优化事件
- `STRATEGIC_ANALYSIS_COMPLETED`: 战略分析完成事件
- `PRINCIPLE_EXTRACTED`: 原则提取事件
- `KNOWLEDGE_UPDATED`: 知识库更新事件

## 最佳实践

### 1. 配置建议

- **分析间隔**: 根据系统负载调整，建议1-4小时
- **最小案例数**: 建议10-20个案例开始分析
- **置信度阈值**: 建议0.7-0.8，确保原则质量

### 2. 监控建议

- 定期检查成功率趋势
- 关注失败原因的分布变化
- 监控原则的置信度变化
- 导出知识库进行备份

### 3. 优化建议

- 根据失败模式调整技能组合
- 基于效率分析优化执行策略
- 定期清理低置信度的原则
- 监控系统性能的改善效果

## 故障排除

### 常见问题

1. **策略师不启动分析**
   - 检查案例数量是否达到最小阈值
   - 确认事件总线连接正常
   - 检查日志中的错误信息

2. **原则置信度过低**
   - 增加案例数量
   - 调整置信度阈值
   - 检查案例质量

3. **系统优化不生效**
   - 确认自动优化已启用
   - 检查原则数量是否足够
   - 验证执行者是否正确接收优化事件

### 调试方法

```python
# 获取策略师状态
knowledge_summary = strategist.get_knowledge_summary()
print(f"案例数: {knowledge_summary['cases_count']}")
print(f"原则数: {knowledge_summary['principles_count']}")

# 获取详细洞察
insights = strategist.get_strategic_insights()
print(f"成功率: {insights.get('success_rate', 0):.2%}")

# 导出知识库进行调试
monitor.export_knowledge_base("debug_export.json")
```

## 扩展功能

### 自定义分析器

可以扩展策略师的分析能力：

```python
class CustomAnalyzer:
    def analyze_custom_pattern(self, cases):
        # 自定义分析逻辑
        pass

# 在策略师中集成
strategist.add_analyzer(CustomAnalyzer())
```

### 自定义原则提取器

可以添加自定义的原则提取逻辑：

```python
class CustomPrincipleExtractor:
    def extract_custom_principles(self, patterns):
        # 自定义原则提取逻辑
        pass

# 在策略师中集成
strategist.add_principle_extractor(CustomPrincipleExtractor())
```

## 总结

策略师代理作为系统的"大脑的大脑"，通过持续的观察、分析和优化，不断提升整个系统的智能水平和执行效率。它不直接参与任务执行，而是通过影响其他代理的决策过程来实现系统级别的优化。

这种元认知设计使得系统具备了自我改进的能力，能够从经验中学习，并不断优化自己的问题解决方法论。
