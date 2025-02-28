@echo off
echo Installing required packages...
pip install -r requirements.txt

echo.
echo Setting up ChromeDriver...
python setup_chromedriver.py

echo.
echo Press any key to exit...
pause 