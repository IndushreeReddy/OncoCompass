"""
Variant normalization: HGVS protein format, 3-letter to 1-letter amino acid.
Used for consistent matching with the oncology knowledge base.
"""

import re
from typing import Optional

# Standard 3-letter to 1-letter amino acid code (plus Ter = *)
AA3_TO_AA1 = {
    "Ala": "A", "Arg": "R", "Asn": "N", "Asp": "D", "Cys": "C",
    "Gln": "Q", "Glu": "E", "Gly": "G", "His": "H", "Ile": "I",
    "Leu": "L", "Lys": "K", "Met": "M", "Phe": "F", "Pro": "P",
    "Ser": "S", "Thr": "T", "Trp": "W", "Tyr": "Y", "Val": "V",
    "Ter": "*",
}


def _is_missing(x: Optional[str]) -> bool:
    if x is None:
        return True
    s = str(x).strip().lower()
    return s in ("", "nan", "none")


def normalize_variant(gene: Optional[str], hgvs: Optional[str]) -> Optional[str]:
    """
    Normalize variant to Gene:p.X123Y format for KB matching.
    Handles 3-letter amino acid HGVSp (e.g. p.Arg123Glu) and simple deletions.
    """
    if _is_missing(gene) or _is_missing(hgvs):
        return None

    gene = str(gene).strip().upper()
    hgvs = str(hgvs).strip()
    if not gene or not hgvs:
        return None

    # Strip transcript prefix if present (e.g. ENST00000123456:p.Arg123Glu -> p.Arg123Glu)
    if ":" in hgvs:
        hgvs = hgvs.split(":")[-1].strip()

    # Substitution: p.Arg123Glu -> Gene:p.R123E
    match = re.search(r"p\.([A-Za-z]{3})(\d+)([A-Za-z]{3})$", hgvs)
    if match:
        ref, pos, alt = match.groups()
        ref1 = AA3_TO_AA1.get(ref, ref)
        alt1 = AA3_TO_AA1.get(alt, alt)
        return f"{gene}:p.{ref1}{pos}{alt1}"

    # Deletion: p.Arg123_Ser125del
    match_del = re.search(r"p\.([A-Za-z]{3})(\d+)_([A-Za-z]{3})(\d+)del", hgvs)
    if match_del:
        aa1, pos1, aa2, pos2 = match_del.groups()
        a1 = AA3_TO_AA1.get(aa1, aa1)
        a2 = AA3_TO_AA1.get(aa2, aa2)
        return f"{gene}:p.{a1}{pos1}_{a2}{pos2}del"

    # Fallback: keep original HGVS with gene prefix
    return f"{gene}:{hgvs}"
