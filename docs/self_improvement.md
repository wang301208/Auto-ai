# 自我改进循环

自我改进模块会将异常、执行时间和结果记录到位于 `improvement.db` 的 SQLite 数据库中。
通过 `install_exception_logger` 可启用异常记录器，并使用 `Profiler` 包裹耗时操作。

## 自我开发模式

`SelfDevelopManager` 在后台线程运行，定期检查仓库中的问题。它会从插件的 TODO 队列、事件日志和性能数据中收集信号，然后利用基于 LLM 的补丁生成器提出代码变更。生成的 diff 由 `PatchAgent` 应用，并通过 `black`、`ruff`、`mypy` 和 `pytest -q` 验证。验证结果会写入改进数据库，并发送事件用于监控。

通过设置环境变量 `SELF_DEVELOP=True` 可以启用该循环，`SELF_DEVELOP_INTERVAL` 控制检查仓库的间隔时间（单位：秒），默认值分别为禁用与 300 秒。

```bash
export SELF_DEVELOP=True
export SELF_DEVELOP_INTERVAL=300  # 可选：每 300 秒扫描一次仓库
```

可以通过 JSON 文件动态叠加配置。该叠加层允许在运行时调整 OpenAI temperature、搜索深度或切换插件。

示例 `overlay.json`：

```json
{
  "temperature": 0.7,
  "search_depth": 3,
  "plugins": ["my-plugin"]
}
```

将此文件传递给你的代理以自定义行为：

```python
from pathlib import Path
from autogpt.config import ConfigBuilder

# 从当前路径读取环境变量并构建配置
config = ConfigBuilder.build_config_from_env(Path.cwd())
# 应用 overlay.json 中的覆盖配置
config.apply_overlay("overlay.json")
```

Critic-Agent 会生成 Markdown 或 JSON 报告，总结错误和性能数据。
Patch-Agent 可以应用 unified diff，并运行 `black`、`ruff` 和 `mypy` 来确保补丁有效。
当系统中存在 `patch` 命令时优先使用；若缺失则回退到 Python 库 [`patch-ng`](https://pypi.org/project/patch-ng/)，否则会提示如何安装所需工具。

## 多次失败后暂停

每次补丁尝试都会以 `success` 标志存储在 `patch_attempts` 表中。当连续三次尝试失败时，`PatchAgent` 会在运行进程旁写入名为 `self_improve.pause` 的时间戳文件并阻止进一步应用补丁。删除该文件即可恢复自我改进循环。

[English version](self_improvement.en.md)
