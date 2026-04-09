"""
write_doc.py — Write extracted form data onto a PDF template.

Uses pypdf + reportlab to overlay text at bbox coordinates.

Coordinate system:
  Schema bbox uses coord_origin="BOTTOMLEFT" (PDF standard = origin at bottom-left).
  ReportLab also uses bottom-left origin, so coordinates map directly.
"""

import io
import json
import os
import re
from datetime import datetime

from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter


def _clean_label(label: str) -> str:
    """Strip trailing field codes like A1, B2, (line 1) for matching."""
    label = re.sub(r'\s+[A-Z]\d+\s*$', '', label)
    label = re.sub(r'\s*\(line \d+\)\s*$', '', label)
    return label.strip().upper()


def fill_pdf(
    responses: dict,
    schema_path: str,
    pdf_template_path: str,
    output_path: str | None = None,
) -> str:
    """
    Overlay extracted responses onto the PDF template using bbox coordinates
    from the schema JSON.

    Args:
        responses:          dict of {field_label: value} from InclusiveCitizenAI
        schema_path:        path to the JSON schema file
        pdf_template_path:  path to the blank PDF template
        output_path:        where to save the filled PDF (auto-generated if None)

    Returns:
        output_path on success, raises on failure.
    """
    if not os.path.exists(pdf_template_path):
        raise FileNotFoundError(f"PDF template not found: {pdf_template_path}")
    if not os.path.exists(schema_path):
        raise FileNotFoundError(f"Schema not found: {schema_path}")

    # Load schema
    with open(schema_path, "r", encoding="utf-8") as f:
        raw = json.load(f)
    fields = raw if isinstance(raw, list) else raw.get("fields") or raw.get("form_fields") or []

    # Build lookup: clean_label -> field entry (first match wins)
    schema_map: dict[str, dict] = {}
    for field in fields:
        if field.get("type") == "section_header":
            continue
        lbl = _clean_label(field.get("original_label") or "")
        if lbl and lbl not in schema_map:
            schema_map[lbl] = field

    # Read the template PDF
    reader = PdfReader(pdf_template_path)
    writer = PdfWriter()

    # Group responses by page
    page_texts: dict[int, list[tuple[float, float, str]]] = {}
    skipped = []

    for resp_label, value in responses.items():
        if not value or value.strip() in ("-", "not provided", ""):
            continue

        clean = _clean_label(resp_label)
        field_entry = schema_map.get(clean)
        if field_entry is None:
            skipped.append(resp_label)
            continue

        bbox     = field_entry.get("bbox", {})
        # Prefer input_bbox (precise input area) over derived offset from label bbox
        input_bbox = field_entry.get("input_bbox") or {}
        page_num = field_entry.get("page", 1) - 1  # 0-indexed

        if input_bbox:
            x = float(input_bbox.get("l", 0))
            # Use bottom of bbox + small offset as text baseline
            y = float(input_bbox.get("b", 0)) + 1.5
        else:
            # Fallback: place text just right of the label
            x = float(bbox.get("r", 0)) + 8
            y = float(bbox.get("b", 0)) + 1.5

        page_texts.setdefault(page_num, []).append((x, y, value))
        print(f"[write_doc] '{resp_label}' -> page {page_num+1} x={x:.1f} y={y:.1f} val='{value}'")

    # Overlay text page by page
    for page_num, page in enumerate(reader.pages):
        # Get actual page dimensions
        media_box = page.mediabox
        page_width  = float(media_box.width)
        page_height = float(media_box.height)

        # Create an overlay canvas in memory
        packet = io.BytesIO()
        c = canvas.Canvas(packet, pagesize=(page_width, page_height))
        c.setFont("Helvetica", 7)
        c.setFillColorRGB(0, 0, 0)

        for (x, y, text) in page_texts.get(page_num, []):
            c.drawString(x, y, str(text))

        c.save()
        packet.seek(0)

        # Merge overlay onto original page
        overlay_reader = PdfReader(packet)
        overlay_page   = overlay_reader.pages[0]
        page.merge_page(overlay_page)
        writer.add_page(page)

    # Auto-generate output path
    if output_path is None:
        base = os.path.splitext(os.path.basename(pdf_template_path))[0]
        ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = os.path.join(
            os.path.dirname(pdf_template_path),
            f"{base}_filled_{ts}.pdf"
        )

    with open(output_path, "wb") as f:
        writer.write(f)

    if skipped:
        print(f"[write_doc] Skipped {len(skipped)} unmatched fields: {skipped}")
    print(f"[write_doc] Wrote {len(responses) - len(skipped)} fields → {output_path}")

    return output_path
