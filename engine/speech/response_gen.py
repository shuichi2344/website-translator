import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()

# Configure your API Key (Add GOOGLE_API_KEY to your .env file)
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

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
}

def get_dialect_from_language(language):
    """Convert language name to dialect for response generation"""
    return LANGUAGE_DIALECT_MAP.get(language, "Standard English")

def generate_final_response(user_question, relevant_chunks, dialect):
    """
    Generates a speech-optimized answer tailored to a specific Southeast Asian dialect.
    """
    model = genai.GenerativeModel('gemini-3-flash-preview')
    
    # Combine the chunks into a single context string
    context = "\n---\n".join(relevant_chunks)
    
    prompt = f"""
    You are the ASEAN Official Digital Assistant. 
    Your goal is to provide accurate government information based ONLY on the provided snippets.
    
    TARGET LANGUAGE: {dialect}
    USER QUESTION: {user_question}
    
    OFFICIAL SNIPPETS:
    {context}
    
    INSTRUCTIONS FOR SPEECH-OPTIMIZED OUTPUT:
    1. LANGUAGE: Respond ENTIRELY in {dialect}. Do not mix languages.
    2. YES/NO FIRST: If the user is asking a closed-ended question, start the response with a clear "Yes" or "No" in the target language.
    3. DIALECT FLAVOR: Use the vocabulary, sentence structure, and particles of {dialect}.
    4. NO WEBSITES OR URLS: Do not mention any website names, portal names, or URLs (e.g., do not say MySikap, ICA, or dot gov).
    5. DATA ONLY: Focus on the specific fees, document requirements, or eligibility details found in the snippets.
    6. NO MARKDOWN: DO NOT use bullet points, bolding (**), asterisks (*), or hashtags (#). 
    7. FLOWING TEXT: Keep the entire response under 80 words for natural-sounding speech.
    8. STOP ABRUPTLY: Once you have given the factual answer and details, STOP. Do not add a polite closing or a "hope this helps."
    9. Text Simplification (Lexical Level): Automatically replace complex legal or medical jargon with simple, everyday language (e.g., 5th-grade reading level). 
    """
    
    try:
        response = model.generate_content(prompt)
        # Final safety strip to remove any rogue markdown if the model hallucinates it
        clean_text = response.text.replace("*", "").replace("#", "").strip()
        return clean_text
    except Exception as e:
        return f"Sorry, I encountered an error processing that: {str(e)}"


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