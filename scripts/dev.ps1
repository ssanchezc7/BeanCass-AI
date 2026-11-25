# Levanta la API (FastAPI, puerto 8000) y la web (Next.js, puerto 3000) en dos ventanas de PowerShell.
# Uso (desde la raíz del repo):  .\scripts\dev.ps1      o desde web/:  pnpm dev:all
$ErrorActionPreference = 'Stop'
$raiz = Split-Path -Parent $PSScriptRoot
$python = Join-Path $raiz 'api\.venv\Scripts\python.exe'

if (-not (Test-Path $python)) {
    Write-Host 'No existe api\.venv. Sigue la sección "Instalación" del README.' -ForegroundColor Red
    exit 1
}

$api = "Set-Location '$raiz\api'; & '$python' -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload --no-access-log"
$web = "Set-Location '$raiz\web'; pnpm dev"

Start-Process powershell -ArgumentList '-NoExit', '-Command', $api
Start-Process powershell -ArgumentList '-NoExit', '-Command', $web

Write-Host 'API: http://127.0.0.1:8000/docs   Web: http://localhost:3000' -ForegroundColor Green
