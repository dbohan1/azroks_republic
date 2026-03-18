@echo off
cd /d "%~dp0"
echo Building AzroksRepublic.exe...
py -m PyInstaller --onefile --windowed --name AzroksRepublic azroks_republic.py
if errorlevel 1 (
    echo.
    echo BUILD FAILED. See errors above.
    pause
    exit /b 1
)
echo.
echo Copying to build\AzroksRepublic.exe...
copy /y "dist\AzroksRepublic.exe" "build\AzroksRepublic.exe"
echo Done!
pause
