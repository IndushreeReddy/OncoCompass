# OncoCompass - Precision Oncology Platform

A precision oncology platform that analyzes cancer genomic data and provides personalized therapy recommendations based on clinically relevant variants.

## Quick Start
1. Download or clone this repo
2. Double-click `setup.bat` (Windows) or run `bash setup.sh` (Mac/Linux)
3. That's it — it installs everything automatically

### Prerequisites

- **Python 3.10+** (for backend)
- **Node.js 18+** (for frontend)
- **VEP** (Ensembl Variant Effect Predictor) - if processing raw VCF files

### Installation & Running

#### Option 1: Use Batch Scripts (Windows)

1. **Start Backend** (in one terminal):
   ```bash
   start_backend.bat
   ```
   Backend will run at `http://localhost:8000`

2. **Start Frontend** (in another terminal):
   ```bash
   start_frontend.bat
   ```
   Frontend will run at `http://localhost:3000` and open automatically

#### Option 2: Manual Setup

**Backend:**

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**Frontend:**

```bash
cd frontend
npm install
npm run dev
```

### Known Issues & Fixes

- **NumPy crash on startup** — If you see `AttributeError: _ARRAY_API not found`, run:
  ```bash
  pip uninstall numpy -y
  pip install "numpy<2.0"
  pip install -r backend/requirements.txt
  ```
- **WeasyPrint / PDF** — WeasyPrint requires GTK+ system libraries on Windows. If unavailable, reports are automatically saved as HTML instead — this is normal behaviour.

### Testing with Sample Files

Two pre-annotated sample files are included so you can test the platform immediately **without needing VEP installed**.

| Sample | Filename |
|--------|----------|
| SIDM00138 | `data/SIDM00138.txt` |
| SIDM01067 | `data/SIDM01067.txt` |

**How to use them:**
1. Start the backend and frontend
2. Open `http://localhost:3000` in your browser
3. Click **Upload** and select either `SIDM00138.txt` or `SIDM01067.txt` from the `data/` folder
4. ✅ Check **"Skip annotation"** — these files are already annotated
5. Click **Upload and Process**
6. Wait for processing to complete
7. Download the report

### Usage

1. Open `http://localhost:3000` in your browser
2. Upload a VCF file (`.vcf`, `.vcf.gz`) or pre-annotated `.txt` file
3. Optionally check "Skip annotation" if your file is already annotated
4. Wait for processing (status updates automatically)
5. Download the PDF report when completed

### API Endpoints

- `POST /upload` - Upload VCF or annotated .txt file
- `GET /jobs/{job_id}` - Get job status
- `GET /jobs/{job_id}/report` - Download PDF report

### Project Structure

```
OncoCompass/
├── backend/           # FastAPI backend
│   ├── main.py       # API routes
│   ├── jobs.py       # Job state & worker
│   ├── config.py     # Configuration
│   └── pipeline/     # Pipeline modules
├── frontend/         # React SPA
│   └── src/
├── scripts/          # Bash scripts (VEP)
├── data/             # Knowledge base, driver genes, sample files
│   ├── SIDM00138.txt # Sample test file 1
│   ├── SIDM01067.txt # Sample test file 2
│   ├── knowledge_base.tsv
│   └── IntOGen-DriverGenes_LUAD.tsv
├── uploads/          # Runtime: uploaded files
├── results/          # Runtime: pipeline results
└── reports/          # Runtime: PDF reports
```

### Configuration

Copy `.env.example` to `.env` and adjust paths if needed:
- `UPLOAD_DIR`, `RESULTS_DIR`, `REPORTS_DIR`
- `VEP_SCRIPT_PATH`
- `DRIVER_GENES_PATH`
- `KNOWLEDGE_BASE_PATH`

### Notes

- The backend worker thread starts automatically when the FastAPI app starts
- Jobs are processed in the background
- Status polling happens every 2.5 seconds
- PDF reports are generated using WeasyPrint (falls back to HTML if not available)