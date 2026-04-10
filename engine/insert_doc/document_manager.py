"""
document_manager.py — Extract form fields and REAL input box coordinates from a PDF.

Strategy:
  1. Use Docling to extract text labels with their bbox.
  2. Use PyMuPDF to extract all drawn rectangles/lines on each page.
  3. For each label, find the nearest drawn rect/line to its right on the same
     horizontal band — that IS the actual input box.
  4. Store both label_bbox and input_bbox in the schema JSON.
"""

import json
import os
import fitz  # PyMuPDF
from docling.document_converter import DocumentConverter

# --- CONFIGURATION ---
source_path      = "document_db/BK-02 (Borang Kemas Kini Maklumat Permohonan STR).pdf"
schema_folder    = "JSON_storage"
registry_file    = "map.json"
new_form_id      = "lhdn_mystr_2026_updated"
new_display_name = "MySTR 2026 (Updated)"
new_schema_filename = f"{new_form_id}.json"

os.makedirs(schema_folder, exist_ok=True)

# ── 1. Extract drawn rectangles per page using PyMuPDF ───────────────────────
def get_drawn_rects(pdf_path: str) -> dict[int, list[dict]]:
    """
    Returns {page_no (1-indexed): [{"l","t","r","b"}, ...]}
    Extracts rectangles and horizontal lines from PDF drawing paths.
    """
    doc = fitz.open(pdf_path)
    page_rects: dict[int, list[dict]] = {}

    for page_num, page in enumerate(doc, start=1):
        rects = []
        page_h = page.rect.height

        for path in page.get_drawings():
            r = path.get("rect")
            if r is None:
                continue

            # Convert PyMuPDF top-left coords → BOTTOMLEFT
            l = r.x0
            r_ = r.x1
            # PyMuPDF: y increases downward; convert to BOTTOMLEFT
            b = page_h - r.y1
            t = page_h - r.y0

            w = r_ - l
            h = t - b

            # Only keep boxes wide enough to be input fields (>20pt wide)
            # and not too tall (skip thick decorative borders)
            if w > 20 and h < 30:
                rects.append({"l": l, "t": t, "r": r_, "b": b, "w": w, "h": h})

        page_rects[page_num] = rects

    doc.close()
    return page_rects

print("Extracting drawn rectangles from PDF...")
drawn_rects = get_drawn_rects(source_path)
print(f"Found rects per page: { {k: len(v) for k,v in drawn_rects.items()} }")

# ── 2. Convert PDF with Docling ───────────────────────────────────────────────
print("Converting PDF with Docling...")
converter = DocumentConverter()
result    = converter.convert(source_path)
doc_json  = result.document.export_to_dict()

# ── 3. Match each label to nearest input rect ─────────────────────────────────
def find_input_rect(
    label_bbox: dict,
    page_no: int,
    drawn: dict[int, list[dict]],
    y_tolerance: float = 6.0,
) -> dict | None:
    """
    Find the drawn rect that is:
      - On the same page
      - Horizontally to the right of the label (rect.l >= label.r - 5)
      - Vertically overlapping within y_tolerance
      - Closest horizontally
    """
    candidates = drawn.get(page_no, [])
    label_r = label_bbox.get("r", 0)
    label_b = label_bbox.get("b", 0)
    label_t = label_bbox.get("t", 0)
    label_mid_y = (label_b + label_t) / 2

    best = None
    best_dist = float("inf")

    for rect in candidates:
        # Must be to the right of the label
        if rect["l"] < label_r - 5:
            continue
        # Must overlap vertically
        rect_mid_y = (rect["b"] + rect["t"]) / 2
        if abs(rect_mid_y - label_mid_y) > y_tolerance:
            continue
        dist = rect["l"] - label_r
        if dist < best_dist:
            best_dist = dist
            best = rect

    return best

# ── 4. Build form fields ──────────────────────────────────────────────────────
form_fields = []

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

    input_rect = find_input_rect(bbox, page_no, drawn_rects)

    if input_rect:
        input_bbox = {
            "l": round(input_rect["l"] + 10, 2),  # padding from left edge
            "t": round(input_rect["t"], 2),
            "r": round(input_rect["r"], 2),
            "b": round(input_rect["b"] + 2, 2),   # padding from bottom edge
            "coord_origin": "BOTTOMLEFT",
        }
    else:
        input_bbox = None

    form_fields.append({
        "field_id": (
            text_content.split()[-1]
            if text_content[-1].isdigit()
            else text_content[:5]
        ),
        "original_label": text_content,
        "type": item.get("label"),
        "status": "pending",
        "bbox": bbox,
        "input_bbox": input_bbox,
        "page": page_no,
    })

matched = sum(1 for f in form_fields if f["input_bbox"] is not None)
print(f"Matched {matched}/{len(form_fields)} fields to input boxes")

# ── 5. Save schema ────────────────────────────────────────────────────────────
schema_path = os.path.join(schema_folder, new_schema_filename)
with open(schema_path, "w", encoding="utf-8") as f:
    json.dump(form_fields, f, indent=2)
print(f"✅ Schema saved → {schema_path}")

# ── 6. Update map.json registry ───────────────────────────────────────────────
if os.path.exists(registry_file):
    with open(registry_file, "r") as f:
        registry = json.load(f)
else:
    registry = {"available_forms": []}

exists = any(form["id"] == new_form_id for form in registry["available_forms"])
if not exists:
    registry["available_forms"].append({
        "id": new_form_id,
        "display_name": new_display_name,
        "schema_file": schema_path,
        "pdf_file": source_path,
        "country": "Malaysia",
        "form_type": "government",
    })
    with open(registry_file, "w") as f:
        json.dump(registry, f, indent=2)
    print(f"✅ Registry updated → {registry_file}")
else:
    print(f"ℹ️  '{new_form_id}' already in registry.")
