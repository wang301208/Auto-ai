# Configuration Reference

The terminal runtime reads configuration from `config.yaml` or JSON.

Set a path with:

```powershell
$env:LOCAL_AGENT_CONFIG_PATH="G:\path\config.yaml"
```

`DUAL_RING_CONFIG_PATH` is also supported for compatibility.

## Minimal `config.yaml`

```yaml
root_path: .dual_ring_runtime
model:
  provider: openai
  name: gpt-4o-mini
providers:
  openai:
    base_url: https://api.openai.com/v1
    api_key_env: OPENAI_API_KEY
adapters:
  remote_llm:
    enabled: true
    dry_run: false
    api_key_env: OPENAI_API_KEY
    base_url: https://api.openai.com/v1
    model: gpt-4o-mini
```

Secrets belong in `.env` beside the config file:

```env
OPENAI_API_KEY=sk-...
```

## Providers

Supported provider presets:

- `openai`
- `openrouter`
- `anthropic`
- `deepseek`
- `nous`
- `openai_compatible`
- `custom`

Use:

```powershell
local-agent providers
local-agent model openrouter:openai/gpt-4o-mini
```

## Model Setup

```powershell
local-agent setup --provider openai --model gpt-4o-mini --api-key sk-...
local-agent setup --provider openrouter --model openai/gpt-4o-mini --api-key $env:OPENROUTER_API_KEY
local-agent setup --provider custom --model my-model --base-url https://llm.example/v1 --api-key-env CUSTOM_API_KEY
```

## Runtime Options

- `root_path`: runtime state directory
- `managed_paths.skill_library`: published skills
- `managed_paths.algorithm_library`: algorithm manifests
- `managed_paths.algorithm_experiments`: experiment reports
- `managed_paths.workspace`: runtime workspace
- `security_defaults.network`: allow network use
- `security_defaults.shell`: allow shell use
- `security_defaults.filesystem.read/write`: filesystem policy
- `security_defaults.environment.allow/request`: environment variable policy

## Adapter Options

- `adapters.remote_llm.enabled`
- `adapters.remote_llm.dry_run`
- `adapters.remote_llm.api_key_env`
- `adapters.remote_llm.base_url`
- `adapters.remote_llm.model`
- `adapters.remote_llm.timeout`
- `adapters.remote_llm.temperature`
- `adapters.remote_llm.max_tokens`
- `adapters.ollama.base_url`
- `adapters.whisper.executable`
- `adapters.xtts.executable`

## Diagnostics

```powershell
local-agent doctor
local-agent model
```
