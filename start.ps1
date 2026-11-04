# start.ps1 — запуск всего стека: PostgreSQL -> backend (uvicorn :8000) -> frontend (Next.js :3000)
# Каждый сервис стартует в своём окне PowerShell (закрытие окна = остановка сервиса).
# Идемпотентно: уже слушающие порты пропускаются.
# Запуск: powershell -ExecutionPolicy Bypass -File .\start.ps1

$ErrorActionPreference = "Stop"
$root = $PSScriptRoot

$PG_CTL     = "C:\Program Files\PostgreSQL\18\bin\pg_ctl.exe"
$PG_DATA    = Join-Path $root "backend\.pgdata"
$PG_LOG     = Join-Path $PG_DATA "server.log"
$BACKEND    = Join-Path $root "backend"
$FRONTEND   = Join-Path $root "frontend"
$PY         = Join-Path $BACKEND ".venv\Scripts\python.exe"

function Test-Port([int]$port) {
    return [bool](Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue)
}

function Wait-Port([int]$port, [int]$timeoutSec) {
    $deadline = (Get-Date).AddSeconds($timeoutSec)
    while ((Get-Date) -lt $deadline) {
        if (Test-Port $port) { return $true }
        Start-Sleep -Milliseconds 500
    }
    return $false
}

function Wait-Http([string]$url, [int]$timeoutSec) {
    $deadline = (Get-Date).AddSeconds($timeoutSec)
    while ((Get-Date) -lt $deadline) {
        try {
            if ((Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 3).StatusCode -lt 400) { return $true }
        } catch { }
        Start-Sleep -Milliseconds 500
    }
    return $false
}

function New-ServiceWindow([string]$title, [string]$workdir, [string]$command) {
    Start-Process -FilePath "powershell" -WorkingDirectory $root -WindowStyle Minimized -ArgumentList @(
        "-NoExit", "-Command",
        "`$Host.UI.RawUI.WindowTitle = '$title'; Set-Location '$workdir'; $command"
    )
}

$failed = @()

# --- 1. PostgreSQL (dev-кластер backend/.pgdata, порт 5432) ---
if (Test-Port 5432) {
    Write-Host "[1/3] PostgreSQL :5432 - уже запущен, пропускаю" -ForegroundColor DarkGray
} elseif (-not (Test-Path $PG_DATA)) {
    Write-Host "[1/3] PostgreSQL - кластер $PG_DATA не найден, пропускаю" -ForegroundColor Red
    $failed += "postgres"
} else {
    Write-Host "[1/3] PostgreSQL :5432 - стартую pg_ctl..." -ForegroundColor Cyan
    & $PG_CTL -D $PG_DATA -l $PG_LOG -o "-p 5432" start | Out-Null
    if (-not (Wait-Port 5432 30)) { $failed += "postgres" }
}

# --- 2. Backend (FastAPI, uvicorn :8000) ---
if (Test-Port 8000) {
    Write-Host "[2/3] Backend :8000 - уже запущен (проверить владельца: Get-NetTCPConnection -LocalPort 8000 | select OwningProcess), пропускаю" -ForegroundColor DarkGray
} elseif (-not (Test-Path $PY)) {
    Write-Host "[2/3] Backend - не найден $PY (создайте venv), пропускаю" -ForegroundColor Red
    $failed += "backend"
} else {
    Write-Host "[2/3] Backend :8000 - запускаю uvicorn..." -ForegroundColor Cyan
    New-ServiceWindow "QCS: backend (8000)" $BACKEND "& '$PY' -m uvicorn app.main:app --port 8000"
    if (-not (Wait-Http "http://localhost:8000/api/v1/health" 60)) { $failed += "backend" }
}

# --- 3. Frontend (Next.js dev :3000) ---
if (Test-Port 3000) {
    Write-Host "[3/3] Frontend :3000 - уже запущен, пропускаю" -ForegroundColor DarkGray
} elseif (-not (Test-Path (Join-Path $FRONTEND "node_modules"))) {
    Write-Host "[3/3] Frontend - нет node_modules (выполните npm install в frontend/), пропускаю" -ForegroundColor Red
    $failed += "frontend"
} else {
    Write-Host "[3/3] Frontend :3000 - запускаю npm run dev..." -ForegroundColor Cyan
    New-ServiceWindow "QCS: frontend (3000)" $FRONTEND "npm run dev"
    if (-not (Wait-Http "http://localhost:3000" 90)) { $failed += "frontend" }
}

Write-Host ""
if ($failed.Count -gt 0) {
    Write-Host "НЕ поднялись: $($failed -join ', ') - смотрите окна сервисов / $PG_LOG" -ForegroundColor Red
    exit 1
}

Write-Host "Стек запущен:" -ForegroundColor Green
Write-Host "  Frontend  http://localhost:3000        (логин: admin@qcs.dev / admin12345)"
Write-Host "  Backend   http://localhost:8000/api/v1  (health: /health)"
Write-Host "  PostgreSQL :5432, БД quote_costing"
exit 0
