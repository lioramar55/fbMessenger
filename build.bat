@echo off
REM Remove previous build artifacts
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist FacebookBot.spec del FacebookBot.spec

REM Check if chromedriver.exe exists
if not exist chromedriver.exe (
    echo ChromeDriver not found. Please run setup.bat first.
    pause
    exit /b 1
)

REM Build the executable with PyInstaller
pyinstaller --clean --onefile --windowed --log-level=ERROR ^
    --add-data "chromedriver.exe;." ^
    --hidden-import=webdriver_manager.chrome ^
    --hidden-import=webdriver_manager.core.os_manager ^
    --hidden-import=webdriver_manager.core.utils ^
    --name="FacebookBot" gui.py

echo.
echo Build completed. Please make sure you have the right version of ChromeDriver in the dist folder.
echo.

pause