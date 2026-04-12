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
        f"Translate the following question into {language} for text-to-speech.\n"
        f"Rules:\n"
        f"- Output ONLY the translated question in a single sentence.\n"
        f"- No parentheses, brackets, slashes, or special characters.\n"
        f"- Short, natural, spoken — as if asking a person face to face.\n"
        f"- Remove any technical codes or form field references.\n\n"
        f"Question: {sentence}\n\n"
        f"Translation:"
    )

    try:
        llm = _get_llm()
        output = llm(
            prompt,
            max_tokens=128,
            temperature=0.2,
            stop=["\n\n", "Question:", "Translation:"],
        )
        result = output["choices"][0]["text"].strip()
        # Strip any residual brackets, parens, slashes
        result = _re.sub(r'[\(\)\[\]\/\\]+', '', result).strip()
        # Remove duplicate sentences (model sometimes echoes the translation twice)
        sentences = [s.strip() for s in _re.split(r'[。？！.?!]', result) if s.strip()]
        if len(sentences) >= 2 and sentences[0] == sentences[1]:
            result = sentences[0]
        elif result:
            # Simpler dedup: if the string is an exact repeat of its first half
            mid = len(result) // 2
            if result[:mid].strip() == result[mid:].strip():
                result = result[:mid].strip()
        return result if result else sentence
    except Exception as e:
        print(f"[translate] Sailor2 failed ({type(e).__name__}: {e})")
        return sentence
