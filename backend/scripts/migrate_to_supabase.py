#!/usr/bin/env python
"""
Migration script to move data from SQLite, MongoDB, or ChromaDB to Supabase PostgreSQL
"""
import os
import sys
import json
import sqlite3
import logging
import argparse
from pathlib import Path
from typing import Dict, List, Any, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("db_migration")

# Add the parent directory to sys.path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
# Load environment variables
load_dotenv()

from ai.memory.supabase_db import SupabaseMemory

# Check for optional dependencies
try:
    import chromadb
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False
    logger.warning("ChromaDB not available. Skipping ChromaDB migration.")

try:
    import pymongo
    from pymongo import MongoClient
    PYMONGO_AVAILABLE = True
except ImportError:
    PYMONGO_AVAILABLE = False
    logger.warning("PyMongo not available. Skipping MongoDB migration.")

def migrate_sqlite_to_supabase(
    short_db_path: str, 
    long_db_path: str, 
    supabase_config: Dict[str, Any]
) -> int:
    """
    Migrate data from SQLite databases to Supabase
    
    Returns:
        int: Number of records migrated
    """
    # Initialize Supabase memory
    supabase_memory = SupabaseMemory(supabase_config, verbose=5)
    
    records_migrated = 0
    
    # Migrate short-term memory
    if os.path.exists(short_db_path):
        try:
            conn = sqlite3.connect(short_db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Get all records from short_mem table
            cursor.execute("SELECT id, content, meta, created_at FROM short_mem")
            rows = cursor.fetchall()
            
            logger.info(f"Found {len(rows)} records in short-term memory")
            
            for row in rows:
                try:
                    # Parse metadata
                    metadata = json.loads(row['meta'] or '{}')
                    
                    # Store in Supabase
                    supabase_memory.store_short_term(
                        text=row['content'],
                        metadata=metadata
                    )
                    records_migrated += 1
                except Exception as e:
                    logger.error(f"Error migrating short-term record {row['id']}: {e}")
            
            conn.close()
            logger.info(f"Migrated {records_migrated} records from short-term memory")
            
        except Exception as e:
            logger.error(f"Error migrating short-term memory: {e}")
    else:
        logger.warning(f"Short-term memory database not found: {short_db_path}")
    
    # Migrate long-term memory
    short_term_records = records_migrated
    records_migrated = 0
    
    if os.path.exists(long_db_path):
        try:
            conn = sqlite3.connect(long_db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Get all records from long_mem table
            cursor.execute("SELECT id, content, meta, created_at FROM long_mem")
            rows = cursor.fetchall()
            
            logger.info(f"Found {len(rows)} records in long-term memory")
            
            for row in rows:
                try:
                    # Parse metadata
                    metadata = json.loads(row['meta'] or '{}')
                    
                    # Check for entity memory
                    if metadata.get("category") == "entity":
                        # Extract entity information if available
                        content = row['content']
                        if content.startswith("Entity ") and ":" in content:
                            # Parse entity format: Entity name(type): description | relationships: ...
                            entity_part = content.split(":", 1)[0].replace("Entity ", "")
                            if "(" in entity_part and ")" in entity_part:
                                name = entity_part.split("(")[0].strip()
                                type_ = entity_part.split("(")[1].split(")")[0].strip()
                                
                                # Get description and relationships
                                remaining = content.split(":", 1)[1]
                                if "| relationships:" in remaining:
                                    desc = remaining.split("| relationships:")[0].strip()
                                    relations = remaining.split("| relationships:")[1].strip()
                                else:
                                    desc = remaining.strip()
                                    relations = ""
                                
                                # Store as entity
                                supabase_memory.store_entity(
                                    name=name,
                                    type_=type_,
                                    desc=desc,
                                    relations=relations
                                )
                            else:
                                # Store as regular long-term memory
                                supabase_memory.store_long_term(
                                    text=content,
                                    metadata=metadata
                                )
                        else:
                            # Store as regular long-term memory
                            supabase_memory.store_long_term(
                                text=content,
                                metadata=metadata
                            )
                    # Check for user memory
                    elif "user_id" in metadata:
                        supabase_memory.store_user_memory(
                            user_id=metadata["user_id"],
                            text=row['content'],
                            extra=metadata
                        )
                    else:
                        # Store as regular long-term memory
                        supabase_memory.store_long_term(
                            text=row['content'],
                            metadata=metadata
                        )
                    
                    records_migrated += 1
                    
                except Exception as e:
                    logger.error(f"Error migrating long-term record {row['id']}: {e}")
            
            conn.close()
            logger.info(f"Migrated {records_migrated} records from long-term memory")
            
        except Exception as e:
            logger.error(f"Error migrating long-term memory: {e}")
    else:
        logger.warning(f"Long-term memory database not found: {long_db_path}")
    
    # Return total records migrated
    return short_term_records + records_migrated

def migrate_mongodb_to_supabase(
    connection_string: str,
    database_name: str,
    supabase_config: Dict[str, Any]
) -> int:
    """
    Migrate data from MongoDB to Supabase
    
    Returns:
        int: Number of records migrated
    """
    if not PYMONGO_AVAILABLE:
        logger.error("PyMongo not available. Cannot migrate from MongoDB.")
        return 0
    
    # Initialize Supabase memory
    supabase_memory = SupabaseMemory(supabase_config, verbose=5)
    
    records_migrated = 0
    
    try:
        # Connect to MongoDB
        mongo_client = MongoClient(connection_string)
        mongo_db = mongo_client[database_name]
        
        # Migrate short_term_memory collection
        if "short_term_memory" in mongo_db.list_collection_names():
            short_term_collection = mongo_db.short_term_memory
            documents = list(short_term_collection.find())
            
            logger.info(f"Found {len(documents)} records in MongoDB short-term memory")
            
            for doc in documents:
                try:
                    # Store in Supabase
                    supabase_memory.store_short_term(
                        text=doc.get("content", ""),
                        metadata=doc.get("metadata", {})
                    )
                    records_migrated += 1
                except Exception as e:
                    logger.error(f"Error migrating MongoDB short-term record {doc.get('_id')}: {e}")
            
            logger.info(f"Migrated {records_migrated} records from MongoDB short-term memory")
        
        # Migrate long_term_memory collection
        short_term_records = records_migrated
        records_migrated = 0
        
        if "long_term_memory" in mongo_db.list_collection_names():
            long_term_collection = mongo_db.long_term_memory
            documents = list(long_term_collection.find())
            
            logger.info(f"Found {len(documents)} records in MongoDB long-term memory")
            
            for doc in documents:
                try:
                    # Store in Supabase
                    supabase_memory.store_long_term(
                        text=doc.get("content", ""),
                        metadata=doc.get("metadata", {})
                    )
                    records_migrated += 1
                except Exception as e:
                    logger.error(f"Error migrating MongoDB long-term record {doc.get('_id')}: {e}")
            
            logger.info(f"Migrated {records_migrated} records from MongoDB long-term memory")
        
        # Migrate entity_memory collection
        long_term_records = records_migrated
        records_migrated = 0
        
        if "entity_memory" in mongo_db.list_collection_names():
            entity_collection = mongo_db.entity_memory
            documents = list(entity_collection.find())
            
            logger.info(f"Found {len(documents)} records in MongoDB entity memory")
            
            for doc in documents:
                try:
                    # Store in Supabase
                    supabase_memory.store_entity(
                        name=doc.get("entity_name", ""),
                        type_=doc.get("entity_type", ""),
                        desc=doc.get("description", ""),
                        relations=doc.get("relationships", "")
                    )
                    records_migrated += 1
                except Exception as e:
                    logger.error(f"Error migrating MongoDB entity record {doc.get('_id')}: {e}")
            
            logger.info(f"Migrated {records_migrated} records from MongoDB entity memory")
        
        # Migrate user_memory collection
        entity_records = records_migrated
        records_migrated = 0
        
        if "user_memory" in mongo_db.list_collection_names():
            user_collection = mongo_db.user_memory
            documents = list(user_collection.find())
            
            logger.info(f"Found {len(documents)} records in MongoDB user memory")
            
            for doc in documents:
                try:
                    # Store in Supabase
                    supabase_memory.store_user_memory(
                        user_id=doc.get("user_id", ""),
                        text=doc.get("content", ""),
                        extra=doc.get("metadata", {})
                    )
                    records_migrated += 1
                except Exception as e:
                    logger.error(f"Error migrating MongoDB user record {doc.get('_id')}: {e}")
            
            logger.info(f"Migrated {records_migrated} records from MongoDB user memory")
        
        # Close MongoDB connection
        mongo_client.close()
        
        # Return total records migrated
        return short_term_records + long_term_records + entity_records + records_migrated
        
    except Exception as e:
        logger.error(f"Error connecting to MongoDB: {e}")
        return 0

def migrate_chroma_to_supabase(
    chroma_path: str,
    supabase_config: Dict[str, Any]
) -> int:
    """
    Migrate data from ChromaDB to Supabase
    
    Returns:
        int: Number of records migrated
    """
    if not CHROMADB_AVAILABLE:
        logger.error("ChromaDB not available. Cannot migrate from ChromaDB.")
        return 0
    
    # Initialize Supabase memory
    supabase_memory = SupabaseMemory(supabase_config, verbose=5)
    
    records_migrated = 0
    
    try:
        # Connect to ChromaDB
        from chromadb.config import Settings as ChromaSettings
        chroma_client = chromadb.PersistentClient(
            path=chroma_path,
            settings=ChromaSettings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        # Get all collections
        collections = chroma_client.list_collections()
        
        for collection in collections:
            collection_name = collection.name
            logger.info(f"Processing ChromaDB collection: {collection_name}")
            
            # Get collection data
            chroma_collection = chroma_client.get_collection(name=collection_name)
            result = chroma_collection.get(include=["documents", "metadatas", "embeddings"])
            
            if result["ids"]:
                logger.info(f"Found {len(result['ids'])} records in ChromaDB collection {collection_name}")
                
                for i, doc_id in enumerate(result["ids"]):
                    try:
                        document = result["documents"][i] if "documents" in result else ""
                        metadata = result["metadatas"][i] if "metadatas" in result else {}
                        embedding = result["embeddings"][i] if "embeddings" in result else None
                        
                        # Determine where to store based on metadata
                        if metadata.get("category") == "entity":
                            # Extract entity information if available
                            if document.startswith("Entity ") and ":" in document:
                                # Parse entity format: Entity name(type): description | relationships: ...
                                entity_part = document.split(":", 1)[0].replace("Entity ", "")
                                if "(" in entity_part and ")" in entity_part:
                                    name = entity_part.split("(")[0].strip()
                                    type_ = entity_part.split("(")[1].split(")")[0].strip()
                                    
                                    # Get description and relationships
                                    remaining = document.split(":", 1)[1]
                                    if "| relationships:" in remaining:
                                        desc = remaining.split("| relationships:")[0].strip()
                                        relations = remaining.split("| relationships:")[1].strip()
                                    else:
                                        desc = remaining.strip()
                                        relations = ""
                                    
                                    # Store as entity
                                    supabase_memory.store_entity(
                                        name=name,
                                        type_=type_,
                                        desc=desc,
                                        relations=relations
                                    )
                                else:
                                    # Store as regular long-term memory
                                    supabase_memory.store_long_term(
                                        text=document,
                                        metadata=metadata
                                    )
                            else:
                                # Store as regular long-term memory
                                supabase_memory.store_long_term(
                                    text=document,
                                    metadata=metadata
                                )
                        elif "user_id" in metadata:
                            supabase_memory.store_user_memory(
                                user_id=metadata["user_id"],
                                text=document,
                                extra=metadata
                            )
                        else:
                            # Assume it's long-term memory (ChromaDB is typically used for this)
                            supabase_memory.store_long_term(
                                text=document,
                                metadata=metadata
                            )
                        
                        records_migrated += 1
                        
                    except Exception as e:
                        logger.error(f"Error migrating ChromaDB record {doc_id}: {e}")
        
        logger.info(f"Migrated {records_migrated} records from ChromaDB")
        
        return records_migrated
        
    except Exception as e:
        logger.error(f"Error connecting to ChromaDB: {e}")
        return 0

def main():
    parser = argparse.ArgumentParser(description="Migrate database to Supabase PostgreSQL")
    parser.add_argument("--sqlite", action="store_true", help="Migrate from SQLite")
    parser.add_argument("--mongodb", action="store_true", help="Migrate from MongoDB")
    parser.add_argument("--chroma", action="store_true", help="Migrate from ChromaDB")
    parser.add_argument("--all", action="store_true", help="Migrate from all available sources")
    parser.add_argument("--short-db", help="Path to short-term SQLite database")
    parser.add_argument("--long-db", help="Path to long-term SQLite database")
    parser.add_argument("--mongo-url", help="MongoDB connection string")
    parser.add_argument("--mongo-db", help="MongoDB database name")
    parser.add_argument("--chroma-path", help="Path to ChromaDB directory")
    
    args = parser.parse_args()
    
    # Get Supabase configuration
    supabase_config = {
        "supabase_url": os.getenv("SUPABASE_URL"),
        "supabase_key": os.getenv("SUPABASE_ANON_KEY"),
        "supabase_service_key": os.getenv("SUPABASE_SERVICE_ROLE_KEY"),
        "pg_host": os.getenv("POSTGRES_HOST"),
        "pg_port": os.getenv("POSTGRES_PORT"),
        "pg_db": os.getenv("POSTGRES_DB"),
        "pg_user": os.getenv("POSTGRES_USER"),
        "pg_password": os.getenv("POSTGRES_PASSWORD"),
        "pg_ssl": os.getenv("POSTGRES_SSL")
    }
    
    # Validate Supabase configuration
    if not supabase_config["supabase_url"] or not supabase_config["supabase_key"]:
        logger.error("Supabase configuration is incomplete. Please check your .env file.")
        sys.exit(1)
    
    total_records = 0
    
    # Migrate SQLite
    if args.sqlite or args.all:
        short_db = args.short_db or ".gitmesh/short_term.db"
        long_db = args.long_db or ".gitmesh/long_term.db"
        
        logger.info(f"Migrating SQLite databases: {short_db}, {long_db}")
        sqlite_records = migrate_sqlite_to_supabase(short_db, long_db, supabase_config)
        logger.info(f"Total records migrated from SQLite: {sqlite_records}")
        total_records += sqlite_records
    
    # Migrate MongoDB
    if (args.mongodb or args.all) and PYMONGO_AVAILABLE:
        mongo_url = args.mongo_url or "mongodb://localhost:27017/"
        mongo_db = args.mongo_db or "gitmesh"
        
        logger.info(f"Migrating MongoDB: {mongo_url}, {mongo_db}")
        mongo_records = migrate_mongodb_to_supabase(mongo_url, mongo_db, supabase_config)
        logger.info(f"Total records migrated from MongoDB: {mongo_records}")
        total_records += mongo_records
    
    # Migrate ChromaDB
    if (args.chroma or args.all) and CHROMADB_AVAILABLE:
        chroma_path = args.chroma_path or "chroma_db"
        
        logger.info(f"Migrating ChromaDB: {chroma_path}")
        chroma_records = migrate_chroma_to_supabase(chroma_path, supabase_config)
        logger.info(f"Total records migrated from ChromaDB: {chroma_records}")
        total_records += chroma_records
    
    logger.info(f"Migration complete. Total records migrated: {total_records}")

if __name__ == "__main__":
    main()
