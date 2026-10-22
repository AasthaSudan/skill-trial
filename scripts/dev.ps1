$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot
if (-not (Test-Path -LiteralPath 'backend\.venv\Scripts\python.exe')) { throw 'Run scripts/setup.ps1 first.' }
if (-not (Test-Path -LiteralPath 'frontend\node_modules')) { throw 'Run scripts/setup.ps1 first.' }
$api = Start-Process -FilePath (Join-Path $projectRoot 'backend\.venv\Scripts\python.exe') -ArgumentList @('-m','uvicorn','app.main:app','--app-dir','backend','--host','127.0.0.1','--port','8000','--reload','--reload-dir','backend/app') -WorkingDirectory $projectRoot -WindowStyle Hidden -PassThru
try {
    Write-Host 'SkillTrial: http://127.0.0.1:5173 | API: http://127.0.0.1:8000/docs'
    npm.cmd --prefix frontend run dev
} finally {
    if (-not $api.HasExited) { taskkill.exe /PID $api.Id /T /F | Out-Null }
}
