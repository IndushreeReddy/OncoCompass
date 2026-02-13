"""
Tumor mutational burden (TMB): count non-synonymous variants per exome Mb.
Uses unique (Location, UPLOADED_ALLELE) and configurable exome size.
"""

from typing import Any

import pandas as pd

# Default WES exome size in Mb (adjust per panel if needed)
DEFAULT_EXOME_SIZE_MB = 34.0


def calculate(
    filtered_variants: list[dict[str, Any]] | pd.DataFrame,
    *,
    exome_size_mb: float = DEFAULT_EXOME_SIZE_MB,
    consequence_col: str = "Consequence",
    location_col: str = "Location",
    allele_col: str = "UPLOADED_ALLELE",
) -> dict[str, float | int]:
    """
    Compute TMB from filtered variants.
    Excludes synonymous_variant; counts unique (Location, UPLOADED_ALLELE).
    Returns {"mutation_count": int, "tmb": float (mutations/Mb)}.
    """
    if isinstance(filtered_variants, list) and len(filtered_variants) == 0:
        return {"mutation_count": 0, "tmb": 0.0}

    df = (
        pd.DataFrame(filtered_variants)
        if isinstance(filtered_variants, list)
        else filtered_variants.copy()
    )

    # Exclude synonymous variants (TMB is based on non-synonymous only)
    if consequence_col in df.columns:
        df = df[df[consequence_col].astype(str).str.lower() != "synonymous_variant"]

    # Unique mutations by Location + UPLOADED_ALLELE (VEP column names)
    if location_col in df.columns and allele_col in df.columns:
        mutation_count = df[[location_col, allele_col]].drop_duplicates().shape[0]
    else:
        mutation_count = len(df)

    tmb = mutation_count / exome_size_mb if exome_size_mb > 0 else 0.0
    return {"mutation_count": int(mutation_count), "tmb": round(tmb, 2)}
