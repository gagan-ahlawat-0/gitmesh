"""
GitIngest Integration Tool for TARS v1
=====================================

Clean and simple GitIngest integr            logger.info(f"🔄 Analyzing repository: {repo_url}")
            if auth_token:
                logger.info("🔐 Using GitHub authentication token")
            else:
                logger.info("🌐 Analyzing public repository (no authentication)")
            
            # Call gitingest libraryon using the gitingest library.
Integrates with GitMesh's main authentication system via KeyManager.

Features:
- Automatic GitHub token retrieval from the main app's KeyManager
- Support for token override for specific operations
- Repository submodule support
- Clean API with convenience functions

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
from typing import Dict, Any, Optional, Tuple

try:
    from gitingest import ingest
    # We'll only use the synchronous version to avoid async conflicts
except ImportError:
    raise ImportError("gitingest library not found. Install with: pip install gitingest")

# Handle different import paths depending on how the script is run
try:
    from config.key_manager import KeyManager
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
        # If still can't import, create a mock KeyManager for testing
        class KeyManager:
            def get_github_token(self):
                return os.environ.get("GITHUB_TOKEN") or os.environ.get("GITHUB_PAT")

logger = logging.getLogger(__name__)


class GitIngestTool:
    """
    Clean GitIngest tool for analyzing repositories using the gitingest library.
    
    Features:
    - Direct integration with gitingest library
    - GitHub PAT support using the main app's authentication system
    - Support for submodules
    - Simple and clean API
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
        
        # Set environment variable if token available
        if self.github_token:
            os.environ["GITHUB_TOKEN"] = self.github_token

    def get_token(self) -> Optional[str]:
        """Get GitHub token from instance or KeyManager."""
        if self.github_token:
            return self.github_token
        return self.key_manager.get_github_token()
    
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
            "summary": None,
            "tree": None,
            "content": None,
            "error": None
        }
        
        try:
            # Use provided token, instance token, or get from KeyManager
            auth_token = token or self.get_token()
            
            logger.info(f"� Analyzing repository: {repo_url}")
            
            # Call gitingest library
            if auth_token:
                summary, tree, content = ingest(
                    repo_url, 
                    token=auth_token, 
                    include_submodules=include_submodules
                )
            else:
                summary, tree, content = ingest(
                    repo_url, 
                    include_submodules=include_submodules
                )
            
            result.update({
                "success": True,
                "summary": summary,
                "tree": tree,
                "content": content
            })
            
            logger.info(f"✅ Repository analysis completed successfully")
            
        except Exception as e:
            logger.error(f"❌ Repository analysis failed: {e}")
            result["error"] = str(e)
        
        return result
    
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
                "repo_url": repo_url
            }
        else:
            return {
                "error": result["error"],
                "repo_url": repo_url
            }


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
        auth_token = tool.get_token()
        
        if auth_token:
            summary, tree, content = ingest(repo_url, token=auth_token)
        else:
            summary, tree, content = ingest(repo_url)
        
        return summary, tree, content
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
    result = tool.analyze_repository("https://github.com/RAWx18/Beetle")
    if result["success"]:
        print(f"✅ Success!")
        print(f"📋 Summary: {result['summary'][:200]}...")
        print(f"📄 Content length: {len(result['content'])} characters")
    else:
        print(f"❌ Error: {result['error']}")
    
    # # Example with convenience function
    # print("\n🔧 Using convenience function...")
    # summary, tree, content = extract_details("https://github.com/python/cpython")
    # if summary:
    #     print(f"✅ Extracted details successfully!")
    #     print(f"📋 Summary length: {len(summary)} characters")
    #     print(f"🌳 Tree length: {len(tree)} characters") 
    #     print(f"📄 Content length: {len(content)} characters")
    # else:
    #     print("❌ Failed to extract details")