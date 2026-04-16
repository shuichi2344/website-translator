import os
from pathlib import Path
from dotenv import load_dotenv
from huggingface_hub import login
from sentence_transformers import SentenceTransformer
from engine.speech.chroma_config import ChromaDBConfig

load_dotenv(dotenv_path=Path(__file__).resolve().parents[2] / ".env", override=True)
hf_token = os.getenv("HF_TOKEN")

if hf_token: # Authenticate with Hugging Face
    login(token=hf_token)
else:
    print("Error: HF_TOKEN not found in .env file")

# Load the Gemma model (768 dimensions)
model = SentenceTransformer('google/embeddinggemma-300m')

db_manager = ChromaDBConfig()

def ingest_to_chroma(doc_id, text_chunks, source_urls=None, country=None):
    """
    Ingest text chunks into ChromaDB with optional source URL and country metadata
    
    Args:
        doc_id: Unique document identifier
        text_chunks: List of text chunks to store
        source_urls: Optional dict mapping chunk index to source URL
        country: Optional country name (e.g., "Malaysia", "Thailand") for filtering
    """
    if not text_chunks:
        return
    
    # 1. Generate Embeddings (Your existing Gemma logic)
    embeddings = model.encode(
        text_chunks, 
        prompt_name="Retrieval-document", 
        normalize_embeddings=True,
        show_progress_bar=True
    )
    
    # 2. Prepare metadata for each chunk
    metadatas = []
    source_count = 0
    for i in range(len(text_chunks)):
        metadata = {"doc_id": doc_id}
        if source_urls and i in source_urls:
            metadata["source_url"] = source_urls[i]
            source_count += 1
        if country:
            metadata["country"] = country
        metadatas.append(metadata)
    
    if source_count > 0:
        print(f"   📎 Storing {source_count} chunks with source URLs")
    
    # 3. Call the Manager to store them permanently with metadata
    db_manager.add_document_chunks(
        doc_id=doc_id,
        chunks=text_chunks,
        embeddings=embeddings,
        metadatas=metadatas
    )

def query_from_chroma(question, top_k=5, min_similarity=0.40, country=None, strict_mode=False):
    """
    Search for context directly from the ChromaDB storage.
    
    Args:
        question: The query text
        top_k: Number of results to return
        min_similarity: Minimum similarity threshold (0-1). Chunks below this are filtered out.
                       Lower distance = higher similarity. Default 0.40 = 40% similarity required.
        country: Optional country filter (e.g., "Malaysia", "Thailand"). If provided, only returns
                chunks from that country. If None, returns chunks from all countries.
        strict_mode: If True, uses higher threshold (40%) to prevent cross-topic contamination.
                    If False, uses default threshold (40%) for freshly fetched data.
    
    Returns:
        tuple: (chunks, sources)
        - chunks: list of relevant text chunks (filtered by similarity and country)
        - sources: list of source URLs (or None if not available)
    """
    # Apply strict mode threshold if enabled (now also 40%)
    if strict_mode:
        min_similarity = max(min_similarity, 0.40)  # At least 40% in strict mode
    # 1. Get the collection from the manager
    collection = db_manager.get_collection()
    
    # 2. Gemma requires the "query" prompt for the question
    query_vector = model.encode(
        [question], 
        prompt_name="Retrieval-query", 
        normalize_embeddings=True
    )
    
    # 3. Build where filter for country if specified
    where_filter = None
    if country:
        where_filter = {"country": country}
        print(f"   🌍 Filtering by country: {country}")
    
    # 4. Search ChromaDB directly with distances and optional country filter
    # Chroma handles the mapping of vectors back to text automatically!
    query_params = {
        "query_embeddings": query_vector.tolist(),
        "n_results": top_k,
        "include": ["documents", "metadatas", "distances"]
    }
    
    if where_filter:
        query_params["where"] = where_filter
    
    results = collection.query(**query_params)
    
    # 5. Extract chunks, distances, and source URLs
    chunks = results['documents'][0] if results['documents'] else []
    metadatas = results['metadatas'][0] if results.get('metadatas') else []
    distances = results['distances'][0] if results.get('distances') else []
    
    # 6. Filter chunks by similarity threshold AND keyword relevance
    # ChromaDB returns L2 distance (lower is better)
    # For normalized embeddings: distance = 2 * (1 - cosine_similarity)
    # So: cosine_similarity = 1 - (distance / 2)
    # We want similarity >= min_similarity, which means distance <= 2 * (1 - min_similarity)
    max_distance = 2 * (1 - min_similarity)
    
    # Extract key nouns from question for keyword matching
    import re
    question_lower = question.lower()
    # Remove common words and extract potential keywords
    stop_words = {'how', 'to', 'what', 'when', 'where', 'who', 'why', 'is', 'are', 'the', 'a', 'an', 'can', 'i', 'my', 'do', 'does'}
    question_words = set(re.findall(r'\b\w+\b', question_lower))
    keywords = question_words - stop_words
    
    filtered_chunks = []
    filtered_metadatas = []
    
    for i, (chunk, distance) in enumerate(zip(chunks, distances)):
        similarity = 1 - (distance / 2)
        chunk_country = metadatas[i].get('country', 'Unknown') if i < len(metadatas) else 'Unknown'
        
        if distance <= max_distance:
            # Additional keyword check: at least one key term should appear in chunk
            chunk_lower = chunk.lower()
            keyword_match = any(keyword in chunk_lower for keyword in keywords) if keywords else True
            
            if keyword_match:
                filtered_chunks.append(chunk)
                if i < len(metadatas):
                    filtered_metadatas.append(metadatas[i])
                print(f"   ✓ Chunk {i+1}: distance={distance:.3f}, similarity={similarity:.3f}, country={chunk_country}")
            else:
                print(f"   ✗ Chunk {i+1}: distance={distance:.3f}, similarity={similarity:.3f} (no keyword match)")
        else:
            print(f"   ✗ Chunk {i+1}: distance={distance:.3f}, similarity={similarity:.3f} (below threshold)")
    
    # 7. Extract unique source URLs from filtered results
    sources = []
    seen_urls = set()
    for metadata in filtered_metadatas:
        if metadata and 'source_url' in metadata:
            url = metadata['source_url']
            if url not in seen_urls:
                seen_urls.add(url)
                sources.append(url)
    
    if sources:
        print(f"   📎 Retrieved {len(sources)} unique source URLs from ChromaDB")
    
    return filtered_chunks, sources