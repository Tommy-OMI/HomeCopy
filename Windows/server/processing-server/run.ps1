param(
  [string]$Command = "health",
  [string]$Config = "D:\OMI\config\processing-server.yaml",
  [switch]$Json,
  [switch]$DryRun
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Push-Location $root
try {
  py -m pip install -e . | Out-Host

  $argsList = @($Command)
  if ($Command -ne "health") {
    $argsList += @("--config", $Config)
  }
  if ($Json) {
    $argsList += "--json"
  }
  if ($DryRun) {
    $argsList += "--dry-run"
  }

  omi-processing @argsList
}
finally {
  Pop-Location
}

