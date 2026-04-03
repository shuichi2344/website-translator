"""
RAG Integration: MySQL + ChromaDB
Combines MySQL for message storage with ChromaDB for semantic search
"""
from typing import List, Dict, Any, Optional
import uuid
from sentence_transformers import SentenceTransformer

from engine.database.mysql_handler import MySQLHandler
from engine.database.chroma_singleton import get_chroma_client, get_chroma_collection


class RAGIntegration:
    _instance = None
    _initialized = False
    
    def __new__(cls, chroma_path: str = "./chroma_db"):
        """Singleton pattern to prevent multiple ChromaDB instances"""
        if cls._instance is None:
            cls._instance = super(RAGIntegration, cls).__new__(cls)
        return cls._instance
    
    def __init__(self, chroma_path: str = "./chroma_db"):
        """Initialize RAG system with MySQL and ChromaDB (only once)"""
        # Skip if already initialized
        if self._initialized:
            return
        
        # MySQL handler
        self.mysql = MySQLHandler()
        
        # Use global ChromaDB singleton
        self.chroma_client = get_chroma_client()
        
        # Get or create collection for chat messages
        self.collection = get_chroma_collection(
            name="chat_messages",
            metadata={"description": "Chat message embeddings for RAG"}
        )
        
        # Embedding model
        print("🔄 Loading embedding model...")
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        print("✅ Embedding model loaded")
        
        # Mark as initialized
        RAGIntegration._initialized = True
    
    # ─── Message Storage (MySQL + ChromaDB) ─────────────────────────────
    
    def save_user_message(self, conversation_id: str, message_text: str) -> Optional[str]:
        """
        Save user message to both MySQL and ChromaDB
        
        Flow:
        1. Save message to MySQL (get message_id)
        2. Generate embedding
        3. Store embedding in ChromaDB with message_id as ID
        4. Update MySQL with embedding_id
        
        Returns: message_id
        """
        # Step 1: Save to MySQL first
        message_id = self.mysql.save_message(
            conversation_id=conversation_id,
            sender='user',
            message_text=message_text,
            embedding_id=None  # Will update later
        )
        
        if not message_id:
            print("❌ Failed to save message to MySQL")
            return None
        
        # Step 2: Generate embedding
        embedding = self.embedding_model.encode(message_text).tolist()
        
        # Step 3: Store in ChromaDB (use message_id as embedding_id)
        try:
            self.collection.add(
                ids=[message_id],
                embeddings=[embedding],
                documents=[message_text],
                metadatas=[{
                    "conversation_id": conversation_id,
                    "sender": "user",
                    "message_id": message_id
                }]
            )
            print(f"✅ Embedding stored in ChromaDB: {message_id}")
        except Exception as e:
            print(f"❌ Error storing embedding: {e}")
            return message_id  # Still return message_id even if embedding fails
        
        # Step 4: Update MySQL with embedding_id
        self.mysql.update_message_embedding(message_id, message_id)
        
        return message_id
    
    def save_bot_message(self, conversation_id: str, message_text: str) -> Optional[str]:
        """
        Save bot message to MySQL (optionally to ChromaDB)
        Bot messages can be indexed for context but usually not needed
        """
        message_id = self.mysql.save_message(
            conversation_id=conversation_id,
            sender='bot',
            message_text=message_text,
            embedding_id=None
        )
        return message_id
    
    # ─── RAG Retrieval (ChromaDB → MySQL) ───────────────────────────────
    
    def retrieve_context(self, query: str, conversation_id: str = None, 
                        top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Retrieve relevant context using RAG
        
        Flow:
        1. Convert query to embedding
        2. Search ChromaDB for similar embeddings
        3. Get embedding_ids from results
        4. Fetch actual messages from MySQL using embedding_ids
        
        Returns: List of message dictionaries with full context
        """
        # Step 1: Generate query embedding
        query_embedding = self.embedding_model.encode(query).tolist()
        
        # Step 2: Search ChromaDB
        try:
            # Build where filter if conversation_id provided
            where_filter = {"conversation_id": conversation_id} if conversation_id else None
            
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                where=where_filter
            )
            
            if not results['ids'] or not results['ids'][0]:
                print("ℹ️ No relevant context found")
                return []
            
            # Step 3: Get embedding_ids (which are message_ids)
            embedding_ids = results['ids'][0]
            print(f"✅ Found {len(embedding_ids)} relevant messages")
            
        except Exception as e:
            print(f"❌ Error searching ChromaDB: {e}")
            return []
        
        # Step 4: Fetch full messages from MySQL
        messages = self.mysql.get_messages_by_embedding_ids(embedding_ids)
        
        # Add similarity scores to messages
        if results['distances'] and results['distances'][0]:
            for i, msg in enumerate(messages):
                if i < len(results['distances'][0]):
                    msg['similarity_score'] = 1 - results['distances'][0][i]  # Convert distance to similarity
        
        return messages
    
    # ─── Conversation Management ─────────────────────────────────────────
    
    def get_conversation_history(self, conversation_id: str) -> List[Dict[str, Any]]:
        """Get full conversation history from MySQL"""
        return self.mysql.get_conversation_messages(conversation_id)
    
    def create_conversation(self, user_id: str, title: str = "New Conversation") -> Optional[str]:
        """Create new conversation"""
        return self.mysql.create_conversation(user_id, title)
    
    # ─── RAG-Enhanced Response Generation ────────────────────────────────
    
    def get_context_for_response(self, query: str, conversation_id: str, 
                                 include_history: bool = True) -> Dict[str, Any]:
        """
        Get complete context for generating a response
        
        Returns:
        {
            'relevant_messages': [...],  # From RAG search
            'recent_history': [...],     # Last N messages
            'context_text': '...'        # Formatted context string
        }
        """
        context = {
            'relevant_messages': [],
            'recent_history': [],
            'context_text': ''
        }
        
        # Get relevant messages via RAG
        relevant = self.retrieve_context(query, conversation_id, top_k=5)
        context['relevant_messages'] = relevant
        
        # Get recent conversation history
        if include_history:
            all_messages = self.get_conversation_history(conversation_id)
            context['recent_history'] = all_messages[-10:]  # Last 10 messages
        
        # Format context text for LLM
        context_parts = []
        
        if relevant:
            context_parts.append("=== Relevant Context ===")
            for msg in relevant:
                sender = msg['sender'].upper()
                text = msg['message_text']
                context_parts.append(f"{sender}: {text}")
        
        if context['recent_history']:
            context_parts.append("\n=== Recent Conversation ===")
            for msg in context['recent_history']:
                sender = msg['sender'].upper()
                text = msg['message_text']
                context_parts.append(f"{sender}: {text}")
        
        context['context_text'] = '\n'.join(context_parts)
        
        return context
    
    def close(self):
        """Close all connections"""
        self.mysql.close()
