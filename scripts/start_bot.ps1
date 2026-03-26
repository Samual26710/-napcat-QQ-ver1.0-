$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot

if (-not (Test-Path .venv)) {
    Write-Error "未找到 .venv，请先运行 scripts/install.ps1"
    exit 1
}

$expectedPython = Join-Path $projectRoot '.venv\Scripts\python.exe'
$envFile = Join-Path $projectRoot '.env'

function Get-EnvValue {
    param(
        [string]$Name,
        [string]$DefaultValue
    )

    if (-not (Test-Path $envFile)) {
        return $DefaultValue
    }

    $line = Get-Content $envFile | Where-Object { $_ -match "^$Name=" } | Select-Object -First 1
    if (-not $line) {
        return $DefaultValue
    }

    return ($line -replace "^$Name=", '').Trim()
}

$botHost = Get-EnvValue -Name 'HOST' -DefaultValue '127.0.0.1'
$port = Get-EnvValue -Name 'PORT' -DefaultValue '8080'

$botProcesses = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
    Where-Object {
        $_.Name -eq 'python.exe' -and
        $_.CommandLine -and
        ($_.CommandLine -like '*bot.py*' -or $_.CommandLine -like '*uvicorn*bot:app*')
    }

$botProcess = $botProcesses |
    Where-Object { $_.ExecutablePath -eq $expectedPython } |
    Select-Object -First 1

if ($botProcess) {
    Write-Host "机器人已在运行，PID: $($botProcess.ProcessId)"
    exit 0
}

$conflictingProcesses = $botProcesses |
    Where-Object { $_.ExecutablePath -ne $expectedPython }

foreach ($process in $conflictingProcesses) {
    try {
        Stop-Process -Id $process.ProcessId -Force -ErrorAction Stop
        Write-Host "已停止冲突的机器人进程，PID: $($process.ProcessId)"
    } catch {
        Write-Warning "停止冲突进程失败，PID: $($process.ProcessId)"
    }
}

& $expectedPython -m uvicorn bot:app --host $botHost --port $port
