param(
    [string]$ConfigPath = "configs/local_autonomous_runtime.example.json"
)

$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $RepoRoot

$ResolvedConfigPath = (Resolve-Path -LiteralPath (Join-Path $RepoRoot $ConfigPath)).Path
$env:DUAL_RING_CONFIG_PATH = $ResolvedConfigPath

@"
import os
from dual_ring_ai.runtime.local_runtime import LocalRuntime

runtime = LocalRuntime.from_config_file(os.environ["DUAL_RING_CONFIG_PATH"])
report_path = runtime.write_host_integration_probe()
print(f"Host integration probe: {report_path}")
"@ | python -
