# How to Run OncoCompass

## Frontend (React) - Already Starting! 🚀

The frontend is starting up and will be available at **http://localhost:3000**

It should open automatically in your browser.

## Backend (FastAPI) - Need to Start

**You need Python 3.10+ installed.** If you don't have it:

1. Download from https://www.python.org/downloads/
2. Make sure to check "Add Python to PATH" during installation

Then, open a **new terminal** and run:

### Windows:
```bash
cd c:\Users\VIKRANT\OncoCompass\backend
python -m pip install -r requirements.txt
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Or use the batch file:
```bash
start_backend.bat
```

The backend will run at **http://localhost:8000**

## Once Both Are Running:

1. Frontend: http://localhost:3000 (React app)
2. Backend: http://localhost:8000 (FastAPI API)

Open http://localhost:3000 in your browser and start uploading VCF files!

## Troubleshooting

- **Backend won't start**: Make sure Python 3.10+ is installed and in PATH
- **Frontend can't connect**: Make sure backend is running on port 8000
- **Port already in use**: Change ports in `vite.config.js` (frontend) or `uvicorn` command (backend)
