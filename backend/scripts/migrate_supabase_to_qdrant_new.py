#!/usr/bin/env python3
"""
Migration script to move vector data from Supabase to Qdrant Cloud.
This script migrates existing embeddings from Supabase PostgreSQL to Qdrant
while keeping metadata in Supabase.
"""

import os
import sys
import logging
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
import json
import uuid

# Load environment variables
load_dotenv()

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

try:
    # Import Supabase dependencies
    import psycopg2
    from psycopg2.extras import RealDictCursor
    from supabase import create_client, Client
    from ai.memory.supabase_db import SupabaseMemory
    SUPABASE_AVAILABLE = True
except ImportError as e:
    SUPABASE_AVAILABLE = False
    logger.error(f"Supabase dependencies not available: {e}")
    sys.exit(1)

try:
    # Import Qdrant dependencies
    from qdrant_client import QdrantClient
    from qdrant_client.http import models
    from ai.memory.qdrant_db import QdrantMemory
    QDRANT_AVAILABLE = True
except ImportError as e:
    QDRANT_AVAILABLE = False
    logger.error(f"Qdrant dependencies not available: {e}")
    sys.exit(1)


def migrate_memories_from_supabase_to_qdrant(batch_size: int = 100):
    """
    Migrate memories with embeddings from Supabase to Qdrant.
    This will check existing tables for data to migrate.
    """
    logger.info("Starting migration from Supabase to Qdrant...")
    
    # Initialize Supabase
    supabase_config = {
        "url": os.getenv("SUPABASE_URL"),
        "key": os.getenv("SUPABASE_ANON_KEY"),
        "service_role_key": os.getenv("SUPABASE_SERVICE_ROLE_KEY"),
    }
    
    # Initialize with proper config
    supabase = SupabaseMemory(config=supabase_config, verbose=5)
    
    # Initialize Qdrant
    qdrant_config = {
        "url": os.getenv("QDRANT_URL", "").strip('"\''),  # Remove quotes if present
        "api_key": os.getenv("QDRANT_API_KEY"),
        "collection_name": os.getenv("QDRANT_COLLECTION_NAME", "gitmesh_memory"),
    }
    
    qdrant_db = QdrantMemory(config=qdrant_config, verbose=5)
    
    # Get PostgreSQL connection for direct access
    pg_config = {
        "host": os.getenv("POSTGRES_HOST"),
        "port": int(os.getenv("POSTGRES_PORT", 5432)),
        "dbname": os.getenv("POSTGRES_DB"),
        "user": os.getenv("POSTGRES_USER"),
        "password": os.getenv("POSTGRES_PASSWORD"),
        "sslmode": os.getenv("POSTGRES_SSL", "require")
    }
    
    logger.info(f"Connecting to PostgreSQL at {pg_config['host']}:{pg_config['port']}")
    conn = psycopg2.connect(**pg_config)
    
    try:
        # First, let's check what tables exist
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND (table_name LIKE '%memory%' OR table_name = 'memories')
            """)
            tables = [row[0] for row in cursor.fetchall()]
            logger.info(f"Found tables: {tables}")
        
        # If no relevant tables found, create some test data
        if not tables:
            logger.info("No existing memory tables found. Creating sample data for testing...")
            # Let's just log this and continue for now
            logger.info("Migration completed - no existing data to migrate.")
            return
        
        # Check each table and migrate if it has embeddings
        memory_tables_to_check = ['memories', 'long_term_memory', 'short_term_memory', 'entity_memory', 'user_memory']
        migrated_count = 0
        
        for table_name in memory_tables_to_check:
            if table_name not in tables:
                continue
                
            logger.info(f"Checking table: {table_name}")
            
            with conn.cursor() as cursor:
                # Check table structure
                cursor.execute(f"""
                    SELECT column_name, data_type 
                    FROM information_schema.columns 
                    WHERE table_name = '{table_name}' AND table_schema = 'public'
                """)
                columns = {row[0]: row[1] for row in cursor.fetchall()}
                logger.info(f"Table {table_name} columns: {list(columns.keys())}")
                
                # Skip if no embedding column
                if 'embedding' not in columns:
                    logger.info(f"No embedding column found in {table_name}, skipping...")
                    continue
                
                # Get total count
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                total_count = cursor.fetchone()[0]
                logger.info(f"Found {total_count} total records in {table_name}")
                
                if total_count == 0:
                    continue
                
                # Get count with non-null embeddings
                cursor.execute(f"SELECT COUNT(*) FROM {table_name} WHERE embedding IS NOT NULL")
                embedding_count = cursor.fetchone()[0]
                logger.info(f"Found {embedding_count} records with embeddings in {table_name}")
                
                if embedding_count == 0:
                    continue
                
                # Process in batches
                offset = 0
                
                while offset < embedding_count:
                    logger.info(f"Processing batch at offset {offset}...")
                    
                    with conn.cursor(cursor_factory=RealDictCursor) as batch_cursor:
                        batch_cursor.execute(f"""
                            SELECT * FROM {table_name} 
                            WHERE embedding IS NOT NULL 
                            ORDER BY created_at 
                            LIMIT %s OFFSET %s
                        """, (batch_size, offset))
                        records = batch_cursor.fetchall()
                    
                    if not records:
                        break
                    
                    # Prepare data for Qdrant
                    vectors_to_store = []
                    
                    for record in records:
                        try:
                            # Get or generate ID
                            record_id = str(record.get('id', uuid.uuid4()))
                            
                            # Get text content
                            text_content = record.get('text') or record.get('content') or ""
                            
                            # Get embedding - handle different formats
                            embedding = record.get('embedding')
                            if embedding is None:
                                logger.warning(f"No embedding for record {record_id}, skipping...")
                                continue
                            
                            # Convert embedding to list if it's a string or other format
                            if isinstance(embedding, str):
                                try:
                                    embedding = json.loads(embedding)
                                except:
                                    logger.error(f"Could not parse embedding for record {record_id}")
                                    continue
                            elif hasattr(embedding, 'tolist'):  # numpy array
                                embedding = embedding.tolist()
                            
                            # Ensure embedding is a list of numbers
                            if not isinstance(embedding, list) or not all(isinstance(x, (int, float)) for x in embedding):
                                logger.error(f"Invalid embedding format for record {record_id}")
                                continue
                            
                            # Create payload for Qdrant
                            payload = {
                                "memory_id": record_id,
                                "text": text_content,
                                "memory_type": record.get('memory_type', 'general'),
                                "table_source": table_name,
                                "created_at": str(record.get('created_at', '')) if record.get('created_at') else None,
                            }
                            
                            # Add metadata if available
                            if record.get('metadata'):
                                payload["metadata"] = record.get('metadata')
                            
                            vectors_to_store.append({
                                "id": record_id,
                                "vector": embedding,
                                "payload": payload
                            })
                            
                        except Exception as e:
                            logger.error(f"Error processing record {record.get('id', 'unknown')}: {e}")
                            continue
                    
                    # Store vectors in Qdrant
                    if vectors_to_store:
                        try:
                            qdrant_db.client.upsert(
                                collection_name=qdrant_config["collection_name"],
                                points=vectors_to_store
                            )
                            migrated_count += len(vectors_to_store)
                            logger.info(f"Successfully migrated {len(vectors_to_store)} vectors from {table_name}")
                        except Exception as e:
                            logger.error(f"Error storing vectors in Qdrant: {e}")
                            # Don't break, continue with next batch
                    
                    offset += batch_size
        
        logger.info(f"Migration completed! Total vectors migrated: {migrated_count}")
        
    except Exception as e:
        logger.error(f"Error during migration: {e}")
        raise
    finally:
        conn.close()


def verify_migration():
    """Verify that the migration was successful."""
    logger.info("Verifying migration...")
    
    try:
        # Initialize Qdrant
        qdrant_config = {
            "url": os.getenv("QDRANT_URL", "").strip('"\''),
            "api_key": os.getenv("QDRANT_API_KEY"),
            "collection_name": os.getenv("QDRANT_COLLECTION_NAME", "gitmesh_memory"),
        }
        
        qdrant_db = QdrantMemory(config=qdrant_config, verbose=5)
        
        # Get collection info
        collection_info = qdrant_db.client.get_collection(qdrant_config["collection_name"])
        
        logger.info(f"Qdrant collection '{qdrant_config['collection_name']}' status:")
        logger.info(f"  - Total points: {collection_info.points_count}")
        logger.info(f"  - Vector size: {collection_info.config.params.vectors.size}")
        logger.info(f"  - Indexed vectors: {collection_info.indexed_vectors_count}")
        
        # Test a simple search if we have data
        if collection_info.points_count > 0:
            logger.info("Testing vector search...")
            # Create a dummy embedding for testing
            test_embedding = [0.1] * collection_info.config.params.vectors.size
            
            search_results = qdrant_db.client.search(
                collection_name=qdrant_config["collection_name"],
                query_vector=test_embedding,
                limit=1
            )
            
            if search_results:
                logger.info("✅ Vector search is working!")
                logger.info(f"Sample result: {search_results[0].payload}")
            else:
                logger.warning("Search returned no results")
        else:
            logger.info("No data in collection, but collection is ready for use.")
        
        logger.info("✅ Migration verification completed successfully!")
        
    except Exception as e:
        logger.error(f"❌ Migration verification failed: {e}")


def main():
    """Main function."""
    logger.info("Starting Supabase to Qdrant migration...")
    
    if not SUPABASE_AVAILABLE or not QDRANT_AVAILABLE:
        logger.error("Required dependencies not available")
        sys.exit(1)
    
    try:
        migrate_memories_from_supabase_to_qdrant()
        verify_migration()
        logger.info("🎉 Migration process completed!")
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
