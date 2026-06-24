#!/usr/bin/env python3
"""
Optimized lung cancer variant + TMB pipeline using OncoCompass backend.
Run from project root: python scripts/run_analysis.py [options]
Or: python -m scripts.run_analysis (with OncoCompass on PYTHONPATH)
"""

import argparse
import sys
from pathlib import Path

# Ensure project root is on path when run as script
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from backend.config import DRIVER_GENES_PATH, PROJECT_ROOT
from backend.pipeline.filter_pipeline import run as filter_run
from backend.pipeline.tmb import calculate as tmb_calculate, DEFAULT_EXOME_SIZE_MB


def main() -> None:
    parser = argparse.ArgumentParser(description="OncoCompass: filter VEP output, compute TMB, export variants.")
    parser.add_argument("vep_file", nargs="?", default="SIDM00138.ds.vep.output.txt", help="VEP output .txt path")
    parser.add_argument("--driver", "-d", default=None, help="Driver genes TSV (default: config DRIVER_GENES_PATH)")
    parser.add_argument("--output", "-o", default="lung_cancer_variants_final.csv", help="Output CSV path")
    parser.add_argument("--exome-mb", type=float, default=DEFAULT_EXOME_SIZE_MB, help="Exome size in Mb for TMB")
    parser.add_argument("--no-driver-filter", action="store_true", help="Do not filter by driver genes")
    args = parser.parse_args()

    vep_path = Path(args.vep_file)
    if not vep_path.is_absolute():
        vep_path = PROJECT_ROOT / vep_path
    if not vep_path.exists():
        print(f"Error: VEP file not found: {vep_path}")
        sys.exit(1)

    driver_path = args.driver
    if driver_path is None:
        driver_path = DRIVER_GENES_PATH
    else:
        driver_path = Path(driver_path)
        if not driver_path.is_absolute():
            driver_path = PROJECT_ROOT / driver_path
    use_driver_path = driver_path if not args.no_driver_filter else None

    print("Starting lung cancer variant + TMB pipeline...\n")

    # Filter pipeline: read, filter (AF, canonical, IMPACT, driver), add Normalized_Variant
    records = filter_run(
        vep_path,
        output_path=None,
        max_af=0.01,
        canonical_only=True,
        driver_genes=None,
        driver_genes_path=use_driver_path,
        add_normalized_variant=True,
    )
    print(f"After population + canonical + driver filtering: {len(records)}")

    # TMB (non-synonymous, unique Location + UPLOADED_ALLELE)
    tmb_result = tmb_calculate(records, exome_size_mb=args.exome_mb)
    print("\n===== TMB RESULT =====")
    print(f"Mutation count: {tmb_result['mutation_count']}")
    print(f"TMB: {tmb_result['tmb']} mutations/34 Mb exome")

    # Write final CSV (Gene, Normalized_Variant, Location, Consequence)
    out_path = Path(args.output)
    if not out_path.is_absolute():
        out_path = PROJECT_ROOT / out_path
    out_path.parent.mkdir(parents=True, exist_ok=True)

    import pandas as pd
    final_df = pd.DataFrame(records)
    cols = ["SYMBOL", "Normalized_Variant", "Location", "Consequence"]
    available = [c for c in cols if c in final_df.columns]
    if "SYMBOL" in available and "SYMBOL" in final_df.columns:
        final_df = final_df[available].rename(columns={"SYMBOL": "Gene"})
    else:
        final_df = final_df[available] if available else final_df
    final_df.to_csv(out_path, index=False)

    print("\n===== PIPELINE COMPLETE =====")
    print(f"Output file: {out_path}")
    print(f"Variants exported: {len(final_df)}")


if __name__ == "__main__":
    main()
