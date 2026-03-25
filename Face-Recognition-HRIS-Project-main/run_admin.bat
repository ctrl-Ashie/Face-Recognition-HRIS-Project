@echo off
echo Starting Admin Application...
if not exist ".venv\" (
    echo Virtual environment not found. Please run setup.bat first!
    pause
    exit /b
)
call .venv\Scripts\activate.bat
python admin_app.py
pause
