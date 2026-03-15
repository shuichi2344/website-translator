"""
Test script to verify ChromaDB and EmbeddingGemma setup
"""

import os
from dotenv import load_dotenv

load_dotenv()

print("=" * 60)
print("🧪 Testing ChromaDB & EmbeddingGemma Setup")
print("=" * 60)

# Test 1: Check environment variables
print("\n1️⃣ Checking Environment Variables...")
gemini_key = os.getenv('GEMINI_API_KEY')
hf_token = os.getenv('HUGGINGFACE_TOKEN')

if gemini_key and gemini_key != 'your-gemini-api-key-here':
    print("   ✅ GEMINI_API_KEY is set")
else:
    print("   ❌ GEMINI_API_KEY is missing or placeholder")

if hf_token and hf_token != 'your-huggingface-token-here':
    print("   ✅ HUGGINGFACE_TOKEN is set")
else:
    print("   ⚠️  HUGGINGFACE_TOKEN is missing or placeholder")
    print("      → Embeddings will be disabled")

# Test 2: Check ChromaDB
print("\n2️⃣ Testing ChromaDB...")
try:
    import chromadb
    from chromadb.config import Settings
    
    client = chromadb.PersistentClient(
        path="./chroma_db",
        settings=Settings(
            anonymized_telemetry=False,
            allow_reset=True
        )
    )
    
    collection = client.get_or_create_collection(
        name="document_chunks",
        metadata={"description": "Document chunks with EmbeddingGemma embeddings"}
    )
    
    print(f"   ✅ ChromaDB connected successfully")
    print(f"   📊 Current embeddings: {collection.count()}")
    
except Exception as e:
    print(f"   ❌ ChromaDB error: {e}")

# Test 3: Check EmbeddingGemma
print("\n3️⃣ Testing EmbeddingGemma...")
if hf_token and hf_token != 'your-huggingface-token-here':
    try:
        from huggingface_hub import login
        from sentence_transformers import SentenceTransformer
        
        # Login to Hugging Face
        login(token=hf_token, add_to_git_credential=False)
        print("   ✅ Logged in to Hugging Face")
        
        # Try to load model
        print("   🔄 Loading EmbeddingGemma-300M (this may take a minute)...")
        model = SentenceTransformer("google/embeddinggemma-300m")
        print("   ✅ EmbeddingGemma-300M loaded successfully")
        
        # Test embedding
        test_text = ["This is a test sentence"]
        embeddings = model.encode(test_text, prompt_name="Retrieval-document")
        print(f"   ✅ Test embedding created: {embeddings.shape}")
        
    except Exception as e:
        error_msg = str(e)
        if "gated repo" in error_msg or "401" in error_msg:
            print("   ❌ Access denied to EmbeddingGemma")
            print("      → Request access: https://huggingface.co/google/embeddinggemma-300m")
        else:
            print(f"   ❌ Error: {e}")
else:
    print("   ⚠️  Skipping (no Hugging Face token)")

# Test 4: Test full pipeline with a simple document
print("\n4️⃣ Testing Full Pipeline...")
try:
    from document_summariser_v6_gemini import DocumentSummarizer
    
    # Create summarizer with embeddings enabled
    summarizer = DocumentSummarizer(
        target_lang='en',
        use_ai=True,
        use_embeddings=True,
        use_vector_db=True
    )
    
    # Test with a simple text
    test_text = """
    This is a test document. It contains multiple sentences to test the chunking and embedding process.
    The document should be split into chunks, embedded using EmbeddingGemma, and stored in ChromaDB.
    This will verify that the entire pipeline is working correctly.
    """
    
    print("   🔄 Testing document processing...")
    
    # Generate doc_id
    doc_id = summarizer._get_document_id(test_text)
    print(f"   📝 Document ID: {doc_id[:8]}...")
    
    # Create chunks
    chunks = summarizer._split_into_chunks(test_text, max_words=50, overlap=10)
    print(f"   ✂️  Created {len(chunks)} chunks")
    
    # Create embeddings (this will also store in ChromaDB)
    if summarizer.embedding_model:
        embeddings = summarizer._embed_chunks(chunks, doc_id=doc_id)
        
        if embeddings is not None:
            print(f"   ✅ Embeddings created and stored!")
            
            # Verify storage
            if summarizer.collection:
                count = summarizer.collection.count()
                print(f"   📊 ChromaDB now has {count} embeddings")
        else:
            print("   ⚠️  Embeddings creation failed")
    else:
        print("   ⚠️  Embedding model not initialized")
    
except Exception as e:
    print(f"   ❌ Pipeline test failed: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("🏁 Test Complete!")
print("=" * 60)

# Summary
print("\n📋 Summary:")
print("   • If all tests pass ✅, your setup is complete!")
print("   • If EmbeddingGemma fails ⚠️, add HUGGINGFACE_TOKEN to .env")
print("   • Check HUGGINGFACE_SETUP.md for detailed instructions")
print("\n💡 Next step: Run 'python chroma_config.py stats' to verify embeddings")
