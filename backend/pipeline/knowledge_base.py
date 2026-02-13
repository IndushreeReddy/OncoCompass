"""
Knowledge base matching: map variants (normalized HGVS / gene) to therapies and evidence.
Loads curated data from OncoKB, COSMIC, pharmacogenomics (TSV/CSV in data/).
"""

from pathlib import Path
from typing import Any

import pandas as pd


# Default column names for KB file (TSV/CSV)
GENE_COL = "Gene"
VARIANT_COL = "Variant"  # Normalized form e.g. EGFR:p.L858R; optional for gene-only match
THERAPY_COL = "Therapy"
EVIDENCE_COL = "Evidence_Level"
SOURCE_COL = "Source"


def load_knowledge_base(path: str | Path | None = None) -> pd.DataFrame:
    """
    Load knowledge base from path (TSV or CSV).
    Expected columns: Gene, Variant (optional), Therapy, Evidence_Level (optional), Source (optional).
    If path is a directory, looks for knowledge_base.tsv or knowledge_base.csv inside.
    """
    if path is None:
        try:
            from backend.config import KNOWLEDGE_BASE_PATH
        except ImportError:
            from ..config import KNOWLEDGE_BASE_PATH
        path = KNOWLEDGE_BASE_PATH

    path = Path(path)
    to_try: list[Path] = []
    if path.is_file():
        to_try = [path]
    elif path.is_dir():
        to_try = [path / "knowledge_base.tsv", path / "knowledge_base.csv", path / "therapies.tsv"]
    else:
        # No extension or path doesn't exist yet: try .tsv then .csv
        to_try = [path.with_suffix(".tsv"), path.with_suffix(".csv"), path]

    for p in to_try:
        if p.exists():
            sep = "\t" if p.suffix.lower() == ".tsv" else ","
            df = pd.read_csv(p, sep=sep, low_memory=False)
            # Normalize column names (allow Symbol vs Gene)
            col_map = {c: c for c in df.columns}
            for alias, preferred in [("symbol", GENE_COL), ("drug", THERAPY_COL), ("evidence", EVIDENCE_COL)]:
                for c in df.columns:
                    if c.strip().lower() == alias and preferred not in col_map:
                        col_map[c] = preferred
                        break
            return df.rename(columns=col_map)

    return pd.DataFrame()


def match(
    filtered_variants: list[dict[str, Any]],
    kb_path: str | Path | None = None,
    *,
    gene_key: str = "SYMBOL",
    normalized_variant_key: str = "Normalized_Variant",
) -> list[dict[str, Any]]:
    """
    For each filtered variant, find matching therapies from the knowledge base.
    Matching: exact Normalized_Variant, or Gene match if variant not in KB.
    Returns list of same length as filtered_variants; each item is the variant dict
    plus "matched_therapies": [ {"therapy": str, "evidence_level": str, "source": str}, ... ].
    """
    kb = load_knowledge_base(kb_path)
    if kb.empty:
        return [
            {**v, "matched_therapies": []}
            for v in filtered_variants
        ]

    # Ensure we have required columns
    if GENE_COL not in kb.columns:
        if "Symbol" in kb.columns:
            kb = kb.rename(columns={"Symbol": GENE_COL})
        else:
            return [{**v, "matched_therapies": []} for v in filtered_variants]
    if THERAPY_COL not in kb.columns:
        therapy_cand = next((c for c in kb.columns if "therapy" in c.lower() or "drug" in c.lower()), None)
        if therapy_cand:
            kb = kb.rename(columns={therapy_cand: THERAPY_COL})
        else:
            return [{**v, "matched_therapies": []} for v in filtered_variants]

    has_variant_col = VARIANT_COL in kb.columns
    evidence_col = EVIDENCE_COL if EVIDENCE_COL in kb.columns else None
    source_col = SOURCE_COL if SOURCE_COL in kb.columns else None

    def therapies_for(variant: dict) -> list[dict[str, str]]:
        gene = variant.get(gene_key) or variant.get("Gene")
        norm = variant.get(normalized_variant_key)
        gene = str(gene).strip() if gene is not None else ""
        norm = str(norm).strip() if norm is not None else ""

        # Match rows: same gene, and (no variant column / variant empty / exact variant match)
        mask = kb[GENE_COL].astype(str).str.strip().str.upper() == gene.upper()
        if has_variant_col and norm:
            # Ensure both comparisons are Series before combining
            variant_match = kb[VARIANT_COL].astype(str).str.strip().str.upper() == norm.upper()
            variant_empty = kb[VARIANT_COL].astype(str).str.strip().isin(("", "nan", "."))
            # Combine with OR, then AND with gene mask
            variant_condition = variant_match | variant_empty
            mask = mask & variant_condition
        rows = kb.loc[mask]
        out = []
        for _, r in rows.iterrows():
            out.append({
                "therapy": str(r[THERAPY_COL]).strip() if pd.notna(r[THERAPY_COL]) else "",
                "evidence_level": str(r[evidence_col]).strip() if evidence_col and pd.notna(r.get(evidence_col)) else "",
                "source": str(r[source_col]).strip() if source_col and pd.notna(r.get(source_col)) else "",
            })
        return out

    return [
        {**v, "matched_therapies": therapies_for(v)}
        for v in filtered_variants
    ]
