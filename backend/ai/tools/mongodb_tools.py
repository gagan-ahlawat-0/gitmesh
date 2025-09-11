"""DEPRECATED: MongoDB support has been removed from GitMesh.

GitMesh now uses Supabase PostgreSQL and Qdrant for all data storage needs:
- Supabase PostgreSQL: For structured data, metadata, and relational queries
- Qdrant: For vector embeddings and semantic search

Please migrate to the new storage system:
from ai.memory.memory import GitMeshMemory
from ai.knowledge.knowledge import Knowledge

Usage:
# For memory/chat storage
memory = GitMeshMemory()
memory.store("user123", "Remember this information")
results = memory.search("user123", "information")

# For knowledge/document storage  
knowledge = Knowledge()
knowledge.store("This is important knowledge")
results = knowledge.search("important")
"""

import logging
from typing import List, Dict, Any, Optional, Union
import warnings

class DeprecatedMongoDBTools:
    """Deprecated MongoDB tools - use GitMeshMemory and Knowledge instead."""
    
    def __init__(self, connection_string: str = "", database_name: str = "deprecated"):
        """Initialize deprecated MongoDB tools."""
        warnings.warn(
            "MongoDB support has been removed from GitMesh. "
            "Please use GitMeshMemory (Supabase) and Knowledge (Qdrant) instead.",
            DeprecationWarning,
            stacklevel=2
        )
        logging.error(
            "MongoDB tools are deprecated. Use GitMeshMemory and Knowledge instead."
        )

    def _deprecated_method(self, method_name: str) -> Dict[str, str]:
        """Return deprecation error for any method call."""
        error_msg = (
            f"MongoDB method '{method_name}' is deprecated and removed. "
            "Please use GitMeshMemory (Supabase) or Knowledge (Qdrant) instead."
        )
        logging.error(error_msg)
        return {"error": error_msg}

    def insert_document(self, collection_name: str, document: Dict[str, Any], metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Deprecated - use GitMeshMemory.store() or Knowledge.store() instead."""
        return self._deprecated_method("insert_document")

    def insert_documents(self, collection_name: str, documents: List[Dict[str, Any]], metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Deprecated - use GitMeshMemory.store() or Knowledge.store() instead."""
        return self._deprecated_method("insert_documents")

    def find_documents(self, collection_name: str, query: Dict[str, Any] = None, limit: int = 10, sort: Optional[List[tuple]] = None, projection: Optional[Dict[str, int]] = None) -> Dict[str, str]:
        """Deprecated - use GitMeshMemory.search() or Knowledge.search() instead."""
        return self._deprecated_method("find_documents")

    def update_document(self, collection_name: str, query: Dict[str, Any], update: Dict[str, Any], upsert: bool = False) -> Dict[str, Any]:
        """Deprecated - use GitMeshMemory.store() or Knowledge.store() instead."""
        return self._deprecated_method("update_document")

    def delete_document(self, collection_name: str, query: Dict[str, Any]) -> Dict[str, Any]:
        """Deprecated - functionality not supported in new storage system."""
        return self._deprecated_method("delete_document")

    def create_vector_index(self, collection_name: str, vector_field: str = "embedding", dimensions: int = 1536, similarity: str = "cosine", index_name: str = "vector_index") -> Dict[str, Any]:
        """Deprecated - Qdrant handles indexing automatically."""
        return self._deprecated_method("create_vector_index")

    def vector_search(self, collection_name: str, query_vector: List[float], vector_field: str = "embedding", limit: int = 10, num_candidates: int = 100, score_threshold: float = 0.0, filter_query: Optional[Dict[str, Any]] = None, index_name: str = "vector_index") -> Dict[str, str]:
        """Deprecated - use Knowledge.search() instead."""
        return self._deprecated_method("vector_search")

    def store_with_embedding(self, collection_name: str, text: str, embedding: List[float], metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Deprecated - use Knowledge.store() instead."""
        return self._deprecated_method("store_with_embedding")

    def text_search(self, collection_name: str, query: str, limit: int = 10, text_field: str = "text") -> Dict[str, str]:
        """Deprecated - use GitMeshMemory.search() or Knowledge.search() instead."""
        return self._deprecated_method("text_search")

    def get_stats(self, collection_name: str) -> Dict[str, Any]:
        """Deprecated - stats not available in new storage system."""
        return self._deprecated_method("get_stats")

    def close(self):
        """Deprecated - no connection to close."""
        pass

# Create deprecated instance for backward compatibility
_mongodb_tools = DeprecatedMongoDBTools()

# Export deprecated functions for backward compatibility
def insert_document(collection_name: str, document: Dict[str, Any], metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Deprecated - use GitMeshMemory.store() or Knowledge.store() instead."""
    return _mongodb_tools.insert_document(collection_name, document, metadata)

def insert_documents(collection_name: str, documents: List[Dict[str, Any]], metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Deprecated - use GitMeshMemory.store() or Knowledge.store() instead."""
    return _mongodb_tools.insert_documents(collection_name, documents, metadata)

def find_documents(collection_name: str, query: Dict[str, Any] = None, limit: int = 10, sort: Optional[List[tuple]] = None, projection: Optional[Dict[str, int]] = None) -> Dict[str, str]:
    """Deprecated - use GitMeshMemory.search() or Knowledge.search() instead."""
    return _mongodb_tools.find_documents(collection_name, query, limit, sort, projection)

def update_document(collection_name: str, query: Dict[str, Any], update: Dict[str, Any], upsert: bool = False) -> Dict[str, Any]:
    """Deprecated - use GitMeshMemory.store() or Knowledge.store() instead."""
    return _mongodb_tools.update_document(collection_name, query, update, upsert)

def delete_document(collection_name: str, query: Dict[str, Any]) -> Dict[str, Any]:
    """Deprecated - functionality not supported in new storage system."""
    return _mongodb_tools.delete_document(collection_name, query)

def create_vector_index(collection_name: str, vector_field: str = "embedding", dimensions: int = 1536, similarity: str = "cosine", index_name: str = "vector_index") -> Dict[str, Any]:
    """Deprecated - Qdrant handles indexing automatically."""
    return _mongodb_tools.create_vector_index(collection_name, vector_field, dimensions, similarity, index_name)

def vector_search(collection_name: str, query_vector: List[float], vector_field: str = "embedding", limit: int = 10, num_candidates: int = 100, score_threshold: float = 0.0, filter_query: Optional[Dict[str, Any]] = None, index_name: str = "vector_index") -> Dict[str, str]:
    """Deprecated - use Knowledge.search() instead."""
    return _mongodb_tools.vector_search(collection_name, query_vector, vector_field, limit, num_candidates, score_threshold, filter_query, index_name)

def store_with_embedding(collection_name: str, text: str, embedding: List[float], metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Deprecated - use Knowledge.store() instead."""
    return _mongodb_tools.store_with_embedding(collection_name, text, embedding, metadata)

def text_search(collection_name: str, query: str, limit: int = 10, text_field: str = "text") -> Dict[str, str]:
    """Deprecated - use GitMeshMemory.search() or Knowledge.search() instead."""
    return _mongodb_tools.text_search(collection_name, query, limit, text_field)

def get_stats(collection_name: str) -> Dict[str, Any]:
    """Deprecated - stats not available in new storage system."""
    return _mongodb_tools.get_stats(collection_name)

def connect_mongodb(connection_string: str, database_name: str = "deprecated") -> DeprecatedMongoDBTools:
    """Deprecated - use GitMeshMemory or Knowledge instead."""
    return DeprecatedMongoDBTools(connection_string, database_name)

if __name__ == "__main__":
    print("\n==================================================")
    print("DEPRECATED: MongoDB Tools")
    print("==================================================\n")
    
    print("MongoDB support has been removed from GitMesh.")
    print("Please use the new storage system:\n")
    
    print("For memory/chat storage:")
    print("from ai.memory.memory import GitMeshMemory")
    print("memory = GitMeshMemory()")
    print("memory.store('user123', 'Remember this')")
    print("results = memory.search('user123', 'Remember')")
    print()
    
    print("For knowledge/document storage:")
    print("from ai.knowledge.knowledge import Knowledge")
    print("knowledge = Knowledge()")
    print("knowledge.store('Important knowledge')")
    print("results = knowledge.search('important')")
    print()
    
    print("==================================================")
    print("Migration Complete - Use Supabase + Qdrant")
    print("==================================================\n")