import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()

# Configure your API Key (Add GOOGLE_API_KEY to your .env file)
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

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
    
    TARGET DIALECT: {dialect}
    USER QUESTION: {user_question}
    
    OFFICIAL SNIPPETS:
    {context}
    
    INSTRUCTIONS FOR SPEECH-OPTIMIZED OUTPUT:
    1. YES/NO FIRST: If the user is asking a closed-ended question, start the response with a clear "Yes" or "No".
    2. DIALECT FLAVOR: Use the vocabulary, sentence structure, and particles of the {dialect}.
    3. NO WEBSITES OR URLS: Do not mention any website names, portal names, or URLs (e.g., do not say MySikap, ICA, or dot gov).
    4. DATA ONLY: Focus on the specific fees, document requirements, or eligibility details found in the snippets.
    5. NO MARKDOWN: DO NOT use bullet points, bolding (**), asterisks (*), or hashtags (#). 
    6. FLOWING TEXT: Keep the entire response under 80 words for natural-sounding speech.
    7. STOP ABRUPTLY: Once you have given the factual answer and details, STOP. Do not add a polite closing or a "hope this helps."
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