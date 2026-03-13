from speech_to_text import speech_to_text
from web_scraping import get_chunks_from_list
from text_to_speech import speak_answer
from government_mapping import find_specific_gov_links
from embedding import create_vector_db, query_vector_db
from response_gen import generate_final_response
import asyncio

country_suffix = "my"

def main():
    result = speech_to_text()

    raw = result.get("raw")
    question = result.get("question")
    query = result["query"]
    dialect = result["dialect"]

    print("-" * 30)
    if raw:
        print("Raw:", raw)
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

    # 2. Extract and Chunk
    all_chunks = get_chunks_from_list(links)
    print(f"\nTotal unique chunks collected: {len(all_chunks)}")

    if not all_chunks:
        print("Extraction failed or no text found on pages.")
        return

    # 3. Create Vector Knowledge Base
    print("\nCreating Knowledge Base...")
    index, chunks = create_vector_db(all_chunks)

    # 4. Handle User Interaction
    # Suggestion: Use input() for a live demo, or keep it hardcoded for testing
    # question = "Can I renew my Malaysia passport online?"
    print(f"\nProcessing Question: {question}")

    # Search for the most relevant 3 snippets
    relevant_info = query_vector_db(question, index, chunks, top_k=3)

    print("\n--- Most Relevant Official Info Found ---")
    for i, snippet in enumerate(relevant_info, 1):
        # Print a short preview of what the AI is "reading"
        preview = snippet.replace('\n', ' ')[:150]
        print(f"[{i}] {preview}...")

    # 5. Generate Answer using Gemini
    final_answer = ""
    print("\nDrafting your answer...")
    try:
        final_answer = generate_final_response(question, relevant_info)

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

    # 6. Convert text to speech
    print("\nSpeaking the answer...")
    asyncio.run(speak_answer(final_answer))

if __name__ == "__main__":
    main()