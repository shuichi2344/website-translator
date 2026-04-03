# MySQL + ChromaDB RAG Integration Setup Guide

## Overview
This system combines MySQL (for structured data) with ChromaDB (for semantic search) to create a powerful RAG (Retrieval-Augmented Generation) chatbot.

## Architecture

```
User Message Flow:
┌─────────────┐
│ User sends  │
│  message    │
└──────┬──────┘
       │
       ├──────────────────────────────────────┐
       │                                      │
       ▼                                      ▼
┌─────────────┐                      ┌──────────────┐
│   MySQL     │                      │  ChromaDB    │
│  messages   │                      │  embeddings  │
│             │                      │              │
│ - message_id│◄─────────────────────┤ - embedding  │
│ - text      │  embedding_id        │ - metadata   │
│ - sender    │                      │              │
└─────────────┘                      └──────────────┘

RAG Retrieval Flow:
┌─────────────┐
│ User query  │
└──────┬──────┘
       │
       ▼
┌──────────────┐
│  Generate    │
│  embedding   │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│  ChromaDB    │
│  Search      │
│  (semantic)  │
└──────┬───────┘
       │
       ▼ (embedding_ids)
┌──────────────┐
│   MySQL      │
│  Fetch full  │
│  messages    │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│  Context for │
│  LLM         │
└──────────────┘
```

## Step 1: Setup MySQL Database

### 1.1 Install MySQL
- Download from: https://dev.mysql.com/downloads/mysql/
- Or use XAMPP/WAMP which includes MySQL

### 1.2 Create Database
Run the SQL script you provided:

```sql
CREATE DATABASE ai_chatbot;
USE ai_chatbot;

CREATE TABLE users (
    user_id CHAR(36) PRIMARY KEY,
    name VARCHAR(50),
    email VARCHAR(100) UNIQUE,
    password_hash VARCHAR(255),
    country VARCHAR(50),
    language VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    last_login TIMESTAMP NULL DEFAULT NULL,
    is_active BOOLEAN DEFAULT TRUE
);

CREATE TABLE conversations (
    conversation_id CHAR(36) PRIMARY KEY,
    user_id CHAR(36),
    title VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

CREATE TABLE messages (
    message_id CHAR(36) PRIMARY KEY,
    conversation_id CHAR(36),
    sender ENUM('user', 'bot'),
    message_text TEXT,
    embedding_id VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (conversation_id) REFERENCES conversations(conversation_id) ON DELETE CASCADE
);

CREATE INDEX idx_user_id ON conversations(user_id);
CREATE INDEX idx_conversation_id ON messages(conversation_id);
CREATE INDEX idx_embedding_id ON messages(embedding_id);
```

## Step 2: Configure Environment Variables

Edit `.env` file:

```env
# MySQL Database Configuration
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your_actual_password
MYSQL_DATABASE=ai_chatbot
```

## Step 3: Install Dependencies

```bash
# Activate virtual environment
.venv\Scripts\activate

# Install MySQL connector and bcrypt
pip install mysql-connector-python bcrypt

# Or install all requirements
pip install -r requirements.txt
```

## Step 4: Test the Integration

### Test Authentication
```bash
python engine/database/auth_example.py
```

This will demonstrate:
1. User registration with password hashing
2. User login with authentication
3. Profile management
4. Complete chat flow with RAG

### Test RAG Only
```bash
python engine/database/example_usage.py
```

## Usage in Your Application

### Complete Flow with Authentication

```python
from engine.database.auth_handler import AuthHandler
from engine.database.rag_integration import RAGIntegration

auth = AuthHandler()
rag = RAGIntegration()

# 1. Register new user
registration = auth.register_user(
    name="John Doe",
    email="john@example.com",
    password="SecurePass123!",
    country="Malaysia",
    language="en"
)

if registration['success']:
    user_id = registration['user_id']
    print(f"User registered: {user_id}")

# 2. Login user
login = auth.login_user(
    email="john@example.com",
    password="SecurePass123!"
)

if login['success']:
    user_id = login['user_id']
    user_data = login['user_data']
    print(f"Welcome {user_data['name']}!")
    
    # 3. Create conversation
    conversation_id = rag.create_conversation(
        user_id=user_id,
        title="Government Services Help"
    )
    
    # 4. Save user message with RAG
    message_id = rag.save_user_message(
        conversation_id=conversation_id,
        message_text="How do I renew my passport?"
    )
    
    # 5. Get context for response
    context = rag.get_context_for_response(
        query="passport renewal process",
        conversation_id=conversation_id
    )
    
    # 6. Generate and save bot response
    # response = your_llm.generate(context['context_text'])
    rag.save_bot_message(conversation_id, response)
```

### Basic Usage

```python
from engine.database.rag_integration import RAGIntegration

# Initialize
rag = RAGIntegration(chroma_path="./chroma_db")

# Create conversation
conversation_id = rag.create_conversation(
    user_id="user-123",
    title="Help with Services"
)

# Save user message (auto-generates embedding)
message_id = rag.save_user_message(
    conversation_id=conversation_id,
    message_text="How do I renew my passport?"
)

# Get context for generating response
context = rag.get_context_for_response(
    query="passport renewal process",
    conversation_id=conversation_id
)

# Use context with your LLM
# response = your_llm.generate(context['context_text'])

# Save bot response
rag.save_bot_message(conversation_id, response)
```

### Integration with Flask Backend

```python
from flask import Flask, request, jsonify
from engine.database.rag_integration import RAGIntegration

app = Flask(__name__)
rag = RAGIntegration()

@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    user_id = data['user_id']
    conversation_id = data.get('conversation_id')
    message = data['message']
    
    # Create conversation if new
    if not conversation_id:
        conversation_id = rag.create_conversation(user_id)
    
    # Save user message
    rag.save_user_message(conversation_id, message)
    
    # Get context using RAG
    context = rag.get_context_for_response(message, conversation_id)
    
    # Generate response (integrate with your LLM)
    # bot_response = generate_with_llm(context['context_text'], message)
    bot_response = "Your AI response here"
    
    # Save bot response
    rag.save_bot_message(conversation_id, bot_response)
    
    return jsonify({
        'conversation_id': conversation_id,
        'response': bot_response,
        'context_used': len(context['relevant_messages'])
    })
```

## Key Features

### 1. Automatic Embedding Generation
- User messages are automatically embedded using SentenceTransformer
- Embeddings stored in ChromaDB with message_id as key
- MySQL updated with embedding_id for linking

### 2. Semantic Search
- Query converted to embedding
- ChromaDB finds similar messages
- Returns top-k most relevant results

### 3. Context Retrieval
- Combines RAG search results with recent conversation history
- Provides formatted context string for LLM
- Includes similarity scores

### 4. Conversation Management
- Full conversation history in MySQL
- Organized by user and conversation
- Timestamps for all messages

## Database Schema Explained

### users table
Stores complete user information:
- **user_id**: Unique identifier (UUID)
- **name**: User's full name
- **email**: Unique email address (for login)
- **password_hash**: Bcrypt hashed password (NEVER stores plain text)
- **country**: User's country
- **language**: Preferred language (en, ms, zh-cn, etc.)
- **created_at**: Account creation timestamp
- **updated_at**: Last profile update timestamp
- **last_login**: Last successful login timestamp
- **is_active**: Account status (can be deactivated)

**Security Features:**
- Passwords are hashed using bcrypt (industry standard)
- Email is unique (prevents duplicate accounts)
- Password hash is never returned in API responses
- Supports account deactivation

### conversations table
- Groups messages into conversations
- Each user can have multiple conversations
- Has title and timestamps

### messages table
- Stores actual message content
- `sender`: 'user' or 'bot'
- `embedding_id`: Links to ChromaDB (same as message_id)
- Indexed for fast retrieval

## ChromaDB Collection

Collection name: `chat_messages`

Each document contains:
- `id`: message_id (same as MySQL)
- `embedding`: Vector representation
- `document`: Original message text
- `metadata`: conversation_id, sender, message_id

## Performance Tips

1. **Index Optimization**
   - Already indexed: user_id, conversation_id, embedding_id
   - Add more indexes if needed for your queries

2. **Batch Operations**
   - For bulk imports, use batch inserts
   - ChromaDB supports batch add operations

3. **Connection Pooling**
   - For production, use connection pooling
   - Example: `mysql.connector.pooling.MySQLConnectionPool`

4. **Embedding Model**
   - Current: `all-MiniLM-L6-v2` (fast, good quality)
   - Upgrade to larger models for better accuracy
   - Options: `all-mpnet-base-v2`, multilingual models

## Troubleshooting

### Connection Error
```
Error connecting to MySQL: Access denied
```
**Solution**: Check MYSQL_USER and MYSQL_PASSWORD in .env

### Embedding Error
```
Error storing embedding
```
**Solution**: Ensure ChromaDB path is writable, check disk space

### No Results from RAG
```
No relevant context found
```
**Solution**: 
- Check if messages are being embedded
- Verify ChromaDB collection has documents
- Try increasing top_k parameter

## Next Steps

1. **Add Authentication**
   - Implement user login/signup
   - Hash passwords properly (use bcrypt)

2. **Integrate with LLM**
   - Connect to Gemini/OpenAI/Ollama
   - Pass context to LLM for response generation

3. **Add to Flask Backend**
   - Create `/chat` endpoint
   - Handle conversation management
   - Return AI responses

4. **Connect to Browser Extension**
   - Update background.js to call new endpoint
   - Pass conversation_id for context

## Support

For issues or questions:
1. Check MySQL connection with: `mysql -u root -p`
2. Verify ChromaDB with: `ls -la chroma_db/`
3. Test with: `python engine/database/example_usage.py`
