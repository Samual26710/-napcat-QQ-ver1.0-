param(
    [string]$ShortcutName = 'QQ Bot Launcher.lnk'
)

$startupDir = [Environment]::GetFolderPath('Startup')
$shortcutPath = Join-Path $startupDir $ShortcutName

if (Test-Path $shortcutPath) {
    Remove-Item $shortcutPath -Force
    Write-Host "已移除开机自启快捷方式: $shortcutPath"
} else {
    Write-Host "未找到开机自启快捷方式: $shortcutPath"
}