@echo off
echo Creating and setting up environment...

REM Create and activate virtual environment
if not exist venv (
    echo Creating virtual environment...
    python -m venv venv
)

echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Upgrade pip and install dependencies
echo Installing packages...
pip install --upgrade pip

REM Install packages one by one with pre-built wheels where possible
pip install --only-binary=:all: numpy
pip install --only-binary=:all: pandas
pip install selenium
pip install webdriver_manager
pip install ttkthemes
pip install pyinstaller

REM Create a simple spec file
echo Creating spec file...
echo from PyInstaller.building.api import * > FacebookGroupBot.spec
echo from PyInstaller.building.build_main import * >> FacebookGroupBot.spec
echo from PyInstaller.utils.hooks import collect_all >> FacebookGroupBot.spec
echo block_cipher = None >> FacebookGroupBot.spec
echo a = Analysis(['gui.py'], >> FacebookGroupBot.spec
echo             pathex=[], >> FacebookGroupBot.spec
echo             binaries=[], >> FacebookGroupBot.spec
echo             datas=[('README.md', '.'), ('requirements.txt', '.')], >> FacebookGroupBot.spec
echo             hiddenimports=[], >> FacebookGroupBot.spec
echo             hookspath=[], >> FacebookGroupBot.spec
echo             hooksconfig={}, >> FacebookGroupBot.spec
echo             runtime_hooks=[], >> FacebookGroupBot.spec
echo             excludes=[], >> FacebookGroupBot.spec
echo             win_no_prefer_redirects=False, >> FacebookGroupBot.spec
echo             win_private_assemblies=False, >> FacebookGroupBot.spec
echo             cipher=block_cipher, >> FacebookGroupBot.spec
echo             noarchive=False) >> FacebookGroupBot.spec
echo pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher) >> FacebookGroupBot.spec
echo exe = EXE(pyz, >> FacebookGroupBot.spec
echo           a.scripts, >> FacebookGroupBot.spec
echo           a.binaries, >> FacebookGroupBot.spec
echo           a.zipfiles, >> FacebookGroupBot.spec
echo           a.datas, >> FacebookGroupBot.spec
echo           [], >> FacebookGroupBot.spec
echo           name='FacebookGroupBot', >> FacebookGroupBot.spec
echo           debug=False, >> FacebookGroupBot.spec
echo           bootloader_ignore_signals=False, >> FacebookGroupBot.spec
echo           strip=False, >> FacebookGroupBot.spec
echo           upx=True, >> FacebookGroupBot.spec
echo           upx_exclude=[], >> FacebookGroupBot.spec
echo           runtime_tmpdir=None, >> FacebookGroupBot.spec
echo           console=False, >> FacebookGroupBot.spec
echo           disable_windowed_traceback=False, >> FacebookGroupBot.spec
echo           target_arch=None, >> FacebookGroupBot.spec
echo           codesign_identity=None, >> FacebookGroupBot.spec
echo           entitlements_file=None) >> FacebookGroupBot.spec

REM Build using the spec file
echo Building executable with spec file...
python -m PyInstaller FacebookGroupBot.spec

echo.
if exist "dist\FacebookGroupBot.exe" (
    echo Build successful! Executable created at dist\FacebookGroupBot.exe
    echo.
    echo Remember to distribute the following file with the executable:
    echo - members.csv (with a "Profile Link" column)
) else (
    echo Build failed! Check the output above for errors.
)

call venv\Scripts\deactivate.bat

pause 