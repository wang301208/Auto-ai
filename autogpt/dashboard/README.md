# AutoGPT Dashboard

This simple Flask application subscribes to the shared `MessageQueue` and
presents a live view of issue‑related events.

## Running

```bash
python -m autogpt.dashboard.app
```

The dashboard listens on `http://localhost:8000/` by default. If the environment
variable `DASHBOARD_TOKEN` is set (or a token is passed to `run_dashboard`), the
same value must be supplied as a query parameter or `X-Dashboard-Token` header
when accessing the dashboard.

## Features

- Streams events such as `ISSUE_DETECTED`, `DIAGNOSIS_COMPLETE`,
  `CODE_FIX_PROPOSED`, `HUMAN_APPROVAL_REQUIRED`, and `ISSUE_RESOLVED`.
- Displays the latest state, timestamp, and source agent information for each
  issue.
- Exposes an `/issues` endpoint with the aggregated per‑issue state.
