"""
GitHub API utilities and helper functions
"""

import os
import asyncio
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Tuple
from urllib.parse import urlencode
import aiohttp
import logging
from cachetools import TTLCache

from config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class GitHubRateLimitManager:
    """GitHub API rate limit manager."""
    
    def __init__(self):
        self.rate_limits = {}
        self.statistics = {
            'total_requests': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'rate_limit_hits': 0
        }
    
    def update_rate_limit(self, token: str, headers: Dict[str, str]):
        """Update rate limit information from response headers."""
        try:
            self.rate_limits[token] = {
                'limit': int(headers.get('x-ratelimit-limit', 5000)),
                'remaining': int(headers.get('x-ratelimit-remaining', 5000)),
                'reset': int(headers.get('x-ratelimit-reset', 0)),
                'used': int(headers.get('x-ratelimit-used', 0)),
                'resource': headers.get('x-ratelimit-resource', 'core'),
                'last_updated': datetime.now()
            }
        except (ValueError, TypeError) as e:
            logger.warning(f"Failed to parse rate limit headers: {e}")
    
    def get_rate_limit_status(self, token: str) -> Dict[str, Any]:
        """Get current rate limit status for token."""
        if token not in self.rate_limits:
            return {
                'limit': 5000,
                'remaining': 5000,
                'used': 0,
                'reset': int((datetime.now() + timedelta(hours=1)).timestamp()),
                'reset_date': (datetime.now() + timedelta(hours=1)).isoformat(),
                'is_near_limit': False,
                'is_rate_limited': False,
                'resource': 'core'
            }
        
        rate_limit = self.rate_limits[token]
        reset_date = datetime.fromtimestamp(rate_limit['reset'])
        
        return {
            'limit': rate_limit['limit'],
            'remaining': rate_limit['remaining'],
            'used': rate_limit['used'],
            'reset': rate_limit['reset'],
            'reset_date': reset_date.isoformat(),
            'is_near_limit': rate_limit['remaining'] < (rate_limit['limit'] * 0.2),
            'is_rate_limited': rate_limit['remaining'] <= 0,
            'resource': rate_limit['resource']
        }
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get usage statistics."""
        total_requests = self.statistics['total_requests']
        cache_hits = self.statistics['cache_hits']
        
        return {
            'total_requests': total_requests,
            'cache_hits': cache_hits,
            'cache_misses': self.statistics['cache_misses'],
            'rate_limit_hits': self.statistics['rate_limit_hits'],
            'cache_hit_rate': (cache_hits / total_requests * 100) if total_requests > 0 else 0
        }


class GitHubCacheManager:
    """GitHub API response cache manager."""
    
    def __init__(self, max_size: int = 1000, ttl: int = 300):
        self.cache = TTLCache(maxsize=max_size, ttl=ttl)
        self.statistics = {
            'hits': 0,
            'misses': 0,
            'size': 0
        }
    
    def _generate_key(self, url: str, params: Dict[str, Any] = None) -> str:
        """Generate cache key from URL and parameters."""
        if params:
            url += '?' + urlencode(sorted(params.items()))
        return hashlib.md5(url.encode()).hexdigest()
    
    def get(self, url: str, params: Dict[str, Any] = None) -> Optional[Any]:
        """Get cached response."""
        key = self._generate_key(url, params)
        
        if key in self.cache:
            self.statistics['hits'] += 1
            return self.cache[key]
        
        self.statistics['misses'] += 1
        return None
    
    def set(self, url: str, data: Any, params: Dict[str, Any] = None):
        """Cache response data."""
        key = self._generate_key(url, params)
        self.cache[key] = data
        self.statistics['size'] = len(self.cache)
    
    def clear(self):
        """Clear all cached data."""
        self.cache.clear()
        self.statistics['size'] = 0
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_requests = self.statistics['hits'] + self.statistics['misses']
        
        return {
            'hits': self.statistics['hits'],
            'misses': self.statistics['misses'],
            'size': self.statistics['size'],
            'hit_rate': (self.statistics['hits'] / total_requests * 100) if total_requests > 0 else 0
        }


class GitHubAPIClient:
    """GitHub API client with rate limiting and caching."""
    
    def __init__(self):
        self.base_url = "https://api.github.com"
        self.rate_limit_manager = GitHubRateLimitManager()
        self.cache_manager = GitHubCacheManager()
        self.timeout = aiohttp.ClientTimeout(total=30)
    
    async def _make_request(
        self, 
        method: str, 
        endpoint: str, 
        token: Optional[str] = None,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        use_cache: bool = True
    ) -> Tuple[Dict[str, Any], Dict[str, str]]:
        """Make GitHub API request with rate limiting and caching."""
        url = f"{self.base_url}{endpoint}"
        
        # Check cache first for GET requests
        if method.upper() == 'GET' and use_cache:
            cached_response = self.cache_manager.get(url, params)
            if cached_response:
                self.rate_limit_manager.statistics['cache_hits'] += 1
                return cached_response, {}
        
        # Prepare headers
        headers = {
            'Accept': 'application/vnd.github.v3+json',
            'User-Agent': 'Beetle-AI'
        }
        
        if token:
            headers['Authorization'] = f'token {token}'
        
        self.rate_limit_manager.statistics['total_requests'] += 1
        
        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.request(
                    method, url, headers=headers, params=params, json=data
                ) as response:
                    # Update rate limit info
                    self.rate_limit_manager.update_rate_limit(token or 'public', dict(response.headers))
                    
                    if response.status == 403 and 'rate limit' in response.reason.lower():
                        self.rate_limit_manager.statistics['rate_limit_hits'] += 1
                        raise Exception(f"GitHub API rate limit exceeded")
                    
                    if response.status == 404:
                        raise Exception(f"Resource not found: {endpoint}")
                    
                    if not response.ok:
                        error_text = await response.text()
                        raise Exception(f"GitHub API error {response.status}: {error_text}")
                    
                    response_data = await response.json()
                    response_headers = dict(response.headers)
                    
                    # Cache successful GET responses
                    if method.upper() == 'GET' and use_cache:
                        self.cache_manager.set(url, (response_data, response_headers), params)
                    
                    return response_data, response_headers
                    
        except aiohttp.ClientError as e:
            logger.error(f"GitHub API request failed: {e}")
            raise Exception(f"GitHub API request failed: {e}")
    
    async def get(self, endpoint: str, token: Optional[str] = None, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Make GET request to GitHub API."""
        response_data, _ = await self._make_request('GET', endpoint, token, params)
        return response_data
    
    async def post(self, endpoint: str, token: Optional[str] = None, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Make POST request to GitHub API."""
        response_data, _ = await self._make_request('POST', endpoint, token, data=data, use_cache=False)
        return response_data
    
    async def put(self, endpoint: str, token: Optional[str] = None, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Make PUT request to GitHub API."""
        response_data, _ = await self._make_request('PUT', endpoint, token, data=data, use_cache=False)
        return response_data
    
    async def delete(self, endpoint: str, token: Optional[str] = None) -> Dict[str, Any]:
        """Make DELETE request to GitHub API."""
        response_data, _ = await self._make_request('DELETE', endpoint, token, use_cache=False)
        return response_data


class GitHubService:
    """High-level GitHub service with all API operations."""
    
    def __init__(self):
        self.client = GitHubAPIClient()
    
    # User Operations
    
    async def get_user_profile(self, token: str) -> Dict[str, Any]:
        """Get authenticated user profile."""
        return await self.client.get('/user', token)
    
    async def get_user_repositories(self, token: str, page: int = 1, per_page: int = 30) -> List[Dict[str, Any]]:
        """Get user repositories."""
        params = {'page': page, 'per_page': per_page, 'sort': 'updated'}
        return await self.client.get('/user/repos', token, params)
    
    async def get_user_activity(self, token: str, username: str, page: int = 1, per_page: int = 30) -> List[Dict[str, Any]]:
        """Get user public activity."""
        params = {'page': page, 'per_page': per_page}
        return await self.client.get(f'/users/{username}/events/public', token, params)
    
    async def get_user_starred(self, token: str, page: int = 1, per_page: int = 30) -> List[Dict[str, Any]]:
        """Get user starred repositories."""
        params = {'page': page, 'per_page': per_page, 'sort': 'updated'}
        return await self.client.get('/user/starred', token, params)
    
    # Repository Operations
    
    async def get_repository_details(self, token: str, owner: str, repo: str) -> Dict[str, Any]:
        """Get repository details."""
        return await self.client.get(f'/repos/{owner}/{repo}', token)
    
    async def get_repository_branches(self, token: str, owner: str, repo: str) -> List[Dict[str, Any]]:
        """Get repository branches."""
        return await self.client.get(f'/repos/{owner}/{repo}/branches', token)
    
    async def get_repository_commits(
        self, 
        token: str, 
        owner: str, 
        repo: str, 
        branch: str = 'main',
        page: int = 1, 
        per_page: int = 30,
        since: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get repository commits."""
        params = {
            'sha': branch,
            'page': page,
            'per_page': per_page
        }
        if since:
            params['since'] = since
        
        return await self.client.get(f'/repos/{owner}/{repo}/commits', token, params)
    
    async def get_repository_issues(
        self, 
        token: str, 
        owner: str, 
        repo: str, 
        state: str = 'open',
        page: int = 1, 
        per_page: int = 30
    ) -> List[Dict[str, Any]]:
        """Get repository issues."""
        params = {
            'state': state,
            'page': page,
            'per_page': per_page,
            'sort': 'updated'
        }
        return await self.client.get(f'/repos/{owner}/{repo}/issues', token, params)
    
    async def get_repository_pull_requests(
        self, 
        token: str, 
        owner: str, 
        repo: str, 
        state: str = 'open',
        page: int = 1, 
        per_page: int = 30
    ) -> List[Dict[str, Any]]:
        """Get repository pull requests."""
        params = {
            'state': state,
            'page': page,
            'per_page': per_page,
            'sort': 'updated'
        }
        return await self.client.get(f'/repos/{owner}/{repo}/pulls', token, params)
    
    async def get_repository_contributors(self, token: str, owner: str, repo: str) -> List[Dict[str, Any]]:
        """Get repository contributors."""
        return await self.client.get(f'/repos/{owner}/{repo}/contributors', token)
    
    async def get_repository_languages(self, token: str, owner: str, repo: str) -> Dict[str, int]:
        """Get repository languages."""
        return await self.client.get(f'/repos/{owner}/{repo}/languages', token)
    
    async def get_repository_tree(self, token: str, owner: str, repo: str, branch: str = 'main') -> List[Dict[str, Any]]:
        """Get repository tree structure."""
        try:
            # Get the commit SHA for the branch
            branch_data = await self.client.get(f'/repos/{owner}/{repo}/branches/{branch}', token)
            tree_sha = branch_data['commit']['commit']['tree']['sha']
            
            # Get the tree with recursive option
            params = {'recursive': '1'}
            tree_data = await self.client.get(f'/repos/{owner}/{repo}/git/trees/{tree_sha}', token, params)
            
            return tree_data.get('tree', [])
        except Exception as e:
            logger.error(f"Failed to get repository tree: {e}")
            return []
    
    async def get_file_content(self, token: str, owner: str, repo: str, path: str, branch: str = 'main') -> Dict[str, Any]:
        """Get file content from repository."""
        params = {'ref': branch}
        return await self.client.get(f'/repos/{owner}/{repo}/contents/{path}', token, params)
    
    # Search Operations
    
    async def search_repositories(
        self, 
        token: Optional[str], 
        query: str, 
        sort: str = 'stars', 
        order: str = 'desc',
        page: int = 1, 
        per_page: int = 30
    ) -> Dict[str, Any]:
        """Search repositories."""
        params = {
            'q': query,
            'sort': sort,
            'order': order,
            'page': page,
            'per_page': per_page
        }
        return await self.client.get('/search/repositories', token, params)
    
    async def search_users(
        self, 
        token: Optional[str], 
        query: str, 
        sort: str = 'followers', 
        order: str = 'desc',
        page: int = 1, 
        per_page: int = 30
    ) -> Dict[str, Any]:
        """Search users."""
        params = {
            'q': query,
            'sort': sort,
            'order': order,
            'page': page,
            'per_page': per_page
        }
        return await self.client.get('/search/users', token, params)
    
    async def search_organizations(
        self, 
        token: Optional[str], 
        query: str, 
        sort: str = 'repositories', 
        order: str = 'desc',
        page: int = 1, 
        per_page: int = 30
    ) -> Dict[str, Any]:
        """Search organizations."""
        params = {
            'q': query,
            'sort': sort,
            'order': order,
            'page': page,
            'per_page': per_page
        }
        return await self.client.get('/search/organizations', token, params)
    
    # Trending Repositories
    
    async def get_trending_repositories(
        self, 
        token: Optional[str], 
        since: str = 'weekly', 
        language: Optional[str] = None,
        page: int = 1, 
        per_page: int = 30
    ) -> Dict[str, Any]:
        """Get trending repositories."""
        # Calculate date range
        now = datetime.now()
        if since == 'daily':
            past_date = now - timedelta(days=1)
        elif since == 'weekly':
            past_date = now - timedelta(days=7)
        elif since == 'monthly':
            past_date = now - timedelta(days=30)
        else:
            past_date = now - timedelta(days=7)
        
        # Build search query
        query = f"created:>{past_date.strftime('%Y-%m-%d')} stars:>100"
        if language:
            query += f" language:{language}"
        
        params = {
            'q': query,
            'sort': 'stars',
            'order': 'desc',
            'page': page,
            'per_page': per_page
        }
        
        search_result = await self.client.get('/search/repositories', token, params)
        
        return {
            'repositories': search_result.get('items', []),
            'total': search_result.get('total_count', 0)
        }
    
    # Utility Methods
    
    async def get_repository_trees_for_all_branches(self, token: str, owner: str, repo: str) -> Dict[str, Any]:
        """Get file trees for all branches in a repository."""
        try:
            branches = await self.get_repository_branches(token, owner, repo)
            trees_by_branch = {}
            
            for branch in branches:
                try:
                    tree = await self.get_repository_tree(token, owner, repo, branch['name'])
                    trees_by_branch[branch['name']] = tree
                except Exception as e:
                    logger.error(f"Failed to get tree for branch {branch['name']}: {e}")
                    trees_by_branch[branch['name']] = {'error': str(e)}
            
            return trees_by_branch
        except Exception as e:
            logger.error(f"Failed to get trees for all branches: {e}")
            return {}
    
    def is_valid_owner(self, owner: str) -> bool:
        """Validate repository owner name."""
        if not owner or len(owner) < 1 or len(owner) > 39:
            return False
        
        # GitHub username rules
        import re
        return bool(re.match(r'^[a-zA-Z0-9]([a-zA-Z0-9-])*[a-zA-Z0-9]$', owner))
    
    def get_rate_limit_status(self, token: str) -> Dict[str, Any]:
        """Get rate limit status for token."""
        return self.client.rate_limit_manager.get_rate_limit_status(token)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get API usage statistics."""
        return self.client.rate_limit_manager.get_statistics()
    
    def get_cache_statistics(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return self.client.cache_manager.get_statistics()
    
    def clear_cache(self):
        """Clear API response cache."""
        self.client.cache_manager.clear()


# Global GitHub service instance
github_service = GitHubService()


# Fallback data for demo mode and API failures

def get_fallback_trending_repositories(language: Optional[str] = None, page: int = 1, per_page: int = 30) -> List[Dict[str, Any]]:
    """Get fallback trending repositories data."""
    popular_repos = [
        {
            'id': 70107786,
            'name': 'next.js',
            'full_name': 'vercel/next.js',
            'description': 'The React Framework for the Web. Used by some of the world\'s largest companies.',
            'language': 'TypeScript',
            'stargazers_count': 120000,
            'forks_count': 26000,
            'updated_at': datetime.now().isoformat(),
            'private': False,
            'html_url': 'https://github.com/vercel/next.js',
            'owner': {
                'login': 'vercel',
                'avatar_url': 'https://github.com/vercel.png'
            }
        },
        {
            'id': 70107787,
            'name': 'react',
            'full_name': 'facebook/react',
            'description': 'The library for web and native user interfaces.',
            'language': 'JavaScript',
            'stargazers_count': 220000,
            'forks_count': 45000,
            'updated_at': datetime.now().isoformat(),
            'private': False,
            'html_url': 'https://github.com/facebook/react',
            'owner': {
                'login': 'facebook',
                'avatar_url': 'https://github.com/facebook.png'
            }
        },
        {
            'id': 70107788,
            'name': 'vscode',
            'full_name': 'microsoft/vscode',
            'description': 'Visual Studio Code. Code editing. Redefined.',
            'language': 'TypeScript',
            'stargazers_count': 155000,
            'forks_count': 27000,
            'updated_at': datetime.now().isoformat(),
            'private': False,
            'html_url': 'https://github.com/microsoft/vscode',
            'owner': {
                'login': 'microsoft',
                'avatar_url': 'https://github.com/microsoft.png'
            }
        },
        {
            'id': 70107789,
            'name': 'svelte',
            'full_name': 'sveltejs/svelte',
            'description': 'Cybernetically enhanced web apps.',
            'language': 'TypeScript',
            'stargazers_count': 85000,
            'forks_count': 12000,
            'updated_at': datetime.now().isoformat(),
            'private': False,
            'html_url': 'https://github.com/sveltejs/svelte',
            'owner': {
                'login': 'sveltejs',
                'avatar_url': 'https://github.com/sveltejs.png'
            }
        },
        {
            'id': 70107790,
            'name': 'rust',
            'full_name': 'rust-lang/rust',
            'description': 'Empowering everyone to build reliable and efficient software.',
            'language': 'Rust',
            'stargazers_count': 95000,
            'forks_count': 15000,
            'updated_at': datetime.now().isoformat(),
            'private': False,
            'html_url': 'https://github.com/rust-lang/rust',
            'owner': {
                'login': 'rust-lang',
                'avatar_url': 'https://github.com/rust-lang.png'
            }
        }
    ]
    
    # Filter by language if specified
    if language:
        popular_repos = [
            repo for repo in popular_repos 
            if repo['language'] and repo['language'].lower() == language.lower()
        ]
    
    # Apply pagination
    start_index = (page - 1) * per_page
    end_index = start_index + per_page
    return popular_repos[start_index:end_index]


def get_demo_starred_repositories() -> List[Dict[str, Any]]:
    """Get demo starred repositories for demo mode."""
    return [
        {
            'id': 101,
            'name': 'next.js',
            'full_name': 'vercel/next.js',
            'description': 'The React Framework for the Web.',
            'language': 'TypeScript',
            'stargazers_count': 120000,
            'forks_count': 26000,
            'updated_at': datetime.now().isoformat(),
            'private': False,
            'html_url': 'https://github.com/vercel/next.js',
            'owner': {
                'login': 'vercel',
                'avatar_url': 'https://github.com/vercel.png'
            }
        },
        {
            'id': 102,
            'name': 'react',
            'full_name': 'facebook/react',
            'description': 'The library for web and native user interfaces.',
            'language': 'JavaScript',
            'stargazers_count': 220000,
            'forks_count': 45000,
            'updated_at': (datetime.now() - timedelta(hours=4)).isoformat(),
            'private': False,
            'html_url': 'https://github.com/facebook/react',
            'owner': {
                'login': 'facebook',
                'avatar_url': 'https://github.com/facebook.png'
            }
        }
    ]
