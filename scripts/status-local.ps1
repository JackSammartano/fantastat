[CmdletBinding()]
param()

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$PidFile = Join-Path $ProjectRoot "reports\runtime\local-processes.json"

if (-not (Test-Path -LiteralPath $PidFile)) {
    Write-Output "Servizi locali non registrati."
    exit 1
}

$State = Get-Content -LiteralPath $PidFile -Raw | ConvertFrom-Json
foreach ($ServiceName in @("backend", "frontend")) {
    $Expected = $State.$ServiceName
    $Process = Get-Process -Id $Expected.id -ErrorAction SilentlyContinue
    if ($null -eq $Process) {
        Write-Output "${ServiceName}: fermo (PID $($Expected.id))"
    } else {
        Write-Output "${ServiceName}: attivo (PID $($Process.Id), $($Process.ProcessName), porta $($Expected.port))"
    }
}
