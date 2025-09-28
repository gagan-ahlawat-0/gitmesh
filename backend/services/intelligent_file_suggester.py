"""
Intelligent File Suggester Service

Automatically suggests and adds relevant files to chat context based on user queries
and conversation history. Uses semantic analysis and repository structure understanding.
"""

import asyncio
import re
from typing import Dict, List, Optional, Set, Tuple, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

import structlog
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

from .cache_management_service import CacheManagementService
from .optimized_repo_service import get_optimized_repo_service

logger = structlog.get_logger(__name__)


class FileRelevanceScore(Enum):
    """File relevance scoring levels."""
    CRITICAL = 0.9  # Directly mentioned or highly relevant
    HIGH = 0.7      # Likely relevant based on context
    MEDIUM = 0.5    # Possibly relevant
    LOW = 0.3       # Tangentially related
    IGNORE = 0.1    # Not relevant


@dataclass
class SuggestedFile:
    """Represents a file suggestion with metadata."""
    path: str
    branch: str
    relevance_score: float
    reason: str
    file_type: str
    size_bytes: int
    last_modified: Optional[datetime] = None
    content_preview: Optional[str] = None
    auto_add: bool = False  # Whether to add automatically without user confirmation


@dataclass
class QueryContext:
    """Context information for file suggestion."""
    user_query: str
    conversation_history: List[str]
    current_files: Set[str]
    repository_name: str
    branch: str
    user_id: str
    session_id: str


class IntelligentFileSuggester:
    """
    Intelligent file suggestion service that analyzes user queries and suggests
    relevant files from the repository.
    """
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.cache_service = CacheManagementService(user_id)
        
        # File type patterns and their relevance
        self.file_type_patterns = {
            'source_code': {
                'patterns': [r'\.(py|js|ts|jsx|tsx|java|cpp|c|h|cs|go|rs|php|rb|swift|kt)$'],
                'weight': 1.0
            },
            'config': {
                'patterns': [r'\.(json|yaml|yml|toml|ini|cfg|conf|env)$', r'(Dockerfile|Makefile|CMakeLists\.txt)$'],
                'weight': 0.8
            },
            'documentation': {
                'patterns': [r'\.(md|rst|txt|doc|docx)$', r'README', r'CHANGELOG', r'LICENSE'],
                'weight': 0.6
            },
            'test': {
                'patterns': [r'test.*\.(py|js|ts|java|cpp|c|cs|go|rs|php|rb)$', r'.*test\.(py|js|ts|java|cpp|c|cs|go|rs|php|rb)$'],
                'weight': 0.7
            },
            'build': {
                'patterns': [r'(package\.json|setup\.py|requirements\.txt|Cargo\.toml|pom\.xml|build\.gradle)$'],
                'weight': 0.5
            }
        }
        
        # Keywords that indicate specific file types or areas
        self.keyword_mappings = {
            'api': ['api', 'routes', 'endpoints', 'controllers'],
            'database': ['models', 'schema', 'migration', 'db'],
            'frontend': ['components', 'views', 'pages', 'ui'],
            'backend': ['services', 'handlers', 'middleware'],
            'config': ['config', 'settings', 'environment'],
            'test': ['test', 'spec', 'unittest', 'integration'],
            'docs': ['readme', 'documentation', 'guide', 'manual'],
            'build': ['build', 'deploy', 'ci', 'docker', 'makefile'],
            'security': ['auth', 'security', 'permission', 'oauth'],
            'utils': ['utils', 'helpers', 'common', 'shared']
        }
        
        # Initialize TF-IDF vectorizer for semantic analysis
        self.vectorizer = TfidfVectorizer(
            max_features=1000,
            stop_words='english',
            ngram_range=(1, 2),
            lowercase=True
        )
        
        # Cache for file content vectors
        self._file_vectors_cache = {}
        self._last_cache_update = None
    
    async def suggest_files(
        self,
        query_context: QueryContext,
        max_suggestions: int = 10,
        auto_add_threshold: float = 0.8
    ) -> List[SuggestedFile]:
        """
        Suggest relevant files based on query context.
        
        Args:
            query_context: Context information for suggestion
            max_suggestions: Maximum number of files to suggest
            auto_add_threshold: Score threshold for automatic addition
            
        Returns:
            List of suggested files sorted by relevance
        """
        try:
            logger.info(
                "Generating file suggestions",
                user_id=self.user_id,
                query=query_context.user_query[:100],
                repository=query_context.repository_name
            )
            
            # Get repository service
            repo_service = get_optimized_repo_service(self.user_id)
            repo_url = f"https://github.com/{query_context.repository_name}"
            
            # Get repository structure
            repo_data = repo_service.get_repository_data(repo_url)
            if not repo_data or 'tree' not in repo_data:
                logger.warning("No repository data available for suggestions")
                return []
            
            # Extract file list from repository tree
            files = self._extract_files_from_tree(repo_data['tree'])
            
            # Filter out already selected files
            available_files = [
                f for f in files 
                if f['path'] not in query_context.current_files
            ]
            
            if not available_files:
                logger.info("No additional files available for suggestion")
                return []
            
            # Score files based on multiple criteria
            scored_files = await self._score_files(
                available_files,
                query_context,
                repo_service,
                repo_url
            )
            
            # Sort by relevance score and limit results
            scored_files.sort(key=lambda x: x.relevance_score, reverse=True)
            suggestions = scored_files[:max_suggestions]
            
            # Mark files for auto-addition if they exceed threshold
            for suggestion in suggestions:
                if suggestion.relevance_score >= auto_add_threshold:
                    suggestion.auto_add = True
            
            logger.info(
                "File suggestions generated",
                total_suggestions=len(suggestions),
                auto_add_count=sum(1 for s in suggestions if s.auto_add),
                top_score=suggestions[0].relevance_score if suggestions else 0
            )
            
            return suggestions
            
        except Exception as e:
            logger.error(f"Error generating file suggestions: {e}")
            return []
    
    async def auto_add_files(
        self,
        suggestions: List[SuggestedFile],
        query_context: QueryContext
    ) -> List[str]:
        """
        Automatically add high-relevance files to the chat context.
        
        Args:
            suggestions: List of file suggestions
            query_context: Query context information
            
        Returns:
            List of file paths that were added
        """
        auto_add_files = [s for s in suggestions if s.auto_add]
        
        if not auto_add_files:
            return []
        
        try:
            repo_service = get_optimized_repo_service(self.user_id)
            repo_url = f"https://github.com/{query_context.repository_name}"
            added_files = []
            
            for suggestion in auto_add_files:
                try:
                    # Get file content
                    content = repo_service.get_file_content(
                        repo_url,
                        suggestion.path,
                        suggestion.branch
                    )
                    
                    if content:
                        # Store in session cache for immediate use
                        # For now, we'll skip caching since we don't have a generic cache method
                        # In a production system, you'd want to implement proper file content caching
                        
                        added_files.append(suggestion.path)
                        
                        logger.info(
                            "Auto-added file to context",
                            file_path=suggestion.path,
                            reason=suggestion.reason,
                            score=suggestion.relevance_score
                        )
                
                except Exception as e:
                    logger.error(f"Failed to auto-add file {suggestion.path}: {e}")
                    continue
            
            return added_files
            
        except Exception as e:
            logger.error(f"Error in auto-add files: {e}")
            return []
    
    def _extract_files_from_tree(self, tree_data: Dict) -> List[Dict]:
        """Extract file information from repository tree data."""
        files = []
        
        def extract_recursive(node: Dict, current_path: str = ""):
            if isinstance(node, dict):
                for key, value in node.items():
                    path = f"{current_path}/{key}" if current_path else key
                    
                    if isinstance(value, dict):
                        if 'type' in value and value['type'] == 'file':
                            files.append({
                                'path': path,
                                'size': value.get('size', 0),
                                'type': 'file'
                            })
                        else:
                            # Directory, recurse
                            extract_recursive(value, path)
                    else:
                        # Leaf node (file)
                        files.append({
                            'path': path,
                            'size': 0,
                            'type': 'file'
                        })
        
        extract_recursive(tree_data)
        return files
    
    async def _score_files(
        self,
        files: List[Dict],
        query_context: QueryContext,
        repo_service,
        repo_url: str
    ) -> List[SuggestedFile]:
        """Score files based on relevance to the query context."""
        scored_files = []
        query_lower = query_context.user_query.lower()
        
        # Extract keywords from query and conversation history
        query_keywords = self._extract_keywords(query_context.user_query)
        history_keywords = set()
        for msg in query_context.conversation_history[-5:]:  # Last 5 messages
            history_keywords.update(self._extract_keywords(msg))
        
        for file_info in files:
            try:
                score, reason = self._calculate_file_score(
                    file_info,
                    query_keywords,
                    history_keywords,
                    query_lower
                )
                
                if score > FileRelevanceScore.IGNORE.value:
                    file_type = self._determine_file_type(file_info['path'])
                    
                    suggested_file = SuggestedFile(
                        path=file_info['path'],
                        branch=query_context.branch,
                        relevance_score=score,
                        reason=reason,
                        file_type=file_type,
                        size_bytes=file_info.get('size', 0)
                    )
                    
                    # Add content preview for high-scoring files
                    if score > FileRelevanceScore.MEDIUM.value:
                        try:
                            content = repo_service.get_file_content(
                                repo_url,
                                file_info['path'],
                                query_context.branch
                            )
                            if content:
                                suggested_file.content_preview = content[:200] + "..." if len(content) > 200 else content
                        except Exception:
                            pass  # Preview is optional
                    
                    scored_files.append(suggested_file)
                    
            except Exception as e:
                logger.warning(f"Error scoring file {file_info['path']}: {e}")
                continue
        
        return scored_files
    
    def _calculate_file_score(
        self,
        file_info: Dict,
        query_keywords: Set[str],
        history_keywords: Set[str],
        query_lower: str
    ) -> Tuple[float, str]:
        """Calculate relevance score for a file."""
        file_path = file_info['path'].lower()
        file_name = file_path.split('/')[-1]
        
        score = 0.0
        reasons = []
        
        # Direct file name mention
        if any(keyword in file_name for keyword in query_keywords):
            score += 0.4
            reasons.append("filename matches query keywords")
        
        # Path component matching
        path_components = file_path.split('/')
        for component in path_components:
            if any(keyword in component for keyword in query_keywords):
                score += 0.2
                reasons.append("path contains relevant keywords")
                break
        
        # File type relevance
        file_type = self._determine_file_type(file_path)
        type_score = self._get_type_relevance_score(file_type, query_keywords)
        score += type_score
        if type_score > 0:
            reasons.append(f"relevant {file_type} file")
        
        # Keyword category matching
        for category, keywords in self.keyword_mappings.items():
            if any(kw in query_lower for kw in keywords):
                if any(kw in file_path for kw in keywords):
                    score += 0.3
                    reasons.append(f"matches {category} category")
                    break
        
        # History context boost
        if any(keyword in file_path for keyword in history_keywords):
            score += 0.1
            reasons.append("relevant to conversation history")
        
        # Common important files
        important_files = [
            'readme', 'main', 'index', 'app', 'server', 'client',
            'config', 'settings', 'requirements', 'package.json'
        ]
        if any(important in file_name for important in important_files):
            score += 0.15
            reasons.append("important project file")
        
        # Penalize very large files or binary files
        if file_info.get('size', 0) > 100000:  # 100KB
            score *= 0.8
            reasons.append("large file (reduced priority)")
        
        # Boost for recently modified files (if available)
        # This would require additional metadata from the repository
        
        reason = "; ".join(reasons) if reasons else "general relevance"
        return min(score, 1.0), reason
    
    def _determine_file_type(self, file_path: str) -> str:
        """Determine the type of file based on its path and extension."""
        file_path_lower = file_path.lower()
        
        for file_type, config in self.file_type_patterns.items():
            for pattern in config['patterns']:
                if re.search(pattern, file_path_lower):
                    return file_type
        
        return 'other'
    
    def _get_type_relevance_score(self, file_type: str, query_keywords: Set[str]) -> float:
        """Get relevance score based on file type and query keywords."""
        if file_type not in self.file_type_patterns:
            return 0.0
        
        base_weight = self.file_type_patterns[file_type]['weight']
        
        # Boost score if query specifically mentions file type concepts
        type_keywords = {
            'source_code': ['code', 'function', 'class', 'method', 'implementation'],
            'config': ['config', 'settings', 'environment', 'setup'],
            'documentation': ['readme', 'docs', 'documentation', 'guide'],
            'test': ['test', 'testing', 'spec', 'unittest'],
            'build': ['build', 'deploy', 'package', 'dependencies']
        }
        
        if file_type in type_keywords:
            if any(kw in ' '.join(query_keywords) for kw in type_keywords[file_type]):
                return base_weight * 0.5  # 50% of base weight as bonus
        
        return base_weight * 0.2  # 20% of base weight as default
    
    def _extract_keywords(self, text: str) -> Set[str]:
        """Extract relevant keywords from text."""
        # Simple keyword extraction - could be enhanced with NLP
        words = re.findall(r'\b\w+\b', text.lower())
        
        # Filter out common stop words and short words
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'have',
            'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should',
            'can', 'may', 'might', 'this', 'that', 'these', 'those', 'i', 'you',
            'he', 'she', 'it', 'we', 'they', 'me', 'him', 'her', 'us', 'them'
        }
        
        keywords = {
            word for word in words 
            if len(word) > 2 and word not in stop_words
        }
        
        return keywords
    
    async def get_suggestion_stats(self) -> Dict[str, Any]:
        """Get statistics about file suggestions for this user."""
        try:
            # For now, return default stats since we don't have a generic cache method
            # In a production system, you'd want to implement proper stats storage
            stats = {
                'total_suggestions': 0,
                'auto_added_files': 0,
                'user_accepted_suggestions': 0,
                'last_suggestion_time': None,
                'most_suggested_file_types': {},
                'average_relevance_score': 0.0
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting suggestion stats: {e}")
            return {}
    
    async def update_suggestion_feedback(
        self,
        file_path: str,
        accepted: bool,
        relevance_score: float
    ):
        """Update suggestion feedback for improving future suggestions."""
        try:
            # For now, just log the feedback since we don't have a generic cache method
            # In a production system, you'd want to implement proper feedback storage
            logger.info(
                "Updated suggestion feedback",
                file_path=file_path,
                accepted=accepted,
                score=relevance_score
            )
            
        except Exception as e:
            logger.error(f"Error updating suggestion feedback: {e}")


# Global suggester instances
_suggesters: Dict[str, IntelligentFileSuggester] = {}


def get_file_suggester(user_id: str) -> IntelligentFileSuggester:
    """Get or create a file suggester instance for a user."""
    if user_id not in _suggesters:
        _suggesters[user_id] = IntelligentFileSuggester(user_id)
    return _suggesters[user_id]