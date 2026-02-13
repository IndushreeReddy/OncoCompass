# OncoCompass — Detailed To-Do List

Step-by-step tasks in order. Complete one step before moving to the next unless a step explicitly allows parallel work.

---

## Phase 1: Project structure

1. **Create root directories**
   - [x] Create `backend/` folder.
   - [x] Create `frontend/` folder.
   - [x] Create `scripts/` folder.
   - [x] Create `data/` folder (for VEP cache and knowledge base).

2. **Create runtime directories**
   - [x] Create `uploads/` (for uploaded files per job).
   - [x] Create `results/` (for annotated.txt, intermediates, status per job).
   - [x] Create `reports/` (for generated PDFs per job).
   - [x] Add `uploads/`, `results/`, and `reports/` to `.gitignore` if you track them as runtime-only.

3. **Backend package structure**
   - [x] Create `backend/pipeline/` folder.
   - [x] Add `backend/__init__.py` and `backend/pipeline/__init__.py` (empty or with package exports).

4. **Configuration**
   - [x] Create `.env.example` with placeholders: e.g. `UPLOAD_DIR`, `RESULTS_DIR`, `REPORTS_DIR`, `VEP_SCRIPT_PATH`, `DATA_DIR`, `KNOWLEDGE_BASE_PATH`.
   - [x] Create `backend/config.py`: load settings from environment (e.g. using `os.getenv` or `pydantic-settings`), resolve paths relative to project root.

5. **Dependencies**
   - [x] Create `backend/requirements.txt` with: `fastapi`, `uvicorn`, and any pipeline deps (e.g. `pandas` for filter, PDF library). Add pipeline dependencies as you implement each module.

---

## Phase 2: Pipeline — core modules

6. **Filter pipeline**
   - [x] Create `backend/pipeline/filter_pipeline.py`.
   - [x] Implement function that reads Annotated VCF `.txt` from a given path (e.g. `results/{job_id}/annotated.txt`).
   - [x] Apply filtering logic: remove common population variants, keep high/moderate impact, canonical transcripts, cancer driver genes (per your plan).
   - [x] Write filtered variants to a structured format (e.g. list of dicts or DataFrame) and optionally save to `results/{job_id}/filtered.csv` or similar for downstream steps.

7. **TMB calculation**
   - [ ] Create `backend/pipeline/tmb.py`.
   - [ ] Implement TMB calculation from filtered variant count (and exome size if needed).
   - [ ] Expose a function that accepts filtered variants (or path to filtered output) and returns TMB value(s).

8. **Knowledge base matching**
   - [x] Create `backend/pipeline/knowledge_base.py`.
   - [x] Load curated knowledge base from `data/` (or path from config): OncoKB, COSMIC, pharmacogenomics data.
   - [x] Implement matching logic: map variants (e.g. HGVS protein) to therapies and evidence levels.
   - [x] Expose a function that accepts filtered variants and returns matched therapies + evidence.

9. **Bash VEP script (if using raw VCF)**
   - [ ] Create `scripts/run_vep.sh`.
   - [ ] Script accepts: input VCF path, output path for Annotated VCF `.txt`.
   - [ ] Invoke VEP so output is in Annotated VCF text format and write to the given `.txt` path.
   - [ ] Ensure script is executable and uses paths from env or arguments only.

---

## Phase 3: Pipeline — orchestrator and PDF

10. **Orchestrator**
    - [x] Create `backend/pipeline/orchestrator.py`.
    - [x] Implement `run(job_id: str, input_file_path: str, skip_annotation: bool)` (or equivalent).
    - [x] If not skip_annotation and file is raw VCF: call `run_vep.sh` via `subprocess` (input VCF → `results/{job_id}/annotated.txt`).
    - [x] If skip_annotation or file is `.txt`: copy/move uploaded file to `results/{job_id}/annotated.txt` (or use as-is).
    - [x] Call filter pipeline on `results/{job_id}/annotated.txt` → filtered variants.
    - [x] Call TMB module with filtered variants → TMB value.
    - [x] Call knowledge_base module with filtered variants → therapies + evidence.
    - [x] Call report_pdf.generate(...) with filtered variants, TMB, therapies; output to `reports/{job_id}/report.pdf`.
    - [x] On any exception: re-raise or return error so job status can be set to `failed`.

11. **PDF report**
    - [ ] Create `backend/pipeline/report_pdf.py`.
    - [ ] Choose PDF library: WeasyPrint, ReportLab, or fpdf2; add to `requirements.txt`.
    - [ ] Implement `generate(filtered_variants, tmb, therapies_evidence, output_path: str)`.
    - [ ] Include in PDF: summary, TMB, table of actionable variants, associated therapies, evidence levels, biomarker notes (per plan).

---

## Phase 4: Job state and FastAPI app

12. **Job state**
    - [x] Create `backend/jobs.py`.
    - [x] Define in-memory store (e.g. dict) for job status: `job_id` → `{ "status": "pending"|"running"|"completed"|"failed", "progress": str | None, "error": str | None }`.
    - [x] Optional: add helpers to read/write `results/{job_id}/status.json` for persistence.
    - [x] Provide: `create_job()`, `get_job(job_id)`, `update_job(job_id, ...)`.

13. **Job queue and worker**
    - [x] In `backend/jobs.py` (or `backend/worker.py`): create a `queue.Queue` for job IDs.
    - [x] Implement a worker function that loops: `job_id = queue.get()` → load upload path and options for that job → call `orchestrator.run(job_id, ...)`.
    - [x] Update job status to `running` at start, `completed` or `failed` at end; set `progress` during steps if desired.
    - [x] Start the worker in a background thread when the FastAPI app starts (e.g. in `lifespan` or `on_event("startup")`).

14. **FastAPI app — upload and job routes**
    - [x] Create `backend/main.py`.
    - [x] Implement `POST /upload`: accept multipart form with `file` and optional `skip_annotation`; generate `job_id` (e.g. UUID); save file to `uploads/{job_id}/` (keep original filename or use a fixed name like `input.vcf`/`input.txt`); enqueue `job_id`; create job in job store with status `pending`; return `{ "job_id": "..." }`.
    - [x] Implement `GET /jobs/{job_id}`: return job status (status, progress, error) or 404.

15. **FastAPI app — report download and CORS**
    - [x] Implement `GET /jobs/{job_id}/report`: if job is `completed` and `reports/{job_id}/report.pdf` exists, return file (e.g. `FileResponse`); else 404 or 409.
    - [x] Add CORS middleware so the React app (e.g. on another port) can call the API.

16. **Wire worker to app**
    - [x] On app startup: start the job queue worker thread; pass it the queue and any config (paths, etc.).
    - [x] Ensure the orchestrator can resolve paths (uploads dir, results dir, reports dir) via config.

---

## Phase 5: React SPA

17. **Scaffold React app**
    - [x] Create React app under `frontend/` (e.g. `create-react-app` or Vite).
    - [x] Add `frontend/.env.example` with `REACT_APP_API_URL=http://localhost:8000` (or your backend URL).

18. **Upload page**
    - [x] Build upload UI: file input (accept VCF and .txt), optional “Skip annotation” checkbox (or infer from filename).
    - [x] On submit: `POST /upload` with form-data; on success, store `job_id` and navigate or show status section.

19. **Status and download**
    - [x] After upload, poll `GET /jobs/{job_id}` every 2–3 seconds.
    - [x] Display status: Pending, Running (optionally progress), Completed, Failed (show error if any).
    - [x] When status is `completed`, show a “Download PDF” button that requests `GET /jobs/{job_id}/report` and triggers file download (e.g. open in new tab or fetch as blob and save).

20. **Polish**
    - [x] Handle errors: upload failure, 404 for job, report not ready.
    - [x] Optional: basic styling and layout so the flow is clear for the hackathon demo.

---

## Phase 6: Chat placeholder

21. **Chat stub**
    - [ ] In `backend/main.py`, add a placeholder route (e.g. `POST /chat` or comment) and a short comment that chat will use job results and will be implemented later.
    - [ ] Optional: in React, add a placeholder “Chat” tab or section that shows “Coming soon” or is disabled.

---

## Phase 7: Documentation and run instructions

22. **README and run**
    - [ ] Update `README.md`: how to install backend deps, set `.env`, run FastAPI (e.g. `uvicorn backend.main:app`); how to install and run React (e.g. `cd frontend && npm install && npm start`); where to put VEP cache and knowledge base in `data/`.
    - [ ] Verify end-to-end: upload a small Annotated VCF .txt → job completes → PDF downloads.

---

## Summary checklist

- [ ] Phase 1: Project structure
- [ ] Phase 2: Pipeline (filter, TMB, KB, VEP script)
- [ ] Phase 3: Orchestrator + PDF report
- [ ] Phase 4: Job state, queue, worker, FastAPI routes
- [ ] Phase 5: React SPA (upload, status, download)
- [ ] Phase 6: Chat placeholder
- [ ] Phase 7: README and end-to-end test
