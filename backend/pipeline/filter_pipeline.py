"""
Filter pipeline: read Annotated VCF .txt, apply clinical filters, output structured variants.
Filters: remove common population variants, keep high/moderate impact,
canonical transcripts, optionally prioritize cancer driver genes.
"""

import json
from pathlib import Path
from typing import Any

import pandas as pd

# Default max population AF (1%) above which variants are excluded
DEFAULT_MAX_AF = 0.01
# IMPACT values to keep (VEP: HIGH, MODERATE)
KEEP_IMPACTS = {"HIGH", "MODERATE"}


def read_annotated_txt(path: str | Path) -> pd.DataFrame:
    """
    Read Annotated VCF .txt (VEP-style tab-separated).
    Skips comment lines (##); line starting with # is the header.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Annotated file not found: {path}")

    with open(path, encoding="utf-8", errors="replace") as f:
        lines = [line for line in f if line.startswith("#")]
    if not lines:
        raise ValueError(f"No header line found in {path}")

    # Last #-line is the header (column names)
    header_line = lines[-1].lstrip("#").strip()
    col_names = [c.strip() for c in header_line.split("\t")]

    df = pd.read_csv(path, sep="\t", comment="#", header=None, names=col_names, low_memory=False)
    return df


def _normalize_column_names(df: pd.DataFrame) -> pd.DataFrame:
    """Ensure we can find columns case-insensitively / with common VEP names."""
    col_map = {c: c for c in df.columns}
    lower = {c.lower(): c for c in df.columns}
    # Common VEP / gnomAD names
    aliases = [
        ("impact", "IMPACT"),
        ("gnomad_af", "gnomAD_AF"),
        ("gnomadg_af", "gnomADg_AF"),
        ("gnomade_af", "gnomADe_AF"),
        ("af", "AF"),
        ("existing_variation", "Existing_variation"),
        ("symbol", "SYMBOL"),
        ("gene", "Gene"),
        ("consequence", "Consequence"),
        ("canonical", "CANONICAL"),
        ("hgvsp", "HGVSp"),
        ("hgvsc", "HGVSc"),
    ]
    for alias, preferred in aliases:
        if alias in lower and preferred not in col_map:
            col_map[lower[alias]] = preferred
    return df.rename(columns={c: col_map.get(c, c) for c in df.columns})


def filter_variants(
    df: pd.DataFrame,
    *,
    max_af: float = DEFAULT_MAX_AF,
    keep_impacts: set[str] | None = None,
    canonical_only: bool = True,
    driver_genes: set[str] | None = None,
) -> pd.DataFrame:
    """
    Apply filters to annotated variant DataFrame.
    - max_af: exclude rows where any AF column > this (e.g. 0.01 = 1%).
    - keep_impacts: set of IMPACT values to keep (default HIGH, MODERATE).
    - canonical_only: if True and CANONICAL column exists, keep only CANONICAL == 'YES'.
    - driver_genes: if set, keep only variants in these genes (SYMBOL or Gene); None = no gene filter.
    """
    keep_impacts = keep_impacts or KEEP_IMPACTS
    out = df.copy()
    
    # Return empty DataFrame if input is empty
    if len(out) == 0:
        return out
    
    out = _normalize_column_names(out)

    # Population frequency: exclude if any AF column > max_af
    # Match working code pattern: filter column-by-column using simple boolean indexing
    # Priority: gnomADe_AF (main), then other AF columns
    af_cols = [c for c in out.columns if "af" in c.lower() or c in ("AF", "gnomAD_AF", "gnomADg_AF", "gnomADe_AF")]
    # #region agent log
    try:
        with open(r'c:\Users\VIKRANT\OncoCompass\.cursor\debug.log', 'a') as f:
            f.write(json.dumps({"location": "filter_pipeline.py:91", "message": "AF filtering start", "data": {"af_cols": af_cols, "df_len": len(out)}, "timestamp": pd.Timestamp.now().timestamp()}) + '\n')
    except: pass
    # #endregion
    if af_cols and len(out) > 0:
        # Prefer gnomADe_AF (matches working code), fallback to first AF column
        primary_af = "gnomADe_AF" if "gnomADe_AF" in out.columns else (af_cols[0] if af_cols else None)
        # #region agent log
        try:
            with open(r'c:\Users\VIKRANT\OncoCompass\.cursor\debug.log', 'a') as f:
                f.write(json.dumps({"location": "filter_pipeline.py:95", "message": "Using primary AF column", "data": {"primary_af": primary_af}, "timestamp": pd.Timestamp.now().timestamp()}) + '\n')
        except: pass
        # #endregion
        if primary_af and primary_af in out.columns:
            # Match working code: replace "-", convert to float, filter with simple boolean indexing
            out[primary_af] = out[primary_af].replace("-", 0).replace("", 0)
            out[primary_af] = pd.to_numeric(out[primary_af], errors="coerce").fillna(0).astype(float)
            # #region agent log
            try:
                with open(r'c:\Users\VIKRANT\OncoCompass\.cursor\debug.log', 'a') as f:
                    f.write(json.dumps({"location": "filter_pipeline.py:100", "message": "Before filtering", "data": {"df_len": len(out), "af_col": primary_af, "max_af": max_af}, "timestamp": pd.Timestamp.now().timestamp()}) + '\n')
            except: pass
            # #endregion
            # Simple boolean filter like working code: df = df[df["gnomADe_AF"] < 0.01]
            out = out[out[primary_af] < max_af]
            # #region agent log
            try:
                with open(r'c:\Users\VIKRANT\OncoCompass\.cursor\debug.log', 'a') as f:
                    f.write(json.dumps({"location": "filter_pipeline.py:103", "message": "After filtering", "data": {"df_len": len(out)}, "timestamp": pd.Timestamp.now().timestamp()}) + '\n')
            except: pass
            # #endregion
            out = out.reset_index(drop=True)

    # IMPACT
    if "IMPACT" in out.columns:
        out = out[out["IMPACT"].astype(str).str.upper().isin(keep_impacts)]
        out = out.reset_index(drop=True)

    # Canonical transcript
    if canonical_only and "CANONICAL" in out.columns:
        out = out[out["CANONICAL"].astype(str).str.upper() == "YES"]
        out = out.reset_index(drop=True)

    # Cancer driver genes (optional)
    if driver_genes:
        symbol_col = "SYMBOL" if "SYMBOL" in out.columns else ("Gene" if "Gene" in out.columns else None)
        if symbol_col:
            out = out[out[symbol_col].astype(str).isin(driver_genes)]
            out = out.reset_index(drop=True)

    return out


def load_driver_genes_from_tsv(path: str | Path, symbol_column: str = "Symbol") -> set[str]:
    """Load driver gene symbols from IntOGen-style TSV (e.g. IntOGen-DriverGenes_LUAD.tsv)."""
    path = Path(path)
    if not path.exists():
        return set()
    df = pd.read_csv(path, sep="\t", low_memory=False)
    if symbol_column not in df.columns:
        symbol_column = df.columns[0]
    return set(df[symbol_column].dropna().astype(str).unique())


def run(
    annotated_txt_path: str | Path,
    *,
    output_path: str | Path | None = None,
    max_af: float = DEFAULT_MAX_AF,
    canonical_only: bool = True,
    driver_genes: set[str] | None = None,
    driver_genes_path: str | Path | None = None,
    symbol_column: str = "Symbol",
    add_normalized_variant: bool = True,
) -> list[dict[str, Any]]:
    """
    Read Annotated VCF .txt, apply filters, optionally save to CSV.
    If driver_genes_path is set, load driver genes from that TSV (column Symbol).
    If add_normalized_variant is True, add Normalized_Variant (Gene:p.X123Y) for KB matching.
    Returns list of dicts (one per filtered variant) for downstream TMB and KB.
    """
    if driver_genes_path and (driver_genes is None or len(driver_genes) == 0):
        driver_genes = load_driver_genes_from_tsv(driver_genes_path, symbol_column=symbol_column)

    df = read_annotated_txt(annotated_txt_path)
    filtered = filter_variants(
        df,
        max_af=max_af,
        canonical_only=canonical_only,
        driver_genes=driver_genes,
    )
    records = filtered.to_dict(orient="records")

    if add_normalized_variant:
        from .variant_utils import normalize_variant
        symbol_col = "SYMBOL" if "SYMBOL" in filtered.columns else "Gene"
        hgvsp_col = "HGVSp" if "HGVSp" in filtered.columns else "HGVSp"
        for i, row in enumerate(records):
            gene = row.get(symbol_col) if symbol_col in row else None
            hgvs = row.get(hgvsp_col) if hgvsp_col in row else None
            records[i]["Normalized_Variant"] = normalize_variant(gene, hgvs)

    if output_path:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(records).to_csv(output_path, index=False)

    return records
