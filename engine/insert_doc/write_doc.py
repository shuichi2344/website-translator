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

    # Load schema → lookup by clean label
    with open(schema_path, "r", encoding="utf-8") as f:
        raw = json.load(f)
    fields = raw if isinstance(raw, list) else raw.get("fields") or raw.get("form_fields") or []

    schema_map: dict[str, dict] = {}
    for field in fields:
        if field.get("type") == "section_header":
            continue
        lbl = _clean_label(field.get("original_label") or "")
        if lbl and lbl not in schema_map:
            schema_map[lbl] = field

    doc = fitz.open(pdf_template_path)
    skipped = []
    written = 0

    for resp_label, value in responses.items():
        if not value or value.strip() in ("-", "not provided", ""):
            continue

        clean = _clean_label(resp_label)
        direct = (input_bboxes or {}).get(resp_label)
        field_entry = schema_map.get(clean)

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
        is_phone = any(w in resp_label.upper() for w in ("TELEFON", "PHONE", "TEL"))

        for box_idx, bbox in enumerate(bbox_list):
            if not remaining:
                break
            x     = float(bbox.get("l", 0))
            # Use "t" (top of box in BOTTOMLEFT coords = the input line position).
            # "b" in the schema is the padded bottom edge and sits ~5pt above the
            # actual drawn line, causing text to land in the row above.
            y_bl  = float(bbox.get("t", bbox.get("b", 0)))
            y_top = page_height - y_bl - 4  # 2pt gap above the input line
            box_w = float(bbox.get("r", x + 200)) - x

            if is_phone and len(bbox_list) == 2:
                # Phone: first box gets area code (3 digits), second gets the rest
                digits = remaining.replace("-", "").replace(" ", "")
                if box_idx == 0:
                    chunk = digits[:3]
                    remaining = digits[3:]
                else:
                    chunk = remaining
                    remaining = ""
            elif is_phone and len(bbox_list) == 1:
                # Only one box detected — manually place second part at l+100
                digits = remaining.replace("-", "").replace(" ", "")
                chunk = digits[:3]
                remaining = digits[3:]
                # Write second part at x+45 same y
                if remaining:
                    x2 = x + 45
                    page.insert_text(fitz.Point(x2, y_top), remaining, fontsize=font_size, color=(0, 0, 0))
                    print(f"[write_doc] '{resp_label}' p{page_num+1} x={x2:.1f} y={y_top:.1f} -> '{remaining}' (phone box 2)")
                    remaining = ""
            elif len(bbox_list) == 1:
                # Single box — write full value, no truncation
                chunk = remaining
                remaining = ""
            else:
                # Multi-box address: estimate chars by box width
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

    # Insert signature at hardcoded Tandatangan position
    if signature_path and os.path.exists(signature_path):
        sig_page = doc[0]
        sig_ph = sig_page.rect.height
        x0 = 200.35
        y_t_bl = 316.13
        x1 = x0 + 80
        y_b_bl = y_t_bl - 40
        sig_rect = fitz.Rect(x0, sig_ph - y_t_bl, x0 + 60, sig_ph - (y_t_bl - 20))
        sig_page.insert_image(sig_rect, filename=signature_path, keep_proportion=False)
        print(f"[write_doc] Signature inserted at {sig_rect}")

    doc.save(output_path)
    doc.close()

    if skipped:
        print(f"[write_doc] Skipped {len(skipped)}: {skipped}")
    print(f"[write_doc] Done — {written} fields → {output_path}")
    return output_path

# if __name__ == "__main__":
#     import tempfile

#     # Generate a test signature PNG using PyMuPDF (no Pillow needed)
#     sig_tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
#     sig_path = sig_tmp.name
#     sig_tmp.close()

#     sig_doc = fitz.open()
#     sig_page = sig_doc.new_page(width=180, height=80)
#     # Draw a squiggle as test signature
#     sig_page.draw_line(fitz.Point(10, 40), fitz.Point(40, 20), color=(0,0,0), width=2)
#     sig_page.draw_line(fitz.Point(40, 20), fitz.Point(70, 55), color=(0,0,0), width=2)
#     sig_page.draw_line(fitz.Point(70, 55), fitz.Point(100, 25), color=(0,0,0), width=2)
#     sig_page.draw_line(fitz.Point(100, 25), fitz.Point(130, 50), color=(0,0,0), width=2)
#     sig_page.draw_line(fitz.Point(130, 50), fitz.Point(160, 30), color=(0,0,0), width=2)
#     sig_page.draw_line(fitz.Point(160, 30), fitz.Point(190, 45), color=(0,0,0), width=2)
#     mat = fitz.Matrix(2, 2)
#     pix = sig_page.get_pixmap(matrix=mat, alpha=False)
#     pix.save(sig_path)
#     sig_doc.close()
#     print(f"Test signature saved → {sig_path}")

#     test_responses = {
#         "Nama (seperti di MyKad) A1": "Chook Yao Yu",
#         "Nombor MyKad A2": "050407070897",
#         "Nombor Telefon Rumah A3": "0312345678",
#         "Nombor Telefon Bimbit A4": "0169448464",
#         "Alamat Surat Menyurat A5": "BLK 3-18-2 Terubong Condo Jalan Bukit Gambir",
#         "Poskod": "11060",
#         "Bandar": "Ayer Itam",
#         "Negeri": "Pulau Pinang",
#         "Nama Bank Pemohon A6": "CIMB",
#         "Nombor Akaun Bank Pemohon A7": "1234567890",
#         "Alamat e-Mel A8": "test@gmail.com",
#     }

#     out = fill_pdf(
#         responses=test_responses,
#         schema_path="JSON_storage/lhdn_mystr_2026_updated.json",
#         pdf_template_path="document_db/BK-02 (Borang Kemas Kini Maklumat Permohonan STR).pdf",
#         output_path="document_db/test_output.pdf",
#         signature_path=sig_path,
#     )
#     print(f"\n✅ Test PDF saved → {out}")
