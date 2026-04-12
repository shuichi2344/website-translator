"""
translate.py — Translate text using the Sailor2-8B GGUF model (CPU-optimised).
Sailor2 is purpose-built for Southeast Asian languages.
"""

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

    import re as _re

    prompt = (
        f"<|im_start|>system\n"
        f"You are a translator. Output ONLY the translated sentence. No explanations, no notes, no language names.\n"
        f"<|im_end|>\n"
        f"<|im_start|>user\n"
        f"Translate this question into {language}. Reply with the translation only:\n"
        f"{sentence}\n"
        f"<|im_end|>\n"
        f"<|im_start|>assistant\n"
    )

    # Patterns that indicate leaked meta-commentary from the model
    _LEAK_PATTERNS = [
        r'\bdalam bahasa\b.*',
        r'\bin\s+\w+\s+language\b.*',
        r'\btranslation\b.*',
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
            stop=["\n", "<|im_end|>", "Question:", "Translation:", "Note:"],
        )
        result = output["choices"][0]["text"].strip()

        # Remove leaked meta-commentary (e.g. "dalam bahasa Melayu", "in Malay language")
        for pattern in _LEAK_PATTERNS:
            result = _re.sub(pattern, '', result, flags=_re.IGNORECASE).strip()

        # Strip residual brackets, parens, slashes (including fullwidth Chinese variants)
        result = _re.sub(r'[\(\)\[\]\/\\（）【】]+', '', result).strip()
        result = _re.sub(r'[（(][^）)]*[）)]', '', result).strip()  # remove parenthetical phrases

        # Collapse repeated characters (e.g. "222222..." hallucination)
        result = _re.sub(r'(.)\1{4,}', r'\1', result).strip()

        # Take only the first sentence if multiple leaked through (handles CJK punctuation too)
        first = _re.split(r'(?<=[.?!？。！])\s*', result)[0].strip()
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
