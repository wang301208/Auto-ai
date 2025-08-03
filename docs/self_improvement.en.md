# Self Improvement Loop

The self improvement modules record exceptions, execution times and results in a
SQLite database located at `improvement.db`. You can enable the logger via
`install_exception_logger` and wrap costly operations with `Profiler`.

## Self-development mode

`SelfDevelopManager` runs in a background thread and periodically inspects the
repository for issues. It gathers signals from the plugin TODO queue, event logs
and performance data, then uses the LLM based patch generator to propose code
changes. Generated diffs are applied with `PatchAgent` and validated using
`black`, `ruff`, `mypy` and `pytest -q`. Results are written to the improvement
database and an event is emitted for monitoring.

Enable this loop by setting the `SELF_DEVELOP` environment variable to `True`.
The `SELF_DEVELOP_INTERVAL` variable controls how often the repository is
scanned (in seconds). Defaults are disabled and 300 seconds respectively.

Configuration values can be overlaid dynamically using a JSON file. The overlay
supports adjusting OpenAI temperature, search depth or toggling plugins at
runtime.

Example `overlay.json`:

```json
{
  "temperature": 0.7,
  "search_depth": 3,
  "plugins": ["my-plugin"]
}
```

Pass this file to your agent to customize behaviour:

```python
from pathlib import Path
from autogpt.config import ConfigBuilder

config = ConfigBuilder.build_config_from_env(Path.cwd())
config.apply_overlay("overlay.json")
```

The Critic-Agent generates a Markdown or JSON report summarising errors and
profiling data. The Patch-Agent can apply unified diffs and runs `black`,
`ruff` and `mypy` to ensure the patch is valid. It uses the system `patch`
command when available. If `patch` is missing, it falls back to the
[`patch-ng`](https://pypi.org/project/patch-ng/) Python library if installed;
otherwise a clear error explains how to install the required tool.

## Pause after repeated failures

Each patch attempt is stored in the `patch_attempts` table with a `success`
flag. When three attempts fail in a row `PatchAgent` writes a timestamp file
named `self_improve.pause` next to the running process and further patch
application is blocked. Delete this file to resume the self‑improvement loop.
