# Python 3 Installation Guide

## Problem
Your system has Python 2.7, but OncoCompass requires **Python 3.10 or higher**.

## Solution: Install Python 3

### Step 1: Download Python 3
1. Go to https://www.python.org/downloads/
2. Click "Download Python 3.x.x" (latest version)
3. Run the installer

### Step 2: During Installation
**IMPORTANT:** Check the box that says:
- ✅ **"Add Python to PATH"** or **"Add Python to environment variables"**

This is crucial! Without this, Python won't be accessible from the command line.

### Step 3: Verify Installation
Open a **new** PowerShell/Command Prompt window and run:
```bash
python --version
```

You should see something like:
```
Python 3.11.x
```

If you still see `Python 2.7.x`, Python 3 might not be in PATH. Try:
```bash
python3 --version
```

### Step 4: Install Backend Dependencies
Once Python 3 is installed, run:
```bash
cd c:\Users\VIKRANT\OncoCompass\backend
python -m pip install -r requirements.txt
```

Or use the batch file:
```bash
start_backend.bat
```

## Alternative: Use Python Launcher (Windows)

If both Python 2 and 3 are installed, you can use:
```bash
py -3 -m pip install -r requirements.txt
py -3 -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## Still Having Issues?

1. **Check if Python 3 is installed:**
   - Open PowerShell
   - Run: `Get-Command python*`
   - Look for `python.exe` or `python3.exe`

2. **Manually add Python to PATH:**
   - Find where Python 3 is installed (usually `C:\Users\YourName\AppData\Local\Programs\Python\Python3xx\`)
   - Add it to System Environment Variables PATH

3. **Use full path:**
   ```bash
   "C:\Users\YourName\AppData\Local\Programs\Python\Python3xx\python.exe" -m pip install -r requirements.txt
   ```
