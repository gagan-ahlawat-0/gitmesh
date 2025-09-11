#!/usr/bin/env python3
"""
Test script for validating the hybrid memory system.
This script tests both Qdrant and Supabase connections and basic operations.
"""

import os
import sys
from dotenv import load_dotenv
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables from .env file
load_dotenv()

def test_connections():
    """Test connections to both Supabase and Qdrant."""
    from ai.memory.supabase_db import SupabaseMemory
    from ai.memory.qdrant_db import QdrantMemory
    
    logger.info("Testing Supabase connection...")
    try:
        supabase_config = {
            "url": os.environ.get("SUPABASE_URL"),
            "key": os.environ.get("SUPABASE_ANON_KEY"),
            "service_role_key": os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
        }
        supabase_db = SupabaseMemory(config=supabase_config, verbose=5)
        logger.info("✅ Supabase connection successful")
    except Exception as e:
        logger.error(f"❌ Supabase connection failed: {str(e)}")
        return False
    
    logger.info("Testing Qdrant connection...")
    try:
        qdrant_config = {
            "url": os.environ.get("QDRANT_URL"),
            "api_key": os.environ.get("QDRANT_API_KEY"),
            "collection_name": os.environ.get("QDRANT_COLLECTION_NAME", "gitmesh_memory")
        }
        qdrant_db = QdrantMemory(config=qdrant_config, verbose=5)
        logger.info("✅ Qdrant connection successful")
    except Exception as e:
        logger.error(f"❌ Qdrant connection failed: {str(e)}")
        return False
    
    return True

def test_hybrid_memory_operations():
    """Test basic operations with the hybrid memory system."""
    from ai.memory.hybrid_memory import Memory
    
    logger.info("Testing hybrid memory operations...")
    try:
        memory_config = {
            "provider": "hybrid",
            "vector_provider": "qdrant",
            "use_embedding": True
        }
        memory = Memory(memory_config)
        
        # Test storing data
        logger.info("Testing store operation...")
        test_data = "This is a test entry for the hybrid memory system."
        metadata = {
            "source": "test_script",
            "importance": 0.8,
            "tags": ["test", "hybrid", "memory"]
        }
        
        memory_id = memory.store_long_term(test_data, metadata=metadata)
        logger.info(f"✅ Successfully stored test data with ID: {memory_id}")
        
        # Test searching data
        logger.info("Testing search operation...")
        search_results = memory.search_long_term("test hybrid memory", limit=5)
        
        if search_results and len(search_results) > 0:
            logger.info(f"✅ Successfully retrieved {len(search_results)} search results")
            # Print first result
            if search_results:
                logger.info(f"First result: {search_results[0]}")
        else:
            logger.warning("⚠️ Search returned no results")
        
        return True
    except Exception as e:
        logger.error(f"❌ Hybrid memory operations failed: {str(e)}")
        return False

if __name__ == "__main__":
    logger.info("Starting hybrid memory system test")
    
    if not test_connections():
        logger.error("Connection tests failed. Please check your configuration.")
        sys.exit(1)
    
    if not test_hybrid_memory_operations():
        logger.error("Memory operation tests failed.")
        sys.exit(1)
    
    logger.info("✅ All tests completed successfully!")
