# 双环AI系统 (Dual Ring AI System)

一个基于事件驱动的AI代理系统，包含两个主要环路：
1. **"创世纪"工厂** - 负责自动开发和维护技能
2. **"执行者"驱动** - 负责执行用户任务和技能组合

## 系统架构

### 核心组件

- **事件总线**: 基于Redis的发布/订阅系统
- **知识库**: 插件库和技能库
- **向量数据库**: ChromaDB用于语义搜索
- **监控仪表盘**: 实时可视化系统状态

### 代理系统

#### 创世纪工厂 (Genesis Factory)
- **哨兵代理 (Sentry)**: 监控系统状态，检测问题
- **考古学家代理 (Archaeologist)**: 诊断问题，分析根本原因
- **TDD开发者代理 (TDD Developer)**: 基于诊断结果开发代码修复
- **QA代理 (QA)**: 质量保证和人类审批流程

#### 执行者系统 (Executor System)
- **任务规划器 (Task Planner)**: 将用户目标分解为具体子任务
- **技能组合器 (Skill Composer)**: 为子任务找到合适的技能
- **执行引擎 (Execution Engine)**: 执行技能组合，处理能力缺口

#### 监控系统
- **仪表盘 (Dashboard)**: 实时可视化界面

## 安装和配置

### 依赖项

```bash
pip install redis chromadb sentence-transformers streamlit watchdog requests
```

### 配置Redis

确保Redis服务器正在运行：

```bash
# Ubuntu/Debian
sudo apt-get install redis-server
sudo systemctl start redis-server

# macOS
brew install redis
brew services start redis

# Windows
# 下载并安装Redis for Windows
```

### 配置文件

创建配置文件 `config.json`：

```json
{
  "redis_host": "localhost",
  "redis_port": 6379,
  "redis_db": 0,
  "skill_library_path": "skill_library",
  "plugin_library_path": "plugins",
  "vector_db_path": "vector_db",
  "workspace_path": "workspace",
  "enable_genesis": true,
  "enable_executor": true,
  "enable_dashboard": true
}
```

## 使用方法

### 启动系统

```bash
# 交互模式
python -m dual_ring_ai.main_controller --interactive

# 守护进程模式
python -m dual_ring_ai.main_controller --daemon

# 执行特定目标
python -m dual_ring_ai.main_controller --goal "创建一个Web API"

# 使用配置文件
python -m dual_ring_ai.main_controller --config config.json --interactive
```

### 交互模式命令

```
help                    - 显示帮助信息
status                  - 显示系统状态
execute <goal>          - 执行任务
status <plan_id>        - 查看执行状态
stats                   - 显示系统统计
events                  - 显示最近事件
quit/exit               - 退出系统
```

### 示例任务

```bash
# 执行任务
execute 创建一个数据分析和可视化工具

# 查看执行状态
status plan_20231201_143022

# 查看系统统计
stats
```

## 系统工作流程

### 1. 问题检测 (哨兵代理)
- 监控API端点健康状态
- 监控日志文件变化
- 检查GitHub仓库更新
- 发布 `ISSUE_DETECTED` 事件

### 2. 问题诊断 (考古学家代理)
- 订阅 `ISSUE_DETECTED` 事件
- 分析问题根本原因
- 查找相关技能和插件
- 发布 `DIAGNOSIS_COMPLETE` 事件

### 3. 代码开发 (TDD开发者代理)
- 订阅 `DIAGNOSIS_COMPLETE` 事件
- 生成代码修复
- 运行测试验证
- 发布 `CODE_FIX_PROPOSED` 事件

### 4. 质量保证 (QA代理)
- 订阅 `CODE_FIX_PROPOSED` 事件
- 执行质量检查
- 请求人类审批（如需要）
- 部署修复

### 5. 任务执行 (执行者系统)
- 任务规划器分解用户目标
- 技能组合器找到合适技能
- 执行引擎运行技能组合
- 处理能力缺口

## 技能开发

### 技能结构

```
skill_library/
├── my_skill/
│   ├── main.py          # 主代码文件
│   ├── skill.json       # 技能元数据
│   └── test_main.py     # 测试文件
```

### 技能元数据示例

```json
{
  "skill_name": "data_analyzer",
  "version": "1.0.0",
  "description": "Analyze data and generate insights",
  "tags": ["data", "analysis", "insights"],
  "parameters": {
    "data_path": {
      "type": "string",
      "required": true,
      "description": "Path to the data file"
    },
    "analysis_type": {
      "type": "string",
      "required": false,
      "default": "basic",
      "description": "Type of analysis to perform"
    }
  }
}
```

### 技能代码示例

```python
"""
Data analysis skill
"""

import json
import pandas as pd
from typing import Dict, Any

def main(data_path: str, analysis_type: str = "basic") -> Dict[str, Any]:
    """
    Main function for data analysis skill
    
    Args:
        data_path: Path to the data file
        analysis_type: Type of analysis to perform
    
    Returns:
        Dict[str, Any]: Analysis results
    """
    try:
        # Load data
        df = pd.read_csv(data_path)
        
        # Perform analysis
        if analysis_type == "basic":
            result = {
                "rows": len(df),
                "columns": len(df.columns),
                "missing_values": df.isnull().sum().to_dict(),
                "data_types": df.dtypes.to_dict()
            }
        else:
            result = {
                "summary": df.describe().to_dict(),
                "correlations": df.corr().to_dict()
            }
        
        return {
            "status": "success",
            "result": result,
            "skill_name": "data_analyzer"
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "skill_name": "data_analyzer"
        }

if __name__ == "__main__":
    result = main("data.csv", "basic")
    print(json.dumps(result, indent=2))
```

## 监控和调试

### 仪表盘访问

启动系统后，可以通过以下方式访问监控仪表盘：

1. **Streamlit界面**: 自动启动Web界面
2. **控制台界面**: 在终端显示实时状态

### 日志查看

系统会生成详细的日志信息：

```bash
# 查看系统日志
tail -f logs/dual_ring_ai.log

# 查看特定代理日志
tail -f logs/sentry_agent.log
```

### 事件追踪

所有系统事件都会通过事件总线传递，可以通过仪表盘查看：

```bash
# 查看最近事件
events

# 查看系统统计
stats
```

## 扩展和定制

### 添加新代理

1. 创建代理类
2. 继承基础代理接口
3. 实现事件处理逻辑
4. 在主控制器中注册

### 自定义事件类型

在 `dual_ring_ai/core/event_bus.py` 中添加新的事件类型：

```python
class EventTypes:
    # 添加新事件类型
    CUSTOM_EVENT = "CUSTOM_EVENT"
```

### 配置代理行为

通过修改配置文件来调整代理行为：

```json
{
  "sentry_agent": {
    "api_check_interval": 30,
    "log_patterns": ["*.log", "error.log"]
  },
  "qa_agent": {
    "quality_thresholds": {
      "min_code_quality_score": 0.8,
      "min_test_coverage": 0.9
    }
  }
}
```

## 故障排除

### 常见问题

1. **Redis连接失败**
   - 检查Redis服务是否运行
   - 验证连接参数

2. **技能执行失败**
   - 检查技能代码语法
   - 验证依赖项是否安装
   - 查看技能日志

3. **事件丢失**
   - 检查事件总线连接
   - 验证订阅配置

### 调试模式

启用详细日志：

```bash
export LOG_LEVEL=DEBUG
python -m dual_ring_ai.main_controller --interactive
```

## 贡献指南

1. Fork 项目
2. 创建功能分支
3. 提交更改
4. 推送到分支
5. 创建 Pull Request

## 许可证

本项目采用 MIT 许可证。

## 联系方式

如有问题或建议，请通过以下方式联系：

- 提交 Issue
- 发送邮件
- 参与讨论

---

**双环AI系统** - 让AI代理协同工作，实现智能自动化
