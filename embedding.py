import numpy as np
import faiss
import os
from dotenv import load_dotenv
from huggingface_hub import login
from sentence_transformers import SentenceTransformer

load_dotenv()

# Get the token
hf_token = os.getenv("HF_TOKEN")

if hf_token:
    # Authenticate with Hugging Face
    login(token=hf_token)
else:
    print("Error: HF_TOKEN not found in .env file")

# Load the Gemma model (768 dimensions)
model = SentenceTransformer('google/embeddinggemma-300m')

def create_vector_db(chunks):
    if not chunks:
        return None, None

    # 1. Gemma requires the "document" prompt for context chunks
    embeddings = model.encode(
        chunks, 
        prompt_name="Retrieval-document", 
        normalize_embeddings=True,
        show_progress_bar=True
    )
    
    # 2. Update dimension to 768 (auto-detected here)
    dimension = embeddings.shape[1]
    
    # 3. Use IndexFlatIP (Inner Product) for normalized vectors
    index = faiss.IndexFlatIP(dimension)
    index.add(np.array(embeddings).astype('float32'))
    
    return index, chunks

def query_vector_db(question, index, chunks, top_k=3):
    if index is None:
        return ["No knowledge base available."]

    # 1. Gemma requires the "query" prompt for the user question
    query_vector = model.encode(
        [question], 
        prompt_name="Retrieval-query", 
        normalize_embeddings=True
    )
    
    # 2. Search (IndexFlatIP returns the highest dot product/similarity)
    distances, indices = index.search(np.array(query_vector).astype('float32'), top_k)
    
    # 3. Map indices back to text
    results = [chunks[i] for i in indices[0] if i < len(chunks)]
    return results