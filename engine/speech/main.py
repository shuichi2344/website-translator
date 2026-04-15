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
    Process voice/text question following RAG architecture:
    1. Query → Embedding
    2. Embedding → Vector Database (ChromaDB)
    3. Vector Database → Relevant Data
    4. Relevant Data + Query → LLM
    5. LLM → Response
    
    Only fetch fresh data (A→B→C→D) if Vector Database has no relevant data
    
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

    # ═══════════════════════════════════════════════════════════════════
    # RAG RETRIEVAL PHASE
    # Step 1: Query → Embedding
    # Step 2: Embedding → Vector Database
    # Step 3: Vector Database → Relevant Data
    # ═══════════════════════════════════════════════════════════════════
    
    print("\n🔍 [RAG Step 1-3] Querying Vector Database (ChromaDB)...")
    relevant_info = []
    sources = []
    
    try:
        # Query ChromaDB with embedded question
        # min_similarity=0.4 means we need at least 40% similarity
        # Filter by country to prevent wrong-country answers
        relevant_info, sources = query_from_chroma(question, top_k=10, min_similarity=0.4, country=country)
        
        # Use only top 3 chunks for accuracy
        if relevant_info and len(relevant_info) >= 3:
            relevant_info = relevant_info[:3]
            print(f"✅ Found {len(relevant_info)} relevant chunks in Vector Database (using top 3)")
            if sources:
                print(f"   📎 From {len(sources)} source URLs")
            print("\n--- Relevant Data Retrieved ---")
            for i, snippet in enumerate(relevant_info, 1):
                preview = snippet.replace('\n', ' ')[:150]
                print(f"[{i}] {preview}...")
        else:
            if relevant_info:
                print(f"ℹ️ Found {len(relevant_info)} chunks but below threshold (need 3+)")
            else:
                print("ℹ️ No relevant data found in Vector Database")
            
    except Exception as e:
        print(f"⚠️ Error querying Vector Database: {e}")
        relevant_info = []
        sources = []

    # ═══════════════════════════════════════════════════════════════════
    # DATA PREPARATION PHASE (Only if Vector Database is empty)
    # Step A: Raw Data Sources (Government websites)
    # Step B: Information Extraction (Firecrawl)
    # Step C: Chunking
    # Step D: Embedding → Store in Vector Database
    # ═══════════════════════════════════════════════════════════════════
    
    if not relevant_info or len(relevant_info) < 3:
        print(f"\n📡 [Data Preparation] Vector Database has insufficient data, fetching fresh sources...")
        
        # Step A: Raw Data Sources
        print(f"[Step A] Searching for government sources from {country}...")
        links = find_specific_gov_links(query, country_suffix)
        
        if not links:
            print("❌ No official links found.")
            return {
                "answer": f"I couldn't find any relevant government sources from {country} for your question. Please make sure SERP_API_KEY is configured in your .env file, or try rephrasing your question.",
                "sources": []
            }

        print(f"✅ Found {len(links)} government sources")

        # Step B: Information Extraction + Step C: Chunking
        print(f"[Step B-C] Extracting and chunking information from sources...")
        all_chunks, chunk_to_url_map = get_chunks_from_list(links)
        print(f"✅ Extracted {len(all_chunks)} text chunks")

        if not all_chunks:
            print("❌ Extraction failed or no text found on pages.")
            return {
                "answer": f"I found some government sources from {country} but couldn't extract information from them. The websites might be unavailable or require authentication.",
                "sources": links
            }

        # Step D: Embedding → Store in Vector Database
        print(f"[Step D] Storing embeddings in Vector Database with source URLs...")
        doc_id = f"gov_search_{country}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        ingest_to_chroma(doc_id, all_chunks, source_urls=chunk_to_url_map, country=country)
        print(f"✅ Stored in Vector Database with ID: {doc_id} (country: {country})")

        # Query for top chunks with 40% similarity threshold
        print(f"\n🔍 [RAG Step 1-3] Re-querying Vector Database with new data...")
        relevant_info, sources = query_from_chroma(question, top_k=10, min_similarity=0.4, country=country)
        
        # Use only top 3 chunks above 40% threshold for accuracy
        if relevant_info and len(relevant_info) >= 3:
            relevant_info = relevant_info[:3]
            print(f"✅ Using top 3 most relevant chunks (all above 40% similarity)")
        elif relevant_info and len(relevant_info) > 0:
            print(f"✅ Using {len(relevant_info)} chunks above 40% threshold")
        else:
            print(f"⚠️ No chunks above 40% threshold, using top 3 chunks from fresh data")
            relevant_info = all_chunks[:3]
        
        print("\n--- Most Relevant Data Retrieved ---")
        for i, snippet in enumerate(relevant_info, 1):
            preview = snippet.replace('\n', ' ')[:150]
            print(f"[{i}] {preview}...")
    else:
        # Using cached data, sources already retrieved
        links = sources if sources else []

    # ═══════════════════════════════════════════════════════════════════
    # GENERATION PHASE
    # Step 4: Relevant Data + Query → LLM
    # Step 5: LLM → Response
    # ═══════════════════════════════════════════════════════════════════
    
    print(f"\n🤖 [RAG Step 4-5] Generating response with LLM...")
    print(f"   Language: {language}")
    print(f"   Context chunks: {len(relevant_info)}")
    
    try:
        final_answer = generate_final_response(question, relevant_info, target_dialect)

        print("\n" + "="*40)
        print("RESPONSE GENERATED")
        print("="*40)
        print(final_answer)
        print("="*40)

        if links:
            print(f"\nSources used (fresh data from {country}):")
            for link in links:
                print(f"- {link}")
        else:
            print(f"\nUsing cached data from Vector Database")

    except Exception as e:
        print(f"\n❌ Error generating response: {e}")
        print("Make sure your GEMINI_API_KEY is set correctly in the .env file.")
        return {
            "answer": f"I encountered an error while generating the response: {str(e)}. Please check your API keys in the .env file.",
            "sources": links if links else []
        }

    return {
        "answer": final_answer,
        "sources": sources if sources else []
    }
