# Stop dev servers (run via stop-dev.bat from CMD).
$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot
$Backend = Join-Path $Root "backend"
$Ports = @(8000, 8001, 8002, 5173)

function Stop-ListenerOnPort {
    param([int]$Port)
    $connections = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
    if (-not $connections) { return }

    foreach ($procId in ($connections.OwningProcess | Sort-Object -Unique)) {
        $proc = Get-Process -Id $procId -ErrorAction SilentlyContinue
        if ($proc) {
            Write-Host "Stopping $($proc.ProcessName) on port $Port (PID $procId)..." -ForegroundColor Yellow
            Start-Process -FilePath "taskkill.exe" -ArgumentList "/F", "/T", "/PID", $procId -Wait -WindowStyle Hidden
        } else {
            Write-Host "Port $Port - stale entry (PID $procId already exited)." -ForegroundColor DarkYellow
        }
    }
}

$venvPython = Join-Path $Backend "venv\Scripts\python.exe"
Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
    Where-Object {
        $_.CommandLine -and (
            $_.CommandLine -like "*uvicorn*app.main:app*" -or
            ($venvPython -and $_.ExecutablePath -eq $venvPython)
        )
    } |
    ForEach-Object {
        Write-Host "Stopping $($_.Name) (PID $($_.ProcessId))..." -ForegroundColor Yellow
        Start-Process -FilePath "taskkill.exe" -ArgumentList "/F", "/T", "/PID", $_.ProcessId -Wait -WindowStyle Hidden
    }

foreach ($port in $Ports) {
    Stop-ListenerOnPort -Port $port
}

Write-Host "Done. If port 8000 is still stuck, wait 30s or reboot, then run start-dev.bat again." -ForegroundColor Cyan
