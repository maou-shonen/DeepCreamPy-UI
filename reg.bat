@echo off
set title=去TMD馬賽克
if exist %~dp0ui_opencv.exe (
	set ui=\"%~dp0ui_opencv.exe\"
)
if exist %~dp0ui_opencv.py (
	for /f %%p in ('python -c "import sys; print(sys.executable)"') do (set ui=\"%%p\" \"%~dp0ui_opencv.py\")
)

echo 失敗 請使用系統管理員執行
reg add HKCR\*\shell\%title%\command /f /d "%ui% \"%%1\""
cls
if errorlevel 1 goto failed
echo 成功
pause
exit /b

:failed
echo 失敗

pause
exit /b