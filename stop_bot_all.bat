@echo off
setlocal
set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

echo 正在停止 NapCat 和机器人...
powershell -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%scripts\stop_all.ps1"
pause
endlocal