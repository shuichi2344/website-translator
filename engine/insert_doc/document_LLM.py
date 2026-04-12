import json
import re
import threading

import ollama
from engine.insert_doc.translate import translate as _sailor2_translate

_OLLAMA_MODEL = "llama3.2"


def _call_llm(prompt: str, max_tokens: int = 60) -> str:
    """Call ollama directly."""
    response = ollama.chat(
        model=_OLLAMA_MODEL,
        messages=[{"role": "user", "content": prompt}],
        options={"num_predict": max_tokens},
    )
    return response["message"]["content"].strip()


ENABLE_TTS = False
TTS_COUNTRY_CODE = "MY"

# Sections that require user confirmation before filling
OPTIONAL_SECTIONS = {
    "MAKLUMAT PASANGAN",
    "MAKLUMAT WARIS",
}

# Sections skipped automatically without asking
AUTO_SKIP_SECTIONS = {
    "UNTUK KEGUNAAN PEJABAT",
    "KEGUNAAN PEJABAT",
    "AKUAN PENERIMAAN KEMAS KINI MAKLUMAT PERMOHONAN STR",
    "AKUAN KEMAS KINI",
}

# Field labels skipped automatically (signature/date handled elsewhere)
AUTO_SKIP_FIELD_KEYWORDS = {
    "signature", "tandatangan", "sign here",
    "date signed", "date of signature", "tarikh tandatangan",
    "hari", "bulan", "tahun",
}

# Date fields that SHOULD be asked (substring match, case-insensitive)
DATE_ASK_KEYWORDS = {
    "date of incident", "date of birth", "tarikh lahir",
    "tarikh kejadian", "incident date", "birth date",
}

# Context prefix for certain sections
SECTION_CONTEXT_PREFIX = {
    "MAKLUMAT PASANGAN": "spouse",
    "MAKLUMAT WARIS":    "next of kin",
}


def _normalise(label: str) -> str:
    return label.strip().upper()


class InclusiveCitizenAI:
    """Section-aware conversational form-filling AI."""

    def __init__(self, schema_path: str, user_language: str = "English"):
        with open(schema_path, "r", encoding="utf-8") as f:
            raw = json.load(f)

        # Flatten sectioned format, injecting _section_name onto each field
        if isinstance(raw, list):
            self.fields = raw
        elif isinstance(raw, dict) and "sections" in raw:
            self.fields = []
            for sec in raw["sections"]:
                sec_name = sec.get("section_name", "")
                for field in sec.get("fields", []):
                    f = field.copy()
                    f["_section_name"] = sec_name
                    self.fields.append(f)
        elif isinstance(raw, dict):
            self.fields = (
                raw.get("extraction_schema")
                or raw.get("fields")
                or raw.get("form_fields")
                or []
            )
        else:
            self.fields = []

        self.fields = self._merge_duplicate_fields(self.fields)

        self.responses: dict = {}
        self._input_bboxes: dict = {}
        self.current_field_index: int = 0
        self._current_merged_slot: int = 0
        self.user_language = user_language
        self._current_section: str = ""
        self._skipped_sections: set = set()
        self._answer_event = threading.Event()
        self._pending_answer: list = [None]

    # ------------------------------------------------------------------
    def _merge_duplicate_fields(self, fields: list) -> list:
        if not fields:
            return fields

        def _base_label(lbl: str) -> str:
            s = lbl.strip()
            s = re.sub(r'\s+line\s+\d+\s*$', '', s, flags=re.IGNORECASE)
            s = re.sub(r'\s+[A-Z]\d+\s*$', '', s)
            return s.strip().upper()

        merged = []
        i = 0
        while i < len(fields):
            field = fields[i].copy()
            label = (field.get("label") or field.get("original_label") or "").strip()
            ftype = field.get("type", "text")

            if ftype == "section_header":
                merged.append(field)
                i += 1
                continue

            base = _base_label(label)
            indices = [i]
            j = i + 1
            while j < len(fields):
                nf = fields[j]
                if nf.get("type", "text") == "section_header":
                    break
                n_label = (nf.get("label") or nf.get("original_label") or "").strip()
                n_base = _base_label(n_label)
                if (nf.get("_section_name") == field.get("_section_name")
                        and (n_label == label or n_base == base)):
                    indices.append(j)
                    j += 1
                else:
                    break

            field["_merged_indices"] = indices
            field["_merged_bboxes"] = [
                fields[k]["input_bbox"]
                for k in indices
                if fields[k].get("input_bbox")
            ]
            merged.append(field)
            i = j

        return merged

    # ------------------------------------------------------------------
    def set_language(self, new_language: str):
        self.user_language = new_language

    def _translate_question(self, question: str) -> str:
        """Translate *question* into user_language using Sailor2 from translate.py."""
        if not question or self.user_language.lower() in ("english", "en"):
            return question
        return _sailor2_translate(question, self.user_language)

    def _should_skip_current_section(self) -> bool:
        return self._current_section in self._skipped_sections

    # ------------------------------------------------------------------
    def generate_question(self) -> str | None:
        while self.current_field_index < len(self.fields):
            field = self.fields[self.current_field_index]
            ftype = field.get("type", "text")
            label = (field.get("label") or field.get("original_label") or "").strip()
            norm  = _normalise(label)

            # Legacy inline section_header support
            if ftype == "section_header":
                self._current_section = norm
                self.current_field_index += 1
                for skip in AUTO_SKIP_SECTIONS:
                    if skip in norm:
                        self._skipped_sections.add(norm)
                        break
                for opt in OPTIONAL_SECTIONS:
                    if opt in norm and norm not in self._skipped_sections:
                        confirm_q = self._ask_section_confirm(label)
                        return f"SECTION_CONFIRM:{self._translate_question(confirm_q)}"
                continue

            # New format: track section from _section_name
            section_name = field.get("_section_name", "")
            section_norm = _normalise(section_name)
            if section_norm and section_norm != self._current_section:
                self._current_section = section_norm
                for skip in AUTO_SKIP_SECTIONS:
                    if skip in section_norm:
                        self._skipped_sections.add(section_norm)
                        break
                for opt in OPTIONAL_SECTIONS:
                    if opt in section_norm and section_norm not in self._skipped_sections:
                        confirm_q = self._ask_section_confirm(section_name)
                        return f"SECTION_CONFIRM:{self._translate_question(confirm_q)}"

            if self._should_skip_current_section():
                self.current_field_index += 1
                continue

            if not (field.get("input_bbox") or field.get("_merged_bboxes")):
                self.current_field_index += 1
                continue

            label_lower = label.lower()
            # Skip date/signature fields unless they are meaningful date inputs
            is_askable_date = any(kw in label_lower for kw in DATE_ASK_KEYWORDS)
            if not is_askable_date and (
                any(kw in label_lower for kw in AUTO_SKIP_FIELD_KEYWORDS)
                or label_lower.strip().rstrip(':') == "date"
            ):
                self.current_field_index += 1
                continue

            prefix = ""
            for sec, ctx in SECTION_CONTEXT_PREFIX.items():
                if sec in self._current_section:
                    prefix = ctx + " "
                    break

            self._current_merged_slot = 0
            num_bboxes = len(field.get("_merged_bboxes") or [])
            clean_label = re.sub(r'\s+line\s+\d+\s*$', '', label, flags=re.IGNORECASE).strip()
            question = self._ask_llm(
                clean_label, prefix,
                total_lines=num_bboxes,
                section=field.get("_section_name", ""),
                row=field.get("row"),
            )
            return self._translate_question(question)

        return None

    # ------------------------------------------------------------------
    def confirm_section(self, user_answer: str) -> bool:
        yes = any(w in user_answer.lower() for w in ("yes", "ya", "ada", "y", "ok", "sure", "have"))
        if not yes:
            self._skipped_sections.add(self._current_section)
        return yes

    # ------------------------------------------------------------------
    def _ask_section_confirm(self, section_label: str) -> str:
        prompt = (
            f"You are a friendly voice assistant helping someone fill in a form.\n"
            f"The form has an optional section called: \"{section_label}\"\n\n"
            f"Write a single natural yes/no question in English asking if the user has info for this section.\n"
            f"RULES: under 15 words, plain text only, no special characters.\n"
            f"Return ONLY the question.\n"
        )
        response = _call_llm(prompt, max_tokens=40)
        return re.sub(r'[\/\-\(\)\[\]"\']+', '', response.strip()).strip()

    # ------------------------------------------------------------------
    def _ask_llm(self, label: str, prefix: str = "", line: int = 0,
                 total_lines: int = 0, section: str = "", row: int | None = None) -> str:
        line_hint    = f" up to {total_lines} lines optional" if total_lines > 1 else ""
        relationship = f" Field is about the user's {prefix}." if prefix else ""

        ordinals = {"1": "first", "2": "second", "3": "third", "4": "fourth", "5": "fifth"}
        row_hint = ordinals.get(str(row), f"row {row}") if row else ""

        # Legacy: detect row from label like "(Row 2)"
        if not row_hint:
            m = re.search(r'\(row\s*(\d+)\)', label, re.IGNORECASE)
            if m:
                row_hint = ordinals.get(m.group(1), f"row {m.group(1)}")
                label = re.sub(r'\s*\(row\s*\d+\)', '', label, flags=re.IGNORECASE).strip()

        section_clean = re.sub(r'^\d+[\.\)]\s*', '', section).strip().title() if section else ""

        if section_clean and row_hint:
            section_hint = f"Section: {section_clean}. This is for the {row_hint} entry."
        elif section_clean:
            section_hint = f"Section: {section_clean}."
        elif row_hint:
            section_hint = f"This is for the {row_hint} entry."
        else:
            section_hint = ""

        prompt = (
            f"You are a focused voice assistant collecting form data.\n"
            f"Field: \"{label}{line_hint}\"\n"
            f"{section_hint}\n"
            f"{relationship}\n\n"
            f"Write a single spoken question in English for this field.\n"
            f"RULES: under 15 words, plain text only, no special characters, no codes.\n"
            f"The question must clearly match the exact field — do not confuse date with time.\n"
            f"Return ONLY the question.\n\n"
            f"Examples:\n"
            f"Field: Full Name, section: Policyholder Details → What is your full name?\n"
            f"Field: Date of Incident, section: Accident Details → What was the date of the incident?\n"
            f"Field: Time, section: Accident Details → What time did the incident happen?\n"
            f"Field: Statement of Facts, section: Accident Details → Please describe what happened.\n"
            f"Field: Date of Birth → What is your date of birth?\n"
        )
        response = _call_llm(prompt, max_tokens=60)
        return re.sub(r'[\/\-\(\)\[\]"\']+', '', response.strip()).strip()

    # ------------------------------------------------------------------
    def wait_for_answer(self, timeout: float = 300.0) -> str | None:
        self._answer_event.clear()
        self._pending_answer[0] = None
        triggered = self._answer_event.wait(timeout=timeout)
        return self._pending_answer[0] if triggered else None

    def submit_answer(self, text: str):
        self._pending_answer[0] = text
        self._answer_event.set()

    # ------------------------------------------------------------------
    def extract_and_save(self, user_text: str) -> str:
        field = self.fields[self.current_field_index]
        label = field.get("label") or field.get("original_label") or "this field"

        _na_phrases = {
            "no", "none", "n/a", "na", "nil", "tiada", "tak ada",
            "don't have", "do not have", "i don't have", "i don't",
            "haven't", "-", "/", "skip", "kosong"
        }
        stripped = user_text.strip()
        if stripped.lower() in _na_phrases:
            value = "-"
            self._save_value(field, label, value)
            self._current_merged_slot = 0
            self.current_field_index += 1
            return value

        # Treat any input ≤ 80 chars as a direct value — covers names, IDs,
        # addresses, and short answers in any language including CJK scripts.
        is_direct = len(stripped) <= 80 and not re.search(
            r'\b(is|are|was|were|my|the|it|i am|i have)\b',
            stripped, re.IGNORECASE
        )
        if is_direct:
            value = stripped
            print(f"[extract] field='{label}' direct -> '{value}'")
            self._save_value(field, label, value)
            self._current_merged_slot = 0
            self.current_field_index += 1
            return value

        prompt = (
            f"Extract the value for field: {label}\n"
            f"The user may answer in any language — extract the value exactly as given.\n"
            f"RULES: no summarising, no translation, no explanation.\n"
            f"Output ONLY the extracted value. If no relevant value found, output RETRY.\n\n"
            f"User input: {user_text}\n"
            f"Output:"
        )
        raw   = _call_llm(prompt, max_tokens=40)
        value = raw.split("\n")[0].replace("Output:", "").strip().strip('"').strip("'")

        print(f"[extract] field='{label}' input='{user_text}' -> '{value}'")

        if "RETRY" in value.upper() or len(value.strip()) < 1:
            # Last resort: just use the raw input rather than blocking the user
            value = stripped
            print(f"[extract] fallback to raw input -> '{value}'")

        self._save_value(field, label, value)
        self._current_merged_slot = 0
        self.current_field_index += 1
        return value

    def _save_value(self, field: dict, label: str, value: str):
        self.responses[label] = value
        bboxes = field.get("_merged_bboxes") or []
        if not bboxes and field.get("input_bbox"):
            bboxes = [field["input_bbox"]]
        self._input_bboxes[label] = bboxes if len(bboxes) > 1 else (bboxes[0] if bboxes else None)

    # ------------------------------------------------------------------
    def get_final_json(self) -> str:
        return json.dumps(self.responses, indent=2, ensure_ascii=False)

    def get_tts_summary(self) -> str:
        """Return a short human-readable summary of collected responses."""
        if not self.responses:
            return "No information collected."
        lines = [f"{k} {v}" for k, v in self.responses.items() if v and v != "-"]
        return ". ".join(lines[:10])  # cap at 10 fields to keep it speakable

    # ------------------------------------------------------------------
    @property
    def progress(self) -> tuple[int, int]:
        answered = 0
        total    = 0
        current_section = ""

        for i, field in enumerate(self.fields):
            ftype = field.get("type", "text")
            label = (field.get("label") or field.get("original_label") or "").strip()

            if ftype == "section_header":
                current_section = _normalise(label)
                continue

            sec_norm = _normalise(field.get("_section_name", ""))
            if sec_norm:
                current_section = sec_norm

            if current_section in self._skipped_sections:
                continue
            if not (field.get("input_bbox") or field.get("_merged_bboxes")):
                continue
            label_lower = label.lower()
            is_askable_date = any(kw in label_lower for kw in DATE_ASK_KEYWORDS)
            if not is_askable_date and (
                any(kw in label_lower for kw in AUTO_SKIP_FIELD_KEYWORDS)
                or label_lower.strip().rstrip(':') == "date"
            ):
                continue

            total += 1
            if i < self.current_field_index:
                answered += 1

        return answered, total

# ---------------------------------------------------------------------------
# if __name__ == "__main__":
#     schema_path = "JSON_storage/Apex_Motor_Vehicle_Insurans_Claim_Form.json"
#     ai = InclusiveCitizenAI(schema_path, user_language="Tamil")

#     print(f"--- Generating questions for: {schema_path} (language: {ai.user_language}) ---\n")
#     questions = []

#     while True:
#         result = ai.generate_question()
#         if result is None:
#             break
#         if result.startswith("SECTION_CONFIRM:"):
#             ai.confirm_section("yes")
#             continue
#         questions.append(result)
#         ai.current_field_index += 1

#     print(f"Total questions generated: {len(questions)}\n")
#     for i, q in enumerate(questions, 1):
#         print(f"[{i}] {q}")
