"""
FastAPI application: upload, job status, report download endpoints.
"""

import uuid
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response

try:
    from .config import REPORTS_DIR, UPLOAD_DIR
    from .jobs import STATUS_COMPLETED, create_job, enqueue_job, get_job, start_worker
except ImportError:
    # Fallback for when running directly (not as package)
    from config import REPORTS_DIR, UPLOAD_DIR
    from jobs import STATUS_COMPLETED, create_job, enqueue_job, get_job, start_worker

app = FastAPI(title="OncoCompass API", version="1.0.0")

# CORS middleware: allow React app (typically on port 3000) to call API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],  # React dev servers
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    """Start the background worker thread on app startup."""
    start_worker()


@app.post("/upload")
async def upload_file(
    file: Annotated[UploadFile, File(...)],
    skip_annotation: bool = Form(default=False),
) -> dict[str, str]:
    """
    Upload a VCF or annotated .txt file for processing.
    - file: VCF file (.vcf, .vcf.gz) or annotated VCF .txt
    - skip_annotation: if True, skip VEP annotation step (assume file is pre-annotated)
    Returns: {"job_id": "..."}
    """
    # Generate unique job ID
    job_id = str(uuid.uuid4())

    # Create job directory
    job_upload_dir = UPLOAD_DIR / job_id
    job_upload_dir.mkdir(parents=True, exist_ok=True)

    # Determine filename (keep original or use input.vcf/input.txt)
    original_filename = file.filename or "input"
    file_ext = Path(original_filename).suffix.lower()
    if file_ext in (".vcf", ".gz") or original_filename.endswith(".vcf.gz"):
        saved_filename = "input.vcf.gz" if original_filename.endswith(".vcf.gz") else "input.vcf"
    elif file_ext == ".txt":
        saved_filename = "input.txt"
    else:
        saved_filename = original_filename

    saved_path = job_upload_dir / saved_filename

    # Save uploaded file
    try:
        with open(saved_path, "wb") as f:
            content = await file.read()
            f.write(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")

    # Create job entry
    create_job(
        job_id,
        input_file_path=str(saved_path),
        skip_annotation=skip_annotation,
        original_filename=original_filename,
    )

    # Enqueue job for processing
    enqueue_job(job_id)

    return {"job_id": job_id}


@app.get("/jobs/{job_id}")
async def get_job_status(job_id: str) -> dict:
    """
    Get job status by job_id.
    Returns: {"status": "pending|running|completed|failed", "progress": "...", "error": "...", ...}
    """
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    # Return only relevant fields (exclude internal fields if needed)
    return {
        "job_id": job.get("job_id", job_id),
        "status": job.get("status", "pending"),
        "progress": job.get("progress"),
        "error": job.get("error"),
        "report_path": job.get("report_path"),
        "tmb": job.get("tmb"),
        "variant_count": job.get("variant_count"),
    }


@app.get("/jobs/{job_id}/report")
async def download_report(job_id: str) -> Response:
    """
    Download report for a completed job (PDF, HTML, or TXT).
    Returns the report file if job is completed and report exists, else 404 or 409.
    """
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    status = job.get("status")
    if status != STATUS_COMPLETED:
        raise HTTPException(
            status_code=409,
            detail=f"Job {job_id} is not completed (status: {status})",
        )

    # Determine report directory
    report_dir = REPORTS_DIR / job_id
    
    # Check what file actually exists in the report directory, prioritize PDF > HTML > TXT
    pdf_path = report_dir / "report.pdf"
    html_path = report_dir / "report.html"
    txt_path = report_dir / "report.txt"
    
    file_path = None
    media_type = None
    filename = None
    
    if pdf_path.exists():
        file_path = pdf_path
        media_type = "application/pdf"
        filename = f"onco_report_{job_id}.pdf"
    elif html_path.exists():
        file_path = html_path
        media_type = "text/html"
        filename = f"onco_report_{job_id}.html"
    elif txt_path.exists():
        file_path = txt_path
        media_type = "text/plain"
        filename = f"onco_report_{job_id}.txt"
    else:
        # Last resort: check if report_path from job exists
        report_path = job.get("report_path")
        if report_path:
            report_path = Path(report_path)
            if report_path.exists():
                file_path = report_path
                ext = report_path.suffix.lower()
                if ext == ".pdf":
                    media_type = "application/pdf"
                elif ext == ".html":
                    media_type = "text/html"
                elif ext == ".txt":
                    media_type = "text/plain"
                else:
                    media_type = "application/octet-stream"
                filename = f"onco_report_{job_id}{ext}"
    
    if not file_path or not file_path.exists():
        raise HTTPException(status_code=404, detail=f"Report file not found for job {job_id}")


@app.get("/jobs/{job_id}/report/view")
async def view_report(job_id: str) -> Response:
    """
    View HTML report directly in browser (for HTML reports only).
    Opens the report in a new tab instead of downloading.
    """
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    status = job.get("status")
    if status != STATUS_COMPLETED:
        raise HTTPException(
            status_code=409,
            detail=f"Job {job_id} is not completed (status: {status})",
        )

    # Check for HTML file
    report_dir = REPORTS_DIR / job_id
    html_path = report_dir / "report.html"
    
    if not html_path.exists():
        raise HTTPException(status_code=404, detail=f"HTML report not found for job {job_id}")
    
    # Read file content
    try:
        content = html_path.read_bytes()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read report file: {str(e)}")
    
    # Return Response with inline disposition to view in browser
    return Response(
        content=content,
        media_type="text/html",
        headers={
            "Content-Disposition": 'inline',
        }
    )
    
    # Read file content
    try:
        content = file_path.read_bytes()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read report file: {str(e)}")
    
    # Return Response with explicit headers to force download
    # For HTML files, we'll use 'inline' so they can be viewed, but still downloadable
    disposition = "attachment" if media_type != "text/html" else "attachment"
    
    return Response(
        content=content,
        media_type=media_type,
        headers={
            "Content-Disposition": f'{disposition}; filename="{filename}"',
        }
    )
