"""
TARS v1 Command Line Interface
=============================

CLI interface for the TARS (Tactical AI Resource System) v1.

Usage examples:
  python -m integrations.tars.v1.cli --interactive
  python -m integrations.tars.v1.cli --analyze-project --urls "https://github.com/owner/repo" --repositories "https://github.com/owner/repo.git"
  python -m integrations.tars.v1.cli --query "Analyze the latest trends in AI/ML"
"""

import asyncio
import argparse
import json
import os
import sys
from typing import List, Optional, Dict, Any
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent.parent))

from integrations.tars.v1.main import TarsMain


def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="TARS v1 - Tactical AI Resource System",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    # Mode selection
    parser.add_argument(
        "--interactive", 
        action="store_true",
        help="Start interactive mode"
    )
    
    parser.add_argument(
        "--analyze-project",
        action="store_true", 
        help="Analyze a project comprehensively"
    )
    
    parser.add_argument(
        "--query",
        type=str,
        help="Process a single query"
    )
    
    parser.add_argument(
        "--status",
        action="store_true",
        help="Show system status"
    )
    
    # Project analysis options
    parser.add_argument(
        "--urls",
        type=str,
        nargs="+",
        help="Web URLs to analyze"
    )
    
    parser.add_argument(
        "--repositories", 
        type=str,
        nargs="+",
        help="Git repository URLs"
    )
    
    parser.add_argument(
        "--documents",
        type=str,
        nargs="+", 
        help="Document file paths"
    )
    
    parser.add_argument(
        "--data-files",
        type=str,
        nargs="+",
        help="Data file paths (CSV, Excel, etc.)"
    )
    
    parser.add_argument(
        "--github-repos",
        type=str,
        nargs="+",
        help="GitHub repositories for issue/PR analysis (format: owner/repo)"
    )
    
    # Configuration options
    parser.add_argument(
        "--user-id",
        type=str,
        default="cli_user",
        help="User identifier (default: cli_user)"
    )
    
    parser.add_argument(
        "--project-id",
        type=str,
        help="Project identifier (auto-generated if not provided)"
    )
    
    parser.add_argument(
        "--memory-provider",
        choices=["supabase", "qdrant", "chroma"],
        default="supabase",
        help="Memory provider (default: supabase)"
    )
    
    parser.add_argument(
        "--llm-model",
        type=str,
        default="gpt-4o",
        help="LLM model to use (default: gpt-4o)"
    )
    
    parser.add_argument(
        "--config-file",
        type=str,
        help="Load configuration from JSON file"
    )
    
    parser.add_argument(
        "--output-file",
        type=str,
        help="Save results to file"
    )
    
    parser.add_argument(
        "--verbose",
        action="store_true",
        default=True,
        help="Enable verbose output (default: enabled)"
    )
    
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Disable verbose output"
    )
    
    return parser.parse_args()


def load_config_file(config_path: str) -> Dict[str, Any]:
    """Load configuration from JSON file."""
    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ Error loading config file: {e}")
        return {}


def save_results_to_file(results: Dict[str, Any], output_path: str) -> None:
    """Save results to file."""
    try:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        with open(output_path, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        print(f"✅ Results saved to: {output_path}")
        
    except Exception as e:
        print(f"❌ Error saving results: {e}")


async def run_interactive_mode(tars: TarsMain) -> None:
    """Run interactive mode."""
    try:
        print("\n🚀 Starting TARS interactive mode...")
        print("Type 'help' for commands or 'exit' to quit.\n")
        
        await tars.start_interactive_mode()
        
    except KeyboardInterrupt:
        print("\n\n👋 Goodbye!")
    except Exception as e:
        print(f"❌ Error in interactive mode: {e}")


async def run_project_analysis(
    tars: TarsMain,
    urls: Optional[List[str]] = None,
    repositories: Optional[List[str]] = None,
    documents: Optional[List[str]] = None,
    data_files: Optional[List[str]] = None,
    github_repos: Optional[List[str]] = None,
    output_file: Optional[str] = None
) -> Dict[str, Any]:
    """Run project analysis."""
    try:
        print("\n📊 Starting comprehensive project analysis...")
        
        # Validate inputs
        if not any([urls, repositories, documents, data_files, github_repos]):
            print("❌ No analysis targets provided. Use --urls, --repositories, --documents, --data-files, or --github-repos")
            return {"error": "No analysis targets provided"}
        
        # Run analysis
        results = await tars.analyze_project(
            web_urls=urls,
            repositories=repositories,
            documents=documents,
            data_files=data_files,
            github_repos=github_repos
        )
        
        # Save results if requested
        if output_file:
            save_results_to_file(results, output_file)
        
        return results
        
    except Exception as e:
        error_msg = f"Error in project analysis: {e}"
        print(f"❌ {error_msg}")
        return {"error": error_msg}


async def run_single_query(
    tars: TarsMain,
    query: str,
    output_file: Optional[str] = None
) -> str:
    """Run a single query."""
    try:
        print(f"\n❓ Processing query: {query}")
        
        response = await tars.process_query(query)
        
        print(f"\n🤖 Response:\n{response}")
        
        # Save response if requested
        if output_file:
            result = {
                "query": query,
                "response": response,
                "timestamp": str(asyncio.get_event_loop().time())
            }
            save_results_to_file(result, output_file)
        
        return response
        
    except Exception as e:
        error_msg = f"Error processing query: {e}"
        print(f"❌ {error_msg}")
        return error_msg


async def show_system_status(tars: TarsMain) -> Dict[str, Any]:
    """Show system status."""
    try:
        status = tars.get_system_status()
        
        print("\n📊 TARS System Status")
        print("=" * 50)
        
        # System status
        status_emoji = "✅" if status.get("system_status") == "ready" else "❌"
        print(f"{status_emoji} System Status: {status.get('system_status', 'unknown')}")
        
        # Uptime
        uptime = status.get("uptime_seconds", 0)
        hours, remainder = divmod(uptime, 3600)
        minutes, seconds = divmod(remainder, 60)
        print(f"⏱️  Uptime: {int(hours):02d}:{int(minutes):02d}:{int(seconds):02d}")
        
        # Project info
        print(f"📂 Project: {status.get('project_id', 'N/A')}")
        print(f"👤 User: {status.get('user_id', 'N/A')}")
        
        # Configuration
        config = status.get("configuration", {})
        print(f"🧠 Memory Provider: {config.get('memory_provider', 'N/A')}")
        print(f"🤖 LLM Model: {config.get('llm_model', 'N/A')}")
        
        # Performance metrics
        metrics = status.get("performance_metrics", {})
        print(f"\n📈 Performance Metrics:")
        print(f"   Total Queries: {metrics.get('total_queries', 0)}")
        print(f"   Successful Operations: {metrics.get('successful_operations', 0)}")
        print(f"   Failed Operations: {metrics.get('failed_operations', 0)}")
        
        # Success rate
        total_ops = metrics.get('successful_operations', 0) + metrics.get('failed_operations', 0)
        if total_ops > 0:
            success_rate = (metrics.get('successful_operations', 0) / total_ops) * 100
            print(f"   Success Rate: {success_rate:.1f}%")
        
        # Session health
        if "session_health" in status:
            health = status["session_health"]
            if "error" not in health:
                print(f"\n🏥 Session Health:")
                print(f"   Active Agents: {health.get('active_agents', 0)}")
                print(f"   Memory Usage: {health.get('memory_usage_mb', 0):.1f} MB")
                print(f"   Knowledge Items: {health.get('knowledge_items', 0)}")
        
        print("=" * 50)
        
        return status
        
    except Exception as e:
        error_msg = f"Error getting system status: {e}"
        print(f"❌ {error_msg}")
        return {"error": error_msg}


async def main() -> None:
    """Main CLI function."""
    args = parse_arguments()
    
    # Handle quiet mode
    verbose = args.verbose and not args.quiet
    
    try:
        # Load configuration
        config = {}
        if args.config_file:
            config = load_config_file(args.config_file)
        
        # Build configuration
        memory_config = config.get("memory_config", {})
        if args.memory_provider:
            memory_config["provider"] = args.memory_provider
        
        knowledge_config = config.get("knowledge_config", {})
        
        llm_config = config.get("llm_config", {})
        if args.llm_model:
            llm_config["model"] = args.llm_model
        
        # Initialize TARS
        tars = TarsMain(
            user_id=args.user_id,
            project_id=args.project_id,
            memory_config=memory_config if memory_config else None,
            knowledge_config=knowledge_config if knowledge_config else None,
            llm_config=llm_config if llm_config else None,
            verbose=verbose
        )
        
        # Initialize system
        if not await tars.initialize():
            print("❌ Failed to initialize TARS system")
            sys.exit(1)
        
        try:
            # Execute based on mode
            if args.interactive:
                await run_interactive_mode(tars)
                
            elif args.analyze_project:
                results = await run_project_analysis(
                    tars=tars,
                    urls=args.urls,
                    repositories=args.repositories,
                    documents=args.documents,
                    data_files=args.data_files,
                    github_repos=args.github_repos,
                    output_file=args.output_file
                )
                
                if "error" in results:
                    sys.exit(1)
                    
            elif args.query:
                response = await run_single_query(
                    tars=tars,
                    query=args.query,
                    output_file=args.output_file
                )
                
                if "error" in response.lower()[:50]:
                    sys.exit(1)
                    
            elif args.status:
                status = await show_system_status(tars)
                
                if "error" in status:
                    sys.exit(1)
                    
            else:
                # No mode selected, show help
                print("❓ No mode selected. Use --help to see available options.")
                print("\nQuick start:")
                print("  --interactive          Start interactive mode")
                print("  --analyze-project      Analyze a project")
                print("  --query \"Your query\"   Process a single query")
                print("  --status               Show system status")
                
        finally:
            # Always shutdown gracefully
            await tars.shutdown()
            
    except KeyboardInterrupt:
        print("\n\n🛑 Interrupted by user")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
