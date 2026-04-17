"""
translate.py — Translate text using the Sailor2-8B GGUF model (CPU-optimised).
Sailor2 is purpose-built for Southeast Asian languages.
"""

import re
from llama_cpp import Llama

_llm_instance: Llama | None = None

def _get_llm() -> Llama:
    """Lazy-load the Sailor2 GGUF model (downloaded from HF on first call)."""
    global _llm_instance
    if _llm_instance is not None:
        return _llm_instance

    print("--- Loading Sailor2-8B-Chat (GGUF) for translation ---")
    _llm_instance = Llama.from_pretrained(
        repo_id="bartowski/Sailor2-8B-Chat-GGUF",
        filename="Sailor2-8B-Chat-IQ2_M.gguf",
        n_ctx=2048,
        n_threads=8,
        verbose=False,
    )
    return _llm_instance


def translate(sentence: str, language: str) -> str:
    """
    Translate *sentence* into *language* using Sailor2-8B.

    Args:
        sentence: The text to translate.
        language: Target language name, e.g. "Malay", "Thai", "Vietnamese".

    Returns:
        Translated string, or the original sentence on failure.
    """
    if not sentence or not sentence.strip():
        return sentence

    prompt = (
        f"<|im_start|>system\n"
        f"You are a translator. Output ONLY the translated sentence. No explanations, no notes, no language names.\n"
        f"<|im_end|>\n"
        f"<|im_start|>user\n"
        f"Translate the following text into {language}. Reply with the translation only:\n"
        f"{sentence}\n"
        f"<|im_end|>\n"
        f"<|im_start|>assistant\n"
    )

    # Patterns that indicate leaked meta-commentary from the model
    _LEAK_PATTERNS = [
        r'\s*translated[:\s].*',
        r'\s*translation[:\s].*',
        r'\bdalam bahasa\b.*',
        r'\bin\s+\w+\s+language\b.*',
        r'\bin\s+(?:english|malay|thai|vietnamese|tagalog|indonesian|chinese|tamil)\b.*',
        r'[:\s]+(?:bahasa melayu|bahasa indonesia|malay|english|thai|vietnamese|tagalog|filipino|chinese|tamil|burmese|khmer|lao)\s*$',
        r'\bask\w*\s+directly\b.*',
        r'\bbertanya\s+secara\s+langsung\b.*',
        r'\bsecara\s+langsung\b.*',
    ]

    try:
        llm = _get_llm()
        output = llm(
            prompt,
            max_tokens=80,
            temperature=0.1,
            stop=["\n", "<|im_end|>", "Question:", "Translation:", "Note:", "translated:", "Translated:",
                  " bahasa", " Bahasa", " malay", " Malay", " english", " English"],
        )
        result = output["choices"][0]["text"].strip()

        # Remove leaked meta-commentary (e.g. "dalam bahasa Melayu", "in Malay language")
        for pattern in _LEAK_PATTERNS:
            result = re.sub(pattern, '', result, flags=re.IGNORECASE).strip()

        # Strip residual brackets, parens, slashes (including fullwidth Chinese variants)
        result = re.sub(r'[\(\)\[\]\/\\（）【】]+', '', result).strip()
        result = re.sub(r'[（(][^）)]*[）)]', '', result).strip()  # remove parenthetical phrases

        # Collapse repeated characters (e.g. "222222..." hallucination)
        result = re.sub(r'(.)\1{4,}', r'\1', result).strip()

        # Take only the first sentence if multiple leaked through (handles CJK punctuation too)
        first = re.split(r'(?<=[.?!？。！])\s*', result)[0].strip()
        if first:
            result = first

        # Dedup: if the string is an exact repeat of its first half
        mid = len(result) // 2
        if mid > 0 and result[:mid].strip() == result[mid:].strip():
            result = result[:mid].strip()

        return result if result else sentence
    except Exception as e:
        print(f"[translate] Sailor2 failed ({type(e).__name__}: {e})")
        return sentence


def translate_summary(summary: str, language: str) -> str:
    """
    Translate a multi-sentence form summary into *language*.
    Handles longer text than translate() by splitting into sentences,
    translating each, then rejoining.

    Args:
        summary:  The summary string (e.g. from get_tts_summary()).
        language: Target language name, e.g. "Malay", "Thai".

    Returns:
        Translated summary, or the original on failure.
    """
    if not summary or not summary.strip():
        return summary
    if language.lower() in ("english", "en"):
        return summary

    # Split on ". " boundaries so each chunk fits within the model's context
    sentences = re.split(r'(?<=\.)\s+', summary.strip())
    translated = [translate(s, language) for s in sentences if s.strip()]
    return " ".join(translated)


# Labels whose values must never be translated (identity / contact data)
_NO_TRANSLATE_KEYWORDS = {
    'name', 'nama', 'phone', 'tel', 'mobile', 'fax',
    'email', 'e-mail', 'emel', 'ic ', 'i/c', 'nric',
    'passport', 'policy number', 'nombor polisi',
    'date of birth', 'tarikh lahir', 'birth date',
    'date of incident', 'tarikh kejadian',
    'postcode', 'zip', 'poskod',
    'address', 'alamat', 'addr',
}


def _should_skip_translation(label: str) -> bool:
    """Return True if the field value should NOT be translated."""
    lower = label.lower()
    return any(kw in lower for kw in _NO_TRANSLATE_KEYWORDS)


# Map from language name (as used in map.json) to ISO 639-1 code
_LANGUAGE_TO_ISO = {
    'english':    'en',
    'malay':      'ms',
    'malaysian':  'ms',
    'bahasa':     'ms',
    'thai':       'th',
    'vietnamese': 'vi',
    'tagalog':    'tl',
    'filipino':   'tl',
    'indonesian': 'id',
    'chinese':    'zh',
    'mandarin':   'zh',
    'tamil':      'ta',
    'burmese':    'my',
    'khmer':      'km',
    'lao':        'lo',
}


def _detect_lang_iso(text: str) -> str:
    """Return ISO 639-1 code for the detected language, or 'unknown' on failure."""
    try:
        from fast_langdetect import detect as _fl_detect
        results = _fl_detect(text)
        if isinstance(results, list) and results:
            return results[0].get('lang', 'unknown').lower()
        if isinstance(results, dict):
            return results.get('lang', 'unknown').lower()
    except Exception as e:
        print(f"[translate] lang detect failed: {e}")
    return 'unknown'


def _lang_name_to_iso(language: str) -> str:
    """Convert a language name like 'Malay' to its ISO 639-1 code."""
    return _LANGUAGE_TO_ISO.get(language.lower().strip(), 'unknown')


def translate_field_value(value: str, label: str, language: str) -> str:
    """
    Translate a single form field *value* into *language*, unless:
    - the field is an identity/contact field (name, phone, email, etc.)
    - the value is already in the target language
    - the value is purely numeric/symbolic

    Args:
        value:    The user's answer to translate.
        label:    The field label (used to decide whether to skip translation).
        language: Target language name, e.g. "Malay", "English", "Thai".

    Returns:
        Translated value, or the original value if translation is skipped/fails.
    """
    if not value or not value.strip():
        return value
    if _should_skip_translation(label):
        return value
    # Purely numeric / symbolic — no translation needed
    if re.match(r'^[\d\s\-\/\.\,\+\(\)]+$', value.strip()):
        return value
    # Skip if the value is already in the target language
    target_iso = _lang_name_to_iso(language)
    if target_iso != 'unknown':
        detected_iso = _detect_lang_iso(value)
        if detected_iso == target_iso:
            print(f"[translate] skip — already {language}: '{value[:40]}'")
            return value
    return translate(value, language)

