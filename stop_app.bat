@echo off
echo Stopping SEO Content Creation Agent...
echo.

REM Kill all Python processes
taskkill /F /IM python.exe 2>nul
if %errorlevel% equ 0 (
    echo Python processes stopped successfully.
) else (
    echo No Python processes were running.
)

echo.
echo All processes stopped. You can now start the app again.
pause
