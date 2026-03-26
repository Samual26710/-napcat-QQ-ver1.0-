param(
    [string]$NapCatDir = 'D:\NapCat',
    [string]$ShortcutName = 'QQ Bot Launcher.lnk'
)

$projectRoot = Split-Path -Parent $PSScriptRoot
$startupDir = [Environment]::GetFolderPath('Startup')
$shortcutPath = Join-Path $startupDir $ShortcutName
$launcherScript = Join-Path $PSScriptRoot 'start_all.ps1'

if (-not (Test-Path $launcherScript)) {
    Write-Error "未找到启动脚本: $launcherScript"
    exit 1
}

if (-not (Test-Path $NapCatDir)) {
    Write-Error "未找到 NapCat 目录: $NapCatDir"
    exit 1
}

$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = 'powershell.exe'
$shortcut.Arguments = "-ExecutionPolicy Bypass -WindowStyle Minimized -File `"$launcherScript`" -NapCatDir `"$NapCatDir`""
$shortcut.WorkingDirectory = $projectRoot
$shortcut.IconLocation = 'powershell.exe,0'
$shortcut.Save()

Write-Host "已创建开机自启快捷方式: $shortcutPath"