"""
GitIngest Integration Tool for TARS v1 - Fixed Version
=====================================================

Clean and simple GitIngest integration using the gitingest library.
Integrates with GitMesh's main authentication system via KeyManager.

Features:
- Automatic GitHub token retrieval from the main app's KeyManager
- Support for token override for specific operations
- Repository submodule support
- Clean API with convenience functions
- Proper async/sync handling to avoid event loop conflicts

Authentication Integration:
- Uses config.key_manager.KeyManager to get GitHub tokens stored by the main app
- Automatically handles both public and private repository access
- Falls back to public access if no authentication is available

Usage Examples:

    # Basic usage with automatic auth
    tool = GitIngestTool()
    result = tool.analyze_repository("https://github.com/username/repo")
    
    # With token override
    result = tool.analyze_repository("https://github.com/username/private-repo", 
                                   token="github_pat_...")
    
    # Include submodules
    result = tool.analyze_repository("https://github.com/username/repo-with-submodules", 
                                   include_submodules=True)
    
    # Convenience function
    summary, tree, content = extract_details("https://github.com/username/repo")
"""

import os
import logging
import asyncio
import concurrent.futures
from typing import Dict, Any, Optional, Tuple
from datetime import datetime

try:
    from gitingest import ingest
    # We'll only use the synchronous version to avoid async conflicts
except ImportError:
    raise ImportError("gitingest library not found. Install with: pip install gitingest")

# Handle different import paths depending on how the script is run
try:
    from config.key_manager import KeyManager as BaseKeyManager
    
    # Wrap the KeyManager to filter out invalid tokens
    class KeyManager:
        def __init__(self):
            self.base_manager = BaseKeyManager()
        
        def get_github_token(self):
            token = self.base_manager.get_github_token()
            # Filter out known invalid tokens
            invalid_tokens = [
                "your_dummy_github_token", 
                "your_github_token_here", 
                "placeholder", 
                "dummy",
                None
            ]
            
            if token in invalid_tokens:
                # Clear the stored invalid token
                if hasattr(self.base_manager, 'keys') and 'github_token' in self.base_manager.keys:
                    del self.base_manager.keys['github_token']
                return None
                
            # Also check for invalid token patterns
            if token and not token.startswith(("ghp_", "gho_", "ghu_", "ghs_", "ghr_", "github_pat_")):
                logger.debug(f"Filtering out invalid GitHub token pattern: {token[:10]}...")
                # Clear the stored invalid token
                if hasattr(self.base_manager, 'keys') and 'github_token' in self.base_manager.keys:
                    del self.base_manager.keys['github_token']
                return None
                
            return token
            
except ImportError:
    import sys
    import os
    # Add the backend directory to the path if running directly
    current_dir = os.path.dirname(os.path.abspath(__file__))
    backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
    if backend_dir not in sys.path:
        sys.path.insert(0, backend_dir)
    try:
        from config.key_manager import KeyManager
    except ImportError:
        # Create a safer KeyManager for testing that doesn't return invalid tokens
        class KeyManager:
            def get_github_token(self):
                token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GITHUB_PAT") or os.environ.get("GTM_GITHUB_TOKEN")
                # Filter out known invalid tokens
                if token and token in ["your_dummy_github_token", "your_github_token_here", "placeholder", "dummy"]:
                    return None
                return token

logger = logging.getLogger(__name__)


class GitIngestTool:
    """
    Clean GitIngest tool for analyzing repositories using the gitingest library.
    
    Features:
    - Direct integration with gitingest library
    - GitHub PAT support using the main app's authentication system
    - Support for submodules
    - Simple and clean API
    - Proper sync/async handling
    """
    
    def __init__(self, github_token: Optional[str] = None):
        """
        Initialize GitIngest tool.
        
        Args:
            github_token: GitHub Personal Access Token (optional, uses KeyManager if not provided)
        """
        self.key_manager = KeyManager()
        self.github_token = github_token
        
        # Get token from main app's authentication system if not provided
        if not self.github_token:
            self.github_token = self.key_manager.get_github_token()
        
        # Clean up any placeholder environment tokens that might confuse gitingest
        invalid_env_tokens = ["your_dummy_github_token", "your_github_token_here", "placeholder", "dummy"]
        for env_var in ["GITHUB_TOKEN", "GTM_GITHUB_TOKEN", "GITHUB_PAT"]:
            if env_var in os.environ and os.environ[env_var] in invalid_env_tokens:
                del os.environ[env_var]
                logger.debug(f"Removed invalid {env_var} from environment")
        
        # Only set environment variable if we have a valid token
        if self.github_token and self._is_valid_token(self.github_token):
            os.environ["GITHUB_TOKEN"] = self.github_token

    def _is_valid_token(self, token: str) -> bool:
        """Check if token is valid (not a placeholder)."""
        if not token or not token.strip():
            return False
        if len(token) < 10:
            return False
        if token.startswith("your_") or token in ["your_github_token_here", "placeholder", "dummy"]:
            return False
        # Check for GitHub token patterns
        if not (token.startswith(("ghp_", "gho_", "ghu_", "ghs_", "ghr_", "github_pat_"))):
            return False
        return True
    
    def get_token(self) -> Optional[str]:
        """Get GitHub token from instance or KeyManager."""
        token = self.github_token or self.key_manager.get_github_token()
        
        if token:
            # Debug log to see what token we're getting
            logger.debug(f"Token received from KeyManager: {token[:10] if len(token) > 10 else token}... (length: {len(token)})")
            
            if not self._is_valid_token(token):
                logger.debug(f"Invalid GitHub token format detected, filtering out")
                return None
        else:
            logger.debug("No token available from KeyManager or instance")
            
        return token
    
    def analyze_repository(
        self, 
        repo_url: str, 
        include_submodules: bool = False,
        token: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Analyze a repository using GitIngest library.
        
        Args:
            repo_url: Repository URL to analyze
            include_submodules: Whether to include repository submodules
            token: GitHub token (overrides instance token and KeyManager)
            
        Returns:
            Dictionary containing analysis results
        """
        result = {
            "success": False,
            "repo_url": repo_url,
            "summary": "",
            "tree": "",
            "content": "",
            "error": None,
            "metadata": {
                "repo_url": repo_url,
                "timestamp": datetime.now().isoformat(),
                "include_submodules": include_submodules
            }
        }
        
        try:
            # Use provided token, instance token, or get from KeyManager
            auth_token = token or self.get_token()
            
            logger.info(f"🔄 Analyzing repository: {repo_url}")
            
            # Check if we're in an async context and need to avoid asyncio.run()
            def _run_ingest():
                """Run gitingest in a safe context."""
                # Double-check token validity before using it
                valid_token = auth_token if auth_token and self._is_valid_token(auth_token) else None
                
                # Temporarily clear environment variables to prevent gitingest from using invalid tokens
                env_backup = {}
                env_vars_to_clear = ["GITHUB_TOKEN", "GTM_GITHUB_TOKEN", "GITHUB_PAT"]
                
                for env_var in env_vars_to_clear:
                    if env_var in os.environ:
                        env_backup[env_var] = os.environ[env_var]
                        del os.environ[env_var]
                
                try:
                    if valid_token:
                        logger.info("🔐 Using GitHub authentication token")
                        # Set only the valid token
                        os.environ["GITHUB_TOKEN"] = valid_token
                        try:
                            return ingest(
                                repo_url, 
                                token=valid_token, 
                                include_submodules=include_submodules
                            )
                        except Exception as token_error:
                            # If token fails, try without authentication
                            logger.warning(f"Authentication failed, trying without token: {token_error}")
                            if "GITHUB_TOKEN" in os.environ:
                                del os.environ["GITHUB_TOKEN"]
                            return ingest(
                                repo_url, 
                                include_submodules=include_submodules
                            )
                    else:
                        if auth_token:
                            logger.info(f"🌐 Invalid token format detected, using public access")
                        else:
                            logger.info("🌐 Analyzing public repository (no authentication)")
                        return ingest(
                            repo_url, 
                            include_submodules=include_submodules
                        )
                finally:
                    # Restore environment variables
                    for env_var in env_vars_to_clear:
                        if env_var in os.environ:
                            del os.environ[env_var]
                    for env_var, value in env_backup.items():
                        os.environ[env_var] = value
            
            # Check if we're in an async event loop
            try:
                # If we're in an async context, run in thread pool to avoid conflicts
                loop = asyncio.get_running_loop()
                if loop.is_running():
                    # We're in an async context, use thread pool
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(_run_ingest)
                        summary, tree, content = future.result(timeout=300)  # 5 min timeout
                else:
                    # No running loop, safe to call directly
                    summary, tree, content = _run_ingest()
            except RuntimeError:
                # No event loop, safe to call directly
                summary, tree, content = _run_ingest()
            
            # Ensure we have strings, not None
            summary = summary or ""
            tree = tree or ""
            content = content or ""
            
            result.update({
                "success": True,
                "summary": summary,
                "tree": tree,
                "content": self._format_content_by_file_types(content),  # Enhanced content formatting
                "metadata": {
                    "repo_url": repo_url,
                    "timestamp": datetime.now().isoformat(),
                    "include_submodules": include_submodules,
                    "summary_length": len(summary),
                    "tree_length": len(tree),
                    "content_length": len(content),
                    "has_auth": bool(auth_token and auth_token.strip()),
                    "file_types_detected": self._detect_file_types(content)
                }
            })
            
            logger.info(f"✅ Repository analysis completed successfully")
            
        except Exception as e:
            logger.error(f"❌ Repository analysis failed: {e}")
            result["error"] = str(e)
        
        return result
    
    async def analyze_repository_async(
        self,
        repo_url: str,
        include_submodules: bool = False,
        token: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Async wrapper for analyze_repository to handle async contexts properly.
        
        Args:
            repo_url: Repository URL to analyze
            include_submodules: Whether to include repository submodules
            token: GitHub token (overrides instance token and KeyManager)
            
        Returns:
            Dictionary containing analysis results
        """
        # Run the sync version in a thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, 
            self.analyze_repository,
            repo_url,
            include_submodules,
            token
        )
    
    def get_summary(self, repo_url: str, **kwargs) -> Optional[str]:
        """Get repository summary."""
        result = self.analyze_repository(repo_url, **kwargs)
        return result.get("summary") if result["success"] else None
    
    def get_tree(self, repo_url: str, **kwargs) -> Optional[str]:
        """Get repository tree structure."""
        result = self.analyze_repository(repo_url, **kwargs)
        return result.get("tree") if result["success"] else None
    
    def get_content(self, repo_url: str, **kwargs) -> Optional[str]:
        """Get repository content."""
        result = self.analyze_repository(repo_url, **kwargs)
        return result.get("content") if result["success"] else None
    
    def get_repository_metadata(self, repo_url: str, **kwargs) -> Dict[str, Any]:
        """
        Get repository metadata without full content analysis.
        
        Args:
            repo_url: Repository URL
            **kwargs: Additional parameters
            
        Returns:
            Dictionary with repository metadata
        """
        try:
            # Try to get basic info using the analyze method but only metadata
            result = self.analyze_repository(repo_url, **kwargs)
            
            if result["success"]:
                return {
                    "accessible": True,
                    "info": {
                        "repo_url": repo_url,
                        "updated_at": datetime.now().isoformat(),
                        "size": len(result.get("content", "")),
                        "has_content": bool(result.get("content"))
                    },
                    "metadata": result.get("metadata", {})
                }
            else:
                return {
                    "accessible": False,
                    "error": result.get("error", "Unknown error"),
                    "info": {"repo_url": repo_url}
                }
                
        except Exception as e:
            logger.warning(f"Failed to get repository metadata for {repo_url}: {e}")
            return {
                "accessible": False,
                "error": str(e),
                "info": {"repo_url": repo_url}
            }
    
    def extract_details(self, repo_url: str, **kwargs) -> Dict[str, Any]:
        """
        Extract repository details in a simple format.
        
        Args:
            repo_url: Repository URL
            **kwargs: Additional parameters for analyze_repository
            
        Returns:
            Dictionary with extracted details
        """
        result = self.analyze_repository(repo_url, **kwargs)
        
        if result["success"]:
            return {
                "summary": result["summary"],
                "tree": result["tree"], 
                "content": result["content"],
                "repo_url": repo_url,
                "metadata": result.get("metadata", {})
            }
        else:
            return {
                "error": result["error"],
                "repo_url": repo_url
            }
    
    def _detect_file_types(self, content: str) -> Dict[str, int]:
        """Detect and count different file types in the content."""
        file_types = {}
        import re
        
        # Look for file headers in the format "FILE: filename.ext"
        file_headers = re.findall(r'FILE: ([^\n]+)', content)
        
        for file_header in file_headers:
            # Extract extension
            if '.' in file_header:
                ext = file_header.split('.')[-1].lower()
                file_types[ext] = file_types.get(ext, 0) + 1
            else:
                file_types['no_extension'] = file_types.get('no_extension', 0) + 1
        
        return file_types
    
    def _format_content_by_file_types(self, content: str) -> str:
        """Format content with enhanced context for different file types."""
        if not content:
            return content
        
        # Add file type context header
        file_types = self._detect_file_types(content)
        
        if file_types:
            context_header = "\n=== REPOSITORY CONTENT ANALYSIS ===\n"
            context_header += "This repository contains the following file types:\n"
            
            # Group by programming vs documentation files
            code_files = {}
            doc_files = {}
            config_files = {}
            
            for ext, count in file_types.items():
                if ext in ['py', 'js', 'ts', 'jsx', 'tsx', 'java', 'cpp', 'c', 'h', 'cs', 'php', 'rb', 'go', 'rs', 'swift']:
                    code_files[ext] = count
                elif ext in ['md', 'txt', 'rst', 'doc', 'docx']:
                    doc_files[ext] = count
                elif ext in ['json', 'yaml', 'yml', 'toml', 'ini', 'cfg', 'conf']:
                    config_files[ext] = count
            
            if code_files:
                context_header += f"• Programming Files: {', '.join([f'{count} .{ext}' for ext, count in code_files.items()])}\n"
            if doc_files:
                context_header += f"• Documentation Files: {', '.join([f'{count} .{ext}' for ext, count in doc_files.items()])}\n"
            if config_files:
                context_header += f"• Configuration Files: {', '.join([f'{count} .{ext}' for ext, count in config_files.items()])}\n"
            
            context_header += "\n**ANALYSIS INSTRUCTIONS:**\n"
            if code_files:
                context_header += "- For programming files: Focus on functions, classes, imports, and language-specific patterns\n"
            if doc_files:
                context_header += "- For documentation: Focus on structure, content organization, and technical explanations\n"
            if config_files:
                context_header += "- For configuration: Focus on settings, dependencies, and project setup\n"
            
            context_header += "- Always reference specific files and line ranges when discussing code\n"
            context_header += "- Never hallucinate functions or classes that don't exist in the provided content\n"
            context_header += "=====================================\n\n"
            
            return context_header + content
        
        return content


# Convenience functions
def analyze_repository(
    repo_url: str, 
    github_token: Optional[str] = None,
    include_submodules: bool = False
) -> Dict[str, Any]:
    """Analyze a repository using GitIngest with automatic auth integration."""
    tool = GitIngestTool(github_token=github_token)
    return tool.analyze_repository(repo_url, include_submodules=include_submodules)


def extract_details(repo_url: str, github_token: Optional[str] = None) -> Tuple[str, str, str]:
    """
    Extract repository details using gitingest library with automatic auth integration.
    
    Args:
        repo_url: Repository URL
        github_token: GitHub token override (uses KeyManager if not provided)
        
    Returns:
        Tuple of (summary, tree, content)
    """
    try:
        tool = GitIngestTool(github_token=github_token)
        result = tool.analyze_repository(repo_url)
        
        if result["success"]:
            return result["summary"], result["tree"], result["content"]
        else:
            logger.error(f"Failed to extract repository details: {result['error']}")
            return "", "", ""
            
    except Exception as e:
        logger.error(f"Failed to extract repository details: {e}")
        return "", "", ""


if __name__ == "__main__":
    # Example usage with automatic auth integration
    print("🚀 GitIngest Tool - Integrated with GitMesh Authentication")
    
    # Tool automatically uses KeyManager for authentication
    tool = GitIngestTool()
    
    # Analyze a public repository
    print("\n📄 Analyzing public repository...")
    result = tool.analyze_repository("https://github.com/octocat/Hello-World")
    if result["success"]:
        print(f"✅ Success!")
        print(f"📋 Summary: {result['summary'][:200]}...")
        print(f"📄 Content length: {len(result['content'])} characters")
    else:
        print(f"❌ Error: {result['error']}")
    
    # Example with convenience function
    print("\n🔧 Using convenience function...")
    summary, tree, content = extract_details("https://github.com/octocat/Hello-World")
    if summary:
        print(f"✅ Extracted details successfully!")
        print(f"📋 Summary length: {len(summary)} characters")
        print(f"🌳 Tree length: {len(tree)} characters") 
        print(f"📄 Content length: {len(content)} characters")
    else:
        print("❌ Failed to extract details")
