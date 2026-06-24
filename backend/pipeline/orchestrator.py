"""
Pipeline orchestrator: coordinates VEP (optional), filter, TMB, KB match, PDF report.
Entry point for job processing.
"""

import shutil
import subprocess
from pathlib import Path
from typing import Any

try:
    from ..config import DRIVER_GENES_PATH, REPORTS_DIR, RESULTS_DIR, VEP_SCRIPT_PATH
except ImportError:
    from backend.config import DRIVER_GENES_PATH, REPORTS_DIR, RESULTS_DIR, VEP_SCRIPT_PATH

from .filter_pipeline import run as filter_run
from .knowledge_base import match as kb_match
from .tmb import calculate as tmb_calculate


def _is_vcf_file(path: Path) -> bool:
    """Check if file is raw VCF (.vcf or .vcf.gz)."""
    return path.suffix.lower() in (".vcf", ".gz") or path.name.endswith(".vcf.gz")


def run(
    job_id: str,
    input_file_path: str | Path,
    skip_annotation: bool = False,
    *,
    driver_genes_path: str | Path | None = None,
    exome_size_mb: float = 34.0,
) -> dict[str, Any]:
    """
    Run full pipeline for a job.
    - job_id: unique job identifier
    - input_file_path: path to uploaded file (VCF or annotated .txt)
    - skip_annotation: if True, skip VEP step (assume file is already annotated)
    - driver_genes_path: optional path to driver genes TSV (default: config DRIVER_GENES_PATH)
    - exome_size_mb: exome size for TMB calculation (default: 34.0)

    Returns dict with:
    - "status": "completed" or "failed"
    - "report_path": path to PDF report (if successful)
    - "error": error message (if failed)
    - "tmb": TMB result dict (if successful)
    - "variant_count": number of filtered variants (if successful)
    """
    input_file_path = Path(input_file_path)
    if not input_file_path.exists():
        return {"status": "failed", "error": f"Input file not found: {input_file_path}"}

    job_results_dir = RESULTS_DIR / job_id
    job_reports_dir = REPORTS_DIR / job_id
    annotated_txt = job_results_dir / "annotated.txt"
    report_pdf = job_reports_dir / "report.pdf"

    try:
        # Create job directories
        job_results_dir.mkdir(parents=True, exist_ok=True)
        job_reports_dir.mkdir(parents=True, exist_ok=True)

        # Step 1: VEP annotation (if needed)
        if not skip_annotation and _is_vcf_file(input_file_path):
            # Run VEP bash script: input VCF → annotated.txt
            if not VEP_SCRIPT_PATH.exists():
                return {
                    "status": "failed",
                    "error": f"VEP script not found: {VEP_SCRIPT_PATH}",
                }
            cmd = [
                "bash",
                str(VEP_SCRIPT_PATH),
                str(input_file_path),
                str(annotated_txt),
            ]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False,
                cwd=VEP_SCRIPT_PATH.parent.parent,
            )
            if result.returncode != 0:
                return {
                    "status": "failed",
                    "error": f"VEP annotation failed: {result.stderr}",
                }
        else:
            # Pre-annotated: copy/move to results/{job_id}/annotated.txt
            shutil.copy2(input_file_path, annotated_txt)

        # Step 2: Filter pipeline
        driver_path = driver_genes_path or DRIVER_GENES_PATH
        try:
            filtered_variants = filter_run(
                annotated_txt,
                output_path=job_results_dir / "filtered.csv",
                max_af=0.01,
                canonical_only=True,
                driver_genes=None,
                driver_genes_path=driver_path if driver_path.exists() else None,
                add_normalized_variant=True,
            )
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            return {
                "status": "failed",
                "error": f"Filter pipeline error: {str(e)}\nDetails: {error_details[:500]}",
            }

        # Step 3: TMB calculation
        tmb_result = tmb_calculate(filtered_variants, exome_size_mb=exome_size_mb)

        # Step 4: Knowledge base matching
        try:
            variants_with_therapies = kb_match(filtered_variants)
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            return {
                "status": "failed",
                "error": f"Knowledge base matching error: {str(e)}\nDetails: {error_details[:500]}",
            }

        # Step 5: PDF report generation
        try:
            from .report_pdf import generate as generate_pdf

            generate_pdf(
                variants_with_therapies,
                tmb_result,
                output_path=report_pdf,
                job_id=job_id,
            )
            # Check if PDF was created, if not, use HTML fallback
            html_path = report_pdf.with_suffix(".html")
            if not report_pdf.exists() and html_path.exists():
                report_pdf = html_path  # Use HTML instead
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            # Try HTML fallback
            html_path = report_pdf.with_suffix(".html")
            if html_path.exists():
                report_pdf = html_path  # Use HTML instead
            else:
                return {
                    "status": "failed",
                    "error": f"Report generation error: {str(e)}\nDetails: {error_details[:500]}",
                }

        return {
            "status": "completed",
            "report_path": str(report_pdf),  # Ensure it's a string, not Path object
            "tmb": tmb_result,
            "variant_count": len(filtered_variants),
        }

    except subprocess.CalledProcessError as e:
        return {"status": "failed", "error": f"Subprocess error: {e.stderr}"}
    except Exception as e:
        return {"status": "failed", "error": f"Pipeline error: {str(e)}"}
