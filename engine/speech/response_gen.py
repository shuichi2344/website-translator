from groq import Groq
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).resolve().parents[2] / ".env", override=True)

# Configure Groq client
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# Language to dialect mapping
LANGUAGE_DIALECT_MAP = {
    "English": "Standard English",
    "Bahasa Melayu": "Bahasa Melayu (Malaysian Malay)",
    "Bahasa Indonesia": "Bahasa Indonesia (Indonesian)",
    "Thai": "Thai",
    "Vietnamese": "Vietnamese",
    "Filipino/Tagalog": "Filipino/Tagalog",
    "Burmese": "Burmese",
    "Khmer": "Khmer (Cambodian)",
    "Lao": "Lao",
    "Chinese (Simplified)": "Simplified Chinese",
    "Tamil": "Tamil",
    # Singlish / Manglish and mixed dialects
    "Manglish": "Manglish (Malaysian English with Malay/Chinese particles like lah, lor, mah, kan)",
    "Singlish": "Singlish (Singaporean English with particles like lah, lor, sia, can or not)",
    "Manglish+English": "Manglish (Malaysian English with Malay/Chinese particles like lah, lor, mah, kan)",
    "Singlish+English": "Singlish (Singaporean English with particles like lah, lor, sia, can or not)",
    "English+Manglish": "Manglish (Malaysian English with Malay/Chinese particles like lah, lor, mah, kan)",
    "English+Singlish": "Singlish (Singaporean English with particles like lah, lor, sia, can or not)",
    "Hokkien": "Hokkien-influenced English (mix Hokkien words naturally)",
    "Cantonese": "Cantonese-influenced English (mix Cantonese words naturally)",
    "Taglish": "Taglish (Tagalog-English mix)",
    "Thai-English": "Thai-English (mix simple Thai words naturally)",
}

def get_dialect_from_language(language):
    """Convert language name to dialect for response generation"""
    return LANGUAGE_DIALECT_MAP.get(language, "Standard English")

# Dialects that should be treated as plain English for output
_ENGLISH_OUTPUT_DIALECTS = {
    "Manglish", "Singlish",
    "Manglish+English", "Singlish+English",
    "English+Manglish", "English+Singlish",
}

def _normalize_dialect(dialect: str) -> str:
    """Map Singlish/Manglish variants to Standard English for output generation."""
    for variant in _ENGLISH_OUTPUT_DIALECTS:
        if variant.lower() in dialect.lower():
            print(f"   ℹ️ Dialect '{dialect}' mapped to Standard English for output")
            return "Standard English"
    return dialect

def _build_prompt(user_question, relevant_chunks, dialect):
    """Build the shared prompt string."""
    dialect = _normalize_dialect(dialect)
    context = "\n---\n".join(relevant_chunks)
    return f"""You are the ASEAN Official Digital Assistant. 
Your goal is to provide accurate government information based ONLY on the provided snippets.

TARGET LANGUAGE/DIALECT: {dialect}
USER QUESTION: {user_question}

OFFICIAL SNIPPETS:
{context}

INSTRUCTIONS FOR SPEECH-OPTIMIZED OUTPUT:
1. LANGUAGE: Respond ENTIRELY in {dialect}. Do not mix languages unless the dialect itself is a mix (e.g. Manglish, Singlish, Taglish).
2. YES/NO FIRST: If the user is asking a closed-ended question, start the response with a clear "Yes" or "No" in the target language.
3. DIALECT FLAVOR: Use the vocabulary, sentence structure, and particles natural to {dialect}. For example, if Manglish: use lah, lor, mah, kan naturally at sentence ends. If Singlish: use lah, lor, sia, can or not, right naturally.
4. NO WEBSITES OR URLS: Do not mention any URLs (e.g., do not say MySikap, ICA, or dot gov).
5. DATA ONLY: Focus on the specific fees, document requirements, or eligibility details found in the snippets.
6. NO MARKDOWN: DO NOT use bolding (**), asterisks (*), or hashtags (#). 
7. Use bullet points and numbering.
8. STOP ABRUPTLY: Once you have given the factual answer and details, STOP. Do not add a polite closing or a "hope this helps."
9. Text Simplification: Replace complex legal or medical jargon with simple, everyday language (5th-grade reading level). 
"""

def generate_final_response(user_question, relevant_chunks, dialect):
    """
    Generates a speech-optimized answer tailored to a specific Southeast Asian dialect.
    Model hierarchy: llama-3.3-70b-versatile (primary with retries) → llama-3.1-8b-instant (backup) → Ollama qwen2.5:7b
    """
    prompt = _build_prompt(user_question, relevant_chunks, dialect)

    # Try llama-3.3-70b-versatile first (primary model with retry logic)
    max_retries = 3
    retry_delay = 2

    for attempt in range(max_retries):
        try:
            if attempt > 0:
                print(f"🔄 Retry attempt {attempt + 1}/{max_retries} for llama-3.3-70b-versatile...")
                import time
                time.sleep(retry_delay * attempt)
            else:
                print("✨ Using llama-3.3-70b-versatile (primary)...")

            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.4,
                max_tokens=1024,
            )

            answer = response.choices[0].message.content
            if answer:
                clean_text = answer.replace("*", "").replace("#", "").strip()
                print("✅ llama-3.3-70b-versatile response generated successfully")
                return clean_text

            if attempt < max_retries - 1:
                print("⚠️ llama-3.3-70b-versatile returned empty response, retrying...")
                continue

        except Exception as e:
            error_msg = str(e).lower()

            if 'rate' in error_msg or 'quota' in error_msg or 'limit' in error_msg or '429' in error_msg:
                if attempt < max_retries - 1:
                    print(f"⚠️ llama-3.3-70b-versatile rate limit hit, retrying in {retry_delay * (attempt + 1)}s...")
                    continue
                else:
                    print(f"⚠️ llama-3.3-70b-versatile rate limit exceeded after {max_retries} attempts")
            else:
                print(f"⚠️ llama-3.3-70b-versatile error: {e}")
                if attempt < max_retries - 1:
                    continue

    # Try llama-3.1-8b-instant as backup
    print("   Trying llama-3.1-8b-instant (backup model)...")
    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4,
            max_tokens=1024,
        )

        answer = response.choices[0].message.content
        if answer:
            clean_text = answer.replace("*", "").replace("#", "").strip()
            print("✅ llama-3.1-8b-instant response generated successfully")
            return clean_text

    except Exception as e:
        print(f"⚠️ llama-3.1-8b-instant error: {e}")

    # Final fallback to Ollama qwen2.5
    print("   Falling back to Ollama qwen2.5:7b (local model)...")
    try:
        import requests

        context = "\n---\n".join(relevant_chunks)

        ollama_prompt = f"""You are the ASEAN Official Digital Assistant.
Answer the user's question based ONLY on the provided government information.

TARGET LANGUAGE: {dialect}
USER QUESTION: {user_question}

GOVERNMENT INFORMATION:
{context}

IMPORTANT:
- Respond ENTIRELY in {dialect}. Do NOT write in English unless {dialect} is English.
- Use everyday words (5th-grade reading level).
- Keep sentences simple and short.
- Use bullet points and numbering.
- NO WEBSITES OR URLS.
- STOP when done — no polite closings.

Answer (in {dialect}):"""

        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "qwen2.5:7b",
                "prompt": ollama_prompt,
                "stream": False,
                "options": {
                    "temperature": 0.4,
                    "top_p": 0.95,
                }
            },
            timeout=120
        )

        if response.status_code == 200:
            result = response.json()
            answer = result.get('response', '').strip()
            if answer:
                answer = answer.replace('**', '').replace('*', '').replace('__', '').replace('#', '')
                print("✅ qwen2.5 response generated successfully")
                return answer

    except Exception as e:
        print(f"⚠️ qwen2.5 error: {e}")

    # If all models fail, return error message
    return "Sorry, I encountered an error processing that. Please try again."


# Test run
# from web_scraping import get_chunks_from_list
# if __name__ == "__main__":
#     test_urls = [
#         "https://www.imi.gov.my/index.php/en/main-services/passport/malaysian-international-passport/",
#         "https://www.malaysia.gov.my/portal/content/27671"
#     ]
#     all_chunks = get_chunks_from_list(test_urls)
#     print(f"\nTotal unique chunks gathered: {len(all_chunks)}")

#     response = generate_final_response("Can I renew my Malaysia passport online?", all_chunks, "Kelantanese Malay")
#     print("\n" + "="*40)
#     print("OFFICIAL ASSISTANT RESPONSE")
#     print("="*40)
#     print(response)
#     print("="*40)
#     print("\nSources checked:")
#     for link in test_urls:
#         print(f"- {link}")
