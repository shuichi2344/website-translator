import json
import re
import threading

import ollama
from engine.insert_doc.translate import translate as _sailor2_translate, translate_summary as _translate_summary

_OLLAMA_MODEL = "llama3.2"

_DIGIT_WORDS = {
    # English
    'zero': '0', 'one': '1', 'two': '2', 'three': '3', 'four': '4',
    'five': '5', 'six': '6', 'seven': '7', 'eight': '8', 'nine': '9',
    # Malay / Indonesian
    'kosong': '0', 'satu': '1', 'dua': '2', 'tiga': '3', 'empat': '4',
    'lima': '5', 'enam': '6', 'tujuh': '7', 'lapan': '8', 'sembilan': '9',
    # Thai (romanised by Whisper)
    'sun': '0', 'nung': '1', 'song': '2', 'sam': '3', 'si': '4',
    'ha': '5', 'hok': '6', 'jet': '7', 'paet': '8', 'kao': '9',
    # Vietnamese
    'không': '0', 'một': '1', 'hai': '2', 'ba': '3', 'bốn': '4',
    'năm': '5', 'sáu': '6', 'bảy': '7', 'tám': '8', 'chín': '9',
    # Tagalog / Filipino
    'wala': '0', 'isa': '1', 'dalawa': '2', 'tatlo': '3', 'apat': '4',
    'limang': '5', 'anim': '6', 'pito': '7', 'walo': '8', 'siyam': '9',
}

# Unicode digit ranges → ASCII: Thai ๐-๙, Arabic-Indic ٠-٩,
# Extended Arabic-Indic ۰-۹, Devanagari ०-९, Bengali ০-৯,
# Chinese fullwidth ０-９
_UNICODE_DIGIT_TABLE = str.maketrans(
    '๐๑๒๓๔๕๖๗๘๙'   # Thai
    '٠١٢٣٤٥٦٧٨٩'   # Arabic-Indic
    '۰۱۲۳۴۵۶۷۸۹'   # Extended Arabic-Indic
    '०१२३४५६७८९'   # Devanagari
    '০১২৩৪৫৬৭৮৯'   # Bengali
    '０１２３４５６７８９',  # Fullwidth
    '0123456789' * 6
)

# Chinese / Japanese / Korean digit characters
_CJK_DIGIT_MAP = {
    '零': '0', '〇': '0', '一': '1', '二': '2', '三': '3', '四': '4',
    '五': '5', '六': '6', '七': '7', '八': '8', '九': '9',
    '壹': '1', '貳': '2', '參': '3', '肆': '4', '伍': '5',
    '陸': '6', '柒': '7', '捌': '8', '玖': '9',
}

_SYMBOL_MAP = [
    (re.compile(r'\bat sign\b',    re.IGNORECASE), '@'),
    (re.compile(r'\bdot\b',        re.IGNORECASE), '.'),
    (re.compile(r'\bperiod\b',     re.IGNORECASE), '.'),
    (re.compile(r'\bdash\b',       re.IGNORECASE), '-'),
    (re.compile(r'\bhyphen\b',     re.IGNORECASE), '-'),
    (re.compile(r'\bunderscore\b', re.IGNORECASE), '_'),
    (re.compile(r'\bslash\b',      re.IGNORECASE), '/'),
    (re.compile(r'\bplus\b',       re.IGNORECASE), '+'),
    (re.compile(r'\bampersand\b',  re.IGNORECASE), '&'),
    (re.compile(r'\bhash\b',       re.IGNORECASE), '#'),
    (re.compile(r'\bpound sign\b', re.IGNORECASE), '#'),
    (re.compile(r'\bcolon\b',      re.IGNORECASE), ':'),
    (re.compile(r'\bsemicolon\b',  re.IGNORECASE), ';'),
    (re.compile(r'\bspace\b',      re.IGNORECASE), ' '),
]

_RE_AT = re.compile(r'\bat\b', re.IGNORECASE)
_EMAIL_LABEL_KEYWORDS = {'email', 'e-mail', 'emel', 'mel'}

# ---------------------------------------------------------------------------
# Manglish / Singlish sentence-final and filler particles to strip
# ---------------------------------------------------------------------------
_PARTICLES = [
    # Manglish / Singlish sentence-final
    "lah", "la", "lor", "loh", "mah", "meh", "wor", "woh",
    "hor", "hah", "har", "hor", "sia", "sial", "kan", "kan",
    "leh", "leh", "nah", "wah", "ah", "oh", "oi",
    # Filler / discourse
    "one", "de", "dei", "nia", "only", "also", "also lah",
    # Malay particles that leak into Manglish
    "pun", "je", "je lah", "boleh", "kan", "tau", "tahu",
]
# Build a single regex: matches any particle at end-of-string (with optional punctuation)
# or as a standalone comma-separated tag anywhere in the string.
_PARTICLE_END_RE = re.compile(
    r'(?:[,\s]+(?:' + '|'.join(re.escape(p) for p in _PARTICLES) + r'))+[.!?,\s]*$',
    re.IGNORECASE,
)
# Also strip particles that appear as leading interjections: "wah, my name is..."
_PARTICLE_LEAD_RE = re.compile(
    r'^(?:(?:' + '|'.join(re.escape(p) for p in _PARTICLES) + r')[,!\s]+)+',
    re.IGNORECASE,
)


def _strip_particles(text: str) -> str:
    """Remove Manglish/Singlish particles from the start and end of a string."""
    s = _PARTICLE_END_RE.sub('', text).strip()
    s = _PARTICLE_LEAD_RE.sub('', s).strip()
    return s.strip('.,!? ')

# Single letters separated by hyphens OR spaces: J-A-M-E-S or J A M E S
_RE_LETTER_RUN = re.compile(r'\b([A-Za-z][\s\-])+[A-Za-z]\b')
# Single digits separated by hyphens, spaces, or commas (including combinations like ", ")
_RE_DIGIT_RUN  = re.compile(r'(?<!\d)\d(?:[\s,\-]+\d){2,}(?!\d)')
# Sequence of digit-words separated by spaces or hyphens
_DIGIT_WORD_PAT = '|'.join(_DIGIT_WORDS)
_RE_DIGIT_WORDS = re.compile(
    r'\b(?:' + _DIGIT_WORD_PAT + r')(?:[\s\-]+(?:' + _DIGIT_WORD_PAT + r'))+\b',
    re.IGNORECASE,
)


def _collapse_spelled(text: str, label: str = "") -> str:
    """Collapse Whisper's spelled-out letters/digits/symbols into compact form."""
    s = text

    # Normalize Unicode digit scripts → ASCII digits
    s = s.translate(_UNICODE_DIGIT_TABLE)
    for cjk, digit in _CJK_DIGIT_MAP.items():
        s = s.replace(cjk, digit)

    # Replace symbol words first
    for pattern, char in _SYMBOL_MAP:
        s = pattern.sub(char, s)

    # "at" -> "@" only for email fields
    if any(kw in label.lower() for kw in _EMAIL_LABEL_KEYWORDS):
        s = _RE_AT.sub('@', s)

    # Remove spaces around punctuation that shouldn't have them: "john . doe" -> "john.doe"
    s = re.sub(r'\s*([.@_/+&#:;])\s*', r'\1', s)

    # Digit words run: "one two three" -> "123"
    def _digit_run(m):
        run = m.group(0)
        for word, digit in _DIGIT_WORDS.items():
            run = re.sub(r'\b' + word + r'\b', digit, run, flags=re.IGNORECASE)
        return re.sub(r'[\s\-]+', '', run)
    s = _RE_DIGIT_WORDS.sub(_digit_run, s)

    # Letter run: J-A-M-E-S or J A M E S -> JAMES
    s = _RE_LETTER_RUN.sub(lambda m: re.sub(r'[\s\-]', '', m.group(0)), s)

    # Digit run: 1-2-3 or 1 2 3 or 1, 2, 3 -> 123
    s = _RE_DIGIT_RUN.sub(lambda m: re.sub(r'[\s,\-]', '', m.group(0)), s)

    # Collapse multiple spaces left over
    s = re.sub(r'  +', ' ', s)

    return s.strip().strip('.,')




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
        _YES_WORDS = {
            # English
            "yes", "yep", "yeah", "yup", "sure", "ok", "okay", "correct", "confirm", "have",
            # Malay / Indonesian
            "ya", "ada", "betul", "boleh", "setuju", "iya", "oke", "benar",
            # Thai (romanised)
            "chai", "krub", "kha",
            # Vietnamese
            "vâng", "có", "đúng",
            # Filipino / Tagalog
            "oo", "opo", "sige",
            # Chinese
            "是", "好", "对", "可以",
            # Tamil
            "ஆம்", "சரி",
        }
        yes = any(w in user_answer.lower() for w in _YES_WORDS)
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

        # Collapse spelled-out letters/digits/symbols Whisper transcribes literally
        collapsed = _collapse_spelled(stripped, label=label)
        if collapsed != stripped:
            print(f"[extract] spelling collapsed: '{stripped}' -> '{collapsed}'")
            stripped = collapsed

        # Strip Manglish/Singlish particles (lah, lor, mah, kan, wor, sia, etc.)
        departicled = _strip_particles(stripped)
        if departicled != stripped:
            print(f"[extract] particles stripped: '{stripped}' -> '{departicled}'")
            stripped = departicled

        # Normalize time fields — extract HH:MM from verbose answers
        if re.search(r'\btime\b', label, re.IGNORECASE):
            m = re.search(r'\b([01]?\d|2[0-3]):([0-5]\d)\b', stripped)
            if m:
                stripped = m.group(0)
                print(f"[extract] time normalized -> '{stripped}'")
        if stripped.lower() in _na_phrases:
            value = "-"
            self._save_value(field, label, value)
            self._current_merged_slot = 0
            self.current_field_index += 1
            return value

        # Treat any input ≤ 80 chars as a direct value
        is_direct = len(stripped) <= 80 and not re.search(
            r'\b(is|are|was|were|my|the|it|i am|i have)\b',
            stripped, re.IGNORECASE
        )
        if is_direct:
            value = stripped
            if any(kw in label.lower() for kw in _EMAIL_LABEL_KEYWORDS):
                value = value.lower()
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
            value = stripped
            print(f"[extract] fallback to raw input -> '{value}'")

        if any(kw in label.lower() for kw in _EMAIL_LABEL_KEYWORDS):
            value = value.lower()

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
        """Return a short human-readable summary of collected responses, translated to user_language."""
        if not self.responses:
            return "No information collected."
        lines = [f"{k} {v}" for k, v in self.responses.items() if v and v != "-"]
        summary = ". ".join(lines[:10])
        return _translate_summary(summary, self.user_language)

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
