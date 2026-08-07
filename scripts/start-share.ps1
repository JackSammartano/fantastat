[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$Password,
    [int]$Port = 8080
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$Runtime = Join-Path $ProjectRoot "reports\runtime"
$PidFile = Join-Path $Runtime "share-process.json"

if (Test-Path -LiteralPath $PidFile) {
    throw "Condivisione già registrata. Eseguire scripts\stop-share.ps1."
}
New-Item -ItemType Directory -Path $Runtime -Force | Out-Null
$env:FANTACALCIO_READ_ONLY = "1"
$env:FANTACALCIO_SHARE_PASSWORD = $Password
$Process = Start-Process `
    -FilePath $Python `
    -ArgumentList "-m", "uvicorn", "backend.app.main:app", "--host", "127.0.0.1", "--port", "$Port" `
    -WorkingDirectory $ProjectRoot `
    -WindowStyle Hidden `
    -RedirectStandardOutput (Join-Path $Runtime "share.stdout.log") `
    -RedirectStandardError (Join-Path $Runtime "share.stderr.log") `
    -PassThru
@{ id = $Process.Id; port = $Port; started_at = (Get-Date).ToString("o") } |
    ConvertTo-Json | Set-Content -LiteralPath $PidFile -Encoding utf8
Write-Output "Istanza protetta in sola lettura avviata su http://127.0.0.1:$Port"
