@echo off
setlocal
set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

echo 正在手动启动 NapCat 和机器人...
powershell -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%scripts\start_all.ps1"
if errorlevel 1 (
	echo.
	echo 启动失败，请检查窗口输出。
	pause
)
endlocal