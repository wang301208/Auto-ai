# Agents

## ArchaeologistAgent

`ArchaeologistAgent` is an event‑driven diagnostic helper that assists plugin
authors in understanding runtime failures. The agent listens for
`ISSUE_DETECTED` events on Auto‑GPT's event bus. When triggered it performs a
series of git and dependency checks and finally publishes a
`DIAGNOSIS_COMPLETE` event summarising its findings.

### Workflow

1. **Subscribe** – On initialisation the agent subscribes to
   `ISSUE_DETECTED` events on the shared `MessageQueue`.
2. **Collect context** – When an event is received the agent extracts metadata
   such as the affected file, line number and commit hash from the payload or
   the provided error log.
3. **Analyse the repository** – The agent may temporarily check out the
   referenced commit, run `git blame` on the file and scan the file for import
   statements to gather dependency information.
4. **Generate recommendations** – The results are condensed into a summary and
   simple actionable advice.
5. **Publish results** – A `DIAGNOSIS_COMPLETE` event is emitted so other
   components can surface the diagnostics to users or additional tools.

### Event bus and tool requirements

```python
from autogpt.event_bus import EventMessage, MessageQueue
from autogpt.agents import Archaeologist, ISSUE_DETECTED

message_queue = MessageQueue()
archaeologist = Archaeologist(message_queue)
```

To receive the agent's output, subscribe to `DIAGNOSIS_COMPLETE` events:

```python
from autogpt.agents import DIAGNOSIS_COMPLETE

message_queue.subscribe(DIAGNOSIS_COMPLETE, handle_diagnostics)
```

The agent requires the following tools to operate:

- **Git** – used for `git checkout` and `git blame` operations.
- **Python's `requests` package`** – used to fetch dependency release notes
  from PyPI.
- **Network access** – needed to retrieve package information.

Ensure these dependencies are installed and accessible to the runtime
environment where the agent executes.

### Example flow

A plugin encounters an exception and publishes an `ISSUE_DETECTED` event:

```python
message_queue.publish(
    EventMessage(
        ISSUE_DETECTED,
        payload={
            "plugin": "example-plugin",
            "error_log": 'File "example.py", line 10, in <module>\nImportError',
        },
    )
)
```

`ArchaeologistAgent` receives the event, extracts the file and line number from
`error_log`, runs `git blame` and inspects the file's imports. It then emits a
`DIAGNOSIS_COMPLETE` event containing a summary and recommendations:

```text
Diagnostics for plugin example-plugin at example.py:10
Investigate compatibility issues in: some_dependency
```

Other components subscribed to `DIAGNOSIS_COMPLETE` can display the message to
users or log it for further analysis.

