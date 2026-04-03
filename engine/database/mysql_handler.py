"""
MySQL Database Handler for AI Chatbot
Manages users, conversations, and messages
"""
import mysql.connector
from mysql.connector import Error
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
import os
from dotenv import load_dotenv

load_dotenv()


class MySQLHandler:
    def __init__(self):
        """Initialize MySQL connection"""
        self.connection = None
        self.connect()
    
    def connect(self):
        """Establish connection to MySQL database"""
        try:
            port = os.getenv('MYSQL_PORT', '3306')
            port = int(port) if port and port.strip() else 3306
            
            self.connection = mysql.connector.connect(
                host=os.getenv('MYSQL_HOST', 'localhost'),
                port=port,
                user=os.getenv('MYSQL_USER', 'root'),
                password=os.getenv('MYSQL_PASSWORD', ''),
                database=os.getenv('MYSQL_DATABASE', 'ai_chatbot')
            )
            if self.connection.is_connected():
                print("✅ Connected to MySQL database")
        except Error as e:
            print(f"❌ Error connecting to MySQL: {e}")
            raise
    
    def ensure_connection(self):
        """Ensure connection is alive, reconnect if needed"""
        try:
            if not self.connection.is_connected():
                self.connect()
        except:
            self.connect()
    
    # ─── User Management ─────────────────────────────────────────────────
    
    def create_user(self, name: str, email: str, password_hash: str, 
                   country: str = None, language: str = 'en') -> Optional[str]:
        """Create a new user and return user_id"""
        self.ensure_connection()
        cursor = self.connection.cursor()
        user_id = str(uuid.uuid4())
        
        try:
            query = """
                INSERT INTO users (user_id, name, email, password_hash, country, language)
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            cursor.execute(query, (user_id, name, email, password_hash, country, language))
            self.connection.commit()
            print(f"✅ User created: {email}")
            return user_id
        except Error as e:
            print(f"❌ Error creating user: {e}")
            return None
        finally:
            cursor.close()
    
    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get user by email"""
        self.ensure_connection()
        cursor = self.connection.cursor(dictionary=True)
        
        try:
            query = "SELECT * FROM users WHERE email = %s"
            cursor.execute(query, (email,))
            return cursor.fetchone()
        except Error as e:
            print(f"❌ Error fetching user: {e}")
            return None
        finally:
            cursor.close()
    
    def update_last_login(self, user_id: str):
        """Update user's last login timestamp"""
        self.ensure_connection()
        cursor = self.connection.cursor()
        
        try:
            query = "UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE user_id = %s"
            cursor.execute(query, (user_id,))
            self.connection.commit()
        except Error as e:
            print(f"❌ Error updating last login: {e}")
        finally:
            cursor.close()
    
    # ─── Conversation Management ─────────────────────────────────────────
    
    def create_conversation(self, user_id: str, title: str = "New Conversation") -> Optional[str]:
        """Create a new conversation and return conversation_id"""
        self.ensure_connection()
        cursor = self.connection.cursor()
        conversation_id = str(uuid.uuid4())
        
        try:
            query = """
                INSERT INTO conversations (conversation_id, user_id, title)
                VALUES (%s, %s, %s)
            """
            cursor.execute(query, (conversation_id, user_id, title))
            self.connection.commit()
            print(f"✅ Conversation created: {conversation_id}")
            return conversation_id
        except Error as e:
            print(f"❌ Error creating conversation: {e}")
            return None
        finally:
            cursor.close()
    
    def get_user_conversations(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all conversations for a user"""
        self.ensure_connection()
        cursor = self.connection.cursor(dictionary=True)
        
        try:
            query = """
                SELECT * FROM conversations 
                WHERE user_id = %s 
                ORDER BY created_at DESC
            """
            cursor.execute(query, (user_id,))
            return cursor.fetchall()
        except Error as e:
            print(f"❌ Error fetching conversations: {e}")
            return []
        finally:
            cursor.close()
    
    # ─── Message Management ──────────────────────────────────────────────
    
    def save_message(self, conversation_id: str, sender: str, 
                    message_text: str, embedding_id: str = None) -> Optional[str]:
        """
        Save a message to MySQL
        Returns message_id
        """
        self.ensure_connection()
        cursor = self.connection.cursor()
        message_id = str(uuid.uuid4())
        
        try:
            query = """
                INSERT INTO messages (message_id, conversation_id, sender, message_text, embedding_id)
                VALUES (%s, %s, %s, %s, %s)
            """
            cursor.execute(query, (message_id, conversation_id, sender, message_text, embedding_id))
            self.connection.commit()
            print(f"✅ Message saved: {message_id}")
            return message_id
        except Error as e:
            print(f"❌ Error saving message: {e}")
            return None
        finally:
            cursor.close()
    
    def update_message_embedding(self, message_id: str, embedding_id: str):
        """Update message with embedding_id after ChromaDB storage"""
        self.ensure_connection()
        cursor = self.connection.cursor()
        
        try:
            query = "UPDATE messages SET embedding_id = %s WHERE message_id = %s"
            cursor.execute(query, (embedding_id, message_id))
            self.connection.commit()
            print(f"✅ Embedding ID updated for message: {message_id}")
        except Error as e:
            print(f"❌ Error updating embedding: {e}")
        finally:
            cursor.close()
    
    def get_conversation_messages(self, conversation_id: str) -> List[Dict[str, Any]]:
        """Get all messages in a conversation"""
        self.ensure_connection()
        cursor = self.connection.cursor(dictionary=True)
        
        try:
            query = """
                SELECT * FROM messages 
                WHERE conversation_id = %s 
                ORDER BY created_at ASC
            """
            cursor.execute(query, (conversation_id,))
            return cursor.fetchall()
        except Error as e:
            print(f"❌ Error fetching messages: {e}")
            return []
        finally:
            cursor.close()
    
    def get_messages_by_embedding_ids(self, embedding_ids: List[str]) -> List[Dict[str, Any]]:
        """
        Get messages by their embedding IDs (for RAG retrieval)
        Used after ChromaDB search to fetch actual message content
        """
        self.ensure_connection()
        cursor = self.connection.cursor(dictionary=True)
        
        try:
            if not embedding_ids:
                return []
            
            placeholders = ','.join(['%s'] * len(embedding_ids))
            query = f"""
                SELECT * FROM messages 
                WHERE embedding_id IN ({placeholders})
                ORDER BY created_at DESC
            """
            cursor.execute(query, tuple(embedding_ids))
            return cursor.fetchall()
        except Error as e:
            print(f"❌ Error fetching messages by embedding IDs: {e}")
            return []
        finally:
            cursor.close()
    
    def close(self):
        """Close database connection"""
        if self.connection and self.connection.is_connected():
            self.connection.close()
            print("✅ MySQL connection closed")
