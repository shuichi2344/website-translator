# ChromaDB Configuration & Management Guide

## Overview

This guide covers ChromaDB installation, configuration, management, and best practices for the Bridge document summarizer with EmbeddingGemma-300M.

## Installation

### Prerequisites

```bash
# Python 3.8 or higher
python --version

# pip package manager
pip --version
```

### Install ChromaDB

```bash
# Install ChromaDB with all dependencies
pip install chromadb

# Or install with specific version
pip install chromadb==0.4.22
```

### Install EmbeddingGemma Dependencies

```bash
# Install sentence-transformers for EmbeddingGemma
pip install sentence-transformers

# Install Hugging Face Hub for authentication
pip install huggingface-hub
```

### Complete Installation (All at Once)

```bash
pip install chromadb sentence-transformers huggingface-hub
```

### Verify Installation

```bash
# Test ChromaDB
python -c "import chromadb; print('ChromaDB version:', chromadb.__version__)"

# Test sentence-transformers
python -c "from sentence_transformers import SentenceTransformer; print('✅ sentence-transformers installed')"

# Test Hugging Face Hub
python -c "from huggingface_hub import login; print('✅ huggingface-hub installed')"
```

### Setup Hugging Face Authentication

1. **Request Access to EmbeddingGemma**
   - Go to: https://huggingface.co/google/embeddinggemma-300m
   - Click "Agree and access repository"
   - Access is usually granted instantly

2. **Get Your Token**
   - Go to: https://huggingface.co/settings/tokens
   - Click "New token" → Name: `bridge-embeddings` → Type: Read
   - Copy the token (starts with `hf_`)

3. **Add to .env File**
   ```bash
   HUGGINGFACE_TOKEN="hf_YourActualTokenHere"
   ```

4. **Test Authentication**
   ```bash
   python test_chromadb.py
   ```

See `HUGGINGFACE_SETUP.md` for detailed authentication instructions.

## Quick Start

### First Time Setup

```bash
# 1. Install dependencies
pip install chromadb sentence-transformers huggingface-hub

# 2. Set up Hugging Face token in .env
echo 'HUGGINGFACE_TOKEN="hf_YourTokenHere"' >> .env

# 3. Test the setup
python test_chromadb.py

# 4. Check database status
python chroma_config.py stats
```

### How Embeddings Are Saved

The system automatically creates and stores embeddings for ALL documents (both short and long):

1. **Document Processing**
   - Text is extracted from document/website
   - Document ID is generated using MD5 hash
   - System checks if embeddings already exist

2. **Chunking**
   - Text is split into chunks (max 2000 words, 300 word overlap)
   - Supports both word-based and character-based chunking (for ASEAN languages)

3. **Embedding Creation**
   - Each chunk is embedded using EmbeddingGemma-300M (768-dim vectors)
   - Uses `Retrieval-document` prompt for optimal retrieval

4. **Storage in ChromaDB**
   - Embeddings are stored with metadata (doc_id, chunk_index)
   - Persistent storage in `./chroma_db/` directory
   - Automatic deduplication using doc_id

5. **Smart Caching**
   - Same document = instant retrieval (no re-processing)
   - Embeddings persist across sessions
   - Fast similarity search (<10ms)

### Verify Embeddings Are Saved

```bash
# Process a document
python document_summariser_v6_gemini.py

# Check if embeddings were saved
python chroma_config.py stats

# Should show:
# total_chunks: X (where X > 0)
# unique_documents: Y (where Y > 0)
```

### Check Database Status

```bash
python chroma_config.py stats
```

Output:
```
📊 ChromaDB Statistics
============================================================
  total_chunks: 150
  unique_documents: 12
  database_size_mb: 45.23
  database_path: ./chroma_db
  collection_name: document_chunks
  timestamp: 2026-03-14T10:30:00
============================================================
```

### List All Documents

```bash
python chroma_config.py list
```

Output:
```
📚 Documents in database: 12
============================================================
  • 5d41402a... - 15 chunks
  • 7c9e6679... - 8 chunks
  • 9b8c7d6e... - 22 chunks
============================================================
```

## Configuration

### Default Settings

Located in `chroma_config.py`:

```python
# Database location
DEFAULT_DB_PATH = "./chroma_db"

# Collection name
DEFAULT_COLLECTION_NAME = "document_chunks"

# Embedding dimension
DEFAULT_EMBEDDING_DIM = 768

# Performance
BATCH_SIZE = 100
MAX_CACHE_SIZE = 1000

# Maintenance
AUTO_CLEANUP_DAYS = 30
MAX_DB_SIZE_GB = 10
```

### Custom Configuration

```python
from chroma_config import ChromaDBConfig

# Custom database path
config = ChromaDBConfig(
    db_path="./my_custom_db",
    collection_name="my_collection"
)

# Get statistics
stats = config.get_stats()
print(stats)
```

## Management Commands

### 1. View Statistics

```bash
python chroma_config.py stats
```

Shows:
- Total chunks stored
- Unique documents
- Database size
- Collection info

### 2. List Documents

```bash
python chroma_config.py list
```

Shows all documents with:
- Document ID (first 8 chars)
- Number of chunks per document

### 3. Delete Document

```bash
python chroma_config.py delete 5d41402a
```

Deletes all chunks for a specific document ID.

### 4. Cleanup Old Embeddings

```bash
python chroma_config.py cleanup
```

Removes embeddings older than 30 days (configurable).

### 5. Optimize Database

```bash
python chroma_config.py optimize
```

Performs:
- Cleanup of old embeddings
- Database size optimization
- Performance improvements

### 6. Backup Database

```bash
python chroma_config.py backup
```

Creates timestamped backup:
```
./chroma_db_backup_20260314_103000/
```

### 7. Export Metadata

```bash
python chroma_config.py export
```

Exports to `chroma_metadata.json`:
```json
{
  "exported_at": "2026-03-14T10:30:00",
  "total_documents": 12,
  "total_chunks": 150,
  "documents": [
    {
      "doc_id": "5d41402abc4b2a76b9719d911017c592",
      "chunk_count": 15,
      "chunks": [...]
    }
  ]
}
```

### 8. Clear All Data

```bash
python chroma_config.py clear
```

⚠️ **Warning:** This deletes ALL embeddings!

## Python API

### Initialize Configuration

```python
from chroma_config import ChromaDBConfig

config = ChromaDBConfig()
```

### Get Statistics

```python
stats = config.get_stats()
print(f"Total chunks: {stats['total_chunks']}")
print(f"Database size: {stats['database_size_mb']} MB")
```

### Delete Specific Document

```python
doc_id = "5d41402abc4b2a76b9719d911017c592"
config.delete_document(doc_id)
```

### Cleanup Old Embeddings

```python
# Delete embeddings older than 30 days
deleted_count = config.cleanup_old_embeddings(days=30)
print(f"Deleted {deleted_count} old embeddings")
```

### Optimize Database

```python
config.optimize_database()
```

### Create Backup

```python
backup_path = config.backup_database()
print(f"Backup created at: {backup_path}")
```

### Export Metadata

```python
config.export_metadata("my_export.json")
```

### Clear Collection

```python
config.clear_collection()
```

## Maintenance Schedule

### Daily
- Check database size
- Monitor chunk count

### Weekly
- Run optimization
- Review document list

### Monthly
- Create backup
- Cleanup old embeddings
- Export metadata

### As Needed
- Delete specific documents
- Clear collection (if needed)

## Best Practices

### 1. Regular Backups

```bash
# Create weekly backup
python chroma_config.py backup

# Or use cron job (Linux/Mac)
0 0 * * 0 cd /path/to/project && python chroma_config.py backup
```

### 2. Monitor Database Size

```python
config = ChromaDBConfig()
stats = config.get_stats()

if stats['database_size_mb'] > 1000:  # 1GB
    print("⚠️  Database size exceeds 1GB - consider cleanup")
    config.cleanup_old_embeddings(days=30)
```

### 3. Periodic Optimization

```bash
# Run monthly
python chroma_config.py optimize
```

### 4. Document Lifecycle

```python
# After processing document
doc_id = summarizer._get_document_id(text)

# Later, if document is outdated
config.delete_document(doc_id)
```

## Troubleshooting

### Embeddings Not Being Saved

**Problem:** ChromaDB shows 0 chunks after processing documents

**Symptoms:**
```bash
python chroma_config.py stats
# Shows: total_chunks: 0
```

**Common Causes & Solutions:**

1. **Missing Hugging Face Token**
   ```bash
   # Check if token is set
   python -c "import os; from dotenv import load_dotenv; load_dotenv(); print('Token:', os.getenv('HUGGINGFACE_TOKEN')[:10] if os.getenv('HUGGINGFACE_TOKEN') else 'NOT SET')"
   
   # Solution: Add token to .env
   HUGGINGFACE_TOKEN="hf_YourTokenHere"
   ```

2. **Wrong Prompt Names** (Fixed in v2.0)
   - Old code used: `retrieval_document` and `retrieval_query`
   - Correct names: `Retrieval-document` and `Retrieval-query` (capital R, hyphen)
   - This is now fixed in the latest version

3. **Missing `_get_document_id()` Function** (Fixed in v2.0)
   - Function was called but not defined
   - Now properly implemented using MD5 hash

4. **Short Documents Not Embedded** (Fixed in v2.0)
   - Old code only embedded documents > 5000 words
   - Now ALL documents are embedded regardless of length

**Verification:**
```bash
# Run comprehensive test
python test_chromadb.py

# Should show all ✅ green checkmarks
# Final line should show: "ChromaDB now has X embeddings"
```

### Database Locked Error

**Problem:** `database is locked`

**Solution:**
```bash
# Close all Python processes
pkill -f python

# Or delete lock file
rm chroma_db/*.lock
```

### Out of Disk Space

**Problem:** Database too large

**Solution:**
```bash
# Check size
python chroma_config.py stats

# Cleanup old data
python chroma_config.py cleanup

# Or clear all
python chroma_config.py clear
```

### Slow Queries

**Problem:** Queries taking too long

**Solution:**
```bash
# Optimize database
python chroma_config.py optimize

# Check collection size
python chroma_config.py stats
```

### Corrupted Database

**Problem:** Database errors

**Solution:**
```bash
# Restore from backup
rm -rf chroma_db
cp -r chroma_db_backup_20260314_103000 chroma_db

# Or start fresh
python chroma_config.py clear
```

## Advanced Configuration

### Custom Collection Settings

```python
import chromadb
from chromadb.config import Settings

client = chromadb.PersistentClient(
    path="./chroma_db",
    settings=Settings(
        anonymized_telemetry=False,
        allow_reset=True,
        is_persistent=True,
        # Advanced settings
        chroma_db_impl="duckdb+parquet",
        chroma_api_impl="local"
    )
)
```

### Multiple Collections

```python
config = ChromaDBConfig()
client = config.get_client()

# Create separate collections
malaysia_col = client.get_or_create_collection("malaysia_docs")
singapore_col = client.get_or_create_collection("singapore_docs")
```

### Metadata Filtering

```python
collection = config.get_collection()

# Query with metadata filter
results = collection.query(
    query_embeddings=[query_embedding],
    where={"country": "malaysia"},
    n_results=10
)
```

## Performance Tuning

### Batch Operations

```python
# Add embeddings in batches
BATCH_SIZE = 100

for i in range(0, len(chunks), BATCH_SIZE):
    batch = chunks[i:i+BATCH_SIZE]
    collection.add(
        ids=[...],
        embeddings=[...],
        documents=batch
    )
```

### Query Optimization

```python
# Limit results for faster queries
results = collection.query(
    query_embeddings=[...],
    n_results=10,  # Only get top 10
    include=["documents"]  # Don't include embeddings
)
```

### Memory Management

```python
# For large databases, use streaming
def process_in_batches(collection, batch_size=100):
    offset = 0
    while True:
        results = collection.get(
            limit=batch_size,
            offset=offset
        )
        
        if not results['ids']:
            break
        
        # Process batch
        yield results
        offset += batch_size
```

## Monitoring

### Database Health Check

```python
def health_check():
    config = ChromaDBConfig()
    stats = config.get_stats()
    
    issues = []
    
    # Check size
    if stats['database_size_mb'] > 5000:  # 5GB
        issues.append("Database size exceeds 5GB")
    
    # Check chunk count
    if stats['total_chunks'] > 100000:
        issues.append("Too many chunks - consider cleanup")
    
    if issues:
        print("⚠️  Health check issues:")
        for issue in issues:
            print(f"   • {issue}")
    else:
        print("✅ Database healthy")
    
    return len(issues) == 0
```

### Usage Statistics

```python
def usage_report():
    config = ChromaDBConfig()
    stats = config.get_stats()
    
    print(f"""
    📊 ChromaDB Usage Report
    ========================
    Documents: {stats['unique_documents']}
    Chunks: {stats['total_chunks']}
    Size: {stats['database_size_mb']} MB
    Avg chunks/doc: {stats['total_chunks'] / max(stats['unique_documents'], 1):.1f}
    """)
```

## Security

### Access Control

```python
# Restrict database path
DB_PATH = os.getenv("CHROMA_DB_PATH", "./chroma_db")

# Validate path
if not DB_PATH.startswith("./"):
    raise ValueError("Invalid database path")
```

### Data Privacy

```python
# Don't store sensitive data in metadata
metadata = {
    "doc_id": doc_id,
    "chunk_index": i,
    # Don't include: user_id, email, etc.
}
```

## Summary

✅ **Easy management** - Simple CLI commands
✅ **Monitoring** - Track size, chunks, documents
✅ **Maintenance** - Cleanup, optimize, backup
✅ **Troubleshooting** - Clear error messages
✅ **Performance** - Batch operations, query optimization
✅ **Security** - Access control, data privacy

Use `python chroma_config.py` for all your ChromaDB management needs! 🚀
