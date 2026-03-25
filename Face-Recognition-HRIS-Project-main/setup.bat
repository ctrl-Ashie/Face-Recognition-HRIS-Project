@echo off
echo ===================================================
echo  Face Recognition HRIS - Setup ^& Installer
echo ===================================================
echo.

echo Checking for Python...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Python was not found! Please install Python and ensure it is in your PATH.
    pause
    exit /b
)

if not exist ".venv\" (
    echo Creating a new virtual environment (.venv)...
    python -m venv .venv
)

echo Activating virtual environment...
call .venv\Scripts\activate.bat

echo Upgrading pip...
python -m pip install --upgrade pip

echo Installing dependencies from requirements.txt...
pip install -r requirements.txt

echo.
echo ===================================================
echo  Installation Complete! All dependencies are ready.
echo.
echo  You can now start the applications by running:
echo   - run_main.bat     (For the Employee App)
echo   - run_admin.bat    (For the Admin App)
echo ===================================================
pause
