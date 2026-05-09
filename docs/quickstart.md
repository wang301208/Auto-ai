# Quickstart

## Two-minute path

From the project root:

```powershell
python -m pip install -e .
cd ui-tui
npm install
npm run build
cd ..
local-agent setup --provider openai --model gpt-4o-mini --api-key $env:OPENAI_API_KEY
local-agent
```

Type your first message at the `>` prompt. The terminal UI talks directly to the Python gateway over stdin/stdout JSON-RPC.

## First conversation

Useful first prompts:

```text
检查运行状态
show adapter health
parallel agents tasks=[{"method":"runtime.adapters"},{"method":"governance.requests"}]
```

Attach project context with `@path`:

```text
Summarize this file @docs/configuration-reference.md
```

## CLI Commands

```powershell
local-agent setup --provider openai --model gpt-4o-mini --api-key sk-...
local-agent model openrouter:openai/gpt-4o-mini
local-agent providers
local-agent doctor
local-agent
local-agent tui
```

`doctor` checks the runtime, model configuration, and readiness gates.

## TUI Commands

Inside the terminal UI:

```text
/help
/status
/tools
/model
/personality concise operator
/save
/resume
/compact
/quit
```

## Hotkeys

- `Enter`: submit
- `Shift+Enter` or `Alt+Enter`: new line
- `Tab`: apply completion
- `Up/Down`: history or completion selection
- `Ctrl+C`: interrupt, clear input, or exit
- `Ctrl+D`: exit
- `Ctrl+L`: clear transcript
