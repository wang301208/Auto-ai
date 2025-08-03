## Plugins

⚠️💀 **WARNING** 💀⚠️: Review the code of any plugin you use thoroughly, as plugins can execute any Python code, potentially leading to malicious activities, such as stealing your API keys.

To configure plugins, you can create or edit the `plugins_config.yaml` file in the root directory of Auto-GPT. This file allows you to enable or disable plugins as desired. For specific configuration instructions, please refer to the documentation provided for each plugin. The file should be formatted in YAML. Here is an example for your reference:

```yaml
plugin_a:
  config:
    api_key: my-api-key
  enabled: false
plugin_b:
  config: {}
  enabled: true
```

See our [Plugins Repo](https://github.com/Significant-Gravitas/Auto-GPT-Plugins) for more info on how to install all the amazing plugins the community has built!

Alternatively, developers can use the [Auto-GPT Plugin Template](https://github.com/Significant-Gravitas/Auto-GPT-Plugin-Template) as a starting point for creating your own plugins.

### Automatically filling plugin gaps

When the agent encounters a command that returns the special result `NEED_TOOL` (or
repeated errors) the `PluginTodoQueue` increments a counter for that command. After
three consecutive failures the counter is reset, the missing capability is written
to a persistent TODO queue and a `plugin_gap` event is fired on the event bus. This
mechanism lets you capture functionality that Auto‑GPT needed but could not
complete.

#### Generating plugins from gaps

1. Inspect the queue file (for example `todo_queue.json`) or subscribe to the
   event bus to discover reported gaps.
2. Create a specification for the new tool under `plugins/stubs/` as
   `<name>.spec.json`:

   ```json
   {
     "name": "sample",
     "description": "sample plugin"
   }
   ```

3. Turn the specs into Python modules by running:

   ```bash
   python scripts/generate_plugins.py
   ```

   If `OPENAI_API_KEY` is set the script will ask the API to implement the
   plugin, otherwise it writes a simple stub.
4. Reload the plugin registry by restarting Auto‑GPT (or calling
   `scan_plugins`), which regenerates `plugin_registry.json` and activates the
   generated plugin.

#### Enabling the queue

To start capturing plugin gaps, instantiate the queue and pass it to your agent:

```python
from autogpt.event_bus import EventBus
from autogpt.self_improve import PluginTodoQueue
from autogpt.agents import Agent

event_bus = EventBus("events.db")
plugin_queue = PluginTodoQueue("todo_queue.json", event_bus)
agent = Agent(..., plugin_queue=plugin_queue)
```

With this configuration, every repeated `NEED_TOOL` failure queues a todo item and
emits a `plugin_gap` event, enabling an iterative plugin generation pipeline.

