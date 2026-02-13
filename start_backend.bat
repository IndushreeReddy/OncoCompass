@echo off
echo Starting OncoCompass Backend...
echo.
echo Checking for Python 3...
python --version 2>nul | findstr /R "3\.[0-9]" >nul
if %errorlevel% neq 0 (
    echo ERROR: Python 3 is required but not found!
    echo.
    echo Please install Python 3.10+ from: https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during installation.
    echo.
    echo After installing Python 3, try running this script again.
    pause
    exit /b 1
)

cd backend
echo Installing dependencies...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo.
    echo ERROR: Failed to install dependencies!
    echo Make sure you have Python 3.10+ installed and pip is available.
    pause
    exit /b 1
)

echo.
echo Starting FastAPI server on http://localhost:8000
echo Press Ctrl+C to stop the server
echo.
cd ..
python -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
pause
