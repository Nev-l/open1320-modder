@echo off
echo Building 1320 Legends Car Modder...
cd /d "%~dp0"

pip install -r requirements.txt --quiet

pyinstaller 1320CarModder.spec --noconfirm

echo.
if exist "dist\1320CarModder.exe" (
    echo BUILD SUCCESS
    copy /Y "dist\1320CarModder.exe" "..\1320CarModder.exe"
    echo Copied to mods\1320CarModder.exe
) else (
    echo BUILD FAILED - check output above
)
pause
