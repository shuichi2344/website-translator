import google.generativeai as genai
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).resolve().parents[2] / ".env", override=True)

# Configure your API Key (Add GEMINI_API_KEY to your .env file)
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

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

def generate_final_response(user_question, relevant_chunks, dialect):
    """
    Generates a speech-optimized answer tailored to a specific Southeast Asian dialect.
    Model hierarchy: Gemini 3 Flash (primary with retries) → Gemini 3.1 Flash Lite (backup) → Ollama qwen2.5:7b
    """
    # Try Gemini 3 Flash first (primary model with retry logic)
    max_retries = 3
    retry_delay = 2
    
    for attempt in range(max_retries):
        try:
            if attempt > 0:
                print(f"🔄 Retry attempt {attempt + 1}/{max_retries} for Gemini 3 Flash...")
                import time
                time.sleep(retry_delay * attempt)
            else:
                print(f"✨ Using Gemini 3 Flash (primary)...")
            
            model = genai.GenerativeModel('gemini-3-flash-preview')
            
            # Combine the chunks into a single context string
            context = "\n---\n".join(relevant_chunks)
            
            prompt = f"""
    You are the ASEAN Official Digital Assistant. 
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
            
            response = model.generate_content(prompt)
            
            if response and response.text:
                # Final safety strip to remove any rogue markdown
                clean_text = response.text.replace("*", "").replace("#", "").strip()
                print(f"✅ Gemini 3 Flash response generated successfully")
                return clean_text
            
            # If no response, try next attempt
            if attempt < max_retries - 1:
                print("⚠️ Gemini 3 Flash returned empty response, retrying...")
                continue
                
        except Exception as e:
            error_msg = str(e).lower()
            
            # Check if it's a rate limit error
            if 'rate' in error_msg or 'quota' in error_msg or 'limit' in error_msg or '429' in error_msg:
                if attempt < max_retries - 1:
                    print(f"⚠️ Gemini 3 Flash rate limit hit, retrying in {retry_delay * (attempt + 1)}s...")
                    continue
                else:
                    print(f"⚠️ Gemini 3 Flash rate limit exceeded after {max_retries} attempts")
            else:
                print(f"⚠️ Gemini 3 Flash error: {e}")
                if attempt < max_retries - 1:
                    continue
    
    # Try Gemini 3.1 Flash Lite as backup
    print("   Trying Gemini 3.1 Flash Lite (backup model)...")
    try:
        model_backup = genai.GenerativeModel('gemini-3.1-flash-lite-preview')
        context = "\n---\n".join(relevant_chunks)
        
        prompt = f"""
    You are the ASEAN Official Digital Assistant. 
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
        
        response = model_backup.generate_content(prompt)
        
        if response and response.text:
            clean_text = response.text.replace("*", "").replace("#", "").strip()
            print(f"✅ Gemini 3.1 Flash Lite response generated successfully")
            return clean_text
            
    except Exception as e:
        print(f"⚠️ Gemini 3.1 Flash Lite error: {e}")
    
    # Final fallback to Ollama qwen2.5
    print("   Falling back to Ollama qwen2.5:7b (local model)...")
    try:
        import requests
        
        context = "\n---\n".join(relevant_chunks)
        
        prompt = f"""You are the ASEAN Official Digital Assistant.
Answer the user's question based ONLY on the provided government information.

USER QUESTION: {user_question}

GOVERNMENT INFORMATION:
{context}

IMPORTANT - Write in simple, clear English:
- Use everyday words that kids understand (avoid technical jargon)
- Keep sentences simple for understanding
- Focus on the MAIN IDEAS only - skip minor details
- Use bullet points and numbering.
- NO WEBSITES OR URLS: Do not mention any URLs
- STOP when done - no polite closings
- Automatically replace complex legal or medical jargon with simple, everyday language (e.g., 5th-grade reading level). 


Answer (in simple, clear English):"""
        
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "qwen2.5:7b",
                "prompt": prompt,
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
                print(f"✅ qwen2.5 response generated successfully")
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