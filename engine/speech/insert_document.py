import io
import re
import asyncio
import torch
import numpy as np
import speech_recognition as sr
from transformers import AutoProcessor, SeamlessM4Tv2ForSpeechToText
from llama_cpp import Llama
from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from text_to_speech import speak_answer
import json

USER_LANGUAGE = "en"
ENABLE_TTS = True
TTS_COUNTRY_CODE = "MY"

# Cache for translated prompts to avoid re-translating the same string
_translation_cache: dict[str, str] = {}


def translate(text: str, target_lang: str) -> str:
    """Translate text to target_lang using Sailor2. Returns original if lang is English."""
    if target_lang == "en" or not text:
        return text

    cache_key = f"{target_lang}:{text}"
    if cache_key in _translation_cache:
        return _translation_cache[cache_key]

    response = llm(
        f"<|im_start|>system\nYou are a translator. Translate the given text to {target_lang}. Output ONLY the translated text, nothing else.<|im_end|>\n"
        f"<|im_start|>user\n{text}<|im_end|>\n<|im_start|>assistant\n",
        max_tokens=128,
        stop=["<|im_end|>"],
    )
    translated = response["choices"][0]["text"].strip()
    _translation_cache[cache_key] = translated
    return translated


def t(lang: str, key: str, mapping: dict | None = None, **kwargs) -> str:
    """Get a UI prompt from map.json and translate it to the target language."""
    base = (mapping or {}).get(key, "") if mapping else ""
    if not base:
        return ""
    text = base.format(**kwargs) if kwargs else base
    return translate(text, lang)


# ==========================================
# 1. INITIALIZATION (Load once into RAM)
# ==========================================
print("--- Loading Models (This may take 1 min) ---")

# Sailor2 LLM for Refinement
# This assumes the GGUF file is in your Hugging Face cache
llm = Llama.from_pretrained(
    repo_id="bartowski/Sailor2-8B-Chat-GGUF",
    filename="Sailor2-8B-Chat-IQ2_M.gguf",
    n_ctx=2048,
    n_threads=8,
    verbose=False
)

# ==========================================
# 2. THE BRAIN (Sailor2 Refinement)
# ==========================================
def refine_text(raw_text, task="name"):
    # Dynamic prompts based on the JSON 'refine_task'
    prompts = {
        "name": f"The user said their name: '{raw_text}'. Output only the clean, capitalized Full Name.",
        "ic": f"The user said their IC: '{raw_text}'. Output only the 12 digits, no spaces.",
        "phone": f"The user said their phone: '{raw_text}'. Output only the digits, no dashes.",
        "job_category": f"The user said their job status: '{raw_text}'. Based on 1-Kerajaan, 2-Swasta, 3-Sendiri, 4-Tidak Bekerja, 5-Pesara, output ONLY the single digit 1, 2, 3, 4, or 5."
    }

    target_prompt = prompts.get(task, f"Clean this text: {raw_text}")

    response = llm(
        f"<|im_start|>system\nYou are a form-filling expert. Output ONLY the requested value.<|im_end|>\n<|im_start|>user\n{target_prompt}<|im_end|>\n<|im_start|>assistant\n",
        max_tokens=32,
        stop=["<|im_end|>"]
    )
    return response['choices'][0]['text'].strip().upper()

# ==========================================
# 3. THE EARS (Direct Voice Input)
# ==========================================
def listen_and_process(prompt, timeout=10, phrase_time_limit=None, pause_threshold=3.0, ui_prompts=None):
    recognizer = sr.Recognizer()
    recognizer.pause_threshold = float(pause_threshold)
    with sr.Microphone() as source:
        if ENABLE_TTS and prompt:
            try:
                asyncio.run(speak_answer(prompt, TTS_COUNTRY_CODE))
            except RuntimeError:
                loop = asyncio.new_event_loop()
                try:
                    loop.run_until_complete(speak_answer(prompt, TTS_COUNTRY_CODE))
                finally:
                    loop.close()
        print(f"\n[AI]: {prompt}")
        recognizer.adjust_for_ambient_noise(source, duration=1)
        listening_msg = t(USER_LANGUAGE, "listening", ui_prompts) if ui_prompts else "Listening..."
        print(listening_msg)
        try:
            # Capture audio from mic
            audio_data = recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_time_limit)
            
            # Use Google's engine to get raw text (Directly returns a string)
            raw_text = recognizer.recognize_google(audio_data)
            return raw_text
            
        except sr.UnknownValueError:
            return "Error: Could not understand audio."
        except sr.RequestError:
            return "Error: Could not reach speech service (Check internet)."
        except Exception as e:
            return f"Error: {str(e)}"

# ==========================================
# 4. THE HANDS (PDF Generation)
# ==========================================
def load_form_mapping(mapping_path="map.json"):
    with open(mapping_path, "r", encoding="utf-8") as f:
        return json.load(f)


def normalize_value(field_id, raw_value, field_meta):
    if raw_value is None:
        return ""

    value = str(raw_value).strip()
    if not value:
        return ""

    field_type = (field_meta or {}).get("type", "text")
    max_length = (field_meta or {}).get("max_length")

    if field_type in {"numeric", "radio"}:
        value = "".join(ch for ch in value if ch.isdigit())
    elif field_type == "email":
        value = value.strip()
    else:
        value = value.upper()

    if isinstance(max_length, int) and max_length > 0:
        value = value[:max_length]

    return value


ENUM_VALUE_MAP = {
    "pekerjaan": {
        "1": ["government", "govt", "civil service", "public sector", "kerajaan"],
        "2": ["private", "swasta"],
        "3": ["self employed", "self-employed", "business", "own business", "bekerja sendiri", "sendiri"],
        "4": ["unemployed", "jobless", "not working", "no job", "tidak bekerja"],
        "5": ["retired", "pensioner", "pesara"],
    },
    "pekerjaan_pasangan": {
        "1": ["government", "govt", "civil service", "public sector", "kerajaan"],
        "2": ["private", "swasta"],
        "3": ["self employed", "self-employed", "business", "own business", "bekerja sendiri", "sendiri"],
        "4": ["unemployed", "jobless", "not working", "no job", "tidak bekerja"],
        "5": ["retired", "pensioner", "pesara"],
    },
    "status_perkahwinan": {
        "1": ["married", "kahwin"],
        "2": ["divorced", "cerai"],
        "3": ["spouse deceased", "spouse died", "deceased", "widow", "widower", "kematian pasangan"],
        "4": ["single", "bujang"],
    },
    "jantina": {"1": ["male", "man", "lelaki"], "2": ["female", "woman", "perempuan"]},
    "jantina_pasangan": {"1": ["male", "man", "lelaki"], "2": ["female", "woman", "perempuan"]},
    "kategori_permohonan": {
        "1": ["new", "new application", "permohonan baharu", "baharu"],
        "2": ["update", "update information", "kemas kini", "kemaskini", "kini"],
    },
    "permohonan_baharu": {"1": ["yes", "ya"], "0": ["no", "tidak"]},
    "jenis_pengenalan_pasangan": {
        "1": ["mykad"],
        "2": ["mypr"],
        "3": ["mykas"],
        "4": ["passport", "pasport"],
        "5": ["birth certificate", "sijil lahir"],
    },
    "negara_asal_pasangan": {"1": ["indonesia"], "2": ["thailand"], "3": ["singapore"], "4": ["other", "lain"]},
    "anak_status": {"1": ["biological", "anak kandung", "kandung"], "2": ["adopted", "anak angkat", "angkat"]},
}


def parse_enum_answer(raw_text, mapping):
    if raw_text is None:
        return ""

    text = str(raw_text).strip().lower()
    if not text:
        return ""

    allowed = set(mapping.keys())

    # First pass: direct digit match
    for ch in text:
        if ch.isdigit() and ch in allowed:
            return ch

    # Second pass: keyword match
    for digit, keywords in mapping.items():
        for kw in keywords:
            kw_norm = str(kw).strip().lower()
            if kw_norm and kw_norm in text:
                return digit

    # Third pass: use Sailor2 to interpret number words in any language
    allowed_str = ", ".join(f"{k}" for k in sorted(allowed))
    response = llm(
        f"<|im_start|>system\nYou are a number extractor. The user was asked to pick one of these options: {allowed_str}. "
        f"Output ONLY the single digit that best matches what the user said. If unsure, output nothing.<|im_end|>\n"
        f"<|im_start|>user\n{raw_text}<|im_end|>\n<|im_start|>assistant\n",
        max_tokens=4,
        stop=["<|im_end|>"],
    )
    digit = response["choices"][0]["text"].strip()
    if digit in allowed:
        return digit

    return ""


def parse_yes_no(raw_text):
    if raw_text is None:
        return None

    text = str(raw_text).strip().lower()
    if not text:
        return None

    if "1" in text:
        return True
    if "0" in text:
        return False

    yes_words = {"yes", "ya", "yup", "yeah", "betul", "ada", "have"}
    no_words = {"no", "tidak", "tak", "tiada", "none", "nope", "dont", "don't"}

    for w in yes_words:
        if w in text:
            return True
    for w in no_words:
        if w in text:
            return False

    return None


def parse_spelled_out(raw_text: str, is_email: bool = False) -> str:
    """
    Convert character-by-character speech into a string.
    e.g. "C H O O K space Y A O space Y U" -> "CHOOK YAO YU"
    For email: "j o h n at g m a i l dot c o m" -> "JOHN@GMAIL.COM"
    """
    if not raw_text:
        return ""

    text = raw_text.strip().lower()

    # Google STT transcribes "u" as "you" — fix it
    text = re.sub(r'\byou\b', 'u', text)

    # Split into tokens
    tokens = text.split()

    result = []
    current_word = []

    for token in tokens:
        if token == 'space':
            if current_word:
                result.append(''.join(current_word).upper())
                current_word = []
            result.append(' ')
        elif is_email and token in ('at', 'alias', '@'):
            if current_word:
                result.append(''.join(current_word).upper())
                current_word = []
            result.append('@')
        elif is_email and token in ('dot', 'period', 'titik'):
            if current_word:
                result.append(''.join(current_word).upper())
                current_word = []
            result.append('.')
        elif is_email and token in ('underscore', 'underline', '_'):
            if current_word:
                result.append(''.join(current_word).upper())
                current_word = []
            result.append('_')
        elif is_email and token in ('dash', 'hyphen', '-'):
            if current_word:
                result.append(''.join(current_word).upper())
                current_word = []
            result.append('-')
        elif len(token) == 1 and token.isalpha():
            current_word.append(token)
        else:
            # Multi-char token — treat as a word block
            if current_word:
                result.append(''.join(current_word).upper())
                current_word = []
            result.append(token.upper())

    if current_word:
        result.append(''.join(current_word).upper())

    output = ''.join(result)
    output = re.sub(r' +', ' ', output).strip()
    return output


def get_prompt_and_refine_task(field_id, field_meta, lang, ui_prompts):
    enum_fields = {
        "permohonan_baharu",
        "kategori_permohonan",
        "jantina",
        "status_perkahwinan",
        "pekerjaan",
        "jenis_pengenalan_pasangan",
        "negara_asal_pasangan",
        "jantina_pasangan",
        "pekerjaan_pasangan",
    }

    if field_id in {"no_tel_bimbit", "no_tel_rumah", "no_tel_pasangan", "no_tel_waris"}:
        return t(lang, "prompt_phone", ui_prompts), "phone"

    if field_id == "no_mykad":
        return t(lang, "prompt_mykad", ui_prompts), "ic"

    if field_id == "nama_pemohon":
        return t(lang, "prompt_full_name", ui_prompts), "name"

    if field_id == "nombor_lokasi":
        return "", None

    if field_id == "pekerjaan":
        return t(lang, "prompt_job", ui_prompts), "job_category"

    if field_id == "status_perkahwinan":
        return t(lang, "prompt_marital", ui_prompts), "job_category"

    if field_id in {"jantina", "jantina_pasangan"}:
        return t(lang, "prompt_gender", ui_prompts), "job_category"

    if field_id == "kategori_permohonan":
        return t(lang, "prompt_application_category", ui_prompts), "job_category"

    if field_id == "permohonan_baharu":
        return t(lang, "prompt_new_application", ui_prompts), "job_category"

    if field_id == "negeri":
        return t(lang, "prompt_state", ui_prompts), None

    field_type = (field_meta or {}).get("type", "text")
    label = (field_meta or {}).get("label") or field_id.replace("_", " ")
    prompt_key = "prompt_generic_spell" if (field_meta or {}).get("spell_out") else "prompt_generic"
    default_prompt = t(lang, prompt_key, ui_prompts, label=label)
    if field_type in {"date", "email", "text_multiline", "dropdown"}:
        return default_prompt, None
    if field_id in enum_fields:
        return default_prompt, "job_category"
    if field_type == "text":
        return default_prompt, "name"
    if field_type == "radio":
        return default_prompt, "job_category"
    return default_prompt, None


def split_digits(value):
    return "".join(ch for ch in str(value or "") if ch.isdigit())


def split_date_dd_mm_yyyy(value):
    digits = split_digits(value)
    if len(digits) == 8:
        return digits[6:8], digits[4:6], digits[0:4]
    if len(digits) == 6:
        return digits[4:6], digits[2:4], "20" + digits[0:2]
    return "", "", ""


def draw_text(can, x, y, text, font_size=10):
    if text is None:
        return
    s = str(text).strip()
    if not s:
        return
    can.setFont("Helvetica", int(font_size) if font_size else 10)
    can.drawString(float(x), float(y), s)


def draw_lines(can, x, y, lines, line_height=12, font_size=10, max_lines=None):
    if not lines:
        return
    effective_lines = list(lines)
    if isinstance(max_lines, int) and max_lines > 0:
        effective_lines = effective_lines[:max_lines]
    for i, line in enumerate(effective_lines):
        draw_text(can, x, y - (i * float(line_height)), line, font_size=font_size)


def render_field(can, field_id, field_meta, data):
    field_type = (field_meta or {}).get("type", "text")
    render = (field_meta or {}).get("render")

    if render and isinstance(render, dict):
        strategy = render.get("strategy")
        if strategy in {"split_phone_mobile", "split_phone_home"}:
            digits = split_digits(data.get(field_id))
            prefix = render.get("prefix", {})
            suffix = render.get("suffix", {})
            draw_text(can, prefix.get("x"), prefix.get("y"), digits[: int(prefix.get("max_length", 0)) or 3], font_size=prefix.get("font_size", 10))
            draw_text(can, suffix.get("x"), suffix.get("y"), digits[int(prefix.get("max_length", 0)) or 3 :], font_size=suffix.get("font_size", 10))
            return

        if strategy == "split_date_dd_mm_yyyy":
            dd, mm, yyyy = split_date_dd_mm_yyyy(data.get(field_id))
            day = render.get("day", {})
            month = render.get("month", {})
            year = render.get("year", {})
            draw_text(can, day.get("x"), day.get("y"), dd, font_size=day.get("font_size", 10))
            draw_text(can, month.get("x"), month.get("y"), mm, font_size=month.get("font_size", 10))
            draw_text(can, year.get("x"), year.get("y"), yyyy, font_size=year.get("font_size", 10))
            return

        if strategy == "table_rows":
            items = data.get(field_id) or []
            row_ys = render.get("row_ys") or []
            columns = render.get("columns") or {}
            max_items = int(field_meta.get("max_items", len(row_ys) or 0) or 0)
            for row_index in range(min(max_items, len(row_ys))):
                row_y = row_ys[row_index]
                item = items[row_index] if row_index < len(items) else {}
                for key, col in columns.items():
                    draw_text(can, col.get("x"), row_y, item.get(key, ""), font_size=col.get("font_size", 8))
            return

    if field_type == "text_multiline":
        raw = data.get(field_id)
        if isinstance(raw, str):
            lines = [line.strip() for line in raw.splitlines() if line.strip()]
        else:
            lines = []
        draw_lines(
            can,
            field_meta.get("x"),
            field_meta.get("y"),
            lines,
            line_height=field_meta.get("line_height", 12),
            font_size=field_meta.get("font_size", 10),
            max_lines=field_meta.get("max_lines"),
        )
        return

    draw_text(can, field_meta.get("x"), field_meta.get("y"), data.get(field_id), font_size=field_meta.get("font_size", 10))


def generate_final_pdf(data, mapping, template_path):
    existing_pdf = PdfReader(template_path)
    writer = PdfWriter()

    meta = mapping.get("form_metadata", {})
    page_size = meta.get("page_size") or {}

    page_width = float(page_size.get("width") or existing_pdf.pages[0].mediabox.width)
    page_height = float(page_size.get("height") or existing_pdf.pages[0].mediabox.height)
    total_pages = int(meta.get("pages") or len(existing_pdf.pages))

    packet = io.BytesIO()
    can = canvas.Canvas(packet, pagesize=(page_width, page_height))

    field_mapping = mapping.get("field_mapping", {})
    for page_index in range(1, total_pages + 1):
        can.setFont("Helvetica", 10)
        for field_id, field_meta in field_mapping.items():
            if int((field_meta or {}).get("page", 1) or 1) != page_index:
                continue
            render_field(can, field_id, field_meta, data)
        if page_index < total_pages:
            can.showPage()

    can.save()
    packet.seek(0)

    overlay_pdf = PdfReader(packet)
    for i, base_page in enumerate(existing_pdf.pages):
        overlay_page = overlay_pdf.pages[i] if i < len(overlay_pdf.pages) else None
        if overlay_page is not None:
            base_page.merge_page(overlay_page)
        writer.add_page(base_page)

    output_filename = meta.get("output_file") or "The_Inclusive_Citizen_Output.pdf"
    with open(output_filename, "wb") as f:
        writer.write(f)

    print(f"\n[SUCCESS] Form generated: {output_filename}")

def run_form_filling_session(mapping_path="map.json", template_path="MySTR_borang.pdf"):
    mapping = load_form_mapping(mapping_path)
    meta = mapping.get("form_metadata", {})
    ui_prompts = mapping.get("ui_prompts", {})
    template_path = meta.get("template_file") or template_path
    field_mapping = mapping.get("field_mapping", {})
    lang = USER_LANGUAGE

    collected_data = {}
    spouse_fields = {
        "nama_pasangan",
        "jenis_pengenalan_pasangan",
        "negara_asal_pasangan",
        "no_pengenalan_pasangan",
        "jantina_pasangan",
        "no_tel_pasangan",
        "pekerjaan_pasangan",
        "nama_bank_pasangan",
        "no_akaun_bank_pasangan",
    }
    waris_fields = {
        "waris_pilihan",
        "hubungan_waris",
        "nama_waris",
        "no_pengenalan_waris",
        "no_tel_waris",
    }
    have_waris = None

    sortable_fields = []
    for field_id, field_meta in field_mapping.items():
        if "pegawai" in field_id:
            continue
        if field_id == "pejabat_tarikh_terima":
            continue
        if field_id == "nombor_lokasi":
            continue
        if field_id == "permohonan_baharu":
            continue
        if (field_meta or {}).get("type") == "list":
            continue
        if (field_meta or {}).get("skip") or (field_meta or {}).get("copy_from"):
            continue
        page = int((field_meta or {}).get("page", 1) or 1)
        y = float((field_meta or {}).get("y") or 0)
        x = float((field_meta or {}).get("x") or 0)
        sortable_fields.append((page, -y, x, field_id))
    sortable_fields.sort()

    for _, _, _, field_id in sortable_fields:
        if collected_data.get("status_perkahwinan") == "4" and field_id in spouse_fields:
            continue

        # Check skip_if condition from map.json
        field_meta_check = field_mapping.get(field_id, {})
        skip_if = (field_meta_check or {}).get("skip_if")
        if skip_if and all(collected_data.get(k) == v for k, v in skip_if.items()):
            continue
        if field_id in waris_fields:
            if have_waris is None:
                answer = None
                for _ in range(2):
                    raw = listen_and_process(t(lang, "prompt_have_waris", ui_prompts), ui_prompts=ui_prompts)
                    if "Error" in raw:
                        continue
                    answer = parse_yes_no(raw)
                    if answer is not None:
                        break
                have_waris = True if answer is None else answer

            if not have_waris:
                continue

            if field_id == "waris_pilihan":
                collected_data["waris_pilihan"] = "X"
                continue
        field_meta = field_mapping.get(field_id, {})
        prompt, refine_task = get_prompt_and_refine_task(field_id, field_meta, lang, ui_prompts)
        if not prompt:
            continue
        max_attempts = 3 if field_id == "status_perkahwinan" else 1
        normalized = ""
        for attempt in range(max_attempts):
            if field_id == "alamat_surat_menyurat":
                raw_input = listen_and_process(prompt, timeout=20, phrase_time_limit=25, pause_threshold=3.0, ui_prompts=ui_prompts)
            else:
                raw_input = listen_and_process(prompt, ui_prompts=ui_prompts)

            if "Error" in raw_input:
                if field_id == "status_perkahwinan" and attempt < (max_attempts - 1):
                    print(t(lang, "retry_hear", ui_prompts))
                    continue
                print(f"Skipping {field_id} due to error.")
                break

            field_type = (field_meta or {}).get("type", "text")
            if field_type == "checkbox":
                lowered = str(raw_input).strip().lower()
                normalized = "X" if ("ya" in lowered or "yes" in lowered) else ""
            elif field_id in ENUM_VALUE_MAP:
                normalized = parse_enum_answer(raw_input, ENUM_VALUE_MAP[field_id])
            else:
                if (field_meta or {}).get("spell_out"):
                    is_email = (field_meta or {}).get("type") == "email"
                    refined = parse_spelled_out(raw_input, is_email=is_email)
                else:
                    refined = refine_text(raw_input, task=refine_task) if refine_task else raw_input
                normalized = normalize_value(field_id, refined, field_meta)

            if normalized:
                break

            if field_id == "status_perkahwinan" and attempt < (max_attempts - 1):
                print(t(lang, "retry_unclear_1_4", ui_prompts))

        if normalized:
            collected_data[field_id] = normalized
            print(f"Verified {field_id}: {normalized}")
            if field_id == "kategori_permohonan" and "permohonan_baharu" in field_mapping:
                collected_data["permohonan_baharu"] = normalized
        else:
            print(f"Skipping {field_id}: empty after normalization.")

    if "anak" in field_mapping:
        anak_meta = field_mapping.get("anak", {})
        max_items = int(anak_meta.get("max_items") or 5)
        raw_count = listen_and_process(t(lang, "prompt_child_count", ui_prompts, max_items=max_items), ui_prompts=ui_prompts)
        if "Error" not in raw_count:
            count_digits = split_digits(raw_count)
            count = int(count_digits) if count_digits else 0
            count = max(0, min(max_items, count))
            children = []
            for idx in range(1, count + 1):
                raw_name = listen_and_process(t(lang, "prompt_child_name", ui_prompts, idx=idx), ui_prompts=ui_prompts)
                raw_ic = listen_and_process(t(lang, "prompt_child_id", ui_prompts, idx=idx), ui_prompts=ui_prompts)
                raw_age = listen_and_process(t(lang, "prompt_child_age", ui_prompts, idx=idx), ui_prompts=ui_prompts)
                raw_status = listen_and_process(t(lang, "prompt_child_status", ui_prompts, idx=idx), ui_prompts=ui_prompts)

                if "Error" in raw_name or "Error" in raw_ic or "Error" in raw_age or "Error" in raw_status:
                    continue

                child = {
                    "nama": normalize_value("nama", refine_text(raw_name, task="name"), {"type": "text", "max_length": 30}),
                    "no_pengenalan": normalize_value("no_pengenalan", refine_text(raw_ic, task="ic"), {"type": "text", "max_length": 20}),
                    "umur": normalize_value("umur", raw_age, {"type": "numeric", "max_length": 2}),
                    "status": parse_enum_answer(raw_status, ENUM_VALUE_MAP["anak_status"]),
                }
                children.append(child)

            if children:
                collected_data["anak"] = children

    # Auto-fill fields that copy from another field
    for field_id, field_meta in field_mapping.items():
        source = (field_meta or {}).get("copy_from")
        if source and source in collected_data:
            collected_data[field_id] = collected_data[source]

    if collected_data:
        generate_final_pdf(collected_data, mapping=mapping, template_path=template_path)

# ==========================================
# 5. THE WORKFLOW (Demo Loop)
# ==========================================
if __name__ == "__main__":
    run_form_filling_session("map.json", template_path="MySTR_borang.pdf")
