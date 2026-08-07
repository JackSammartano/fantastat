[CmdletBinding()]
param()

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$PidFile = Join-Path $ProjectRoot "reports\runtime\share-process.json"
if (-not (Test-Path -LiteralPath $PidFile)) {
    Write-Output "Nessuna condivisione registrata."
    exit 0
}
$State = Get-Content -LiteralPath $PidFile -Raw | ConvertFrom-Json
$Process = Get-Process -Id $State.id -ErrorAction SilentlyContinue
if ($null -ne $Process) { Stop-Process -Id $Process.Id }
Remove-Item -LiteralPath $PidFile
Write-Output "Istanza condivisa arrestata."
