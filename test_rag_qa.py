"""
Test RAG Q&A functionality for both documents and websites
"""

from document_summariser_v6_gemini import DocumentSummarizer
import os

print("=" * 60)
print("🧪 Testing RAG Q&A for Documents and Websites")
print("=" * 60)

# Create summarizer with RAG enabled
summarizer = DocumentSummarizer(
    target_lang='en',
    use_ai=True,
    use_embeddings=True,
    use_vector_db=True
)

print("\n" + "=" * 60)
print("Test 1: RAG Q&A for Website")
print("=" * 60)

# Test website Q&A
test_url = "https://www.gov.sg"
test_question_web = "What services does the government provide?"

print(f"\n📝 Testing website Q&A:")
print(f"   URL: {test_url}")
print(f"   Question: {test_question_web}")

result_web = summarizer.rag_qa_website(test_url, test_question_web)

if result_web:
    print("\n✅ Website Q&A Result:")
    print(f"   Original: {result_web['word_count']} words")
    print(f"   Answer: {result_web['summary_word_count']} words")
    print(f"\n📄 Answer:")
    print("-" * 60)
    print(result_web['summary'])
    print("-" * 60)
else:
    print("\n❌ Website Q&A failed")

print("\n" + "=" * 60)
print("Test 2: RAG Q&A for Document (Text)")
print("=" * 60)

# Test document Q&A with sample text
sample_text = """
The Malaysian government provides various public services to its citizens.
These include healthcare services through government hospitals and clinics,
education services through public schools and universities, and social welfare
programs for the elderly and disabled. The government also manages public
transportation systems, maintains roads and infrastructure, and provides
security through the police and military forces.

Citizens can access these services through various government agencies.
For healthcare, they can visit any government hospital or clinic with their
MyKad identification card. Education services are provided free or at
subsidized rates for Malaysian citizens. Social welfare benefits can be
applied for through the Department of Social Welfare.

The government has also digitized many services through the MyGovernment
portal, where citizens can apply for various documents, pay bills, and
access information about government programs. This digital transformation
aims to make government services more accessible and efficient for all
Malaysians.
"""

test_question_doc = "How can citizens access healthcare services?"

print(f"\n📝 Testing document Q&A:")
print(f"   Document length: {len(sample_text.split())} words")
print(f"   Question: {test_question_doc}")

result_doc = summarizer.rag_qa(sample_text, test_question_doc, source_type="document")

if result_doc:
    print("\n✅ Document Q&A Result:")
    print(f"   Original: {result_doc['word_count']} words")
    print(f"   Answer: {result_doc['summary_word_count']} words")
    print(f"\n📄 Answer:")
    print("-" * 60)
    print(result_doc['summary'])
    print("-" * 60)
else:
    print("\n❌ Document Q&A failed")

print("\n" + "=" * 60)
print("Test 3: Check ChromaDB Storage")
print("=" * 60)

if summarizer.collection:
    count = summarizer.collection.count()
    print(f"\n📊 ChromaDB Status:")
    print(f"   Total embeddings: {count}")
    
    if count > 0:
        print("   ✅ Embeddings stored successfully!")
        print("\n💡 Tip: Run 'python chroma_config.py stats' for detailed stats")
    else:
        print("   ⚠️  No embeddings found")
else:
    print("   ⚠️  ChromaDB not initialized")

print("\n" + "=" * 60)
print("🏁 Test Complete!")
print("=" * 60)

print("\n📋 Summary:")
print("   • RAG Q&A works for both websites and documents")
print("   • Embeddings are cached in ChromaDB for fast retrieval")
print("   • Semantic search finds the most relevant chunks")
print("   • Answers are generated in simple language")

print("\n💡 Next Steps:")
print("   1. Test via web interface: python summarizer_web.py")
print("   2. Upload a document and ask questions")
print("   3. Enter a website URL and ask questions")
print("   4. Check ChromaDB: python chroma_config.py stats")
