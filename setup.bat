@echo off
echo ============================================
echo  OncoCompass - First-time setup
echo ============================================

REM -- Copy .env files if they don't exist --
if not exist .env (
    copy .env.example .env
    echo [OK] Created .env from .env.example
) else (
    echo [SKIP] .env already exists
)

if not exist frontend\.env (
    copy frontend\.env.example frontend\.env
    echo [OK] Created frontend\.env from frontend\.env.example
) else (
    echo [SKIP] frontend\.env already exists
)

REM -- Create runtime directories --
if not exist uploads mkdir uploads
if not exist results mkdir results
if not exist reports mkdir reports
echo [OK] Runtime directories ready

REM -- Install Python dependencies --
echo.
echo Installing Python dependencies...
pip install -r backend\requirements.txt
if errorlevel 1 (
    echo [ERROR] pip install failed. Make sure Python 3.10+ is on your PATH.
    pause
    exit /b 1
)
echo [OK] Python dependencies installed

REM -- Install Node dependencies --
echo.
echo Installing frontend dependencies...
cd frontend
call npm install
if errorlevel 1 (
    echo [ERROR] npm install failed. Make sure Node.js 18+ is on your PATH.
    cd ..
    pause
    exit /b 1
)
cd ..
echo [OK] Frontend dependencies installed

echo.
echo ============================================
echo  Setup complete!
echo  Run start_backend.bat in one terminal,
echo  then start_frontend.bat in another.
echo ============================================
pause