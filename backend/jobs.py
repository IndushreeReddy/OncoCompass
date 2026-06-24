"""
Job state management: in-memory store with optional persistence to filesystem.
Thread-safe for use with FastAPI and background worker thread.
"""

import json
import queue
import threading
from pathlib import Path
from typing import Any

try:
    from .config import RESULTS_DIR, UPLOAD_DIR
except ImportError:
    from backend.config import RESULTS_DIR, UPLOAD_DIR

# In-memory job store: job_id -> status dict
_jobs: dict[str, dict[str, Any]] = {}
_lock = threading.Lock()

# Job queue: holds job_id strings
_job_queue: queue.Queue[str] = queue.Queue()

# Worker thread control
_worker_thread: threading.Thread | None = None
_worker_running = False

# Job status values
STATUS_PENDING = "pending"
STATUS_RUNNING = "running"
STATUS_COMPLETED = "completed"
STATUS_FAILED = "failed"


def create_job(job_id: str, **kwargs: Any) -> dict[str, Any]:
    """
    Create a new job entry.
    Returns the job status dict.
    """
    with _lock:
        job = {
            "job_id": job_id,
            "status": STATUS_PENDING,
            "progress": None,
            "error": None,
            **kwargs,
        }
        _jobs[job_id] = job
        _persist_job(job_id, job)
        return job.copy()


def get_job(job_id: str) -> dict[str, Any] | None:
    """
    Get job status by job_id.
    Returns None if job not found.
    """
    with _lock:
        job = _jobs.get(job_id)
        if job:
            return job.copy()
        # Try loading from disk if not in memory
        return _load_job_from_disk(job_id)


def update_job(
    job_id: str,
    *,
    status: str | None = None,
    progress: str | None = None,
    error: str | None = None,
    **kwargs: Any,
) -> dict[str, Any] | None:
    """
    Update job status fields.
    - status: "pending" | "running" | "completed" | "failed"
    - progress: optional progress message
    - error: optional error message
    - **kwargs: any additional fields to update
    Returns updated job dict or None if job not found.
    """
    with _lock:
        if job_id not in _jobs:
            # Try loading from disk
            job = _load_job_from_disk(job_id)
            if job:
                _jobs[job_id] = job
            else:
                return None

        job = _jobs[job_id]
        if status is not None:
            job["status"] = status
        if progress is not None:
            job["progress"] = progress
        if error is not None:
            job["error"] = error
        job.update(kwargs)
        _persist_job(job_id, job)
        return job.copy()


def delete_job(job_id: str) -> bool:
    """
    Remove job from memory (and optionally delete status.json).
    Returns True if job existed and was deleted.
    """
    with _lock:
        if job_id in _jobs:
            del _jobs[job_id]
            status_file = RESULTS_DIR / job_id / "status.json"
            if status_file.exists():
                try:
                    status_file.unlink()
                except OSError:
                    pass
            return True
        return False


def list_jobs() -> list[dict[str, Any]]:
    """List all jobs (in-memory only)."""
    with _lock:
        return [job.copy() for job in _jobs.values()]


def _persist_job(job_id: str, job: dict[str, Any]) -> None:
    """Write job status to results/{job_id}/status.json."""
    try:
        status_file = RESULTS_DIR / job_id / "status.json"
        status_file.parent.mkdir(parents=True, exist_ok=True)
        # Only persist essential fields
        persisted = {
            "job_id": job.get("job_id", job_id),
            "status": job.get("status", STATUS_PENDING),
            "progress": job.get("progress"),
            "error": job.get("error"),
        }
        status_file.write_text(json.dumps(persisted, indent=2), encoding="utf-8")
    except (OSError, json.JSONEncodeError):
        # Silently fail persistence (in-memory still works)
        pass


def _load_job_from_disk(job_id: str) -> dict[str, Any] | None:
    """Load job status from results/{job_id}/status.json if it exists."""
    try:
        status_file = RESULTS_DIR / job_id / "status.json"
        if status_file.exists():
            data = json.loads(status_file.read_text(encoding="utf-8"))
            # Restore to in-memory store
            _jobs[job_id] = data
            return data.copy()
    except (OSError, json.JSONDecodeError):
        pass
    return None


def enqueue_job(job_id: str) -> None:
    """Add job_id to the processing queue."""
    _job_queue.put(job_id)


def _worker_loop() -> None:
    """Background worker: process jobs from queue."""
    global _worker_running
    _worker_running = True

    try:
        from .pipeline.orchestrator import run as orchestrator_run
    except ImportError:
        from backend.pipeline.orchestrator import run as orchestrator_run

    while _worker_running:
        try:
            # Get job_id from queue (blocks until available or timeout)
            job_id = _job_queue.get(timeout=1.0)
        except queue.Empty:
            continue

        try:
            # Load job details
            job = get_job(job_id)
            if not job:
                continue

            input_file_path = job.get("input_file_path")
            if not input_file_path:
                update_job(job_id, status=STATUS_FAILED, error="Missing input_file_path")
                continue

            input_path = Path(input_file_path)
            if not input_path.is_absolute():
                # Assume it's relative to UPLOAD_DIR
                input_path = UPLOAD_DIR / job_id / input_path.name

            skip_annotation = job.get("skip_annotation", False)
            driver_genes_path = job.get("driver_genes_path")
            exome_size_mb = job.get("exome_size_mb", 34.0)

            # Update status to running
            update_job(job_id, status=STATUS_RUNNING, progress="Starting pipeline...")

            # Run orchestrator
            result = orchestrator_run(
                job_id,
                input_path,
                skip_annotation=skip_annotation,
                driver_genes_path=driver_genes_path,
                exome_size_mb=exome_size_mb,
            )

            # Update job based on orchestrator result
            if result.get("status") == "completed":
                update_job(
                    job_id,
                    status=STATUS_COMPLETED,
                    progress="Pipeline completed",
                    report_path=str(result.get("report_path", "")),
                    tmb=result.get("tmb"),
                    variant_count=result.get("variant_count"),
                )
            else:
                update_job(
                    job_id,
                    status=STATUS_FAILED,
                    error=result.get("error", "Pipeline failed"),
                )

        except Exception as e:
            update_job(job_id, status=STATUS_FAILED, error=f"Worker error: {str(e)}")
        finally:
            _job_queue.task_done()


def start_worker() -> None:
    """Start the background worker thread."""
    global _worker_thread, _worker_running
    if _worker_thread is None or not _worker_thread.is_alive():
        _worker_running = True
        _worker_thread = threading.Thread(target=_worker_loop, daemon=True, name="JobWorker")
        _worker_thread.start()


def stop_worker() -> None:
    """Stop the background worker thread (waits for current job to finish)."""
    global _worker_running, _worker_thread
    _worker_running = False
    if _worker_thread and _worker_thread.is_alive():
        _worker_thread.join(timeout=5.0)
