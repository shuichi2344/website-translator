"""
ChromaDB Configuration and Management Utilities
Provides configuration, maintenance, and monitoring tools for the vector database
"""

import chromadb
from chromadb.config import Settings
import os
from pathlib import Path
from datetime import datetime
import json


class ChromaDBConfig:
    """ChromaDB configuration and management"""
    
    # Default configuration
    DEFAULT_DB_PATH = "./chroma_db"
    DEFAULT_COLLECTION_NAME = "document_chunks"
    DEFAULT_EMBEDDING_DIM = 768
    
    # Performance settings
    BATCH_SIZE = 100  # Batch size for bulk operations
    MAX_CACHE_SIZE = 1000  # Maximum number of embeddings to cache in memory
    
    # Maintenance settings
    AUTO_CLEANUP_DAYS = 30  # Auto-delete embeddings older than 30 days
    MAX_DB_SIZE_GB = 10  # Maximum database size in GB
    
    def __init__(self, db_path=None, collection_name=None):
        """Initialize ChromaDB configuration"""
        self.db_path = db_path or self.DEFAULT_DB_PATH
        self.collection_name = collection_name or self.DEFAULT_COLLECTION_NAME
        self.client = None
        self.collection = None
    
    def get_client(self):
        """Get or create ChromaDB client"""
        if self.client is None:
            self.client = chromadb.PersistentClient(
                path=self.db_path,
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=True,
                    is_persistent=True
                )
            )
        return self.client
    
    def get_collection(self):
        """Get or create collection"""
        if self.collection is None:
            client = self.get_client()
            self.collection = client.get_or_create_collection(
                name=self.collection_name,
                metadata={
                    "description": "Document chunks with EmbeddingGemma embeddings",
                    "embedding_dimension": self.DEFAULT_EMBEDDING_DIM,
                    "created_at": datetime.now().isoformat()
                }
            )
        return self.collection
    
    def get_stats(self):
        """Get database statistics"""
        collection = self.get_collection()
        
        # Get collection count
        count = collection.count()
        
        # Get database size
        db_size = self._get_db_size()
        
        # Get unique documents
        unique_docs = self._count_unique_documents()
        
        return {
            "total_chunks": count,
            "unique_documents": unique_docs,
            "database_size_mb": db_size,
            "database_path": self.db_path,
            "collection_name": self.collection_name,
            "timestamp": datetime.now().isoformat()
        }
    
    def _get_db_size(self):
        """Calculate database size in MB"""
        total_size = 0
        db_path = Path(self.db_path)
        
        if db_path.exists():
            for file in db_path.rglob('*'):
                if file.is_file():
                    total_size += file.stat().st_size
        
        return round(total_size / (1024 * 1024), 2)  # Convert to MB
    
    def _count_unique_documents(self):
        """Count unique documents in collection"""
        try:
            collection = self.get_collection()
            results = collection.get(include=["metadatas"])
            
            if results and results['metadatas']:
                doc_ids = set(meta.get('doc_id') for meta in results['metadatas'] if meta.get('doc_id'))
                return len(doc_ids)
        except:
            pass
        
        return 0
    
    def clear_collection(self):
        """Clear all data from collection"""
        try:
            client = self.get_client()
            client.delete_collection(self.collection_name)
            print(f"✅ Collection '{self.collection_name}' cleared successfully")
            
            # Recreate collection
            self.collection = None
            self.get_collection()
            print(f"✅ Collection '{self.collection_name}' recreated")
            
            return True
        except Exception as e:
            print(f"❌ Error clearing collection: {e}")
            return False
    
    def delete_document(self, doc_id):
        """Delete all chunks for a specific document"""
        try:
            collection = self.get_collection()
            
            # Get all chunks for this document
            results = collection.get(
                where={"doc_id": doc_id},
                include=["metadatas"]
            )
            
            if results and results['ids']:
                # Delete all chunks
                collection.delete(ids=results['ids'])
                print(f"✅ Deleted {len(results['ids'])} chunks for doc_id: {doc_id[:8]}...")
                return True
            else:
                print(f"⚠️  No chunks found for doc_id: {doc_id[:8]}...")
                return False
                
        except Exception as e:
            print(f"❌ Error deleting document: {e}")
            return False
    
    def cleanup_old_embeddings(self, days=30):
        """Delete embeddings older than specified days"""
        try:
            collection = self.get_collection()
            cutoff_date = datetime.now().timestamp() - (days * 24 * 60 * 60)
            
            # Get all embeddings with metadata
            results = collection.get(include=["metadatas"])
            
            if not results or not results['metadatas']:
                print("⚠️  No embeddings to clean up")
                return 0
            
            # Find old embeddings
            old_ids = []
            for i, metadata in enumerate(results['metadatas']):
                created_at = metadata.get('created_at', 0)
                if created_at and created_at < cutoff_date:
                    old_ids.append(results['ids'][i])
            
            if old_ids:
                collection.delete(ids=old_ids)
                print(f"✅ Deleted {len(old_ids)} old embeddings (older than {days} days)")
                return len(old_ids)
            else:
                print(f"✅ No embeddings older than {days} days found")
                return 0
                
        except Exception as e:
            print(f"❌ Error cleaning up old embeddings: {e}")
            return 0
    
    def export_metadata(self, output_file="chroma_metadata.json"):
        """Export collection metadata to JSON file"""
        try:
            collection = self.get_collection()
            results = collection.get(include=["metadatas"])
            
            if not results or not results['metadatas']:
                print("⚠️  No metadata to export")
                return False
            
            # Group by document
            documents = {}
            for i, metadata in enumerate(results['metadatas']):
                doc_id = metadata.get('doc_id', 'unknown')
                if doc_id not in documents:
                    documents[doc_id] = {
                        'doc_id': doc_id,
                        'chunk_count': 0,
                        'chunks': []
                    }
                
                documents[doc_id]['chunk_count'] += 1
                documents[doc_id]['chunks'].append({
                    'chunk_id': results['ids'][i],
                    'chunk_index': metadata.get('chunk_index', -1)
                })
            
            # Export to JSON
            export_data = {
                'exported_at': datetime.now().isoformat(),
                'total_documents': len(documents),
                'total_chunks': len(results['ids']),
                'documents': list(documents.values())
            }
            
            with open(output_file, 'w') as f:
                json.dump(export_data, f, indent=2)
            
            print(f"✅ Metadata exported to {output_file}")
            print(f"   • Documents: {len(documents)}")
            print(f"   • Total chunks: {len(results['ids'])}")
            
            return True
            
        except Exception as e:
            print(f"❌ Error exporting metadata: {e}")
            return False
    
    def optimize_database(self):
        """Optimize database performance"""
        try:
            # Get stats before optimization
            stats_before = self.get_stats()
            
            print("🔧 Optimizing ChromaDB...")
            print(f"   Before: {stats_before['total_chunks']} chunks, {stats_before['database_size_mb']} MB")
            
            # Cleanup old embeddings
            deleted = self.cleanup_old_embeddings(self.AUTO_CLEANUP_DAYS)
            
            # Get stats after optimization
            stats_after = self.get_stats()
            
            print(f"   After: {stats_after['total_chunks']} chunks, {stats_after['database_size_mb']} MB")
            print(f"✅ Optimization complete - freed {stats_before['database_size_mb'] - stats_after['database_size_mb']:.2f} MB")
            
            return True
            
        except Exception as e:
            print(f"❌ Error optimizing database: {e}")
            return False
    
    def backup_database(self, backup_path=None):
        """Create backup of ChromaDB"""
        import shutil
        
        try:
            if backup_path is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_path = f"./chroma_db_backup_{timestamp}"
            
            print(f"💾 Creating backup...")
            shutil.copytree(self.db_path, backup_path)
            
            backup_size = self._get_backup_size(backup_path)
            print(f"✅ Backup created: {backup_path}")
            print(f"   Size: {backup_size} MB")
            
            return backup_path
            
        except Exception as e:
            print(f"❌ Error creating backup: {e}")
            return None
    
    def _get_backup_size(self, path):
        """Calculate backup size in MB"""
        total_size = 0
        backup_path = Path(path)
        
        if backup_path.exists():
            for file in backup_path.rglob('*'):
                if file.is_file():
                    total_size += file.stat().st_size
        
        return round(total_size / (1024 * 1024), 2)
    
    def list_documents(self):
        """List all documents in the database"""
        try:
            collection = self.get_collection()
            results = collection.get(include=["metadatas"])
            
            if not results or not results['metadatas']:
                print("⚠️  No documents in database")
                return []
            
            # Group by document
            documents = {}
            for metadata in results['metadatas']:
                doc_id = metadata.get('doc_id', 'unknown')
                if doc_id not in documents:
                    documents[doc_id] = {
                        'doc_id': doc_id,
                        'doc_id_short': doc_id[:8] + '...',
                        'chunk_count': 0
                    }
                documents[doc_id]['chunk_count'] += 1
            
            doc_list = list(documents.values())
            
            print(f"\n📚 Documents in database: {len(doc_list)}")
            print("=" * 60)
            for doc in doc_list:
                print(f"  • {doc['doc_id_short']} - {doc['chunk_count']} chunks")
            print("=" * 60)
            
            return doc_list
            
        except Exception as e:
            print(f"❌ Error listing documents: {e}")
            return []


def main():
    """CLI interface for ChromaDB management"""
    import sys
    
    config = ChromaDBConfig()
    
    if len(sys.argv) < 2:
        print("ChromaDB Management Tool")
        print("=" * 60)
        print("Usage: python chroma_config.py <command>")
        print("\nCommands:")
        print("  stats          - Show database statistics")
        print("  list           - List all documents")
        print("  clear          - Clear all data")
        print("  delete <id>    - Delete specific document")
        print("  cleanup        - Remove old embeddings (30+ days)")
        print("  optimize       - Optimize database")
        print("  backup         - Create database backup")
        print("  export         - Export metadata to JSON")
        print("\nExamples:")
        print("  python chroma_config.py stats")
        print("  python chroma_config.py delete 5d41402a")
        print("  python chroma_config.py backup")
        return
    
    command = sys.argv[1].lower()
    
    if command == "stats":
        stats = config.get_stats()
        print("\n📊 ChromaDB Statistics")
        print("=" * 60)
        for key, value in stats.items():
            print(f"  {key}: {value}")
        print("=" * 60)
    
    elif command == "list":
        config.list_documents()
    
    elif command == "clear":
        confirm = input("⚠️  Are you sure you want to clear ALL data? (yes/no): ")
        if confirm.lower() == "yes":
            config.clear_collection()
        else:
            print("❌ Operation cancelled")
    
    elif command == "delete":
        if len(sys.argv) < 3:
            print("❌ Usage: python chroma_config.py delete <doc_id>")
            return
        doc_id = sys.argv[2]
        config.delete_document(doc_id)
    
    elif command == "cleanup":
        config.cleanup_old_embeddings()
    
    elif command == "optimize":
        config.optimize_database()
    
    elif command == "backup":
        config.backup_database()
    
    elif command == "export":
        config.export_metadata()
    
    else:
        print(f"❌ Unknown command: {command}")
        print("Run 'python chroma_config.py' for help")


if __name__ == "__main__":
    main()
