# Run via start-dev.bat (not by opening this file in Notepad / CMD as start-dev.ps1).
$ErrorActionPreference = "Stop"
$Root = (Get-Item -LiteralPath "$PSScriptRoot\..").FullName
$Backend = Join-Path $Root "backend"
$Frontend = Join-Path $Root "frontend"
$Uvicorn = Join-Path $Backend "venv\Scripts\uvicorn.exe"
$PreferredBackendPort = 8000
$FrontendPort = 5173
$BackendPortCandidates = 8000, 8001, 8002

function Test-TcpPortAvailable {
    param([int]$Port)
    $listener = [System.Net.Sockets.TcpListener]::new(
        [System.Net.IPAddress]::Loopback,
        $Port
    )
    try {
        $listener.Start()
        $listener.Stop()
        return $true
    } catch {
        return $false
    }
}

function Get-AvailableBackendPort {
    param([int[]]$Candidates)

    foreach ($port in $Candidates) {
        if (Test-TcpPortAvailable -Port $port) {
            return $port
        }
    }
    return $null
}

function Stop-ListenerOnPort {
    param(
        [int]$Port,
        [int]$MaxAttempts = 6
    )

    for ($attempt = 1; $attempt -le $MaxAttempts; $attempt++) {
        $connections = @(
            Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
        )
        if (-not $connections) { return $true }

        $pids = $connections.OwningProcess | Sort-Object -Unique
        foreach ($procId in $pids) {
            $proc = Get-Process -Id $procId -ErrorAction SilentlyContinue
            if ($proc) {
                $name = $proc.ProcessName
                Write-Host "Port $Port is in use by $name (PID $procId). Stopping it..." -ForegroundColor Yellow
                Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
                # uvicorn --reload: kill child workers too
                Start-Process -FilePath "taskkill.exe" -ArgumentList "/F", "/T", "/PID", $procId -Wait -WindowStyle Hidden -ErrorAction SilentlyContinue
            } elseif ($attempt -eq 1) {
                Write-Host "Port $Port shows PID $procId but that process is already gone (stale). Waiting for Windows to release the port..." -ForegroundColor Yellow
            }
        }

        Start-Sleep -Seconds 2
    }

    return -not (Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue)
}

function Stop-ProjectPythonServers {
    param([string]$BackendDir)

    $venvPython = Join-Path $BackendDir "venv\Scripts\python.exe"
    Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
        Where-Object {
            $_.CommandLine -and (
                $_.CommandLine -like "*uvicorn*app.main:app*" -or
                ($venvPython -and $_.ExecutablePath -eq $venvPython -and $_.CommandLine -like "*uvicorn*")
            )
        } |
        ForEach-Object {
            Write-Host "Stopping leftover uvicorn (PID $($_.ProcessId))..." -ForegroundColor Yellow
            Start-Process -FilePath "taskkill.exe" -ArgumentList "/F", "/T", "/PID", $_.ProcessId -Wait -WindowStyle Hidden -ErrorAction SilentlyContinue
        }
}

function Start-DevServerWindow {
    param(
        [string]$WorkingDirectory,
        [string]$WindowTitle,
        [string]$Command
    )
    $psArgs = @(
        "-NoExit",
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-Command",
        "`$host.UI.RawUI.WindowTitle = '$WindowTitle'; $Command"
    )
    Start-Process -FilePath "powershell.exe" -WorkingDirectory $WorkingDirectory -ArgumentList $psArgs
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

Stop-ProjectPythonServers -BackendDir $Backend
foreach ($port in $BackendPortCandidates) {
    Stop-ListenerOnPort -Port $port | Out-Null
}
$frontendFree = Stop-ListenerOnPort -Port $FrontendPort

if (-not $frontendFree) {
    Write-Host ""
    Write-Host "Port $FrontendPort is still in use. Close the old frontend window or run stop-dev.bat" -ForegroundColor Red
    exit 1
}

$BackendPort = Get-AvailableBackendPort -Candidates $BackendPortCandidates
if (-not $BackendPort) {
    Write-Host ""
    Write-Host "Ports $($BackendPortCandidates -join ', ') are all in use." -ForegroundColor Red
    Write-Host "  Run stop-dev.bat, close old server windows, or reboot." -ForegroundColor Yellow
    exit 1
}

if ($BackendPort -ne $PreferredBackendPort) {
    Write-Host "Port $PreferredBackendPort is busy - using port $BackendPort instead." -ForegroundColor Yellow
}

Write-Host "Starting backend (port $BackendPort) and frontend (port $FrontendPort) in new windows..." -ForegroundColor Cyan

Start-DevServerWindow -WorkingDirectory $Backend -WindowTitle "RAG Backend ($BackendPort)" -Command @"
Write-Host '=== Backend (FastAPI) ===' -ForegroundColor Green
& '.\venv\Scripts\uvicorn.exe' app.main:app --reload --port $BackendPort
"@

Start-Sleep -Milliseconds 500

Start-DevServerWindow -WorkingDirectory $Frontend -WindowTitle "RAG Frontend ($FrontendPort)" -Command @"
`$env:VITE_BACKEND_PORT = '$BackendPort'
Write-Host '=== Frontend (Vite) ===' -ForegroundColor Green
Write-Host 'API proxy targets http://127.0.0.1:$BackendPort' -ForegroundColor DarkGray
npm run dev
"@

Write-Host "Done. Backend: http://localhost:$BackendPort  Frontend: http://localhost:$FrontendPort" -ForegroundColor Cyan
Write-Host "Close those two PowerShell windows to stop the servers." -ForegroundColor Cyan

