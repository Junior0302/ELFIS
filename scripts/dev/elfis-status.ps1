#Requires -Version 5.1
<#
.SYNOPSIS
  Affiche le statut des services ELFIS (ports + pids.json + health).
#>
[CmdletBinding()]
param(
  [int]$BackendPort = 8000,
  [int]$FrontendPort = 5173
)

$Root = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$PidFile = Join-Path $Root ".elfis-dev\pids.json"

function Port-Up([int]$Port) {
  return [bool](Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue)
}

function Probe([string]$Url) {
  try {
    $r = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 3
    return "$($r.StatusCode)"
  } catch {
    if ($_.Exception.Response) { return "$([int]$_.Exception.Response.StatusCode)" }
    return "DOWN"
  }
}

Write-Host ""
Write-Host "  ELFIS DEV STATUS" -ForegroundColor Cyan
Write-Host "  ----------------"
if (Test-Path $PidFile) {
  $d = Get-Content $PidFile -Raw | ConvertFrom-Json
  Write-Host "  Started : $($d.started_at)"
  Write-Host "  Backend PID : $($d.backend_pid)  Frontend PID : $($d.frontend_pid)"
} else {
  Write-Host "  (pas de session launcher active - pids.json absent)"
}
Write-Host ("  Port {0} : {1}" -f $BackendPort, $(if (Port-Up $BackendPort) { "LISTEN" } else { "closed" }))
Write-Host ("  Port {0} : {1}" -f $FrontendPort, $(if (Port-Up $FrontendPort) { "LISTEN" } else { "closed" }))
Write-Host ("  /api/health        : {0}" -f (Probe "http://127.0.0.1:$BackendPort/api/health"))
Write-Host ("  proxy /api/health  : {0}" -f (Probe "http://localhost:$FrontendPort/api/health"))
Write-Host ("  App               : http://localhost:$FrontendPort")
Write-Host ("  Cockpit Admin     : http://localhost:$FrontendPort/elfadmin")
Write-Host ""
