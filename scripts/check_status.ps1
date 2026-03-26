$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot

$botProcesses = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
    Where-Object {
        $_.Name -eq 'python.exe' -and
        $_.CommandLine -and
        ($_.CommandLine -like '*bot.py*' -or $_.CommandLine -like '*uvicorn*bot:app*')
    }

$napcatProcesses = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
    Where-Object {
        $_.ExecutablePath -and
        $_.ExecutablePath -like 'D:\NapCat*' -and
        $_.Name -in @('NapCatWinBootMain.exe', 'QQ.exe')
    }

$systemQqProcesses = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
    Where-Object {
        $_.ExecutablePath -and
        $_.ExecutablePath -like 'C:\Program Files\Tencent\QQNT*' -and
        $_.Name -eq 'QQ.exe'
    }

$portConnections = Get-NetTCPConnection -ErrorAction SilentlyContinue |
    Where-Object { $_.LocalPort -eq 8080 -or $_.RemotePort -eq 8080 }

$listeningConnection = $portConnections | Where-Object { $_.LocalPort -eq 8080 -and $_.State -eq 'Listen' } | Select-Object -First 1
$establishedConnections = $portConnections | Where-Object { $_.State -eq 'Established' }

$historyPath = Join-Path $projectRoot 'data\chat_sessions.json'

Write-Host '=== QQ Bot Status ==='
Write-Host "Project root: $projectRoot"
Write-Host "Bot process count: $($botProcesses.Count)"
Write-Host "NapCat process count: $($napcatProcesses.Count)"
Write-Host "System QQ process count: $($systemQqProcesses.Count)"

$uvicornBotProcesses = $botProcesses | Where-Object { $_.CommandLine -like '*-m uvicorn bot:app*' }
if ($uvicornBotProcesses.Count -ge 2) {
    Write-Host 'Bot process note: Windows may show a parent process and a worker process for uvicorn. This is expected.'
}

if ($listeningConnection) {
    Write-Host "Bot port 8080: listening (PID $($listeningConnection.OwningProcess))"
} else {
    Write-Host 'Bot port 8080: not listening'
}

if ($establishedConnections) {
    Write-Host "Port 8080 established connections: $($establishedConnections.Count)"
    $establishedConnections |
        Select-Object LocalAddress, LocalPort, RemoteAddress, RemotePort, State, OwningProcess |
        Format-Table -AutoSize
} else {
    Write-Host 'Port 8080 established connections: 0'
}

if (Test-Path $historyPath) {
    Write-Host "Chat history file: exists ($historyPath)"
} else {
    Write-Host "Chat history file: missing ($historyPath)"
}

if ($botProcesses) {
    Write-Host 'Bot processes:'
    $botProcesses |
        Select-Object ProcessId, ExecutablePath, CommandLine |
        Format-List
}

if ($napcatProcesses) {
    Write-Host 'NapCat processes:'
    $napcatProcesses |
        Select-Object ProcessId, Name, ExecutablePath |
        Format-Table -AutoSize
}

if ($systemQqProcesses) {
    Write-Host 'System QQ processes:'
    $systemQqProcesses |
        Select-Object ProcessId, ExecutablePath |
        Format-Table -AutoSize
}