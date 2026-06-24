"""Load settings from environment; resolve paths relative to project root."""

import os
from pathlib import Path

# Project root: directory containing backend/
PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _resolve_path(env_key: str, default_subpath: str) -> Path:
    """Resolve path from env; if relative, resolve against PROJECT_ROOT."""
    raw = os.getenv(env_key)
    if raw is None:
        raw = default_subpath
    p = Path(raw)
    if not p.is_absolute():
        p = PROJECT_ROOT / p
    return p.resolve()


# Runtime directories
UPLOAD_DIR = _resolve_path("UPLOAD_DIR", "uploads")
RESULTS_DIR = _resolve_path("RESULTS_DIR", "results")
REPORTS_DIR = _resolve_path("REPORTS_DIR", "reports")

# VEP script
VEP_SCRIPT_PATH = _resolve_path("VEP_SCRIPT_PATH", "scripts/run_vep.sh")

# Data and knowledge base
DATA_DIR = _resolve_path("DATA_DIR", "data")
KNOWLEDGE_BASE_PATH = _resolve_path("KNOWLEDGE_BASE_PATH", "data/knowledge_base")
# Optional: IntOGen-style driver genes TSV (column Symbol)
DRIVER_GENES_PATH = _resolve_path("DRIVER_GENES_PATH", "data/IntOGen-DriverGenes_LUAD.tsv")

# ── Auto-create runtime directories so cloners don't hit FileNotFoundError ──
for _dir in (UPLOAD_DIR, RESULTS_DIR, REPORTS_DIR):
    _dir.mkdir(parents=True, exist_ok=True)