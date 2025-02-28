@echo off
echo Installing required packages...
pip install -r requirements.txt

echo.
echo Building executable...
pyinstaller --onefile ^
    --name "FacebookGroupBot" ^
    --add-data "README.md;." ^
    --add-data "requirements.txt;." ^
    --noconsole ^
    --icon NONE ^
    --clean ^
    gui.py

echo.
if exist "dist\FacebookGroupBot.exe" (
    echo Build successful! Executable created at dist\FacebookGroupBot.exe
    echo.
    echo Remember to distribute the following file with the executable:
    echo - members.csv (with a "Profile Link" column)
) else (
    echo Build failed! Check the output above for errors.
)

pause 