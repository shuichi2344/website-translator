"""
Test real document processing to verify embeddings are saved
"""

from document_summariser_v6_gemini import DocumentSummarizer

print("=" * 60)
print("🧪 Testing Real Document Processing with Embeddings")
print("=" * 60)

# Create summarizer
summarizer = DocumentSummarizer(
    target_lang='en',
    use_ai=True,
    use_embeddings=True,
    use_vector_db=True
)

# Test with a sample website
test_url = "https://www.gov.sg"

print(f"\n📝 Processing website: {test_url}")
print("   This will:")
print("   1. Extract text from website")
print("   2. Split into chunks")
print("   3. Create embeddings")
print("   4. Store in ChromaDB")
print("   5. Generate summary")

result = summarizer.process_website(test_url, crawl_depth=0, max_sublinks=0)

if result:
    print("\n" + "=" * 60)
    print("✅ Processing Complete!")
    print("=" * 60)
    print(f"Original: {result['word_count']} words")
    print(f"Summary: {result['summary_word_count']} words")
    
    # Check ChromaDB
    if summarizer.collection:
        count = summarizer.collection.count()
        print(f"\n📊 ChromaDB Status:")
        print(f"   Total embeddings: {count}")
        
        if count > 0:
            print("   ✅ Embeddings successfully saved!")
        else:
            print("   ⚠️  No embeddings found in database")
    
    print("\n📄 Summary Preview:")
    print("-" * 60)
    print(result['summary'][:500] + "..." if len(result['summary']) > 500 else result['summary'])
    print("-" * 60)
else:
    print("\n❌ Processing failed")

print("\n💡 Verify with: python chroma_config.py stats")
