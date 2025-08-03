## 插件

⚠️💀 **警告** 💀⚠️：使用任何插件前请仔细审查其代码，因为插件可以执行任意 Python 代码，可能导致恶意活动，例如窃取你的 API 密钥。

要配置插件，你可以在 Auto-GPT 根目录创建或编辑 `plugins_config.yaml` 文件。该文件允许你根据需要启用或禁用插件。具体配置说明请参阅各插件提供的文档。该文件应以 YAML 格式编写。以下是一个示例：

```yaml
plugin_a:
  config:
    api_key: my-api-key
  enabled: false
plugin_b:
  config: {}
  enabled: true
```

请参阅我们的 [插件仓库](https://github.com/Significant-Gravitas/Auto-GPT-Plugins)，了解如何安装社区构建的所有精彩插件！

或者，开发者可以使用 [Auto-GPT 插件模板](https://github.com/Significant-Gravitas/Auto-GPT-Plugin-Template) 作为创建自己插件的起点。

### 自动填补插件缺口

当代理遇到返回特殊结果 `NEED_TOOL`（或重复错误）的命令时，`PluginTodoQueue` 会为该命令增加计数器。经过三次连续失败后，计数器将被重置，缺失的功能被写入持久化的 TODO 队列，并在事件总线上触发 `plugin_gap` 事件。该机制能捕获 Auto‑GPT 需要但无法完成的功能。

#### 从缺口生成插件

1. 检查队列文件（例如 `todo_queue.json`）或订阅事件总线以发现报告的缺口。
2. 在 `plugins/stubs/` 下为新工具创建规范，命名为 `<name>.spec.json`：

   ```json
   {
     "name": "sample",
     "description": "sample plugin"
   }
   ```

3. 运行以下命令将规范转换为 Python 模块：

   ```bash
   python scripts/generate_plugins.py
   ```

   如果设置了 `OPENAI_API_KEY`，脚本会请求 API 实现插件，否则会写入一个简单的存根。
4. 通过重启 Auto‑GPT（或调用 `scan_plugins`）重新加载插件注册表，这会重新生成 `plugin_registry.json` 并激活生成的插件。

#### 启用队列

要开始捕获插件缺口，实例化队列并将其传递给代理：

```python
from autogpt.event_bus import EventBus
from autogpt.self_improve import PluginTodoQueue
from autogpt.agents import Agent

event_bus = EventBus("events.db")
plugin_queue = PluginTodoQueue("todo_queue.json", event_bus)
agent = Agent(..., plugin_queue=plugin_queue)
```

通过此配置，每次重复的 `NEED_TOOL` 失败都会排入一个待办项并发出 `plugin_gap` 事件，从而启用迭代的插件生成管道。

