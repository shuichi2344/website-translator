# Database Message Storage Integration ✅

## Overview

All chat messages are now stored in both MySQL (structured data) and ChromaDB (vector embeddings) for full conversation history and semantic search capabilities.

## Architecture

### Dual Storage System

```
┌─────────────────────────────────────────────────────────────┐
│                      User sends message                      │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
         ┌─────────────────────────────┐
         │   Save to MySQL (messages)   │
         │   - message_id (UUID)        │
         │   - conversation_id          │
         │   - sender (user/bot)        │
         │   - message_text             │
         │   - timestamp                │
         └──────────────┬───────────────┘
                        │
                        ▼
         ┌─────────────────────────────┐
         │  Generate embedding vector   │
         │  (SentenceTransformer)       │
         └──────────────┬───────────────┘
                        │
                        ▼
         ┌─────────────────────────────┐
         │   Store in ChromaDB          │
         │   - id: message_id           │
         │   - embedding: [vector]      │
         │   - metadata:                │
         │     * conversation_id        │
         │     * sender                 │
         │     * message_id             │
         └──────────────┬───────────────┘
                        │
                        ▼
         ┌─────────────────────────────┐
         │  Update MySQL with           │
         │  embedding_id = message_id   │
         └─────────────────────────────┘
```

### RAG Retrieval Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    User asks question                        │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
         ┌─────────────────────────────┐
         │  Convert query to embedding  │
         └──────────────┬───────────────┘
                        │
                        ▼
         ┌─────────────────────────────┐
         │  Search ChromaDB             │
         │  - Find similar embeddings   │
         │  - Filter by conversation_id │
         │  - Get top K results         │
         └──────────────┬───────────────┘
                        │
                        ▼
         ┌─────────────────────────────┐
         │  Extract embedding_ids       │
         │  (which are message_ids)     │
         └──────────────┬───────────────┘
                        │
                        ▼
         ┌─────────────────────────────┐
         │  Fetch full messages from    │
         │  MySQL using message_ids     │
         └──────────────┬───────────────┘
                        │
                        ▼
         ┌─────────────────────────────┐
         │  Return messages with        │
         │  full context + metadata     │
         └─────────────────────────────┘
```

## Database Schema

### MySQL Tables

#### users
```sql
CREATE TABLE users (
    user_id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    country VARCHAR(100),
    language VARCHAR(50) DEFAULT 'en',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP NULL
);
```

#### conversations
```sql
CREATE TABLE conversations (
    conversation_id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL,
    title VARCHAR(255) DEFAULT 'New Conversation',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);
```

#### messages
```sql
CREATE TABLE messages (
    message_id VARCHAR(36) PRIMARY KEY,
    conversation_id VARCHAR(36) NOT NULL,
    sender ENUM('user', 'bot') NOT NULL,
    message_text TEXT NOT NULL,
    embedding_id VARCHAR(36),  -- Links to ChromaDB
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (conversation_id) REFERENCES conversations(conversation_id),
    INDEX idx_conversation (conversation_id),
    INDEX idx_embedding (embedding_id)
);
```

### ChromaDB Collection

**Collection Name:** `chat_messages`

**Document Structure:**
```python
{
    "id": "message_id",  # Same as MySQL message_id
    "embedding": [0.123, -0.456, ...],  # 384-dim vector
    "document": "message text",
    "metadata": {
        "conversation_id": "uuid",
        "sender": "user" | "bot",
        "message_id": "uuid"  # Same as id
    }
}
```

## Implementation

### RAGIntegration Class

Located in `engine/database/rag_integration.py`

#### Key Methods

**1. save_user_message(conversation_id, message_text)**
```python
# Saves user message to both MySQL and ChromaDB
message_id = rag.save_user_message(
    conversation_id="abc-123",
    message_text="What is MyKasih?"
)
```

**Flow:**
1. Save to MySQL → get message_id
2. Generate embedding vector
3. Store in ChromaDB with message_id as ID
4. Update MySQL with embedding_id

**2. save_bot_message(conversation_id, message_text)**
```python
# Saves bot response to MySQL (optionally ChromaDB)
message_id = rag.save_bot_message(
    conversation_id="abc-123",
    message_text="MyKasih is a government assistance program..."
)
```

**3. retrieve_context(query, conversation_id, top_k=5)**
```python
# Retrieves relevant messages using semantic search
messages = rag.retrieve_context(
    query="Tell me about MyKasih",
    conversation_id="abc-123",
    top_k=5
)
```

**Returns:**
```python
[
    {
        "message_id": "uuid",
        "conversation_id": "uuid",
        "sender": "user",
        "message_text": "What is MyKasih?",
        "created_at": "2024-01-15 10:30:00",
        "similarity_score": 0.95
    },
    ...
]
```

**4. get_conversation_history(conversation_id)**
```python
# Gets full conversation history in chronological order
messages = rag.get_conversation_history("abc-123")
```

**5. create_conversation(user_id, title)**
```python
# Creates new conversation
conversation_id = rag.create_conversation(
    user_id="user-uuid",
    title="Chat - 2024-01-15 10:30"
)
```

### Integration in Flet App

Located in `app/views/home.py`

#### Initialization

```python
# Import RAG integration
from engine.database.rag_integration import RAGIntegration
rag = RAGIntegration()

# Create/get conversation when entering home view
if not state.conversation_id:
    state.conversation_id = rag.create_conversation(
        user_id=state.user_id,
        title=f"Chat - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    )
```

#### Saving Messages

**User Message:**
```python
# When user sends message
if RAG_AVAILABLE and rag and state.conversation_id:
    rag.save_user_message(state.conversation_id, msg)
```

**Bot Response:**
```python
# When bot responds
if RAG_AVAILABLE and rag and state.conversation_id:
    # Format response with sources
    full_response = answer
    if sources:
        full_response += "\n\nReferences:\n" + "\n".join(
            f"{i+1}. {s}" for i, s in enumerate(sources)
        )
    rag.save_bot_message(state.conversation_id, full_response)
```

## Data Flow Example

### User Asks Question

1. **User types:** "What is MyKasih?"

2. **Save to MySQL:**
   ```sql
   INSERT INTO messages VALUES (
       'msg-001',
       'conv-123',
       'user',
       'What is MyKasih?',
       NULL,
       NOW()
   );
   ```

3. **Generate Embedding:**
   ```python
   embedding = model.encode("What is MyKasih?")
   # Returns: [0.123, -0.456, 0.789, ...]
   ```

4. **Store in ChromaDB:**
   ```python
   collection.add(
       ids=['msg-001'],
       embeddings=[[0.123, -0.456, ...]],
       documents=['What is MyKasih?'],
       metadatas=[{
           'conversation_id': 'conv-123',
           'sender': 'user',
           'message_id': 'msg-001'
       }]
   )
   ```

5. **Update MySQL:**
   ```sql
   UPDATE messages 
   SET embedding_id = 'msg-001' 
   WHERE message_id = 'msg-001';
   ```

### Bot Responds

1. **Bot generates answer:**
   ```
   MyKasih is a government assistance program...
   
   References:
   1. https://www.mykasih.gov.my/about
   2. https://www.malaysia.gov.my/portal/content/30123
   ```

2. **Save to MySQL:**
   ```sql
   INSERT INTO messages VALUES (
       'msg-002',
       'conv-123',
       'bot',
       'MyKasih is a government assistance program...\n\nReferences:\n1. ...',
       NULL,
       NOW()
   );
   ```

### Later: Semantic Search

1. **User asks:** "Tell me more about the assistance program"

2. **Convert to embedding:**
   ```python
   query_embedding = model.encode("Tell me more about the assistance program")
   ```

3. **Search ChromaDB:**
   ```python
   results = collection.query(
       query_embeddings=[query_embedding],
       n_results=5,
       where={'conversation_id': 'conv-123'}
   )
   # Returns: ['msg-001', 'msg-002', ...]
   ```

4. **Fetch from MySQL:**
   ```sql
   SELECT * FROM messages 
   WHERE embedding_id IN ('msg-001', 'msg-002', ...)
   ORDER BY created_at DESC;
   ```

5. **Use as context for response:**
   ```python
   context = "\n".join([msg['message_text'] for msg in messages])
   # Feed to LLM for contextual response
   ```

## Benefits

### 1. Full Conversation History
- All messages stored permanently in MySQL
- Can retrieve entire conversation anytime
- Supports conversation management (list, search, delete)

### 2. Semantic Search
- Find relevant past messages by meaning, not keywords
- "What is MyKasih?" matches "Tell me about the assistance program"
- Improves context for AI responses

### 3. Scalability
- MySQL handles structured queries efficiently
- ChromaDB optimized for vector similarity search
- Each system does what it's best at

### 4. Data Integrity
- message_id links MySQL ↔ ChromaDB
- Consistent IDs make debugging easy
- Can verify data consistency

### 5. Privacy & Control
- User data stored locally (not in cloud)
- Can delete conversations completely
- Full control over data retention

## Configuration

### Environment Variables

```env
# MySQL Configuration
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your_password
MYSQL_DATABASE=ai_chatbot

# ChromaDB Path (local storage)
CHROMA_DB_PATH=./chroma_db
```

### Embedding Model

**Model:** `all-MiniLM-L6-v2` (SentenceTransformers)
- **Dimensions:** 384
- **Speed:** Fast (~1ms per sentence)
- **Quality:** Good for semantic similarity
- **Size:** ~80MB

Can be changed in `rag_integration.py`:
```python
self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
```

## Testing

### Verify Message Storage

```python
from engine.database.rag_integration import RAGIntegration

rag = RAGIntegration()

# Create conversation
conv_id = rag.create_conversation("user-123", "Test Chat")

# Save messages
rag.save_user_message(conv_id, "Hello, how are you?")
rag.save_bot_message(conv_id, "I'm doing well, thank you!")

# Retrieve history
messages = rag.get_conversation_history(conv_id)
print(f"Found {len(messages)} messages")

# Test semantic search
results = rag.retrieve_context("greeting", conv_id, top_k=3)
print(f"Found {len(results)} relevant messages")
```

### Check Database

**MySQL:**
```sql
-- Check messages
SELECT * FROM messages ORDER BY created_at DESC LIMIT 10;

-- Check conversations
SELECT * FROM conversations ORDER BY created_at DESC LIMIT 10;

-- Verify linking
SELECT m.message_id, m.embedding_id, m.message_text 
FROM messages m 
WHERE m.embedding_id IS NOT NULL;
```

**ChromaDB:**
```python
import chromadb

client = chromadb.PersistentClient(path="./chroma_db")
collection = client.get_collection("chat_messages")

# Check count
print(f"Total embeddings: {collection.count()}")

# Peek at data
print(collection.peek())
```

## Troubleshooting

### Messages not saving

**Check:**
1. MySQL connection: `✅ Connected to MySQL database`
2. RAG initialization: `✅ Embedding model loaded`
3. Conversation ID: `state.conversation_id` not empty
4. Error logs in terminal

### Semantic search not working

**Check:**
1. Embeddings stored: `SELECT COUNT(*) FROM messages WHERE embedding_id IS NOT NULL`
2. ChromaDB collection exists: `collection.count() > 0`
3. Query returns results: Check terminal for "Found X relevant messages"

### Slow performance

**Optimize:**
1. Add MySQL indexes on frequently queried columns
2. Use smaller embedding model if needed
3. Limit `top_k` in semantic search
4. Cache recent conversations in memory

## Future Enhancements

1. **Conversation Summarization**
   - Auto-generate conversation titles
   - Summarize long conversations

2. **Multi-turn Context**
   - Use RAG to maintain context across turns
   - Reference previous messages automatically

3. **Conversation Search**
   - Search across all conversations
   - Filter by date, topic, etc.

4. **Export/Import**
   - Export conversations to JSON/PDF
   - Import conversation history

5. **Analytics**
   - Track most asked questions
   - Identify common topics
   - User engagement metrics

## Summary

All chat messages are now stored in both MySQL (structured data) and ChromaDB (vector embeddings), enabling:
- Full conversation history
- Semantic search capabilities
- Context-aware responses
- Data persistence across sessions
- Future RAG enhancements

The system is production-ready and handles message storage automatically whenever users interact with the chatbot.
