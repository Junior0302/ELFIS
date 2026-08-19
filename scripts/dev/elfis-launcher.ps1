#Requires -Version 5.1
<#
.SYNOPSIS
  ELFIS Developer Launcher V1 - démarre backend (8000) + frontend (5173).

.PARAMETER Watch
  Reste attaché ; Ctrl+C arrête tous les services.

.PARAMETER Detach
  Démarre, vérifie, affiche le dashboard, ouvre le navigateur, puis quitte
  (services restent actifs - utiliser npm run dev:stop). Défaut si -Watch absent.

.NOTES
  Aucune modification de logique métier - orchestration locale uniquement.
#>
[CmdletBinding()]
param(
  [switch]$Watch,
  [switch]$Detach,
  [switch]$SkipBrowser,
  [switch]$SkipInstall,
  [int]$BackendPort = 8000,
  [int]$FrontendPort = 5173,
  [int]$HealthTimeoutSec = 90
)

$ErrorActionPreference = "Stop"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$BackendDir = Join-Path $Root "backend"
$FrontendDir = Join-Path $Root "frontend"
$RuntimeDir = Join-Path $Root ".elfis-dev"
$PidFile = Join-Path $RuntimeDir "pids.json"
$BackendOut = Join-Path $RuntimeDir "backend.out.log"
$BackendErr = Join-Path $RuntimeDir "backend.err.log"
$FrontendOut = Join-Path $RuntimeDir "frontend.out.log"
$FrontendErr = Join-Path $RuntimeDir "frontend.err.log"
$StopScript = Join-Path $PSScriptRoot "elfis-stop.ps1"

# Par défaut : détaché (idéal pour npm run dev:all)
$StayAttached = [bool]$Watch
if ($Detach) { $StayAttached = $false }

function Write-Banner {
  Write-Host ""
  Write-Host "  ==================================================" -ForegroundColor Cyan
  Write-Host "     ELFIS Core - Developer Launcher V1" -ForegroundColor Cyan
  Write-Host "  ==================================================" -ForegroundColor Cyan
  Write-Host ""
}

function Write-Step([string]$Msg, [string]$Status = "INFO") {
  $color = switch ($Status) {
    "OK" { "Green" }
    "WARN" { "Yellow" }
    "FAIL" { "Red" }
    default { "Gray" }
  }
  Write-Host ("  [{0}] {1}" -f $Status.PadRight(4), $Msg) -ForegroundColor $color
}

function Test-CommandExists([string]$Name) {
  return [bool](Get-Command $Name -ErrorAction SilentlyContinue)
}

function Get-CommandVersion([string]$Name, [string]$ArgLine = "--version") {
  try {
    $argList = $ArgLine -split "\s+"
    $out = & $Name @argList 2>&1 | Out-String
    return ($out -replace "\s+", " ").Trim()
  } catch {
    return "unknown"
  }
}

function Test-PortListening([int]$Port) {
  $conn = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
  return [bool]$conn
}

function Wait-HttpOk([string]$Url, [int]$TimeoutSec, [int[]]$AcceptStatuses = @(200)) {
  $deadline = (Get-Date).AddSeconds($TimeoutSec)
  while ((Get-Date) -lt $deadline) {
    try {
      $resp = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 3
      if ($AcceptStatuses -contains [int]$resp.StatusCode) {
        return @{ Ok = $true; Status = [int]$resp.StatusCode; Body = $resp.Content }
      }
    } catch {
      $respObj = $_.Exception.Response
      if ($respObj) {
        $code = [int]$respObj.StatusCode
        if ($AcceptStatuses -contains $code) {
          return @{ Ok = $true; Status = $code; Body = "" }
        }
      }
    }
    Start-Sleep -Milliseconds 800
  }
  return @{ Ok = $false; Status = 0; Body = "" }
}

function Assert-Prerequisites {
  Write-Host "  -- Prerequisites" -ForegroundColor White
  $ok = $true
  $checks = @(
    @{ Name = "Python"; Cmd = "python"; Args = "--version" },
    @{ Name = "Node.js"; Cmd = "node"; Args = "--version" },
    @{ Name = "npm"; Cmd = "npm"; Args = "--version" },
    @{ Name = "Git"; Cmd = "git"; Args = "--version" }
  )
  foreach ($c in $checks) {
    if (Test-CommandExists $c.Cmd) {
      $ver = Get-CommandVersion $c.Cmd $c.Args
      Write-Step "$($c.Name) - $ver" "OK"
    } else {
      Write-Step "$($c.Name) introuvable dans PATH" "FAIL"
      $ok = $false
    }
  }
  if (-not $ok) { throw "Prerequisites manquants. Installez Python, Node.js, npm et Git." }
}

function Assert-EnvFiles {
  Write-Host "  -- Fichiers .env" -ForegroundColor White
  $backendEnv = Join-Path $BackendDir ".env"
  $frontendEnv = Join-Path $FrontendDir ".env"
  if (-not (Test-Path $backendEnv)) {
    Write-Step "backend/.env manquant (voir backend/.env.example)" "FAIL"
    throw "Creez backend/.env avant de lancer."
  }
  Write-Step "backend/.env present" "OK"
  if (Test-Path $frontendEnv) {
    Write-Step "frontend/.env present" "OK"
  } else {
    Write-Step "frontend/.env manquant (voir frontend/.env.example)" "WARN"
  }
  $beLines = Get-Content $backendEnv -ErrorAction SilentlyContinue
  $hasDb = $false
  foreach ($line in $beLines) {
    if ($line -match '^\s*DATABASE_URL\s*=') { $hasDb = $true; break }
  }
  if (-not $hasDb) {
    Write-Step "DATABASE_URL absent de backend/.env" "WARN"
  } else {
    Write-Step "DATABASE_URL declare" "OK"
  }
  $jwtWeak = $false
  foreach ($line in $beLines) {
    if ($line -match '^\s*JWT_SECRET\s*=\s*$') { $jwtWeak = $true }
    if ($line -match '^\s*JWT_SECRET\s*=\s*change-me') { $jwtWeak = $true }
  }
  if ($jwtWeak) {
    Write-Step "JWT_SECRET faible / defaut (OK en local uniquement)" "WARN"
  }
}

function Assert-Dependencies {
  Write-Host "  -- Dependances" -ForegroundColor White
  $venvPython = Join-Path $BackendDir ".venv\Scripts\python.exe"
  $uvicorn = Join-Path $BackendDir ".venv\Scripts\uvicorn.exe"
  $nodeModules = Join-Path $FrontendDir "node_modules"
  $req = Join-Path $BackendDir "requirements.txt"

  if (-not (Test-Path $venvPython)) {
    if ($SkipInstall) { throw "backend/.venv manquant." }
    Write-Step "Creation backend/.venv..." "INFO"
    Push-Location $BackendDir
    try {
      python -m venv .venv
      & .\.venv\Scripts\python.exe -m pip install --upgrade pip -q
      & .\.venv\Scripts\python.exe -m pip install -r requirements.txt -q
    } finally { Pop-Location }
  }
  if (-not (Test-Path $uvicorn)) {
    if ($SkipInstall) { throw "uvicorn absent du venv" }
    Write-Step "Installation requirements.txt..." "INFO"
    Push-Location $BackendDir
    try {
      & .\.venv\Scripts\python.exe -m pip install -r $req -q
    } finally { Pop-Location }
  }
  Write-Step "Python venv + uvicorn OK" "OK"

  if (-not (Test-Path $nodeModules)) {
    if ($SkipInstall) { throw "frontend/node_modules manquant." }
    Write-Step "npm install (frontend)..." "INFO"
    Push-Location $FrontendDir
    try { npm install --no-fund --no-audit } finally { Pop-Location }
  }
  Write-Step "frontend/node_modules OK" "OK"
}

function Save-RuntimePids($BackendProc, $FrontendProc) {
  New-Item -ItemType Directory -Force -Path $RuntimeDir | Out-Null
  $payload = @{
    started_at     = (Get-Date).ToString("o")
    backend_port   = $BackendPort
    frontend_port  = $FrontendPort
    backend_pid    = $BackendProc.Id
    frontend_pid   = $FrontendProc.Id
    root           = "$Root"
  } | ConvertTo-Json
  Set-Content -Path $PidFile -Value $payload -Encoding UTF8
}

function Start-ElfisServices {
  Write-Host "  -- Demarrage des services" -ForegroundColor White
  New-Item -ItemType Directory -Force -Path $RuntimeDir | Out-Null
  foreach ($f in @($BackendOut, $BackendErr, $FrontendOut, $FrontendErr)) {
    if (Test-Path $f) { Remove-Item $f -Force -ErrorAction SilentlyContinue }
  }

  foreach ($port in @($BackendPort, $FrontendPort)) {
    if (Test-PortListening $port) {
      Write-Step "Port $port deja occupe - tentative d'arret via elfis-stop" "WARN"
      & $StopScript -Quiet
      Start-Sleep -Seconds 1
      if (Test-PortListening $port) {
        throw "Port $port toujours occupe. Liberer avec stop-elfis.bat puis relancer."
      }
    }
  }

  $venvUvicorn = Join-Path $BackendDir ".venv\Scripts\uvicorn.exe"
  if (-not (Test-Path $venvUvicorn)) { throw "uvicorn introuvable: $venvUvicorn" }

  $backendArgs = @(
    "app.main:app",
    "--reload",
    "--reload-dir", "app",
    "--host", "127.0.0.1",
    "--port", "$BackendPort"
  )
  $backend = Start-Process -FilePath $venvUvicorn `
    -ArgumentList $backendArgs `
    -WorkingDirectory $BackendDir `
    -RedirectStandardOutput $BackendOut `
    -RedirectStandardError $BackendErr `
    -PassThru -WindowStyle Hidden

  $npmCmd = $null
  $npmCmdObj = Get-Command "npm.cmd" -ErrorAction SilentlyContinue
  if ($npmCmdObj) { $npmCmd = $npmCmdObj.Source }
  if (-not $npmCmd) {
    $npmCmdObj = Get-Command "npm" -ErrorAction SilentlyContinue
    if ($npmCmdObj) { $npmCmd = $npmCmdObj.Source }
  }
  if (-not $npmCmd) { throw "npm introuvable" }

  $frontendArgs = @(
    "run", "dev", "--",
    "--host", "localhost",
    "--port", "$FrontendPort",
    "--strictPort"
  )
  $frontend = Start-Process -FilePath $npmCmd `
    -ArgumentList $frontendArgs `
    -WorkingDirectory $FrontendDir `
    -RedirectStandardOutput $FrontendOut `
    -RedirectStandardError $FrontendErr `
    -PassThru -WindowStyle Hidden

  Save-RuntimePids $backend $frontend
  Write-Step "Backend PID $($backend.Id) -> :$BackendPort" "OK"
  Write-Step "Frontend PID $($frontend.Id) -> :$FrontendPort" "OK"
  return @{ Backend = $backend; Frontend = $frontend }
}

function Test-CriticalEndpoints {
  Write-Host "  -- Health checks" -ForegroundColor White
  $healthUrl = "http://127.0.0.1:$BackendPort/api/health"
  $proxyUrl = "http://localhost:$FrontendPort/api/health"
  $authUrl = "http://127.0.0.1:$BackendPort/api/auth/me"
  $platformUrl = "http://127.0.0.1:$BackendPort/api/platform/dashboard"

  $h = Wait-HttpOk -Url $healthUrl -TimeoutSec $HealthTimeoutSec -AcceptStatuses @(200)
  if ($h.Ok) { Write-Step "GET /api/health -> $($h.Status)" "OK" }
  else { Write-Step "GET /api/health timeout" "FAIL"; throw "Backend health KO" }

  $p = Wait-HttpOk -Url $proxyUrl -TimeoutSec $HealthTimeoutSec -AcceptStatuses @(200)
  if ($p.Ok) { Write-Step "GET localhost:$FrontendPort/api/health (proxy) -> $($p.Status)" "OK" }
  else { Write-Step "Proxy Vite /api/health KO" "FAIL"; throw "Frontend proxy KO" }

  $a = Wait-HttpOk -Url $authUrl -TimeoutSec 20 -AcceptStatuses @(401, 403)
  if ($a.Ok) { Write-Step "GET /api/auth/me -> $($a.Status) (auth active)" "OK" }
  else { Write-Step "GET /api/auth/me inattendu (attendu 401/403)" "WARN" }

  $pl = Wait-HttpOk -Url $platformUrl -TimeoutSec 20 -AcceptStatuses @(401, 403)
  if ($pl.Ok) { Write-Step "GET /api/platform/dashboard -> $($pl.Status) (route OK)" "OK" }
  else { Write-Step "GET /api/platform/dashboard inattendu" "WARN" }
}

function Show-Dashboard {
  param($Procs)
  $beAlive = $Procs.Backend -and (-not $Procs.Backend.HasExited)
  $feAlive = $Procs.Frontend -and (-not $Procs.Frontend.HasExited)
  Write-Host ""
  Write-Host "  +---------------- ELFIS DEV STATUS -----------------+" -ForegroundColor Cyan
  Write-Host ("  | Backend   : {0,-8}  http://127.0.0.1:{1,-5} |" -f ($(if ($beAlive) { "UP" } else { "DOWN" }), $BackendPort))
  Write-Host ("  | Frontend  : {0,-8}  http://localhost:{1,-5} |" -f ($(if ($feAlive) { "UP" } else { "DOWN" }), $FrontendPort))
  Write-Host ("  | App       : http://localhost:{0}/" -f $FrontendPort)
  Write-Host ("  | Login     : http://localhost:{0}/login" -f $FrontendPort)
  Write-Host ("  | Cockpit   : http://localhost:{0}/elfadmin" -f $FrontendPort)
  Write-Host ("  | API docs  : http://127.0.0.1:{0}/docs" -f $BackendPort)
  Write-Host ("  | Health    : http://127.0.0.1:{0}/api/health" -f $BackendPort)
  Write-Host "  | Logs      : .elfis-dev/*.log"
  Write-Host "  | Stop      : npm run dev:stop   |  stop-elfis.bat"
  Write-Host "  +----------------------------------------------------+" -ForegroundColor Cyan
  Write-Host ""
}

# -- Main -----------------------------------------------------------------
Write-Banner
$started = $false
try {
  Assert-Prerequisites
  Assert-EnvFiles
  Assert-Dependencies
  $procs = Start-ElfisServices
  $started = $true
  Test-CriticalEndpoints
  Show-Dashboard -Procs $procs

  if (-not $SkipBrowser) {
    try {
      Start-Process "http://localhost:$FrontendPort" | Out-Null
      Write-Step "Navigateur ouvert sur http://localhost:$FrontendPort" "OK"
    } catch {
      Write-Step "Ouverture navigateur ignoree: $($_.Exception.Message)" "WARN"
    }
  }

  if ($StayAttached) {
    Write-Host "  Ctrl+C pour arreter proprement tous les services." -ForegroundColor Yellow
    Write-Host ""
    try {
      while ($true) {
        if ($procs.Backend.HasExited -or $procs.Frontend.HasExited) {
          Write-Step "Un processus s'est arrete de facon inattendue" "FAIL"
          break
        }
        Start-Sleep -Seconds 2
      }
    } finally {
      Write-Step "Arret des services..." "INFO"
      & $StopScript -Quiet
    }
  } else {
    Write-Step "Mode detache - services actifs. Arret: npm run dev:stop" "OK"
  }
  exit 0
} catch {
  Write-Step $_.Exception.Message "FAIL"
  if ($started -and (Test-Path $StopScript)) { & $StopScript -Quiet }
  exit 1
}
