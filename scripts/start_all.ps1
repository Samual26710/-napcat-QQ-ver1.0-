param(
    [string]$NapCatDir = 'D:\NapCat',
    [int]$NapCatWaitSeconds = 8
)

$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot

powershell -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot 'start_napcat.ps1') -NapCatDir $NapCatDir
Start-Sleep -Seconds $NapCatWaitSeconds
powershell -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot 'start_bot.ps1')