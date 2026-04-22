import json
import os
import fitz  # PyMuPDF
from docling.document_converter import DocumentConverter

# --- CONFIGURATION ---
source_path      = "Apex_Life_Beneficiary_Final.pdf"
schema_folder    = "JSON_storage"
registry_file    = "map.json"
new_form_id      = "Apex_Life_Beneficiary"
new_display_name = "Life Beneficiary"
new_schema_filename = f"{new_form_id}.json"

os.makedirs(schema_folder, exist_ok=True)

# ── 1. Helper: Dynamic Metadata Detection ──────────────────────────────────
def detect_metadata(pdf_path: str):
    """
    Scans the first page of the PDF to auto-detect country and form type.
    """
    doc = fitz.open(pdf_path)
    text = doc[0].get_text().lower()
    doc.close()

    # Dynamic Country Detection
    country = "Unknown"
    countries = {
        "malaysia": "Malaysia",
        "singapore": "Singapore",
        "australia": "Australia",
        "usa": "USA"
    }
    for key, val in countries.items():
        if key in text:
            country = val
            break

    # Dynamic Form Type Detection
    form_type = "other"
    types = {
        "government": ["tax", "ministry", "official", "department", "jabatan"],
        "insurance": ["insurance", "policy", "beneficiary", "claim", "premium"],
        "healthcare": ["patient", "medical", "clinic", "hospital", "doctor"],
        "rental": ["tenant", "landlord", "lease", "realty", "property"]
    }
    for category, keywords in types.items():
        if any(k in text for k in keywords):
            form_type = category
            break

    return country, form_type

# ── 2. Extract drawn rectangles per page using PyMuPDF ───────────────────────
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

            l = r.x0
            r_ = r.x1
            b = page_h - r.y1
            t = page_h - r.y0
            w = r_ - l
            h = t - b

            if w > 20 and h < 30:
                rects.append({"l": l, "t": t, "r": r_, "b": b, "w": w, "h": h})

        page_rects[page_num] = rects

    doc.close()
    return page_rects

# ── 3. Match each label to nearest input rect ─────────────────────────────────
def find_input_rect(
    label_bbox: dict,
    page_no: int,
    drawn: dict[int, list[dict]],
    y_tolerance: float = 8.0, # Increased tolerance for dynamic lines
) -> dict | None:
    candidates = drawn.get(page_no, [])
    label_r = label_bbox.get("r", 0)
    label_mid_y = (label_bbox.get("b", 0) + label_bbox.get("t", 0)) / 2

    best = None
    best_dist = float("inf")

    for rect in candidates:
        # Check if rect is to the right (with slight overlap allowance)
        if rect["l"] < label_r - 10:
            continue
            
        # Vertical overlap check
        rect_mid_y = (rect["b"] + rect["t"]) / 2
        if abs(rect_mid_y - label_mid_y) > y_tolerance:
            continue
            
        dist = rect["l"] - label_r
        if dist < best_dist:
            best_dist = dist
            best = rect

    return best

# ── EXECUTION ────────────────────────────────────────────────────────────────
print(f"Auto-detecting metadata for {source_path}...")
dyn_country, dyn_type = detect_metadata(source_path)
print(f"Detected: Country={dyn_country}, Type={dyn_type}")

print("Extracting drawn rectangles...")
drawn_rects = get_drawn_rects(source_path)

print("Converting PDF with Docling...")
converter = DocumentConverter()
result    = converter.convert(source_path)
doc_json  = result.document.export_to_dict()

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

    input_bbox = None
    if input_rect:
        input_bbox = {
            "l": round(input_rect["l"] + 5, 2), # Minor padding
            "t": round(input_rect["t"], 2),
            "r": round(input_rect["r"], 2),
            "b": round(input_rect["b"] + 2, 2),
            "coord_origin": "BOTTOMLEFT",
        }

    form_fields.append({
        "field_id": text_content.replace(" ", "_").lower()[:20],
        "original_label": text_content,
        "type": item.get("label"),
        "status": "pending",
        "bbox": bbox,
        "input_bbox": input_bbox,
        "page": page_no,
    })

# ── SAVE SCHEMA ──
schema_path = os.path.join(schema_folder, new_schema_filename)
with open(schema_path, "w", encoding="utf-8") as f:
    json.dump(form_fields, f, indent=2)
print(f"✅ Schema saved → {schema_path}")

# ── UPDATE REGISTRY ──
if os.path.exists(registry_file):
    with open(registry_file, "r") as f:
        registry = json.load(f)
else:
    registry = {"available_forms": []}

# Update or Add entry
existing_index = next((i for i, f in enumerate(registry["available_forms"]) if f["id"] == new_form_id), None)

entry_data = {
    "id": new_form_id,
    "display_name": new_display_name,
    "schema_file": schema_path,
    "pdf_file": source_path,
    "country": dyn_country,  # Dynamic
    "form_type": dyn_type,   # Dynamic
}

if existing_index is not None:
    registry["available_forms"][existing_index] = entry_data
    print(f"ℹ️ Updated '{new_form_id}' in registry.")
else:
    registry["available_forms"].append(entry_data)
    print(f"✅ Added '{new_form_id}' to registry.")

with open(registry_file, "w") as f:
    json.dump(registry, f, indent=2)