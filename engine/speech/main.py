# from speech_to_text import creat as speech_to_text
from engine.speech.web_scraping import get_chunks_from_list
from engine.speech.text_to_speech import speak_answer
from engine.speech.government_mapping import find_specific_gov_links, get_country_suffix
from engine.speech.embedding import ingest_to_chroma, query_from_chroma
from engine.speech.response_gen import generate_final_response, get_dialect_from_language
import asyncio
from datetime import datetime

def process_voice_result(dialect, question, query, country="Malaysia", language="English"):
    """
    Process voice/text question with user's country and language preferences
    
    Args:
        dialect: Detected dialect from speech (can be overridden by language param)
        question: User's question
        query: Normalized query
        country: User's selected country (for government sources)
        language: User's selected language (for response)
    """
    # Use user's language preference instead of detected dialect
    target_dialect = get_dialect_from_language(language)
    country_suffix = get_country_suffix(country)

    print("-" * 30)
    if question:
        print("Question:", question)
    if dialect:
        print("Detected Dialect:", dialect)
    print("Target Language:", language)
    print("Target Country:", country)
    if query:
        print("Normalized query:", query)
    print("-" * 30)

    # Search for government links from user's country
    links = find_specific_gov_links(query, country_suffix)
    if not links:
        print("No official links found.")
        return {
            "answer": f"I couldn't find any relevant government sources from {country} for your question. Please make sure SERP_API_KEY is configured in your .env file, or try rephrasing your question.",
            "sources": []
        }

    print(f"Found {len(links)} specific sources from {country}. Starting extraction...")

    # Extract and Chunk
    all_chunks = get_chunks_from_list(links)
    print(f"\nTotal unique chunks collected: {len(all_chunks)}")

    if not all_chunks:
        print("Extraction failed or no text found on pages.")
        return {
            "answer": f"I found some government sources from {country} but couldn't extract information from them. The websites might be unavailable or require authentication.",
            "sources": links
        }

    print("\nStoring data to chromadb...")
    doc_id = f"gov_search_{country}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    ingest_to_chroma(doc_id, all_chunks)

    print(f"\nProcessing Question: {question}")
    relevant_info = query_from_chroma(question, top_k=5) # Search for the most relevant 5 snippets

    print("\n--- Most Relevant Official Info Found ---")
    for i, snippet in enumerate(relevant_info, 1):
        # Print a short preview of what the AI is "reading"
        preview = snippet.replace('\n', ' ')[:150]
        print(f"[{i}] {preview}...")

    # Generate Answer using Gemini in user's preferred language
    final_answer = ""
    print(f"\nDrafting your answer in {language}...")
    try:
        final_answer = generate_final_response(question, relevant_info, target_dialect)

        print("\n" + "="*40)
        print("OFFICIAL ASSISTANT RESPONSE")
        print("="*40)
        print(final_answer)
        print("="*40)

        print(f"\nSources checked from {country}:")
        for link in links:
            print(f"- {link}")

    except Exception as e:
        print(f"\nError generating response: {e}")
        print("Make sure your GEMINI_API_KEY is set correctly in the .env file.")
        return {
            "answer": f"I encountered an error while generating the response: {str(e)}. Please check your API keys in the .env file.",
            "sources": links
        }

    # Convert text to speech
    # print("\nSpeaking the answer...")
    # asyncio.run(speak_answer(final_answer))

    return {
        "answer": final_answer,
        "sources": links
    }
