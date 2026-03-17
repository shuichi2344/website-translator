from speech_to_text import run_assistant as speech_to_text
from web_scraping import get_chunks_from_list
from text_to_speech import speak_answer
from government_mapping import find_specific_gov_links
from embedding import ingest_to_chroma, query_from_chroma
from response_gen import generate_final_response
import asyncio
from datetime import datetime

country_suffix = "my"

def main():
    result = speech_to_text()

    dialect = result.get("dialect")
    question = result.get("question")
    query = result.get("query")

    print("-" * 30)
    if question:
        print("Question:", question)
    if dialect:
        print("Dialect:", dialect)
    if query:
        print("Normalized query:", query)
    print("-" * 30)

    # base_link = find_specific_gov_links("Malaysia passport renewal online?", "my")
    links = find_specific_gov_links(query, country_suffix)
    if not links:
        print("No official links found.")
        return

    print(f"Found {len(links)} specific sources. Starting extraction...")

    # Extract and Chunk
    all_chunks = get_chunks_from_list(links)
    print(f"\nTotal unique chunks collected: {len(all_chunks)}")

    if not all_chunks:
        print("Extraction failed or no text found on pages.")
        return

    print("\nStoring data to chromadb...")
    doc_id = f"gov_search_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    ingest_to_chroma(doc_id, all_chunks)

    print(f"\nProcessing Question: {question}")
    relevant_info = query_from_chroma(question, top_k=5) # Search for the most relevant 5 snippets

    print("\n--- Most Relevant Official Info Found ---")
    for i, snippet in enumerate(relevant_info, 1):
        # Print a short preview of what the AI is "reading"
        preview = snippet.replace('\n', ' ')[:150]
        print(f"[{i}] {preview}...")

    # Generate Answer using Gemini
    final_answer = ""
    print("\nDrafting your answer...")
    try:
        final_answer = generate_final_response(question, relevant_info, dialect)

        print("\n" + "="*40)
        print("OFFICIAL ASSISTANT RESPONSE")
        print("="*40)
        print(final_answer)
        print("="*40)

        print("\nSources checked:")
        for link in links:
            print(f"- {link}")

    except Exception as e:
        print(f"\nError generating response: {e}")
        print("Make sure your GOOGLE_API_KEY is set correctly in the .env file.")

    # Convert text to speech
    print("\nSpeaking the answer...")
    asyncio.run(speak_answer(final_answer))

if __name__ == "__main__":
    main()