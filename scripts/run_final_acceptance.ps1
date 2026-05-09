param(
    [string]$ConfigPath = "configs/local_autonomous_runtime.example.json",
    [int]$StressCycles = 10
)

$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $RepoRoot

$ResolvedConfigPath = (Resolve-Path -LiteralPath (Join-Path $RepoRoot $ConfigPath)).Path
$env:DUAL_RING_CONFIG_PATH = $ResolvedConfigPath

$env:DUAL_RING_STRESS_CYCLES = [string]$StressCycles

@"
import os
from dual_ring_ai.runtime.local_runtime import LocalRuntime

runtime = LocalRuntime.from_config_file(os.environ["DUAL_RING_CONFIG_PATH"])
runtime.start()
stress_cycles = int(os.environ["DUAL_RING_STRESS_CYCLES"])
report_path = runtime.write_final_acceptance_report(
    stress_cycles=stress_cycles,
)
print(f"Final acceptance report: {report_path}")
runtime.stop()
"@ | python -
