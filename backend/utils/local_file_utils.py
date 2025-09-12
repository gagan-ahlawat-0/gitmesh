"""
Local file system utilities for development mode
Allows reading repository files directly from filesystem when GitHub token is not available
"""

import os
import mimetypes
import base64
from typing import List, Dict, Any, Optional
from pathlib import Path
import structlog

logger = structlog.get_logger(__name__)

class LocalFileService:
    """Service to read repository files directly from local filesystem."""
    
    def __init__(self, repo_root: str = None):
        """Initialize with repository root path."""
        self.repo_root = repo_root or "/home/parvmittal/Documents/gitmeshfinal"
        
    def get_repository_tree(self, owner: str, repo: str, branch: str = 'main') -> List[Dict[str, Any]]:
        """Get repository tree structure from local filesystem."""
        try:
            repo_path = Path(self.repo_root) / repo
            if not repo_path.exists():
                logger.warning(f"Repository path not found: {repo_path}")
                return []
            
            tree = []
            self._build_tree(repo_path, "", tree, owner, repo)
            return tree
            
        except Exception as e:
            logger.error(f"Failed to get local repository tree: {e}")
            return []
    
    def _build_tree(self, base_path: Path, relative_path: str, tree: List[Dict[str, Any]], owner: str, repo: str):
        """Recursively build tree structure."""
        current_path = base_path / relative_path if relative_path else base_path
        
        if not current_path.exists():
            return
            
        # Skip hidden files and common ignore patterns
        ignore_patterns = {
            '.git', '__pycache__', 'node_modules', '.next', 'dist', 
            'build', '.venv', 'venv', '.env', '.DS_Store'
        }
        
        try:
            for item in current_path.iterdir():
                if item.name.startswith('.') and item.name not in {'.gitignore', '.env.example'}:
                    continue
                if item.name in ignore_patterns:
                    continue
                
                item_path = relative_path + "/" + item.name if relative_path else item.name
                
                if item.is_file():
                    tree.append({
                        "path": item_path,
                        "type": "blob",
                        "size": item.stat().st_size,
                        "mode": "100644",
                        "sha": self._calculate_sha(item),
                        "url": f"https://api.github.com/repos/{owner}/{repo}/git/blobs/{self._calculate_sha(item)}"
                    })
                elif item.is_dir():
                    tree.append({
                        "path": item_path,
                        "type": "tree",
                        "mode": "040000",
                        "sha": self._calculate_sha(item),
                        "url": f"https://api.github.com/repos/{owner}/{repo}/git/trees/{self._calculate_sha(item)}"
                    })
                    # Recursively add subdirectory contents
                    self._build_tree(base_path, item_path, tree, owner, repo)
                    
        except PermissionError:
            logger.warning(f"Permission denied accessing: {current_path}")
        except Exception as e:
            logger.error(f"Error reading directory {current_path}: {e}")
    
    def get_file_content(self, owner: str, repo: str, path: str, branch: str = 'main') -> Dict[str, Any]:
        """Get file content from local filesystem."""
        try:
            repo_path = Path(self.repo_root) / repo
            file_path = repo_path / path
            
            if not file_path.exists() or not file_path.is_file():
                raise FileNotFoundError(f"File not found: {path}")
            
            # Get file stats
            stat = file_path.stat()
            
            # Determine if file is binary
            mime_type, _ = mimetypes.guess_type(str(file_path))
            is_binary = self._is_binary_file(file_path)
            
            if is_binary:
                # For binary files, return base64 encoded content
                with open(file_path, 'rb') as f:
                    content = base64.b64encode(f.read()).decode('utf-8')
                encoding = 'base64'
            else:
                # For text files, return decoded content
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    encoding = 'utf-8'
                except UnicodeDecodeError:
                    # Fallback to base64 for problematic text files
                    with open(file_path, 'rb') as f:
                        content = base64.b64encode(f.read()).decode('utf-8')
                    encoding = 'base64'
            
            return {
                "type": "file",
                "encoding": encoding,
                "size": stat.st_size,
                "name": file_path.name,
                "path": path,
                "content": content,
                "sha": self._calculate_sha(file_path),
                "download_url": f"file://{file_path}",
                "git_url": f"file://{file_path}",
                "html_url": f"file://{file_path}",
                "_links": {
                    "self": f"file://{file_path}",
                    "git": f"file://{file_path}",
                    "html": f"file://{file_path}"
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get local file content for {path}: {e}")
            raise
    
    def _is_binary_file(self, file_path: Path) -> bool:
        """Check if file is binary."""
        try:
            # Read first 1024 bytes to check for null bytes
            with open(file_path, 'rb') as f:
                chunk = f.read(1024)
                return b'\x00' in chunk
        except:
            return True
    
    def _calculate_sha(self, file_path: Path) -> str:
        """Calculate SHA hash for file (simplified)."""
        import hashlib
        try:
            if file_path.is_file():
                with open(file_path, 'rb') as f:
                    content = f.read()
                    # Use Git-style SHA calculation
                    git_header = f"blob {len(content)}\0".encode()
                    return hashlib.sha1(git_header + content).hexdigest()
            else:
                # For directories, use a hash of the path
                return hashlib.sha1(str(file_path).encode()).hexdigest()[:40]
        except Exception as e:
            logger.warning(f"Failed to calculate SHA for {file_path}: {e}")
            # Generate a unique hash based on file path and timestamp
            import time
            return hashlib.sha1(f"{str(file_path)}-{time.time()}".encode()).hexdigest()[:40]

    def get_branches_with_trees(self, owner: str, repo: str) -> Dict[str, Any]:
        """Get branches with trees (local mode only supports main branch)."""
        tree = self.get_repository_tree(owner, repo)
        
        return {
            "branches": [
                {
                    "name": "main", 
                    "commit": {"sha": "local-main"},
                    "protected": False
                }
            ],
            "treesByBranch": {
                "main": tree  # This should be a List[GitHubTreeItem], not a dict
            },
            "summary": {
                "totalFiles": len([t for t in tree if t["type"] == "blob"]),
                "totalDirectories": len([t for t in tree if t["type"] == "tree"]),
                "branches": 1
            }
        }

# Global instance
local_file_service = LocalFileService()
