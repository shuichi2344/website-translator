"""
Global ChromaDB Singleton
Ensures only one ChromaDB client exists across the entire application
"""
import chromadb
from chromadb.config import Settings
from typing import Optional


class ChromaDBSingleton:
    """Global singleton for ChromaDB client"""
    _instance = None
    _client = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ChromaDBSingleton, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize ChromaDB client (only once)"""
        if self._initialized:
            return
        
        # Create client with consistent settings
        self._client = chromadb.PersistentClient(
            path="./chroma_db",
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True,
                is_persistent=True
            )
        )
        
        self._initialized = True
        print("✅ ChromaDB singleton initialized")
    
    def get_client(self):
        """Get the global ChromaDB client"""
        if not self._initialized:
            self.__init__()
        return self._client
    
    def get_or_create_collection(self, name: str, metadata: dict = None):
        """Get or create a collection"""
        client = self.get_client()
        return client.get_or_create_collection(
            name=name,
            metadata=metadata or {}
        )


# Global instance
_chroma_singleton = None


def get_chroma_client():
    """Get the global ChromaDB client"""
    global _chroma_singleton
    if _chroma_singleton is None:
        _chroma_singleton = ChromaDBSingleton()
    return _chroma_singleton.get_client()


def get_chroma_collection(name: str, metadata: dict = None):
    """Get or create a ChromaDB collection"""
    global _chroma_singleton
    if _chroma_singleton is None:
        _chroma_singleton = ChromaDBSingleton()
    return _chroma_singleton.get_or_create_collection(name, metadata)
