[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$PidFile = Join-Path $ProjectRoot "reports\runtime\local-processes.json"

if (-not (Test-Path -LiteralPath $PidFile)) {
    Write-Output "Nessun servizio locale registrato."
    exit 0
}

$State = Get-Content -LiteralPath $PidFile -Raw | ConvertFrom-Json
foreach ($ServiceName in @("backend", "frontend")) {
    $Expected = $State.$ServiceName
    $Process = Get-Process -Id $Expected.id -ErrorAction SilentlyContinue
    $Listener = Get-NetTCPConnection `
        -LocalAddress "127.0.0.1" `
        -LocalPort $Expected.port `
        -State Listen `
        -ErrorAction SilentlyContinue
    if (
        $null -ne $Process -and
        $Process.ProcessName -eq $Expected.name -and
        $null -ne $Listener -and
        $Listener.OwningProcess -eq $Process.Id
    ) {
        Stop-Process -Id $Process.Id
        Write-Output "${ServiceName}: arrestato (PID $($Process.Id))"
    } elseif ($null -ne $Process) {
        Write-Warning "${ServiceName}: PID riutilizzato da un altro processo; non arrestato."
    }
}
Remove-Item -LiteralPath $PidFile
