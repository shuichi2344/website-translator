import os
from dotenv import load_dotenv
from huggingface_hub import login
from sentence_transformers import SentenceTransformer
from engine.speech.chroma_config import ChromaDBConfig

load_dotenv()
hf_token = os.getenv("HF_TOKEN")

if hf_token: # Authenticate with Hugging Face
    login(token=hf_token)
else:
    print("Error: HF_TOKEN not found in .env file")

# Load the Gemma model (768 dimensions) with increased timeout
# Set environment variables to increase timeout and enable offline mode if cached
os.environ['HF_HUB_DOWNLOAD_TIMEOUT'] = '120'  # 120 seconds timeout
os.environ['TRANSFORMERS_OFFLINE'] = '0'  # Allow online access but prefer cache

print("📦 Loading google/embeddinggemma-300m...")
try:
    # Try loading with local_files_only first (fastest if cached)
    try:
        model = SentenceTransformer('google/embeddinggemma-300m', local_files_only=True)
        print("✅ Embedding model loaded from local cache")
    except Exception:
        # Not cached, download with timeout
        print("   Model not cached locally, downloading from Hugging Face...")
        model = SentenceTransformer('google/embeddinggemma-300m')
        print("✅ Embedding model downloaded and loaded successfully")
except Exception as e:
    print(f"❌ Error loading embedding model: {e}")
    print("   This might be due to:")
    print("   1. Slow internet connection")
    print("   2. Hugging Face servers being slow")
    print("   3. Network firewall blocking Hugging Face")
    print("   Retrying with longer timeout (5 minutes)...")
    # Retry with even longer timeout
    os.environ['HF_HUB_DOWNLOAD_TIMEOUT'] = '300'  # 5 minutes
    model = SentenceTransformer('google/embeddinggemma-300m')
    print("✅ Embedding model loaded successfully on retry")

db_manager = ChromaDBConfig()

def ingest_to_chroma(doc_id, text_chunks, source_urls=None):
    """
    Ingest text chunks into ChromaDB with optional source URL metadata
    
    Args:
        doc_id: Unique document identifier
        text_chunks: List of text chunks to store
        source_urls: Optional dict mapping chunk index to source URL
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
    for i in range(len(text_chunks)):
        metadata = {"doc_id": doc_id}
        if source_urls and i in source_urls:
            metadata["source_url"] = source_urls[i]
        metadatas.append(metadata)
    
    # 3. Call the Manager to store them permanently with metadata
    db_manager.add_document_chunks(
        doc_id=doc_id,
        chunks=text_chunks,
        embeddings=embeddings,
        metadatas=metadatas
    )

def query_from_chroma(question, top_k=5, min_similarity=0.6):
    """
    Search for context directly from the ChromaDB storage.
    
    Args:
        question: The query text
        top_k: Number of results to return
        min_similarity: Minimum similarity threshold (0-1). Chunks below this are filtered out.
                       Lower distance = higher similarity. Default 0.6 = 60% similarity required.
    
    Returns:
        tuple: (chunks, sources)
        - chunks: list of relevant text chunks (filtered by similarity)
        - sources: list of source URLs (or None if not available)
    """
    # 1. Get the collection from the manager
    collection = db_manager.get_collection()
    
    # 2. Gemma requires the "query" prompt for the question
    query_vector = model.encode(
        [question], 
        prompt_name="Retrieval-query", 
        normalize_embeddings=True
    )
    
    # 3. Search ChromaDB directly with distances
    # Chroma handles the mapping of vectors back to text automatically!
    results = collection.query(
        query_embeddings=query_vector.tolist(),
        n_results=top_k,
        include=["documents", "metadatas", "distances"]
    )
    
    # 4. Extract chunks, distances, and source URLs
    chunks = results['documents'][0] if results['documents'] else []
    metadatas = results['metadatas'][0] if results.get('metadatas') else []
    distances = results['distances'][0] if results.get('distances') else []
    
    # 5. Filter chunks by similarity threshold
    # ChromaDB returns L2 distance (lower is better)
    # For normalized embeddings: distance = 2 * (1 - cosine_similarity)
    # So: cosine_similarity = 1 - (distance / 2)
    # We want similarity >= min_similarity, which means distance <= 2 * (1 - min_similarity)
    max_distance = 2 * (1 - min_similarity)
    
    filtered_chunks = []
    filtered_metadatas = []
    
    for i, (chunk, distance) in enumerate(zip(chunks, distances)):
        if distance <= max_distance:
            filtered_chunks.append(chunk)
            if i < len(metadatas):
                filtered_metadatas.append(metadatas[i])
            print(f"   ✓ Chunk {i+1}: distance={distance:.3f}, similarity={1 - (distance/2):.3f}")
        else:
            print(f"   ✗ Chunk {i+1}: distance={distance:.3f}, similarity={1 - (distance/2):.3f} (below threshold)")
    
    # 6. Extract unique source URLs from filtered results
    sources = []
    seen_urls = set()
    for metadata in filtered_metadatas:
        if metadata and 'source_url' in metadata:
            url = metadata['source_url']
            if url not in seen_urls:
                seen_urls.add(url)
                sources.append(url)
    
    return filtered_chunks, sources