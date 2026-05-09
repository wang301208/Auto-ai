param(
    [string]$ConfigPath = "configs/local_autonomous_runtime.example.json"
)

$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $RepoRoot

$Config = Get-Content -LiteralPath (Join-Path $RepoRoot $ConfigPath) -Raw | ConvertFrom-Json
$RuntimeRoot = Join-Path $RepoRoot $Config.root_path
$env:DUAL_RING_RUNTIME_ROOT = $RuntimeRoot
$env:DUAL_RING_CONFIG_PATH = (Resolve-Path -LiteralPath (Join-Path $RepoRoot $ConfigPath)).Path

@"
import os
from dual_ring_ai.runtime.local_runtime import LocalRuntime

runtime = LocalRuntime.from_config_file(os.environ["DUAL_RING_CONFIG_PATH"])
runtime.start()
snapshot = runtime.status_snapshot()
preflight_path = runtime.write_preflight_report()
print("LocalRuntimeConfig loaded")
print(snapshot)
print(f"Preflight report: {preflight_path}")
runtime.stop()
"@ | python -
