#!/usr/bin/env python3
"""
Memory usage statistics and monitoring script.
Provides insights into the hybrid memory system usage across Qdrant and Supabase.
"""

import os
import sys
from dotenv import load_dotenv
import logging
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
import argparse

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables from .env file
load_dotenv()

def get_memory_stats():
    """Get statistics about memory usage from both Qdrant and Supabase."""
    from ai.memory.supabase_db import SupabaseDB
    from ai.memory.qdrant_db import QdrantDB
    
    stats = {
        "supabase": {},
        "qdrant": {},
        "timestamp": datetime.now().isoformat()
    }
    
    # Get Supabase stats
    try:
        supabase_config = {
            "url": os.environ.get("SUPABASE_URL"),
            "key": os.environ.get("SUPABASE_ANON_KEY"),
            "service_role_key": os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
        }
        supabase_db = SupabaseDB(supabase_config)
        supabase_db.initialize()
        
        # Get memory counts by table
        memories_count = supabase_db.client.table("memories").select("count").execute()
        entity_count = supabase_db.client.table("entities").select("count").execute()
        user_count = supabase_db.client.table("user_memory").select("count").execute()
        
        stats["supabase"]["memories_count"] = memories_count.data[0]["count"] if memories_count.data else 0
        stats["supabase"]["entities_count"] = entity_count.data[0]["count"] if entity_count.data else 0
        stats["supabase"]["user_memories_count"] = user_count.data[0]["count"] if user_count.data else 0
        stats["supabase"]["total_count"] = (
            stats["supabase"]["memories_count"] + 
            stats["supabase"]["entities_count"] + 
            stats["supabase"]["user_memories_count"]
        )
        
        # Get memory type distribution
        memory_types = supabase_db.client.table("memories").select("memory_type, count(*)").group_by("memory_type").execute()
        for item in memory_types.data:
            stats["supabase"][f"type_{item['memory_type']}_count"] = item["count"]
            
        logger.info("Retrieved Supabase memory statistics")
    except Exception as e:
        logger.error(f"Failed to retrieve Supabase stats: {str(e)}")
    
    # Get Qdrant stats
    try:
        qdrant_config = {
            "url": os.environ.get("QDRANT_URL"),
            "api_key": os.environ.get("QDRANT_API_KEY"),
            "collection_name": os.environ.get("QDRANT_COLLECTION_NAME", "gitmesh_memory")
        }
        qdrant_db = QdrantDB(qdrant_config)
        qdrant_db.initialize()
        
        # Get collection info
        collection_info = qdrant_db.client.get_collection(collection_name=qdrant_config["collection_name"])
        
        stats["qdrant"]["vector_size"] = collection_info.config.params.vectors.size
        stats["qdrant"]["vectors_count"] = collection_info.vectors_count
        stats["qdrant"]["indexed_vectors_count"] = collection_info.indexed_vectors_count
        stats["qdrant"]["points_count"] = collection_info.points_count
        stats["qdrant"]["segments_count"] = collection_info.segments_count
        
        logger.info("Retrieved Qdrant memory statistics")
    except Exception as e:
        logger.error(f"Failed to retrieve Qdrant stats: {str(e)}")
    
    return stats

def display_stats(stats):
    """Display memory statistics in a readable format."""
    print("\n=== HYBRID MEMORY SYSTEM STATISTICS ===")
    print(f"Timestamp: {stats['timestamp']}")
    
    print("\n=== SUPABASE STATISTICS ===")
    if "supabase" in stats and stats["supabase"]:
        print(f"Total entries: {stats['supabase'].get('total_count', 'N/A')}")
        print(f"Memory entries: {stats['supabase'].get('memories_count', 'N/A')}")
        print(f"Entity entries: {stats['supabase'].get('entities_count', 'N/A')}")
        print(f"User memory entries: {stats['supabase'].get('user_memories_count', 'N/A')}")
        
        # Print memory type distribution if available
        for key, value in stats["supabase"].items():
            if key.startswith("type_"):
                memory_type = key.replace("type_", "").replace("_count", "")
                print(f"  - {memory_type}: {value}")
    else:
        print("No Supabase statistics available")
    
    print("\n=== QDRANT STATISTICS ===")
    if "qdrant" in stats and stats["qdrant"]:
        print(f"Vector dimension: {stats['qdrant'].get('vector_size', 'N/A')}")
        print(f"Total vectors: {stats['qdrant'].get('vectors_count', 'N/A')}")
        print(f"Indexed vectors: {stats['qdrant'].get('indexed_vectors_count', 'N/A')}")
        print(f"Total points: {stats['qdrant'].get('points_count', 'N/A')}")
        print(f"Segments: {stats['qdrant'].get('segments_count', 'N/A')}")
    else:
        print("No Qdrant statistics available")
        
def plot_statistics(stats):
    """Create visualizations for memory statistics."""
    try:
        import matplotlib.pyplot as plt
        
        # Create a figure with multiple subplots
        fig, axs = plt.subplots(2, 2, figsize=(12, 10))
        fig.suptitle('Hybrid Memory System Statistics', fontsize=16)
        
        # Supabase data distribution
        if "supabase" in stats and stats["supabase"]:
            supabase_data = [
                stats["supabase"].get("memories_count", 0),
                stats["supabase"].get("entities_count", 0),
                stats["supabase"].get("user_memories_count", 0)
            ]
            axs[0, 0].bar(['Memories', 'Entities', 'User Memories'], supabase_data)
            axs[0, 0].set_title('Supabase Data Distribution')
            axs[0, 0].set_ylabel('Count')
            
            # Memory type distribution
            memory_types = {}
            for key, value in stats["supabase"].items():
                if key.startswith("type_"):
                    memory_type = key.replace("type_", "").replace("_count", "")
                    memory_types[memory_type] = value
                    
            if memory_types:
                axs[0, 1].pie(memory_types.values(), labels=memory_types.keys(), autopct='%1.1f%%')
                axs[0, 1].set_title('Memory Type Distribution')
        
        # Qdrant statistics
        if "qdrant" in stats and stats["qdrant"]:
            qdrant_data = {
                'Total Vectors': stats["qdrant"].get("vectors_count", 0),
                'Indexed Vectors': stats["qdrant"].get("indexed_vectors_count", 0),
                'Total Points': stats["qdrant"].get("points_count", 0)
            }
            axs[1, 0].bar(qdrant_data.keys(), qdrant_data.values())
            axs[1, 0].set_title('Qdrant Vector Statistics')
            axs[1, 0].set_ylabel('Count')
            
            # Add a text box with additional Qdrant info
            qdrant_info = (
                f"Vector Size: {stats['qdrant'].get('vector_size', 'N/A')}\n"
                f"Segments: {stats['qdrant'].get('segments_count', 'N/A')}"
            )
            axs[1, 1].axis('off')
            axs[1, 1].text(0.1, 0.5, qdrant_info, fontsize=12)
        
        plt.tight_layout(rect=[0, 0, 1, 0.95])
        
        # Save the figure
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"memory_stats_{timestamp}.png"
        plt.savefig(output_file)
        print(f"\nStatistics plot saved to {output_file}")
        
        # Show the plot if requested
        plt.show()
        
    except ImportError:
        print("Matplotlib or pandas not available. Skipping visualization.")
    except Exception as e:
        print(f"Error creating visualizations: {str(e)}")

def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(description="Memory usage statistics and monitoring")
    parser.add_argument("--plot", action="store_true", help="Generate plots of the statistics")
    parser.add_argument("--export", action="store_true", help="Export statistics to a CSV file")
    args = parser.parse_args()
    
    try:
        stats = get_memory_stats()
        display_stats(stats)
        
        if args.plot:
            plot_statistics(stats)
            
        if args.export:
            # Flatten the stats dictionary for CSV export
            flat_stats = {"timestamp": stats["timestamp"]}
            
            for storage, metrics in stats.items():
                if storage != "timestamp":
                    for metric, value in metrics.items():
                        flat_stats[f"{storage}_{metric}"] = value
                        
            # Create a DataFrame and export to CSV
            df = pd.DataFrame([flat_stats])
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            csv_file = f"memory_stats_{timestamp}.csv"
            df.to_csv(csv_file, index=False)
            print(f"\nStatistics exported to {csv_file}")
            
    except Exception as e:
        logger.error(f"Error running memory statistics: {str(e)}")
        return 1
        
    return 0

if __name__ == "__main__":
    sys.exit(main())
