# Quick Start Guide

## The Problem
When running `python -m uvicorn main:app` from the `backend` directory, you get:
```
ImportError: attempted relative import with no known parent package
```

## The Solution

Run uvicorn from the **project root** (not from the backend directory):

### From Project Root:
```bash
cd c:\Users\VIKRANT\OncoCompass
python -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

### Or use the batch file:
Double-click `start_backend.bat` (I've updated it to run from the correct directory)

## Complete Startup Steps

1. **Start Backend** (from project root):
   ```bash
   cd c:\Users\VIKRANT\OncoCompass
   python -m pip install -r backend/requirements.txt
   python -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
   ```

2. **Start Frontend** (already running):
   - Should be at http://localhost:3000
   - If not, run: `cd frontend && npm run dev`

3. **Open Browser**:
   - Go to http://localhost:3000
   - Upload a VCF file and watch it process!

## Why This Happens

Python's relative imports (like `from .config import ...`) only work when the module is part of a package. When you run `uvicorn main:app` from inside `backend/`, Python doesn't see `backend` as a package. Running from the project root with `backend.main:app` fixes this.
