import json
import os
from docling.document_converter import DocumentConverter

# --- CONFIGURATION ---
source_path = "document_db/BK-02 (Borang Kemas Kini Maklumat Permohonan STR).pdf"
schema_folder = "JSON_storage"
registry_file = "map.json"
new_form_id = "lhdn_mystr_2026_updated"
new_display_name = "MySTR 2026 (Updated)"
new_schema_filename = f"{new_form_id}.json"

# Create storage folder if it doesn't exist
os.makedirs(schema_folder, exist_ok=True)

# 1. CONVERT PDF
converter = DocumentConverter()
result = converter.convert(source_path)
doc_json = result.document.export_to_dict()

# 2. EXTRACT & CLEAN FIELDS
form_fields = []
for item in doc_json.get("texts", []):
    text_content = item.get("text", "").strip()
    
    # 2.1 Get the provenance/coordinate data
    # Docling usually provides a list of provenance info
    prov_list = item.get("prov", [])
    bbox = None
    page_no = None
    
    if prov_list:
        # Get coordinates from the first provenance entry
        bbox = prov_list[0].get("bbox")
        page_no = prov_list[0].get("page_no")

    # Filtering for meaningful labels (e.g., A1, A2, B1)
    if len(text_content) > 2:
        form_fields.append({
            "field_id": text_content.split()[-1] if text_content[-1].isdigit() else text_content[:5],
            "original_label": text_content,
            "type": item.get("label"),
            "status": "pending",
            "bbox": bbox,       # <--- ADDED COORDINATES (l, t, r, b)
            "page": page_no     # <--- ADDED PAGE NUMBER
        })

# 3. SAVE THE SCHEMA (THE JSON OUTPUT)
schema_path = os.path.join(schema_folder, new_schema_filename)
with open(schema_path, "w", encoding="utf-8") as f:
    json.dump(form_fields, f, indent=2)

# 4. UPDATE MAP.JSON (REGISTRY)
if os.path.exists(registry_file):
    with open(registry_file, "r") as f:
        registry = json.load(f)
else:
    registry = {"available_forms": []}

# Check if form already exists in registry to avoid duplicates
exists = any(form['id'] == new_form_id for form in registry['available_forms'])

if not exists:
    registry['available_forms'].append({
        "id": new_form_id,
        "display_name": new_display_name,
        "schema_file": schema_path
    })
    
    with open(registry_file, "w", encoding="utf-8") as f:
        json.dump(registry, f, indent=2)

print(f"Success! Schema saved to {schema_path} and registry updated in {registry_file}.")