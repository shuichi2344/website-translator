import json
import os
import re
import fitz  # PyMuPDF
from docling.document_converter import DocumentConverter

# --- CONFIGURATION ---
source_path         = "document_db\\Motor_Vehicle_Insurans_Claim_Form.pdf"
schema_folder       = "JSON_storage"
new_form_id         = "Apex_Motor_Vehicle_Insurans_Claim_Form"
new_schema_filename = f"{new_form_id}.json"

os.makedirs(schema_folder, exist_ok=True)

# ── 1. Detect form_id and organization from PDF text ─────────────────────────
def detect_form_meta(pdf_path: str) -> tuple[str, str]:
    """
    Scans the first page to extract organization name and build a form_id.
    Falls back to filename-based defaults if nothing is found.
    """
    doc = fitz.open(pdf_path)
    text = doc[0].get_text()
    doc.close()

    lines = [l.strip() for l in text.splitlines() if l.strip()]

    # Heuristic: first ALL-CAPS line is likely the org name
    organization = "UNKNOWN ORGANIZATION"
    for line in lines:
        if line.isupper() and len(line) > 4:
            organization = line
            break

    # Build a slug form_id from the PDF filename
    base = os.path.splitext(os.path.basename(pdf_path))[0]
    slug = re.sub(r"[^A-Z0-9]+", "-", base.upper()).strip("-")
    form_id = f"{slug}-2026-V1"

    return form_id, organization


# ── 2. Extract drawn rectangles (input boxes) per page ───────────────────────
def get_drawn_rects(pdf_path: str) -> dict[int, list[dict]]:
    doc = fitz.open(pdf_path)
    page_rects: dict[int, list[dict]] = {}

    for page_num, page in enumerate(doc, start=1):
        rects = []
        page_h = page.rect.height

        for path in page.get_drawings():
            r = path.get("rect")
            if r is None:
                continue

            l  = r.x0
            r_ = r.x1
            b  = page_h - r.y1
            t  = page_h - r.y0
            w  = r_ - l
            h  = t - b

            if w > 20 and h < 30:
                rects.append({"l": l, "t": t, "r": r_, "b": b, "w": w, "h": h})

        page_rects[page_num] = rects

    doc.close()
    return page_rects


# ── 3. Match a label bbox to its input rect(s) ───────────────────────────────
def find_input_rect(
    label_bbox: dict,
    page_no: int,
    drawn: dict[int, list[dict]],
    y_tolerance: float = 8.0,
) -> dict | None:
    """Returns the single best input rect (same-row or nearest below)."""
    results = find_all_input_rects(label_bbox, page_no, drawn, y_tolerance)
    return results[0] if results else None


def find_all_input_rects(
    label_bbox: dict,
    page_no: int,
    drawn: dict[int, list[dict]],
    y_tolerance: float = 8.0,
) -> list[dict]:
    """
    Returns all input rects for a label:
    - If a same-row rect exists, return just that one.
    - Otherwise return every rect below the label that overlaps it horizontally,
      sorted top-to-bottom (highest t first in BOTTOMLEFT coords).
    """
    candidates = drawn.get(page_no, [])
    label_l     = label_bbox.get("l", 0)
    label_r     = label_bbox.get("r", 0)
    label_b     = label_bbox.get("b", 0)
    label_mid_y = (label_b + label_bbox.get("t", 0)) / 2

    # ── Strategy 1: same row ──────────────────────────────────────────────────
    best      = None
    best_dist = float("inf")
    for rect in candidates:
        if rect["l"] < label_r - 10:
            continue
        rect_mid_y = (rect["b"] + rect["t"]) / 2
        if abs(rect_mid_y - label_mid_y) > y_tolerance:
            continue
        dist = rect["l"] - label_r
        if dist < best_dist:
            best_dist = dist
            best = rect

    if best:
        return [best]

    # ── Strategy 2: all rows below the label (table column headers) ───────────
    below = []
    for rect in candidates:
        if rect["r"] < label_l or rect["l"] > label_r:
            continue
        gap = label_b - rect["t"]
        if gap < 0 or gap > 80.0:
            continue
        # Skip full-width zero-height decorative border lines
        if rect["h"] == 0 and rect["w"] > 490:
            continue
        below.append(rect)

    # Sort by t descending (closest row first)
    below.sort(key=lambda r: r["t"], reverse=True)
    return below


# ── 4. Decide whether a docling text item is a section header ─────────────────
def is_section_header(item: dict) -> bool:
    return item.get("label") in ("section_header", "title")


# ── EXECUTION ────────────────────────────────────────────────────────────────
print(f"--- Processing: {source_path} ---")

form_id, organization = detect_form_meta(source_path)
print(f"Form ID:      {form_id}")
print(f"Organization: {organization}")

print("Extracting drawn rectangles...")
drawn_rects = get_drawn_rects(source_path)

print("Converting PDF with Docling (this may take a moment)...")
converter = DocumentConverter()
result    = converter.convert(source_path)
doc_json  = result.document.export_to_dict()

# ── 5. Build sections with nested fields ─────────────────────────────────────
sections: list[dict] = []
current_section: dict | None = None

for item in doc_json.get("texts", []):
    text_content = item.get("text", "").strip()
    if len(text_content) <= 2:
        continue

    prov_list = item.get("prov", [])
    if not prov_list:
        continue

    prov    = prov_list[0]
    bbox    = prov.get("bbox")
    page_no = prov.get("page_no")

    if not bbox or not page_no:
        continue

    # Section headers start a new section bucket
    if is_section_header(item):
        current_section = {
            "section_name": text_content,
            "fields": []
        }
        sections.append(current_section)
        continue

    # Everything else is a field label — find its input box(es)
    input_rects = find_all_input_rects(bbox, page_no, drawn_rects)

    # If no section has been created yet, create a default one
    if current_section is None:
        current_section = {"section_name": "GENERAL", "fields": []}
        sections.append(current_section)

    label_bbox = {
        "l": round(bbox.get("l", 0), 3),
        "t": round(bbox.get("t", 0), 3),
        "r": round(bbox.get("r", 0), 3),
        "b": round(bbox.get("b", 0), 3),
        "coord_origin": "BOTTOMLEFT",
    }

    # For signature and date-signed fields, derive input area 10pts above label
    _ABOVE_LABELS = {"policyowner signature", "date signed", "authorized signature", "date"}

    if not input_rects and text_content.lower() in _ABOVE_LABELS:
        input_rects = [{
            "l": bbox.get("l", 0),
            "t": bbox.get("t", 0) + 10,
            "r": bbox.get("r", 0),
            "b": bbox.get("t", 0),
        }]

    # Emit one field per detected input row (table columns get one per row)
    base_id = text_content.replace(" ", "_").lower()[:28]
    for row_idx, input_rect in enumerate(input_rects or [None]):
        input_bbox = None
        if input_rect:
            input_bbox = {
                "l": round(input_rect["l"] + 5, 2),
                "t": round(input_rect["t"], 2),
                "r": round(input_rect["r"], 2),
                "b": round(input_rect["b"] + 2, 2),
                "coord_origin": "BOTTOMLEFT",
            }

        suffix = f"_{row_idx + 1}" if len(input_rects or []) > 1 else ""
        field = {
            "field_id": f"{base_id}{suffix}",
            "label": text_content,
            "row": row_idx + 1 if len(input_rects or []) > 1 else None,
            "input_bbox": input_bbox,
            "label_bbox": label_bbox,
        }
        # Drop None row key for single-row fields
        if field["row"] is None:
            del field["row"]

        current_section["fields"].append(field)

# ── 6. Assemble final schema ──────────────────────────────────────────────────
schema = {
    "form_id": form_id,
    "organization": organization,
    "sections": sections,
}

schema_path = os.path.join(schema_folder, new_schema_filename)
with open(schema_path, "w", encoding="utf-8") as f:
    json.dump(schema, f, indent=2)

print(f"\n✅ Processing Complete!")
print(f"📄 Schema saved to: {schema_path}")
