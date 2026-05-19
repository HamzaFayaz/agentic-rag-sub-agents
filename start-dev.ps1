$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot
$Backend = Join-Path $Root "backend"
$Frontend = Join-Path $Root "frontend"
$Uvicorn = Join-Path $Backend "venv\Scripts\uvicorn.exe"
$BackendPort = 8000
$FrontendPort = 5173

function Stop-ListenerOnPort {
    param([int]$Port)
    $connections = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
    if (-not $connections) { return }

    $pids = $connections.OwningProcess | Sort-Object -Unique
    foreach ($procId in $pids) {
        $proc = Get-Process -Id $procId -ErrorAction SilentlyContinue
        $name = if ($proc) { $proc.ProcessName } else { "unknown" }
        Write-Host "Port $Port is in use by $name (PID $procId). Stopping it..." -ForegroundColor Yellow
        Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
    }
    Start-Sleep -Seconds 1
}

if (-not (Test-Path $Uvicorn)) {
    Write-Host "Backend venv not found. Run:" -ForegroundColor Yellow
    Write-Host "  cd backend; python -m venv venv; .\venv\Scripts\pip install -r requirements.txt"
    exit 1
}

if (-not (Test-Path (Join-Path $Frontend "node_modules"))) {
    Write-Host "Frontend deps not found. Run:" -ForegroundColor Yellow
    Write-Host "  cd frontend; npm install"
    exit 1
}

Stop-ListenerOnPort -Port $BackendPort
Stop-ListenerOnPort -Port $FrontendPort

$stillBlocked = Get-NetTCPConnection -LocalPort $BackendPort -State Listen -ErrorAction SilentlyContinue
if ($stillBlocked) {
    Write-Host "Port $BackendPort is still in use. Close the other app or change `$BackendPort in start-dev.ps1" -ForegroundColor Red
    exit 1
}

Write-Host "Starting backend (port $BackendPort) and frontend (port $FrontendPort) in new windows..." -ForegroundColor Cyan

$backendCmd = @"
Set-Location '$Backend'
Write-Host '=== Backend (FastAPI) ===' -ForegroundColor Green
& '$Uvicorn' app.main:app --reload --port $BackendPort
"@

$frontendCmd = @"
Set-Location '$Frontend'
Write-Host '=== Frontend (Vite) ===' -ForegroundColor Green
npm run dev
"@

Start-Process powershell -ArgumentList "-NoExit", "-Command", $backendCmd
Start-Sleep -Milliseconds 500
Start-Process powershell -ArgumentList "-NoExit", "-Command", $frontendCmd

Write-Host "Done. Backend: http://localhost:$BackendPort  Frontend: http://localhost:$FrontendPort" -ForegroundColor Cyan
Write-Host "Close those windows to stop the servers." -ForegroundColor Cyan
