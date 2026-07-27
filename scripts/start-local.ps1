[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$Frontend = Join-Path $ProjectRoot "frontend"
$Runtime = Join-Path $ProjectRoot "reports\runtime"
$PidFile = Join-Path $Runtime "local-processes.json"

if (-not (Test-Path -LiteralPath $Python)) {
    throw "Virtual environment non trovato: $Python"
}
if (-not (Test-Path -LiteralPath (Join-Path $Frontend "node_modules"))) {
    throw "Dipendenze frontend assenti. Eseguire: cd frontend; npm install"
}
if (Test-Path -LiteralPath $PidFile) {
    throw "Esiste già un file PID. Eseguire scripts\status-local.ps1 o scripts\stop-local.ps1."
}

New-Item -ItemType Directory -Path $Runtime -Force | Out-Null

$Backend = Start-Process `
    -FilePath $Python `
    -ArgumentList "-m", "uvicorn", "backend.app.main:app", "--host", "127.0.0.1", "--port", "8000" `
    -WorkingDirectory $ProjectRoot `
    -WindowStyle Hidden `
    -RedirectStandardOutput (Join-Path $Runtime "backend.stdout.log") `
    -RedirectStandardError (Join-Path $Runtime "backend.stderr.log") `
    -PassThru

$FrontendProcess = Start-Process `
    -FilePath "npm.cmd" `
    -ArgumentList "run", "dev" `
    -WorkingDirectory $Frontend `
    -WindowStyle Hidden `
    -RedirectStandardOutput (Join-Path $Runtime "frontend.stdout.log") `
    -RedirectStandardError (Join-Path $Runtime "frontend.stderr.log") `
    -PassThru

@{
    backend = @{ id = $Backend.Id; name = $Backend.ProcessName }
    frontend = @{ id = $FrontendProcess.Id; name = $FrontendProcess.ProcessName }
    started_at = (Get-Date).ToString("o")
} | ConvertTo-Json -Depth 3 | Set-Content -LiteralPath $PidFile -Encoding utf8

$BackendReady = $false
$FrontendReady = $false
for ($Attempt = 0; $Attempt -lt 20; $Attempt++) {
    Start-Sleep -Milliseconds 500
    try {
        $Health = Invoke-RestMethod -Uri "http://127.0.0.1:8000/health" -TimeoutSec 1
        $BackendReady = $Health.status -eq "ok"
    } catch {}
    try {
        $Response = Invoke-WebRequest -Uri "http://127.0.0.1:5173" -TimeoutSec 1 -UseBasicParsing
        $FrontendReady = $Response.StatusCode -eq 200
    } catch {}
    if ($BackendReady -and $FrontendReady) { break }
}

if (-not ($BackendReady -and $FrontendReady)) {
    Write-Warning "Uno dei servizi non è pronto. Controllare reports\runtime\*.log"
    & (Join-Path $PSScriptRoot "status-local.ps1")
    exit 1
}

$BackendListener = Get-NetTCPConnection -LocalAddress "127.0.0.1" -LocalPort 8000 -State Listen
$FrontendListener = Get-NetTCPConnection -LocalAddress "127.0.0.1" -LocalPort 5173 -State Listen
$BackendActual = Get-Process -Id $BackendListener.OwningProcess
$FrontendActual = Get-Process -Id $FrontendListener.OwningProcess
@{
    backend = @{ id = $BackendActual.Id; name = $BackendActual.ProcessName; port = 8000 }
    frontend = @{ id = $FrontendActual.Id; name = $FrontendActual.ProcessName; port = 5173 }
    started_at = (Get-Date).ToString("o")
} | ConvertTo-Json -Depth 3 | Set-Content -LiteralPath $PidFile -Encoding utf8

Write-Output "Applicazione pronta: http://127.0.0.1:5173"
Write-Output "API Swagger:        http://127.0.0.1:8000/docs"
