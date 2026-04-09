"""
document_manager.py — Extract form fields and input box coordinates from a PDF.

Strategy:
  1. Use Docling to extract all text items (labels) with their bbox.
  2. Use pypdf to extract page dimensions.
  3. For each label, derive the input_bbox by looking to the right on the same
     horizontal band — the input area starts at label_right + gap and extends
     to the right margin of the page.
  4. Store both label_bbox and input_bbox in the schema JSON so write_doc.py
     can place text precisely inside the input box.
"""

import json
import os
from docling.document_converter import DocumentConverter

try:
    from pypdf import PdfReader
    PYPDF_AVAILABLE = True
except ImportError:
    PYPDF_AVAILABLE = False
    print("⚠️  pypdf not installed — page dimensions will default to A4.")

# --- CONFIGURATION ---
source_path    = "document_db/BK-02 (Borang Kemas Kini Maklumat Permohonan STR).pdf"
schema_folder  = "JSON_storage"
registry_file  = "map.json"
new_form_id    = "lhdn_mystr_2026_updated"
new_display_name = "MySTR 2026 (Updated)"
new_schema_filename = f"{new_form_id}.json"

# Gap between label right edge and start of input box (points)
INPUT_GAP = 4
# Minimum width an input box should have (points)
MIN_INPUT_WIDTH = 40

os.makedirs(schema_folder, exist_ok=True)

# ── 1. Get page dimensions from pypdf ────────────────────────────────────────
page_widths: dict[int, float] = {}
page_heights: dict[int, float] = {}

if PYPDF_AVAILABLE and os.path.exists(source_path):
    reader = PdfReader(source_path)
    for i, page in enumerate(reader.pages, start=1):
        mb = page.mediabox
        page_widths[i]  = float(mb.width)
        page_heights[i] = float(mb.height)

def _page_width(page_no: int) -> float:
    return page_widths.get(page_no, 595.0)   # A4 default

def _page_height(page_no: int) -> float:
    return page_heights.get(page_no, 842.0)

# ── 2. Convert PDF with Docling ───────────────────────────────────────────────
converter = DocumentConverter()
result    = converter.convert(source_path)
doc_json  = result.document.export_to_dict()

# ── 3. Extract & clean fields ─────────────────────────────────────────────────
form_fields = []

for item in doc_json.get("texts", []):
    text_content = item.get("text", "").strip()
    if len(text_content) <= 2:
        continue

    prov_list = item.get("prov", [])
    if not prov_list:
        continue

    prov    = prov_list[0]
    bbox    = prov.get("bbox")      # {l, t, r, b, coord_origin}
    page_no = prov.get("page_no")

    if not bbox or not page_no:
        continue

    pw = _page_width(page_no)

    # Derive input_bbox: starts at label right + gap, same vertical band,
    # extends to right margin (page_width - small margin)
    label_r = float(bbox.get("r", 0))
    label_b = float(bbox.get("b", 0))
    label_t = float(bbox.get("t", 0))

    input_x = label_r + INPUT_GAP
    input_w = pw - input_x - 10   # leave 10pt right margin

    if input_w < MIN_INPUT_WIDTH:
        # Label is already near the right edge — skip input box derivation
        input_bbox = None
    else:
        input_bbox = {
            "l": round(input_x, 2),
            "t": round(label_t, 2),
            "r": round(pw - 10, 2),
            "b": round(label_b, 2),
            "coord_origin": "BOTTOMLEFT",
        }

    form_fields.append({
        "field_id": (
            text_content.split()[-1]
            if text_content[-1].isdigit()
            else text_content[:5]
        ),
        "original_label": text_content,
        "type": item.get("label"),
        "status": "pending",
        "bbox": bbox,           # label coordinates (for reference)
        "input_bbox": input_bbox,  # where to write the answer
        "page": page_no,
    })

# ── 4. Save schema ────────────────────────────────────────────────────────────
schema_path = os.path.join(schema_folder, new_schema_filename)
with open(schema_path, "w", encoding="utf-8") as f:
    json.dump(form_fields, f, indent=2)

print(f"✅ Schema saved → {schema_path}  ({len(form_fields)} fields)")

# ── 5. Update map.json registry ───────────────────────────────────────────────
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
    print(f"ℹ️  Form '{new_form_id}' already in registry.")
