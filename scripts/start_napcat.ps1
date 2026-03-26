param(
    [string]$NapCatDir = 'D:\NapCat',
    [string]$QuickLoginAccount = '3882941016',
    [switch]$DisableQuickLogin
)

if (-not (Test-Path $NapCatDir)) {
    Write-Error "NapCat directory not found: $NapCatDir"
    exit 1
}

$napcatBat = Join-Path $NapCatDir 'napcat.bat'
$napcatMainExe = Join-Path $NapCatDir 'NapCatWinBootMain.exe'

if (-not (Test-Path $napcatBat)) {
    Write-Error "NapCat launcher not found: $napcatBat"
    exit 1
}

$launcherPath = $napcatBat
$launcherArguments = ''
if (-not $DisableQuickLogin -and (Test-Path $napcatMainExe) -and $QuickLoginAccount) {
    $launcherPath = $napcatMainExe
    $launcherArguments = $QuickLoginAccount
}

$runningProcess = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
    Where-Object {
        $_.ExecutablePath -and
        $_.ExecutablePath -like "$NapCatDir*" -and
        $_.Name -eq 'NapCatWinBootMain.exe'
    } |
    Select-Object -First 1

if ($runningProcess) {
    Write-Host "NapCat is already running. PID: $($runningProcess.ProcessId)"
    exit 0
}

if ($launcherArguments) {
    Start-Process -FilePath $launcherPath -ArgumentList $launcherArguments -WorkingDirectory $NapCatDir
} else {
    Start-Process -FilePath $launcherPath -WorkingDirectory $NapCatDir
}
Write-Host "NapCat started via: $launcherPath $launcherArguments"