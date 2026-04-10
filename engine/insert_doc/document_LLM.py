import json
import os
import threading

import ollama
from dotenv import load_dotenv

load_dotenv()

_GEMINI_MODEL   = "gemini-2.0-flash"
_FALLBACK_MODEL = "llama3.2"
_gemini_client  = None  # lazy-initialised

def _get_gemini():
    global _gemini_client
    if _gemini_client is None:
        import google.generativeai as genai
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY not set")
        genai.configure(api_key=api_key)
        _gemini_client = genai.GenerativeModel(_GEMINI_MODEL)
    return _gemini_client

def _call_llm(prompt: str, max_tokens: int = 60) -> str:
    """Try Gemini first; fall back to ollama on any failure."""
    try:
        model = _get_gemini()
        response = model.generate_content(
            prompt,
            generation_config={"max_output_tokens": max_tokens, "temperature": 0.3},
        )
        return response.text.strip()
    except Exception as e:
        print(f"[LLM] Gemini failed ({type(e).__name__}: {e}) — falling back to {_FALLBACK_MODEL}")
        response = ollama.chat(
            model=_FALLBACK_MODEL,
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

# Context prefix injected into questions when inside these sections
# The LLM handles translation based on user_language
SECTION_CONTEXT_PREFIX = {
    "MAKLUMAT PASANGAN": "spouse",
    "MAKLUMAT WARIS":    "next of kin",
}


def _normalise(label: str) -> str:
    """Upper-case and strip for reliable section matching."""
    return label.strip().upper()


class InclusiveCitizenAI:
    """
    Section-aware conversational form-filling AI.

    Blocking wait pattern:
        question = ai.generate_question()   # returns str, "SECTION_CONFIRM:<name>", or None
        ai.submit_answer(user_text)         # unblocks wait_for_answer()
    """

    def __init__(self, schema_path: str, user_language: str = "English"):
        with open(schema_path, "r", encoding="utf-8") as f:
            raw = json.load(f)

        if isinstance(raw, list):
            self.fields = raw
        elif isinstance(raw, dict):
            self.fields = raw.get("fields") or raw.get("form_fields") or []
        else:
            self.fields = []

        # Merge consecutive duplicate fields (OCR artifacts)
        self.fields = self._merge_duplicate_fields(self.fields)

        self.responses: dict = {}
        self._input_bboxes: dict = {}  # key -> input_bbox for write_doc
        self.current_field_index: int = 0
        self._current_merged_slot: int = 0  # which line within a merged field
        self.user_language = user_language

        # Section state
        self._current_section: str = ""
        self._skipped_sections: set = set()

        # Blocking wait mechanism
        self._answer_event = threading.Event()
        self._pending_answer: list = [None]

    # ------------------------------------------------------------------
    def _merge_duplicate_fields(self, fields: list) -> list:
        """
        Merge consecutive fields that represent the same logical input.
        Matches on exact label OR when labels share the same base (ignoring
        trailing codes like 'A5', 'B1', etc.) and are consecutive non-headers.
        """
        if not fields:
            return fields

        def _base_label(label: str) -> str:
            """Strip trailing field codes like A5, B1 and line suffixes like 'line 1' for grouping."""
            import re
            s = label.strip()
            s = re.sub(r'\s+line\s+\d+\s*$', '', s, flags=re.IGNORECASE)
            s = re.sub(r'\s+[A-Z]\d+\s*$', '', s)
            return s.strip().upper()

        merged = []
        i = 0
        while i < len(fields):
            field = fields[i].copy()
            label = (field.get("original_label") or "").strip()
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
                n_label = (nf.get("original_label") or "").strip()
                n_base = _base_label(n_label)
                # Merge if exact match OR same base label
                if n_label == label or n_base == base:
                    indices.append(j)
                    j += 1
                else:
                    break

            field["_merged_indices"] = indices
            # Collect all input_bboxes from merged fields so _save_value
            # doesn't need to re-index into the post-merge list.
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

    # ------------------------------------------------------------------
    def _should_skip_current_section(self) -> bool:
        return self._current_section in self._skipped_sections

    # ------------------------------------------------------------------
    def generate_question(self) -> str | None:
        """
        Advance through fields and return the next prompt string.

        Return values:
          - str question text  → show as bot bubble, wait for answer
          - "SECTION_CONFIRM:<Section Name>"  → ask user yes/no, call confirm_section()
          - None               → form is complete
        """
        while self.current_field_index < len(self.fields):
            field = self.fields[self.current_field_index]
            ftype = field.get("type", "text")
            label = (field.get("label") or field.get("original_label") or "").strip()
            norm  = _normalise(label)

            # ── Section header ──────────────────────────────────────────
            if ftype == "section_header":
                self._current_section = norm
                self.current_field_index += 1

                # Auto-skip blacklisted sections
                for skip in AUTO_SKIP_SECTIONS:
                    if skip in norm:
                        self._skipped_sections.add(norm)
                        break

                # Optional sections — ask user
                for opt in OPTIONAL_SECTIONS:
                    if opt in norm:
                        # Only ask once
                        if norm not in self._skipped_sections:
                            confirm_q = self._ask_section_confirm(label)
                            return f"SECTION_CONFIRM:{confirm_q}"
                        break

                continue  # move to next field

            # ── Skip if inside a skipped section ────────────────────────
            if self._should_skip_current_section():
                self.current_field_index += 1
                continue

            # ── Regular field — generate question ───────────────────────
            prefix = ""
            for sec, ctx in SECTION_CONTEXT_PREFIX.items():
                if sec in self._current_section:
                    prefix = ctx + " "
                    break

            self._current_merged_slot = 0
            num_bboxes = len(field.get("_merged_bboxes") or [])
            # Strip internal line suffixes from the label before asking
            import re as _re
            clean_label = _re.sub(r'\s+line\s+\d+\s*$', '', label, flags=_re.IGNORECASE).strip()
            question = self._ask_llm(clean_label, prefix, total_lines=num_bboxes)
            return question

        return None  # all fields processed

    # ------------------------------------------------------------------
    def confirm_section(self, user_answer: str) -> bool:
        """
        Call this after receiving the user's yes/no response to a
        SECTION_CONFIRM prompt.  Returns True if section will be filled.
        """
        yes = any(w in user_answer.lower() for w in ("yes", "ya", "ada", "y", "ok", "sure", "have"))
        if not yes:
            self._skipped_sections.add(self._current_section)
        return yes

    # ------------------------------------------------------------------
    def _ask_section_confirm(self, section_label: str) -> str:
        """Generate a natural yes/no confirmation question for an optional section."""
        prompt = (
            f"You are a friendly voice assistant helping someone fill in a government form.\n"
            f"The form has an optional section called: \"{section_label}\"\n"
            f"User's language: {self.user_language}\n\n"
            f"Write a single, natural spoken question asking if the user has information for this section.\n\n"
            f"STRICT OUTPUT RULES:\n"
            f"- Ask a simple yes or no question in the user's language.\n"
            f"- Use plain everyday words. No jargon, no codes, no technical terms.\n"
            f"- Zero slashes, zero dashes, zero brackets, zero parentheses, zero special characters.\n"
            f"- Keep it under 15 words.\n"
            f"- Return ONLY the question sentence. No quotes, no explanation.\n\n"
            f"Examples:\n"
            f"Section: MAKLUMAT PASANGAN, language English → Do you have any spouse information to fill in?\n"
            f"Section: MAKLUMAT PASANGAN, language Bahasa Melayu → Adakah anda mempunyai maklumat pasangan untuk diisi?\n"
            f"Section: MAKLUMAT WARIS, language English → Do you have next of kin details to add?\n"
            f"Section: MAKLUMAT WARIS, language Bahasa Melayu → Adakah anda mempunyai maklumat waris untuk diisi?\n"
        )
        response = _call_llm(prompt, max_tokens=40)
        import re as _re
        clean = _re.sub(r'[\/\-\(\)\[\]"\']+', '', response.strip())
        return clean.strip()

    # ------------------------------------------------------------------
    def _ask_llm(self, label: str, prefix: str = "", line: int = 0, total_lines: int = 0) -> str:
        line_hint = ""
        if total_lines > 1:
            line_hint = f" up to {total_lines} lines optional"
        relationship = f" Field is about the user's {prefix}." if prefix else ""
        prompt = (
            f"You are a focused voice assistant collecting form data.\n"
            f"Field: \"{label}{line_hint}\"\n"
            f"Language: {self.user_language}\n"
            f"{relationship}\n\n"
            f"Write a single spoken question for this field.\n\n"
            f"RULES:\n"
            f"- Under 12 words. No filler words.\n"
            f"- One question only. Ask for the value directly.\n"
            f"- Plain text only. No slashes, dashes, brackets, parentheses, or special characters.\n"
            f"- No codes like A1 or B2. No jargon.\n"
            f"- If relationship given, ask about that person.\n"
            f"- If lines optional, add: you may continue on the next line.\n"
            f"- Return ONLY the question. No quotes, no explanation.\n\n"
            f"Examples:\n"
            f"Field: Nama seperti di MyKad A1, English → What is your full name?\n"
            f"Field: Nombor MyKad, Bahasa Melayu → Apakah nombor kad pengenalan anda?\n"
            f"Field: Alamat Surat Menyurat A5 up to 3 lines optional, English → What is your mailing address?\n"
            f"Field: Nama Bank Pemohon A6, English → Which bank do you use?\n"
            f"Field: Nombor Akaun Bank Pemohon A7, English → What is your bank account number?\n"
            f"Field: Nama Bank Pasangan, relationship spouse, English → What is your spouse's bank name?\n"
        )
        response = _call_llm(prompt, max_tokens=60)
        # Strip any symbols the LLM may have slipped in
        import re as _re
        clean = _re.sub(r'[\/\-\(\)\[\]"\']+', '', response.strip())
        return clean.strip()

    # ------------------------------------------------------------------
    def wait_for_answer(self, timeout: float = 300.0) -> str | None:
        """Block until submit_answer() is called or timeout elapses."""
        self._answer_event.clear()
        self._pending_answer[0] = None
        triggered = self._answer_event.wait(timeout=timeout)
        return self._pending_answer[0] if triggered else None

    # ------------------------------------------------------------------
    def submit_answer(self, text: str):
        """Called by home.py to unblock wait_for_answer()."""
        self._pending_answer[0] = text
        self._answer_event.set()

    # ------------------------------------------------------------------
    def extract_and_save(self, user_text: str) -> str:
        """
        Extract value for current field. Returns value or 'RETRY'.
        Advances index on success. Stores answer in all merged slots.
        """
        field = self.fields[self.current_field_index]
        label = field.get("label") or field.get("original_label") or "this field"

        # Detect explicit N/A intent before hitting the LLM
        _na_phrases = {
            "no", "none", "n/a", "na", "nil", "tiada", "tak ada",
            "don't have", "do not have", "i don't have", "i don't",
            "haven't", "-", "/", "skip", "kosong"
        }
        if user_text.strip().lower() in _na_phrases:
            value = "-"
            self._save_value(field, label, value)
            # Skip all remaining slots for this field
            self._current_merged_slot = 0
            self.current_field_index += 1
            return value

        prompt = (
            f"Your task is to extract information for the field: {label}.\n\n"
            f"STRICT RULES:\n"
            f"- Extract the value EXACTLY as provided in the user input.\n"
            f"- Do NOT summarize, translate, or infer.\n"
            f"- Do NOT map specific locations to general ones.\n"
            f"- If the user provides a partial value, keep it exactly as written.\n"
            f"- Output ONLY the extracted value. No labels, no quotes, no explanation, no brackets, no parentheses, no slashes, no dashes, no special characters.\n"
            f"- If the input contains no relevant value, output the single word RETRY.\n\n"
            f"User input: {user_text}\n\n"
            f"Output:"
        )
        raw   = _call_llm(prompt, max_tokens=40)
        value = raw.split("\n")[0].replace("Output:", "").strip().strip('"').strip("'")

        print(f"[extract] field='{label}' input='{user_text}' -> '{value}'")

        if "RETRY" in value.upper() or len(value.strip()) < 1:
            return "RETRY"

        self._save_value(field, label, value)
        self._current_merged_slot = 0
        self.current_field_index += 1
        return value

    def _save_value(self, field: dict, label: str, value: str):
        """Store value and collect all merged input_bboxes for write_doc wrapping."""
        self.responses[label] = value
        # Use pre-collected bboxes from _merge_duplicate_fields (avoids stale index lookups)
        bboxes = field.get("_merged_bboxes") or []
        if not bboxes and field.get("input_bbox"):
            bboxes = [field["input_bbox"]]
        self._input_bboxes[label] = bboxes if len(bboxes) > 1 else (bboxes[0] if bboxes else None)

    # ------------------------------------------------------------------
    def get_final_json(self) -> str:
        return json.dumps(self.responses, indent=2, ensure_ascii=False)

    # ------------------------------------------------------------------
    def get_tts_summary(self) -> str:
        """
        Convert responses into a natural, TTS-friendly confirmation script.
        Groups related fields, strips technical codes, handles missing data.
        """
        import re

        def _clean_key(k: str) -> str:
            """Remove trailing codes like A1, B2, (line 1) from field names."""
            k = re.sub(r'\s+[A-Z]\d+\s*$', '', k)
            k = re.sub(r'\s*\(line \d+\)\s*$', '', k)
            return k.strip()

        def _val(v: str) -> str:
            return "not provided" if v.strip() in ("-", "", "nil", "n/a") else v.strip()

        r = self.responses
        lines = []

        # --- Name & IC ---
        name = _val(r.get("Nama (seperti di MyKad) A1", r.get("Nama", "-")))
        ic   = _val(r.get("Nombor MyKad A2", r.get("Nombor MyKad", "-")))
        lines.append(f"Your full name is {name}, and your MyKad number is {ic}.")

        # --- Phone numbers ---
        home   = _val(r.get("Nombor Telefon Rumah A3", r.get("Nombor Telefon Rumah", "-")))
        mobile = _val(r.get("Nombor Telefon Bimbit A4", r.get("Nombor Telefon Bimbit", "-")))
        if home == "not provided":
            lines.append(f"Your mobile number is {mobile}, and you have no home telephone number on record.")
        else:
            lines.append(f"Your home number is {home}, and your mobile number is {mobile}.")

        # --- Address (collect all address-related keys) ---
        addr_keys = [k for k in r if re.search(r'alamat surat menyurat', k, re.I)]
        addr_parts = [_val(r[k]) for k in addr_keys if _val(r[k]) != "not provided"]
        postcode = _val(r.get("Poskod", "-"))
        city     = _val(r.get("Bandar", "-"))
        state    = _val(r.get("Negeri", "-"))
        if addr_parts:
            addr_str = ", ".join(dict.fromkeys(addr_parts))  # deduplicate
            lines.append(
                f"Your mailing address is {addr_str}, "
                f"{postcode}, {city}, {state}."
            )

        # --- Email ---
        email_keys = [k for k in r if re.search(r'e-mel|email', k, re.I)]
        emails = list(dict.fromkeys(_val(r[k]) for k in email_keys))
        primary_email = next((e for e in emails if e != "not provided"), "not provided")
        lines.append(f"Your email address is {primary_email}.")

        # --- Bank details ---
        bank   = _val(r.get("Nama Bank Pemohon A6", r.get("Nama Bank", "-")))
        acc_no = _val(r.get("Nombor Akaun Bank Pemohon A7", r.get("Nombor Akaun Bank", "-")))
        lines.append(f"Your bank is {bank}, with account number {acc_no}.")

        # --- Spouse (if present) ---
        spouse_name = _val(r.get("Your spouse's Nama (seperti di MyKad)", "-"))
        if spouse_name != "not provided":
            lines.append(f"Your spouse's name on record is {spouse_name}.")

        # --- Next of kin (if present) ---
        waris_name = _val(r.get("Your next of kin's Nama", "-"))
        if waris_name != "not provided":
            lines.append(f"Your next of kin's name is {waris_name}.")

        lines.append("Please review these details. Is everything correct?")
        return " ".join(lines)

    @property
    def progress(self) -> tuple[int, int]:
        total = sum(1 for f in self.fields if f.get("type") != "section_header")
        return self.current_field_index, total

# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import sys
    schema_path = sys.argv[1] if len(sys.argv) > 1 else "JSON_storage/lhdn_mystr_2026_updated.json"
    ai = InclusiveCitizenAI(schema_path, user_language="English")

    print(f"--- Inclusive Citizen AI | {schema_path} ---")
    while True:
        result = ai.generate_question()
        if result is None:
            print("\n✅ Form complete!")
            print(ai.get_final_json())
            break
        if result.startswith("SECTION_CONFIRM:"):
            section_name = result.split(":", 1)[1]
            ans = input(f"\nDo you have information for '{section_name}'? (yes/no): ").strip()
            ai.confirm_section(ans)
            continue
        answered, total = ai.progress
        print(f"\n[{answered}/{total}] {result}")
        user_input = input("Your answer: ").strip()
        extracted = ai.extract_and_save(user_input)
        if extracted == "RETRY":
            print("⚠️  Could not extract — please try again.")
