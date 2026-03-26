$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot

$botProcesses = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
    Where-Object {
        $_.Name -eq 'python.exe' -and
        $_.CommandLine -and
        ($_.CommandLine -like '*bot.py*' -or $_.CommandLine -like '*uvicorn*bot:app*')
    }

foreach ($process in $botProcesses) {
    try {
        Stop-Process -Id $process.ProcessId -Force -ErrorAction Stop
        Write-Host "Stopped bot process PID: $($process.ProcessId)"
    } catch {
        Write-Warning "Failed to stop bot process PID: $($process.ProcessId)"
    }
}

$napcatProcesses = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
    Where-Object {
        $_.ExecutablePath -and
        $_.ExecutablePath -like 'D:\NapCat*' -and
        $_.Name -in @('NapCatWinBootMain.exe', 'QQ.exe')
    }

foreach ($process in $napcatProcesses) {
    try {
        Stop-Process -Id $process.ProcessId -Force -ErrorAction Stop
        Write-Host "Stopped NapCat process PID: $($process.ProcessId)"
    } catch {
        Write-Warning "Failed to stop NapCat process PID: $($process.ProcessId)"
    }
}

Write-Host "All bot-related processes have been stopped."