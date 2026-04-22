"""
write_doc.py — Write extracted form data onto a PDF template using PyMuPDF.

Coordinate conversion:
  Schema bbox uses coord_origin="BOTTOMLEFT".
  PyMuPDF uses TOP-LEFT origin:
      y_mupdf = page_height - bbox_b
"""

import json
import os
import re
from datetime import datetime

import fitz  # PyMuPDF
from engine.insert_doc.translate import translate_field_value


def _get_form_language(schema_path: str) -> str:
    """Look up the form language from map.json via schema_path."""
    try:
        map_path = "map.json"
        if not os.path.exists(map_path):
            map_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(schema_path))), "map.json"
            )
        with open(map_path, "r", encoding="utf-8") as f:
            registry = json.load(f)
        norm = os.path.normpath(schema_path)
        for entry in registry.get("available_forms", []):
            if os.path.normpath(entry.get("schema_file", "")) == norm:
                return entry.get("language", "English")
    except Exception as e:
        print(f"[write_doc] Could not read form language: {e}")
    return "English"


def _clean_label(label: str) -> str:
    label = re.sub(r'\s+[A-Z]\d+\s*$', '', label)
    label = re.sub(r'\s*\(line \d+\)\s*$', '', label)
    return label.strip().upper()


def fill_pdf(
    responses: dict,
    schema_path: str,
    pdf_template_path: str,
    output_path: str | None = None,
    input_bboxes: dict | None = None,
    signature_path: str | None = None,
) -> str:
    """
    Write responses onto the PDF template.

    Args:
        responses:          {label: value} from InclusiveCitizenAI.responses
        schema_path:        path to JSON schema
        pdf_template_path:  blank PDF template
        output_path:        save path (auto-generated if None)
        input_bboxes:       optional {label: bbox_dict} from ai._input_bboxes
                            for precise per-line placement
    """
    if not os.path.exists(pdf_template_path):
        raise FileNotFoundError(f"PDF template not found: {pdf_template_path}")
    if not os.path.exists(schema_path):
        raise FileNotFoundError(f"Schema not found: {schema_path}")

    # Load schema → support flat list and sectioned {sections:[{fields:[]}]} formats
    with open(schema_path, "r", encoding="utf-8") as f:
        raw = json.load(f)

    if isinstance(raw, list):
        fields = raw
    elif "sections" in raw:
        fields = [f for sec in raw["sections"] for f in sec.get("fields", [])]
    else:
        fields = raw.get("fields") or raw.get("form_fields") or []

    schema_map: dict[str, dict] = {}
    for field in fields:
        if field.get("type") == "section_header":
            continue
        # support both "label" (new format) and "original_label" (old format)
        lbl = _clean_label(field.get("label") or field.get("original_label") or "")
        if lbl and lbl not in schema_map:
            schema_map[lbl] = field
        # also index by field_id for row-suffixed keys like "full_name_1"
        fid = (field.get("field_id") or "").strip()
        if fid and fid not in schema_map:
            schema_map[fid] = field

    doc = fitz.open(pdf_template_path)
    skipped = []
    written = 0

    # Resolve the form's target language once
    form_language = _get_form_language(schema_path)
    print(f"[write_doc] Form language: {form_language}")

    for resp_label, value in responses.items():
        if not value or value.strip() in ("-", "not provided", ""):
            continue

        # Translate value to the form's language (skips identity/contact fields)
        value = translate_field_value(str(value), resp_label, form_language)

        clean = _clean_label(resp_label)
        direct = (input_bboxes or {}).get(resp_label)
        field_entry = schema_map.get(clean)
        # fallback: try matching by field_id slug (e.g. "Full Name_1" → "full_name_1")
        if not field_entry:
            slug = resp_label.replace(" ", "_").lower()
            field_entry = schema_map.get(slug)

        if not direct and not field_entry:
            skipped.append(resp_label)
            continue

        # Resolve bbox(es) — direct may be a list (multi-line) or single dict
        if direct and isinstance(direct, list):
            bbox_list = direct
        elif direct and isinstance(direct, dict):
            bbox_list = [direct]
        elif field_entry:
            b = field_entry.get("input_bbox") or field_entry.get("bbox") or {}
            bbox_list = [b]
        else:
            skipped.append(resp_label)
            continue

        page_num = (field_entry.get("page") or 1) - 1 if field_entry else 0
        if page_num >= len(doc):
            skipped.append(resp_label)
            continue

        page = doc[page_num]
        page_height = page.rect.height
        font_size = 7

        # Wrap text across available boxes
        remaining = str(value)

        for box_idx, bbox in enumerate(bbox_list):
            if not remaining:
                break
            x     = float(bbox.get("l", 0))
            y_bl  = float(bbox.get("t", bbox.get("b", 0)))
            y_top = page_height - y_bl - 4
            box_w = float(bbox.get("r", x + 200)) - x

            if len(bbox_list) == 1:
                # Single box — write full value as-is
                chunk = remaining
                remaining = ""
            else:
                # Multi-box: distribute text by box width
                chars_per_box = max(1, int(box_w / (font_size * 0.42)))
                chunk = remaining[:chars_per_box].rstrip()
                remaining = remaining[len(chunk):].lstrip()

            print(f"[write_doc] '{resp_label}' p{page_num+1} x={x:.1f} y={y_top:.1f} -> '{chunk}'")
            page.insert_text(fitz.Point(x, y_top), chunk, fontsize=font_size, color=(0, 0, 0))

        written += 1

    # Auto-generate output path
    if output_path is None:
        base = os.path.splitext(os.path.basename(pdf_template_path))[0]
        ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = os.path.join(
            os.path.dirname(pdf_template_path),
            f"{base}_filled_{ts}.pdf"
        )

    # ── Signature ────────────────────────────────────────────────────────
    if signature_path and os.path.exists(signature_path):
        _SIG_KEYWORDS = {"signature", "sign", "tandatangan"}
        sig_field = next(
            (f for f in fields
             if any(kw in (f.get("label") or f.get("original_label") or "").lower() for kw in _SIG_KEYWORDS)),
            None,
        )
        if sig_field:
            pg_num = (sig_field.get("page") or 1) - 1
            sig_pg = doc[min(pg_num, len(doc) - 1)]
            sig_ph = sig_pg.rect.height

            # Prefer the label bbox (the space above the label line) for a
            # larger, more visible signature area. Fall back to input_bbox.
            ib = sig_field.get("bbox") or sig_field.get("input_bbox") or {}
            x0 = float(ib.get("l", 60))
            x1 = float(ib.get("r", 200))
            # In BOTTOMLEFT: t is top, b is bottom. Convert to PyMuPDF top-left.
            bl_t = float(ib.get("t", 320))
            bl_b = float(ib.get("b", 290))
            y0 = sig_ph - bl_t   # top in PyMuPDF coords
            y1 = sig_ph - bl_b   # bottom in PyMuPDF coords
            # Ensure minimum 30pt height for a visible signature
            if y1 - y0 < 30:
                y0 = y1 - 30
            sig_rect = fitz.Rect(x0, y0, x1, y1)
        else:
            sig_pg   = doc[0]
            sig_ph   = sig_pg.rect.height
            sig_rect = fitz.Rect(60, sig_ph - 320, 200, sig_ph - 290)
        sig_pg.insert_image(sig_rect, filename=signature_path, keep_proportion=False)
        print(f"[write_doc] Signature inserted at {sig_rect}")

    # ── Auto-date: Hari/Bulan/Tahun (Malay) + generic "date" fields ──────
    now = datetime.now()
    malay_parts = {
        "Hari":  now.strftime("%d"),
        "Bulan": now.strftime("%m"),
        "Tahun": now.strftime("%Y"),
    }
    _DATE_KEYWORDS = {"date", "tarikh", "signed"}

    for field in fields:
        orig = (field.get("label") or field.get("original_label") or "").strip()
        ib   = field.get("input_bbox")
        if not ib:
            continue

        pg_num = (field.get("page") or 1) - 1
        if pg_num >= len(doc):
            continue
        pg = doc[pg_num]
        ph = pg.rect.height
        x  = float(ib["l"])
        y  = ph - float(ib["t"]) - 2

        # Malay date parts
        if orig in malay_parts:
            pg.insert_text(fitz.Point(x, y), malay_parts[orig], fontsize=7, color=(0, 0, 0))
            print(f"[write_doc] Date part '{orig}'={malay_parts[orig]} at x={x:.1f} y={y:.1f}")
            continue

        # Generic date field (e.g. "Date Signed", "Tarikh") — write full date
        orig_lower = orig.lower()
        _DATE_EXCLUDE = {"birth", "incident"}
        if any(kw in orig_lower for kw in _DATE_KEYWORDS) and not any(ex in orig_lower for ex in _DATE_EXCLUDE):
            date_str = now.strftime("%d/%m/%Y")
            pg.insert_text(fitz.Point(x, y), date_str, fontsize=7, color=(0, 0, 0))
            print(f"[write_doc] Auto-date '{orig}'={date_str} at x={x:.1f} y={y:.1f}")

    doc.save(output_path)
    doc.close()

    if skipped:
        print(f"[write_doc] Skipped {len(skipped)}: {skipped}")
    print(f"[write_doc] Done — {written} fields → {output_path}")
    return output_path

# if __name__ == "__main__":
#     # ── Apex Motor Vehicle Insurance Claim Form ───────────────────────────
#     test_responses = {
#         # Section 1 — Policyholder Details
#         "Full Name:":        "John Michael Doe",
#         "Policy Number:":    "APX-MV-2026-00123",
#         "Email Address:":    "john.doe@email.com",
#         "Phone Number:":     "0123456789",

#         # Section 2 — Accident / Incident Details
#         "Date of Incident:": "04/11/2026",
#         "Time:":             "14:30",
#         "Location of Incident:":  "Jalan Ampang, Kuala Lumpur",
#         "Statement of Facts:":    "Vehicle was rear-ended at a traffic light.",
#     }

#     out = fill_pdf(
#         responses=test_responses,
#         schema_path="JSON_storage/Apex_Motor_Vehicle_Insurans_Claim_Form.json",
#         pdf_template_path="document_db/Motor_Vehicle_Insurans_Claim_Form.pdf",
#         output_path="document_db/Motor_Vehicle_Insurans_Claim_Form_filled.pdf",
#     )
#     print(f"\n✅ Filled PDF saved → {out}")