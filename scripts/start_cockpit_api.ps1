param(
    [string]$ConfigPath = "configs/local_autonomous_runtime.example.json",
    [string]$HostName = "",
    [int]$Port = 0
)

$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $RepoRoot

$Config = Get-Content -LiteralPath (Join-Path $RepoRoot $ConfigPath) -Raw | ConvertFrom-Json
$RuntimeRoot = Join-Path $RepoRoot $Config.root_path
$env:DUAL_RING_RUNTIME_ROOT = $RuntimeRoot
$env:DUAL_RING_CONFIG_PATH = (Resolve-Path -LiteralPath (Join-Path $RepoRoot $ConfigPath)).Path

if ([string]::IsNullOrWhiteSpace($HostName)) {
    $HostName = $Config.cockpit.host
}
if ($Port -eq 0) {
    $Port = [int]$Config.cockpit.port
}

python -m uvicorn dual_ring_ai.dashboard.cockpit_server:app --host $HostName --port $Port
