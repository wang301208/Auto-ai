# Organizational Self-Evolution (Org-Evo)

This repository extension introduces four components to enable GitOps-driven organizational evolution:

- Organizational Charter: A Git repo of YAML agent blueprints
- Founder Agent: Periodically analyzes system metrics and proposes charter changes
- Dynamic Orchestrator: Loads agents by reading charter blueprints with hot reloads
- Architect Cockpit: Minimal Flask UI to approve or reject proposals

## Agent Blueprint YAML

Each agent is defined by a YAML file, e.g. `tdd_developer.yaml`:

```yaml
role_name: "TDD_Developer"
version: "1.0"
core_prompt: |
  你是一个纪律严明的程序员，严格遵循测试驱动开发（TDD）原则。
  你的任务是根据诊断报告，先编写失败的测试，再编写功能代码让测试通过。
  你被授权使用代码执行、文件读写和Git操作插件。

agent_class: "dual_ring_ai.genesis.tdd_developer.TDDDeveloperAgent"

authorized_plugins:
  - "Plugin_Git"
  - "Plugin_FileIO"
  - "Plugin_PytestRunner"
  - "Plugin_CodeExecutor"

subscribed_events:
  - "DIAGNOSIS_COMPLETE"
  - "REFACTORING_REQUESTED"

config:
  workspace_path: "workspace/tdd"
```

## Components

- Blueprint loader: `autogpt/blueprints/schema.py`
- Orchestrator: `autogpt/orchestrator_blueprint.py`
- Founder agent: `autogpt/agents/founder.py`
- Architect UI: `autogpt/dashboard/app_architect.py`

## Quickstart

1. Create a Git repo (e.g. on GitHub) named `organizational_charter` and add YAML blueprints.
2. Run the orchestrator:

```bash
python -m autogpt.orchestrator_blueprint --not-a-real-cli
```

(Import and construct `BlueprintOrchestrator(charter_git_url, local_path)` in your launcher.)

3. Start the Architect UI:

```bash
python -m autogpt.dashboard.app_architect
```

4. Start the Founder agent (provide message queue and repo URL via code):

```python
from autogpt.event_bus import EventBus, MessageQueue
from autogpt.agents.founder import FounderAgent, FounderConfig

bus = EventBus("events.db")
queue = MessageQueue(bus)
founder = FounderAgent(queue, FounderConfig(charter_repo_url="<git url>"))
founder.start()
```

The Founder will emit `HUMAN_ARCHITECT_APPROVAL_REQUIRED` with a proposal branch; review and merge via your normal Git workflow or extend the UI to auto-merge on approval.


