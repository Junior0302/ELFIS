#Requires -Version 5.1
<#
.SYNOPSIS
  Arrêt propre ELFIS Developer Launcher - tue les PIDs suivis et libère 8000/5173.
#>
[CmdletBinding()]
param(
  [switch]$Quiet,
  [int]$BackendPort = 8000,
  [int]$FrontendPort = 5173
)

$ErrorActionPreference = "Continue"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$RuntimeDir = Join-Path $Root ".elfis-dev"
$PidFile = Join-Path $RuntimeDir "pids.json"

function Write-Stop([string]$Msg, [string]$Status = "INFO") {
  if ($Quiet -and $Status -eq "INFO") { return }
  $color = switch ($Status) {
    "OK" { "Green" }
    "WARN" { "Yellow" }
    "FAIL" { "Red" }
    default { "Gray" }
  }
  Write-Host ("  [{0}] {1}" -f $Status.PadRight(4), $Msg) -ForegroundColor $color
}

function Stop-Tree([int]$ProcessId) {
  if ($ProcessId -le 0) { return }
  try {
    $proc = Get-Process -Id $ProcessId -ErrorAction SilentlyContinue
    if (-not $proc) { return }
    # Tue l'arbre (npm -> node, uvicorn reloader -> worker)
    & taskkill.exe /PID $ProcessId /T /F 2>$null | Out-Null
    Write-Stop "Processus $ProcessId arrêté" "OK"
  } catch {
    Write-Stop "Impossible d'arrêter PID $ProcessId : $($_.Exception.Message)" "WARN"
  }
}

function Stop-PortListeners([int]$Port) {
  $pids = @()
  try {
    $conns = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
    foreach ($c in $conns) {
      if ($c.OwningProcess) { $pids += [int]$c.OwningProcess }
    }
  } catch { }
  $pids = $pids | Select-Object -Unique
  foreach ($procId in $pids) {
    Write-Stop "Liberation port $Port (PID $procId)" "INFO"
    Stop-Tree $procId
  }
}

if (-not $Quiet) {
  Write-Host ""
  Write-Host "  ELFIS - arrêt des services de développement" -ForegroundColor Cyan
  Write-Host ""
}

if (Test-Path $PidFile) {
  try {
    $data = Get-Content $PidFile -Raw | ConvertFrom-Json
    if ($data.backend_pid) { Stop-Tree ([int]$data.backend_pid) }
    if ($data.frontend_pid) { Stop-Tree ([int]$data.frontend_pid) }
    if ($data.backend_port) { $BackendPort = [int]$data.backend_port }
    if ($data.frontend_port) { $FrontendPort = [int]$data.frontend_port }
  } catch {
    Write-Stop "Lecture pids.json échouée : $($_.Exception.Message)" "WARN"
  }
  Remove-Item $PidFile -Force -ErrorAction SilentlyContinue
} else {
  Write-Stop "Aucun pids.json - nettoyage des ports uniquement" "WARN"
}

Start-Sleep -Milliseconds 400
Stop-PortListeners $BackendPort
Stop-PortListeners $FrontendPort

# Filet de sécurité : processus uvicorn/vite orphelins liés au repo
try {
  Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
    Where-Object {
      $_.CommandLine -and (
        ($_.CommandLine -like "*uvicorn*app.main:app*" -and $_.CommandLine -like "*$BackendPort*") -or
        ($_.CommandLine -like "*vite*" -and $_.CommandLine -like "*$FrontendPort*")
      )
    } |
    ForEach-Object {
      Write-Stop "Orphelin détecté PID $($_.ProcessId)" "WARN"
      Stop-Tree ([int]$_.ProcessId)
    }
} catch { }

Write-Stop "Ports $BackendPort / $FrontendPort libérés (si libres)." "OK"
if (-not $Quiet) { Write-Host "" }
exit 0
