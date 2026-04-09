import json
import threading
import ollama

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
SECTION_CONTEXT_PREFIX = {
    "MAKLUMAT PASANGAN": "Your spouse's",
    "MAKLUMAT WARIS":    "Your next of kin's",
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
        self.current_field_index: int = 0
        self.user_language = user_language
        self.model_id = "llama3.2"

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
            """Strip trailing field codes like A5, B1, A3 for grouping."""
            import re
            return re.sub(r'\s+[A-Z]\d+\s*$', '', label.strip()).strip().upper()

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
                            return f"SECTION_CONFIRM:{label}"
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

            question = self._ask_llm(label, prefix)
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
    def _ask_llm(self, label: str, prefix: str = "") -> str:
        prompt = (
            f"You are a friendly assistant helping fill a government form.\n"
            f"Field label: \"{prefix}{label}\"\n"
            f"Language: {self.user_language}\n\n"
            f"Write a short, direct question asking the user for this field's value.\n"
            f"Rules:\n"
            f"- Remove technical codes like A1, B2, or parenthetical instructions.\n"
            f"- Do NOT ask yes/no questions. Ask for the actual value.\n"
            f"- Keep it under 15 words.\n"
            f"- Return ONLY the question, no quotes, no explanation.\n\n"
            f"Examples:\n"
            f"Label: Nama (seperti di MyKad) A1 -> What is your full name?\n"
            f"Label: Nombor MyKad -> What is your IC number?\n"
            f"Label: Tarikh -> What is the date? (DD/MM/YYYY)\n"
            f"Label: Your spouse's Nama -> What is your spouse's full name?\n"
        )
        response = ollama.chat(
            model=self.model_id,
            messages=[{"role": "user", "content": prompt}],
            options={"num_predict": 60},
        )
        return response["message"]["content"].strip().strip('"')

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
            self.current_field_index += 1
            return value

        prompt = (
            f"Your task is to extract information for the field: {label}.\n\n"
            f"STRICT RULES:\n"
            f"- Extract the value EXACTLY as provided in the user's input.\n"
            f"- Do NOT summarize, translate, or infer.\n"
            f"- Do NOT map specific locations to general ones (e.g., keep 'Ayer Itam' as 'Ayer Itam', not 'Penang').\n"
            f"- If the user provides a partial value, keep it exactly as written.\n"
            f"- Output ONLY the extracted value — no labels, no quotes, no explanation.\n"
            f"- If the input contains no relevant value, output RETRY.\n\n"
            f"User input: \"{user_text}\"\n\n"
            f"Output:"
        )
        response = ollama.chat(
            model=self.model_id,
            messages=[{"role": "user", "content": prompt}],
            options={"num_predict": 40},
        )
        raw = response["message"]["content"].strip()
        value = raw.split("\n")[0].replace("Output:", "").strip().strip('"').strip("'")

        print(f"[extract] field='{label}' input='{user_text}' -> '{value}'")

        if "RETRY" in value.upper() or len(value.strip()) < 1:
            return "RETRY"

        self._save_value(field, label, value)
        self.current_field_index += 1
        return value

    def _save_value(self, field: dict, label: str, value: str):
        """Store value across merged field slots."""
        merged = field.get("_merged_indices", [self.current_field_index])
        if len(merged) > 1:
            lines = [l.strip() for l in value.split(",")]
            for idx in range(len(merged)):
                line_val = lines[idx] if idx < len(lines) else value
                key = f"{label} (line {idx + 1})"
                self.responses[key] = line_val
        else:
            self.responses[label] = value

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
