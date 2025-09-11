"""
GitIngest Integration Tool for TARS v1
=====================================

Production-ready GitIngest integration that leverages the existing AI framework
with proper GitHub PAT handling and repository analysis.
"""

import os
import subprocess
import tempfile
import shutil
import logging
import requests
from pathlib import Path
from typing import Dict, Any, Optional, List
from urllib.parse import urlparse
import json

# Import from the AI framework
from ai.agent.context_agent import ContextAgent

logger = logging.getLogger(__name__)


class GitIngestTool:
    """
    Production-ready GitIngest tool for analyzing repositories.
    
    Features:
    - Automatic GitHub PAT handling for private repos
    - Integration with existing AI framework context agent
    - Proper error handling and logging
    - Support for both local and remote repositories
    - Memory-efficient processing
    """
    
    def __init__(self, github_pat: Optional[str] = None, verbose: bool = True):
        """
        Initialize GitIngest tool.
        
        Args:
            github_pat: GitHub Personal Access Token (optional, can use environment variable)
            verbose: Enable verbose logging
        """
        self.github_pat = github_pat or os.getenv("GITHUB_PAT") or os.getenv("GITHUB_TOKEN")
        self.verbose = verbose
        
        # Check if gitingest is available
        self._check_gitingest_availability()
        
        if self.verbose:
            logging.basicConfig(level=logging.INFO)
    
    def _check_gitingest_availability(self) -> bool:
        """Check if gitingest is available."""
        try:
            result = subprocess.run(
                ["gitingest", "--help"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                logger.info("✅ GitIngest is available")
                return True
            else:
                logger.warning("⚠️ GitIngest command failed")
                return False
        except (subprocess.TimeoutExpired, FileNotFoundError):
            logger.warning("⚠️ GitIngest not found. Install with: pip install gitingest")
            return False
        except Exception as e:
            logger.error(f"⚠️ Error checking GitIngest: {e}")
            return False
    
    def _is_github_url(self, url: str) -> bool:
        """Check if URL is a GitHub repository."""
        parsed = urlparse(url)
        return parsed.hostname in ["github.com", "www.github.com"]
    
    def _is_private_repo(self, repo_url: str) -> bool:
        """
        Check if a GitHub repository is private by making a simple API call.
        
        Args:
            repo_url: GitHub repository URL
            
        Returns:
            bool: True if private, False if public, None if unknown
        """
        try:
            # Extract owner/repo from URL
            parsed = urlparse(repo_url)
            path_parts = parsed.path.strip('/').split('/')
            if len(path_parts) >= 2:
                owner, repo = path_parts[0], path_parts[1]
                if repo.endswith('.git'):
                    repo = repo[:-4]
                
                # Check repository visibility via GitHub API
                api_url = f"https://api.github.com/repos/{owner}/{repo}"
                headers = {}
                if self.github_pat:
                    headers["Authorization"] = f"token {self.github_pat}"
                
                response = requests.get(api_url, headers=headers, timeout=10)
                
                if response.status_code == 200:
                    repo_data = response.json()
                    return repo_data.get("private", False)
                elif response.status_code == 404:
                    # Could be private or non-existent
                    return True if self.github_pat else None
                    
        except Exception as e:
            logger.warning(f"Could not determine repository visibility: {e}")
        
        return None
    
    def _clone_repository(self, repo_url: str, target_dir: str) -> bool:
        """
        Clone a repository with proper PAT handling.
        
        Args:
            repo_url: Repository URL to clone
            target_dir: Directory to clone into
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Build clone command
            clone_cmd = ["git", "clone"]
            
            # Handle authentication for private repos
            if self._is_github_url(repo_url) and self.github_pat:
                is_private = self._is_private_repo(repo_url)
                if is_private is True:
                    logger.info("🔐 Using GitHub PAT for private repository")
                elif is_private is None:
                    logger.info("🔐 Using GitHub PAT (repository visibility unknown)")
                
                # Inject PAT into URL
                parsed = urlparse(repo_url)
                auth_url = f"https://{self.github_pat}@{parsed.hostname}{parsed.path}"
                clone_cmd.extend([auth_url, target_dir])
            else:
                clone_cmd.extend([repo_url, target_dir])
            
            # Execute clone
            if self.verbose:
                logger.info(f"🔄 Cloning repository: {repo_url}")
            
            result = subprocess.run(
                clone_cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minutes timeout
            )
            
            if result.returncode == 0:
                logger.info("✅ Repository cloned successfully")
                return True
            else:
                logger.error(f"❌ Clone failed: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error("❌ Clone timeout - repository too large or slow connection")
            return False
        except Exception as e:
            logger.error(f"❌ Clone error: {e}")
            return False
    
    def _run_gitingest_analysis(self, project_path: str) -> Optional[str]:
        """
        Run gitingest analysis using the existing AI framework method.
        
        Args:
            project_path: Path to the project to analyze
            
        Returns:
            GitIngest analysis content or None if failed
        """
        try:
            # Create temporary context agent to use existing gitingest functionality
            context_agent = ContextAgent(project_path=project_path, auto_analyze=False)
            
            # Use the existing _run_gitingest_analysis method
            analysis_content = context_agent._run_gitingest_analysis(project_path)
            
            if analysis_content:
                logger.info("✅ GitIngest analysis completed")
                return analysis_content
            else:
                logger.warning("⚠️ GitIngest analysis returned no content")
                return None
                
        except Exception as e:
            logger.error(f"❌ GitIngest analysis error: {e}")
            return None
    
    def analyze_repository(self, repo_url: str, cleanup: bool = True) -> Dict[str, Any]:
        """
        Analyze a repository using GitIngest.
        
        Args:
            repo_url: Repository URL (local path or remote URL)
            cleanup: Whether to cleanup temporary directories
            
        Returns:
            Dictionary containing analysis results
        """
        temp_dir = None
        analysis_result = {
            "success": False,
            "repo_url": repo_url,
            "content": None,
            "error": None,
            "metadata": {}
        }
        
        try:
            # Determine if it's a local path or remote URL
            if os.path.exists(repo_url):
                # Local repository
                project_path = repo_url
                analysis_result["metadata"]["source_type"] = "local"
                logger.info(f"📁 Analyzing local repository: {repo_url}")
            else:
                # Remote repository - need to clone
                temp_dir = tempfile.mkdtemp(prefix="tars_gitingest_")
                project_path = os.path.join(temp_dir, "repo")
                
                analysis_result["metadata"]["source_type"] = "remote"
                analysis_result["metadata"]["temp_dir"] = temp_dir
                
                # Clone the repository
                if not self._clone_repository(repo_url, project_path):
                    analysis_result["error"] = "Failed to clone repository"
                    return analysis_result
            
            # Run GitIngest analysis
            content = self._run_gitingest_analysis(project_path)
            
            if content:
                analysis_result["success"] = True
                analysis_result["content"] = content
                analysis_result["metadata"]["content_length"] = len(content)
                analysis_result["metadata"]["project_path"] = project_path
                
                # Extract some basic metadata from content
                lines = content.split('\n')
                analysis_result["metadata"]["line_count"] = len(lines)
                
                logger.info(f"✅ Repository analysis completed: {len(content)} characters")
            else:
                analysis_result["error"] = "GitIngest analysis produced no content"
                
        except Exception as e:
            logger.error(f"❌ Repository analysis failed: {e}")
            analysis_result["error"] = str(e)
        
        finally:
            # Cleanup temporary directory if requested
            if cleanup and temp_dir and os.path.exists(temp_dir):
                try:
                    shutil.rmtree(temp_dir)
                    logger.info(f"🗑️ Cleaned up temporary directory: {temp_dir}")
                except Exception as e:
                    logger.warning(f"⚠️ Failed to cleanup temp directory: {e}")
        
        return analysis_result
    
    def analyze_multiple_repositories(
        self, 
        repo_urls: List[str], 
        max_concurrent: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Analyze multiple repositories concurrently.
        
        Args:
            repo_urls: List of repository URLs
            max_concurrent: Maximum concurrent analyses
            
        Returns:
            List of analysis results
        """
        import concurrent.futures
        
        results = []
        
        # Process repositories in batches to avoid overwhelming the system
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_concurrent) as executor:
            # Submit all analysis tasks
            future_to_url = {
                executor.submit(self.analyze_repository, url): url 
                for url in repo_urls
            }
            
            # Collect results as they complete
            for future in concurrent.futures.as_completed(future_to_url):
                url = future_to_url[future]
                try:
                    result = future.result(timeout=600)  # 10 minute timeout per repo
                    results.append(result)
                    
                    if result["success"]:
                        logger.info(f"✅ Completed analysis: {url}")
                    else:
                        logger.warning(f"⚠️ Failed analysis: {url} - {result.get('error', 'Unknown error')}")
                        
                except concurrent.futures.TimeoutError:
                    logger.error(f"❌ Analysis timeout: {url}")
                    results.append({
                        "success": False,
                        "repo_url": url,
                        "error": "Analysis timeout",
                        "content": None,
                        "metadata": {}
                    })
                except Exception as e:
                    logger.error(f"❌ Analysis exception: {url} - {e}")
                    results.append({
                        "success": False,
                        "repo_url": url,
                        "error": str(e),
                        "content": None,
                        "metadata": {}
                    })
        
        logger.info(f"📊 Completed batch analysis: {len([r for r in results if r['success']])}/{len(results)} successful")
        return results
    
    def get_repository_metadata(self, repo_url: str) -> Dict[str, Any]:
        """
        Get metadata about a GitHub repository without cloning.
        
        Args:
            repo_url: GitHub repository URL
            
        Returns:
            Repository metadata dictionary
        """
        metadata = {
            "url": repo_url,
            "accessible": False,
            "private": None,
            "info": {}
        }
        
        try:
            if not self._is_github_url(repo_url):
                metadata["error"] = "Not a GitHub URL"
                return metadata
            
            # Extract owner/repo from URL
            parsed = urlparse(repo_url)
            path_parts = parsed.path.strip('/').split('/')
            if len(path_parts) >= 2:
                owner, repo = path_parts[0], path_parts[1]
                if repo.endswith('.git'):
                    repo = repo[:-4]
                
                # Get repository info via GitHub API
                api_url = f"https://api.github.com/repos/{owner}/{repo}"
                headers = {}
                if self.github_pat:
                    headers["Authorization"] = f"token {self.github_pat}"
                
                response = requests.get(api_url, headers=headers, timeout=10)
                
                if response.status_code == 200:
                    repo_data = response.json()
                    metadata["accessible"] = True
                    metadata["private"] = repo_data.get("private", False)
                    metadata["info"] = {
                        "name": repo_data.get("name"),
                        "full_name": repo_data.get("full_name"),
                        "description": repo_data.get("description"),
                        "language": repo_data.get("language"),
                        "size": repo_data.get("size"),
                        "stars": repo_data.get("stargazers_count"),
                        "forks": repo_data.get("forks_count"),
                        "created_at": repo_data.get("created_at"),
                        "updated_at": repo_data.get("updated_at"),
                        "default_branch": repo_data.get("default_branch")
                    }
                elif response.status_code == 404:
                    metadata["error"] = "Repository not found or private"
                else:
                    metadata["error"] = f"GitHub API error: {response.status_code}"
                    
        except Exception as e:
            metadata["error"] = str(e)
        
        return metadata


# Convenience functions for backward compatibility
def analyze_repository(repo_url: str, github_pat: Optional[str] = None) -> Dict[str, Any]:
    """Analyze a single repository using GitIngest."""
    tool = GitIngestTool(github_pat=github_pat)
    return tool.analyze_repository(repo_url)


def analyze_multiple_repositories(
    repo_urls: List[str], 
    github_pat: Optional[str] = None,
    max_concurrent: int = 3
) -> List[Dict[str, Any]]:
    """Analyze multiple repositories using GitIngest."""
    tool = GitIngestTool(github_pat=github_pat)
    return tool.analyze_multiple_repositories(repo_urls, max_concurrent)


def get_repository_metadata(repo_url: str, github_pat: Optional[str] = None) -> Dict[str, Any]:
    """Get repository metadata without cloning."""
    tool = GitIngestTool(github_pat=github_pat)
    return tool.get_repository_metadata(repo_url)


if __name__ == "__main__":
    # Example usage
    tool = GitIngestTool()
    
    # Analyze a public repository
    result = tool.analyze_repository("https://github.com/microsoft/vscode")
    print(f"Analysis result: {result['success']}")
    if result['success']:
        print(f"Content length: {len(result['content'])} characters")
