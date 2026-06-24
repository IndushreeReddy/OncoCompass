#!/usr/bin/env bash
set -e

echo "============================================"
echo " OncoCompass - First-time setup"
echo "============================================"

# -- Copy .env files if they don't exist --
if [ ! -f .env ]; then
    cp .env.example .env
    echo "[OK] Created .env from .env.example"
else
    echo "[SKIP] .env already exists"
fi

if [ ! -f frontend/.env ]; then
    cp frontend/.env.example frontend/.env
    echo "[OK] Created frontend/.env from frontend/.env.example"
else
    echo "[SKIP] frontend/.env already exists"
fi

# -- Create runtime directories --
mkdir -p uploads results reports
echo "[OK] Runtime directories ready"

# -- Install Python dependencies --
echo ""
echo "Installing Python dependencies..."
pip install -r backend/requirements.txt
echo "[OK] Python dependencies installed"

# -- Install Node dependencies --
echo ""
echo "Installing frontend dependencies..."
cd frontend && npm install && cd ..
echo "[OK] Frontend dependencies installed"

echo ""
echo "============================================"
echo " Setup complete!"
echo " In one terminal:   cd backend && uvicorn main:app --reload --port 8000"
echo " In another:        cd frontend && npm run dev"
echo "============================================"