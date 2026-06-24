"""
PDF report generation from pipeline results.
Uses WeasyPrint (HTML→PDF) or fallback to text summary.
"""

from pathlib import Path
from typing import Any


def generate(
    variants_with_therapies: list[dict[str, Any]],
    tmb_result: dict[str, float | int],
    output_path: str | Path,
    *,
    job_id: str | None = None,
) -> None:
    """
    Generate PDF report from pipeline results.
    - variants_with_therapies: list of variant dicts with matched_therapies
    - tmb_result: {"mutation_count": int, "tmb": float}
    - output_path: where to write PDF
    - job_id: optional job identifier for report header
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Generate HTML content first (needed for both PDF and fallback)
    html_content = _generate_html(variants_with_therapies, tmb_result, job_id)
    css_content = _get_css()
    
    # Try to generate PDF with WeasyPrint
    pdf_success = False
    try:
        from weasyprint import HTML, CSS
        from weasyprint.text.fonts import FontConfiguration

        # Write PDF (may fail if GTK+ libraries not available on Windows)
        font_config = FontConfiguration()
        HTML(string=html_content).write_pdf(
            output_path,
            stylesheets=[CSS(string=css_content)],
            font_config=font_config,
        )
        pdf_success = True
    except (ImportError, OSError, Exception):
        # WeasyPrint failed (missing system libraries like GTK+ on Windows)
        # Fallback to HTML + text summary
        pdf_success = False
    
    # Always generate HTML fallback (works without system dependencies)
    html_path = output_path.with_suffix(".html")
    html_path.write_text(html_content, encoding="utf-8")
    # Also write a simple text summary
    _write_text_summary(variants_with_therapies, tmb_result, output_path.with_suffix(".txt"), job_id)
    
    # If PDF failed, the HTML file will be served instead (handled by download endpoint)


def _generate_html(
    variants_with_therapies: list[dict[str, Any]],
    tmb_result: dict[str, float | int],
    job_id: str | None = None,
) -> str:
    """Generate HTML content for PDF."""
    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>OncoCompass Report{(' - ' + job_id) if job_id else ''}</title>
</head>
<body>
    <h1>OncoCompass Precision Oncology Report</h1>
    {f'<p><strong>Job ID:</strong> {job_id}</p>' if job_id else ''}
    
    <h2>Tumor Mutational Burden (TMB)</h2>
    <p><strong>TMB:</strong> {tmb_result.get('tmb', 0)} mutations/Mb</p>
    <p><strong>Mutation Count:</strong> {tmb_result.get('mutation_count', 0)}</p>
    
    <h2>Actionable Variants and Targeted Therapies</h2>
    <table border="1" cellpadding="5" cellspacing="0" style="border-collapse: collapse; width: 100%;">
        <thead>
            <tr>
                <th>Gene</th>
                <th>Variant</th>
                <th>Location</th>
                <th>Consequence</th>
                <th>Therapies</th>
                <th>Evidence Level</th>
            </tr>
        </thead>
        <tbody>
"""
    for v in variants_with_therapies:
        gene = v.get("SYMBOL") or v.get("Gene", "N/A")
        variant = v.get("Normalized_Variant") or v.get("HGVSp", "N/A")
        location = v.get("Location", "N/A")
        consequence = v.get("Consequence", "N/A")
        therapies = v.get("matched_therapies", [])
        if therapies:
            therapy_names = ", ".join([t.get("therapy", "") for t in therapies])
            evidence = ", ".join([t.get("evidence_level", "") for t in therapies if t.get("evidence_level")])
        else:
            therapy_names = "None"
            evidence = "-"
        html += f"""            <tr>
                <td>{gene}</td>
                <td>{variant}</td>
                <td>{location}</td>
                <td>{consequence}</td>
                <td>{therapy_names}</td>
                <td>{evidence}</td>
            </tr>
"""
    html += """        </tbody>
    </table>
</body>
</html>"""
    return html


def _get_css() -> str:
    """Return CSS styles for PDF."""
    return """
        body { font-family: Arial, sans-serif; margin: 20px; }
        h1 { color: #2c3e50; }
        h2 { color: #34495e; margin-top: 20px; }
        table { margin-top: 10px; }
        th { background-color: #3498db; color: white; }
        td { padding: 5px; }
        tr:nth-child(even) { background-color: #f2f2f2; }
    """


def _write_text_summary(
    variants_with_therapies: list[dict[str, Any]],
    tmb_result: dict[str, float | int],
    output_path: Path,
    job_id: str | None = None,
) -> None:
    """Write a simple text summary as fallback."""
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("OncoCompass Precision Oncology Report\n")
        f.write("=" * 50 + "\n\n")
        if job_id:
            f.write(f"Job ID: {job_id}\n\n")
        f.write(f"TMB: {tmb_result.get('tmb', 0)} mutations/Mb\n")
        f.write(f"Mutation Count: {tmb_result.get('mutation_count', 0)}\n\n")
        f.write("Actionable Variants and Therapies:\n")
        f.write("-" * 50 + "\n")
        for v in variants_with_therapies:
            gene = v.get("SYMBOL") or v.get("Gene", "N/A")
            variant = v.get("Normalized_Variant") or v.get("HGVSp", "N/A")
            therapies = v.get("matched_therapies", [])
            f.write(f"\n{gene}: {variant}\n")
            if therapies:
                for t in therapies:
                    f.write(f"  - {t.get('therapy', 'N/A')} (Evidence: {t.get('evidence_level', 'N/A')}, Source: {t.get('source', 'N/A')})\n")
            else:
                f.write("  - No matched therapies\n")
