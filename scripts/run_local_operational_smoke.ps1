param(
    [string]$ConfigPath = "configs/local_autonomous_runtime.example.json",
    [int]$Cycles = 2
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
runtime.start()
report_path = runtime.write_operational_smoke_report(cycles=$Cycles)
print(f"Operational smoke report: {report_path}")
runtime.stop()
"@ | python -
