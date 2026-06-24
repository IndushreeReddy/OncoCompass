"""
FastAPI application: upload, job status, report download endpoints.
"""

import uuid
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

try:
    from .config import REPORTS_DIR, UPLOAD_DIR
    from .jobs import STATUS_COMPLETED, create_job, enqueue_job, get_job, start_worker
except ImportError:
    from config import REPORTS_DIR, UPLOAD_DIR
    from jobs import STATUS_COMPLETED, create_job, enqueue_job, get_job, start_worker

app = FastAPI(title="OncoCompass API", version="1.0.0")

# CORS middleware: allow React app (typically on port 3000 or 5173) to call API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
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
    Returns: {"job_id": "..."}
    """
    job_id = str(uuid.uuid4())

    job_upload_dir = UPLOAD_DIR / job_id
    job_upload_dir.mkdir(parents=True, exist_ok=True)

    original_filename = file.filename or "input"
    file_ext = Path(original_filename).suffix.lower()
    if file_ext in (".vcf", ".gz") or original_filename.endswith(".vcf.gz"):
        saved_filename = "input.vcf.gz" if original_filename.endswith(".vcf.gz") else "input.vcf"
    elif file_ext == ".txt":
        saved_filename = "input.txt"
    else:
        saved_filename = original_filename

    saved_path = job_upload_dir / saved_filename

    try:
        with open(saved_path, "wb") as f:
            content = await file.read()
            f.write(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")

    create_job(
        job_id,
        input_file_path=str(saved_path),
        skip_annotation=skip_annotation,
        original_filename=original_filename,
    )

    enqueue_job(job_id)

    return {"job_id": job_id}


@app.get("/jobs/{job_id}")
async def get_job_status(job_id: str) -> dict:
    """
    Get job status by job_id.
    Returns: {"status": "pending|running|completed|failed", "progress": "...", ...}
    """
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

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
    Download report for a completed job (PDF preferred, HTML or TXT fallback).
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

    # Prioritise PDF → HTML → TXT
    report_dir = REPORTS_DIR / job_id
    candidates = [
        (report_dir / "report.pdf",  "application/pdf",  f"onco_report_{job_id}.pdf"),
        (report_dir / "report.html", "text/html",        f"onco_report_{job_id}.html"),
        (report_dir / "report.txt",  "text/plain",       f"onco_report_{job_id}.txt"),
    ]

    file_path = media_type = filename = None
    for path, mime, fname in candidates:
        if path.exists():
            file_path, media_type, filename = path, mime, fname
            break

    # Last resort: use report_path stored on the job
    if file_path is None:
        stored = job.get("report_path")
        if stored:
            stored_path = Path(stored)
            if stored_path.exists():
                ext = stored_path.suffix.lower()
                mime_map = {".pdf": "application/pdf", ".html": "text/html", ".txt": "text/plain"}
                file_path = stored_path
                media_type = mime_map.get(ext, "application/octet-stream")
                filename = f"onco_report_{job_id}{ext}"

    if file_path is None or not file_path.exists():
        raise HTTPException(status_code=404, detail=f"Report file not found for job {job_id}")

    try:
        content = file_path.read_bytes()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read report file: {str(e)}")

    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.get("/jobs/{job_id}/report/view")
async def view_report(job_id: str) -> Response:
    """
    View HTML report inline in the browser.
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

    html_path = REPORTS_DIR / job_id / "report.html"
    if not html_path.exists():
        raise HTTPException(status_code=404, detail=f"HTML report not found for job {job_id}")

    try:
        content = html_path.read_bytes()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read report file: {str(e)}")

    return Response(
        content=content,
        media_type="text/html",
        headers={"Content-Disposition": "inline"},
    )