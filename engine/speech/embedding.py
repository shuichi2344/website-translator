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

# Load the Gemma model (768 dimensions)
model = SentenceTransformer('google/embeddinggemma-300m')

db_manager = ChromaDBConfig()

def ingest_to_chroma(doc_id, text_chunks):
    if not text_chunks:
        return
    
    # 1. Generate Embeddings (Your existing Gemma logic)
    embeddings = model.encode(
        text_chunks, 
        prompt_name="Retrieval-document", 
        normalize_embeddings=True,
        show_progress_bar=True
    )
    
    # 2. Call the Manager to store them permanently
    db_manager.add_document_chunks(
        doc_id=doc_id,
        chunks=text_chunks,
        embeddings=embeddings
    )

def query_from_chroma(question, top_k=5):
    """
    Search for context directly from the ChromaDB storage.
    """
    # 1. Get the collection from the manager
    collection = db_manager.get_collection()
    
    # 2. Gemma requires the "query" prompt for the question
    query_vector = model.encode(
        [question], 
        prompt_name="Retrieval-query", 
        normalize_embeddings=True
    )
    
    # 3. Search ChromaDB directly
    # Chroma handles the mapping of vectors back to text automatically!
    results = collection.query(
        query_embeddings=query_vector.tolist(),
        n_results=top_k,
        include=["documents", "metadatas"]
    )
    
    # Return the text chunks (the "documents")
    return results['documents'][0] if results['documents'] else []