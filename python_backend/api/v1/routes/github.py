"""
GitHub API integration routes
"""

import os
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, Query, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import logging

from models.api.github_models import (
    RepositoriesResponse, RepositoryResponse, BranchesResponse,
    IssuesResponse, PullRequestsResponse, CommitsResponse,
    ContributorsResponse, LanguagesResponse, ActivityResponse,
    TreeResponse, TreesByBranchResponse, BranchesWithTreesResponse,
    FileContentResponse, SearchResponse, SearchRepositoriesRequest,
    SearchUsersRequest, SearchOrganizationsRequest, TrendingRepositoriesRequest,
    RateLimitResponse, CacheResponse, RepositoryStats, BranchStats,
    DashboardStats
)
from utils.github_utils import github_service, get_fallback_trending_repositories, get_demo_starred_repositories
from utils.auth_utils import rate_limit_manager

logger = logging.getLogger(__name__)
router = APIRouter()
security = HTTPBearer(auto_error=False)


def get_current_user_token(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)) -> Optional[str]:
    """Get current user's GitHub access token."""
    if not credentials:
        return None
    
    token = credentials.credentials
    
    # Handle demo token
    if token == 'demo-token':
        return 'demo-github-token'
    
    try:
        # In a real implementation, decode JWT and get GitHub token from session
        # For now, return the token directly (this would be the encrypted GitHub token)
        return token
    except Exception as e:
        logger.error(f"Failed to get user token: {e}")
        return None


def require_auth(token: Optional[str] = Depends(get_current_user_token)) -> str:
    """Require authentication for protected endpoints."""
    if not token:
        raise HTTPException(status_code=401, detail="Authentication required")
    return token


def get_public_token() -> Optional[str]:
    """Get public GitHub token for unauthenticated requests."""
    return os.getenv('GITHUB_PUBLIC_TOKEN')


# PUBLIC ENDPOINTS (no authentication required)

@router.get("/public/search/repositories", response_model=SearchResponse)
async def public_search_repositories(
    request: Request,
    q: str = Query(..., description="Search query"),
    sort: str = Query("stars", description="Sort field"),
    order: str = Query("desc", description="Sort order"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(10, ge=1, le=30, description="Items per page")
):
    """Search repositories (public endpoint)."""
    # Rate limiting
    client_ip = request.client.host
    if rate_limit_manager.is_rate_limited(f"public_search_{client_ip}", max_requests=60, window_minutes=15):
        raise HTTPException(status_code=429, detail="Too many requests")
    
    try:
        public_token = get_public_token()
        
        if not public_token:
            # Return fallback results
            return SearchResponse(
                total_count=1,
                incomplete_results=False,
                items=[{
                    'id': 1,
                    'name': f'{q}-example',
                    'full_name': f'example/{q}-example',
                    'owner': {
                        'login': 'example',
                        'id': 1,
                        'avatar_url': 'https://github.com/github.png',
                        'type': 'Organization',
                        'html_url': 'https://github.com/example'
                    },
                    'private': False,
                    'html_url': f'https://github.com/example/{q}-example',
                    'description': f'Example repository for {q}. Sign in to GitHub to see real search results.',
                    'fork': False,
                    'url': f'https://api.github.com/repos/example/{q}-example',
                    'created_at': '2023-01-01T00:00:00Z',
                    'updated_at': '2024-01-01T00:00:00Z',
                    'pushed_at': '2024-01-01T00:00:00Z',
                    'clone_url': f'https://github.com/example/{q}-example.git',
                    'stargazers_count': 1000,
                    'watchers_count': 1000,
                    'language': 'JavaScript',
                    'forks_count': 200,
                    'archived': False,
                    'disabled': False,
                    'open_issues_count': 5,
                    'license': {'key': 'mit', 'name': 'MIT License'},
                    'allow_forking': True,
                    'default_branch': 'main',
                    'score': 1.0
                }],
                query=q,
                pagination={'sort': sort, 'order': order, 'page': page, 'per_page': per_page}
            )
        
        search_result = await github_service.search_repositories(
            public_token, q, sort, order, page, per_page
        )
        
        return SearchResponse(
            total_count=search_result.get('total_count', 0),
            incomplete_results=search_result.get('incomplete_results', False),
            items=search_result.get('items', []),
            query=q,
            pagination={'sort': sort, 'order': order, 'page': page, 'per_page': per_page}
        )
        
    except Exception as e:
        logger.error(f"Public repository search error: {e}")
        raise HTTPException(status_code=500, detail="Search temporarily unavailable")


@router.get("/public/search/users", response_model=SearchResponse)
async def public_search_users(
    request: Request,
    q: str = Query(..., description="Search query"),
    sort: str = Query("followers", description="Sort field"),
    order: str = Query("desc", description="Sort order"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(10, ge=1, le=30, description="Items per page")
):
    """Search users (public endpoint)."""
    # Rate limiting
    client_ip = request.client.host
    if rate_limit_manager.is_rate_limited(f"public_search_{client_ip}", max_requests=60, window_minutes=15):
        raise HTTPException(status_code=429, detail="Too many requests")
    
    try:
        public_token = get_public_token()
        
        if not public_token:
            # Return fallback results
            return SearchResponse(
                total_count=1,
                incomplete_results=False,
                items=[{
                    'login': f'{q.lower()}user',
                    'id': 1,
                    'avatar_url': 'https://github.com/github.png',
                    'html_url': f'https://github.com/{q.lower()}user',
                    'type': 'User',
                    'name': f'{q} User',
                    'company': 'Example Company',
                    'blog': '',
                    'location': 'San Francisco',
                    'email': None,
                    'bio': f'Example user for {q}. Sign in to GitHub to see real search results.',
                    'public_repos': 10,
                    'public_gists': 5,
                    'followers': 100,
                    'following': 50,
                    'created_at': '2020-01-01T00:00:00Z',
                    'updated_at': '2024-01-01T00:00:00Z',
                    'score': 1.0
                }],
                query=q,
                pagination={'sort': sort, 'order': order, 'page': page, 'per_page': per_page}
            )
        
        search_result = await github_service.search_users(
            public_token, q, sort, order, page, per_page
        )
        
        return SearchResponse(
            total_count=search_result.get('total_count', 0),
            incomplete_results=search_result.get('incomplete_results', False),
            items=search_result.get('items', []),
            query=q,
            pagination={'sort': sort, 'order': order, 'page': page, 'per_page': per_page}
        )
        
    except Exception as e:
        logger.error(f"Public user search error: {e}")
        raise HTTPException(status_code=500, detail="Search temporarily unavailable")


@router.get("/public/search/organizations", response_model=SearchResponse)
async def public_search_organizations(
    request: Request,
    q: str = Query(..., description="Search query"),
    sort: str = Query("repositories", description="Sort field"),
    order: str = Query("desc", description="Sort order"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(10, ge=1, le=30, description="Items per page")
):
    """Search organizations (public endpoint)."""
    # Rate limiting
    client_ip = request.client.host
    if rate_limit_manager.is_rate_limited(f"public_search_{client_ip}", max_requests=60, window_minutes=15):
        raise HTTPException(status_code=429, detail="Too many requests")
    
    try:
        public_token = get_public_token()
        
        if not public_token:
            # Return fallback results
            return SearchResponse(
                total_count=1,
                incomplete_results=False,
                items=[{
                    'login': f'{q.lower()}org',
                    'id': 2,
                    'avatar_url': 'https://github.com/github.png',
                    'html_url': f'https://github.com/{q.lower()}org',
                    'type': 'Organization',
                    'name': f'{q} Organization',
                    'company': None,
                    'blog': '',
                    'location': 'Global',
                    'email': None,
                    'bio': f'Example organization for {q}. Sign in to GitHub to see real search results.',
                    'public_repos': 25,
                    'public_gists': 0,
                    'followers': 500,
                    'following': 0,
                    'created_at': '2018-01-01T00:00:00Z',
                    'updated_at': '2024-01-01T00:00:00Z',
                    'score': 1.0
                }],
                query=q,
                pagination={'sort': sort, 'order': order, 'page': page, 'per_page': per_page}
            )
        
        search_result = await github_service.search_organizations(
            public_token, q, sort, order, page, per_page
        )
        
        return SearchResponse(
            total_count=search_result.get('total_count', 0),
            incomplete_results=search_result.get('incomplete_results', False),
            items=search_result.get('items', []),
            query=q,
            pagination={'sort': sort, 'order': order, 'page': page, 'per_page': per_page}
        )
        
    except Exception as e:
        logger.error(f"Public organization search error: {e}")
        raise HTTPException(status_code=500, detail="Search temporarily unavailable")


# PROTECTED ENDPOINTS (authentication required)

@router.get("/repositories", response_model=RepositoriesResponse)
async def get_user_repositories(
    token: str = Depends(require_auth),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(100, ge=1, le=100, description="Items per page")
):
    """Get user repositories."""
    try:
        repositories = await github_service.get_user_repositories(token, page, per_page)
        
        return RepositoriesResponse(
            repositories=repositories,
            pagination={
                'page': page,
                'per_page': per_page,
                'total': len(repositories)
            }
        )
    except Exception as e:
        logger.error(f"Error fetching user repositories: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/repositories/{owner}/{repo}", response_model=RepositoryResponse)
async def get_repository_details(
    owner: str,
    repo: str,
    token: str = Depends(require_auth)
):
    """Get repository details."""
    try:
        repository = await github_service.get_repository_details(token, owner, repo)
        return RepositoryResponse(repository=repository)
    except Exception as e:
        logger.error(f"Error fetching repository details: {e}")
        raise HTTPException(status_code=404, detail="Repository not found")


@router.get("/repositories/{owner}/{repo}/branches", response_model=BranchesResponse)
async def get_repository_branches(
    owner: str,
    repo: str,
    token: str = Depends(require_auth)
):
    """Get repository branches."""
    try:
        branches = await github_service.get_repository_branches(token, owner, repo)
        
        return BranchesResponse(
            branches=branches,
            total=len(branches)
        )
    except Exception as e:
        logger.error(f"Error fetching repository branches: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/repositories/{owner}/{repo}/issues", response_model=IssuesResponse)
async def get_repository_issues(
    owner: str,
    repo: str,
    token: str = Depends(require_auth),
    state: str = Query("open", description="Issue state"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(100, ge=1, le=100, description="Items per page")
):
    """Get repository issues."""
    try:
        issues = await github_service.get_repository_issues(token, owner, repo, state, page, per_page)
        
        return IssuesResponse(
            issues=issues,
            pagination={
                'state': state,
                'page': page,
                'per_page': per_page,
                'total': len(issues)
            }
        )
    except Exception as e:
        logger.error(f"Error fetching repository issues: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/repositories/{owner}/{repo}/pulls", response_model=PullRequestsResponse)
async def get_repository_pull_requests(
    owner: str,
    repo: str,
    token: str = Depends(require_auth),
    state: str = Query("open", description="Pull request state"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(100, ge=1, le=100, description="Items per page")
):
    """Get repository pull requests."""
    try:
        pull_requests = await github_service.get_repository_pull_requests(token, owner, repo, state, page, per_page)
        
        return PullRequestsResponse(
            pull_requests=pull_requests,
            pagination={
                'state': state,
                'page': page,
                'per_page': per_page,
                'total': len(pull_requests)
            }
        )
    except Exception as e:
        logger.error(f"Error fetching repository pull requests: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/repositories/{owner}/{repo}/commits", response_model=CommitsResponse)
async def get_repository_commits(
    owner: str,
    repo: str,
    token: str = Depends(require_auth),
    branch: str = Query("main", description="Branch name"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(100, ge=1, le=100, description="Items per page"),
    since: Optional[str] = Query(None, description="Only commits after this date")
):
    """Get repository commits."""
    try:
        commits = await github_service.get_repository_commits(token, owner, repo, branch, page, per_page, since)
        
        return CommitsResponse(
            commits=commits,
            pagination={
                'branch': branch,
                'page': page,
                'per_page': per_page,
                'total': len(commits)
            }
        )
    except Exception as e:
        logger.error(f"Error fetching repository commits: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/repositories/{owner}/{repo}/contributors", response_model=ContributorsResponse)
async def get_repository_contributors(
    owner: str,
    repo: str,
    token: str = Depends(require_auth)
):
    """Get repository contributors."""
    try:
        contributors = await github_service.get_repository_contributors(token, owner, repo)
        
        return ContributorsResponse(
            contributors=contributors,
            total=len(contributors)
        )
    except Exception as e:
        logger.error(f"Error fetching repository contributors: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/repositories/{owner}/{repo}/languages", response_model=LanguagesResponse)
async def get_repository_languages(
    owner: str,
    repo: str,
    token: str = Depends(require_auth)
):
    """Get repository languages."""
    try:
        languages = await github_service.get_repository_languages(token, owner, repo)
        
        return LanguagesResponse(languages=languages)
    except Exception as e:
        logger.error(f"Error fetching repository languages: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/activity", response_model=ActivityResponse)
async def get_user_activity(
    token: str = Depends(require_auth),
    username: Optional[str] = Query(None, description="Username (optional)"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(100, ge=1, le=100, description="Items per page")
):
    """Get user activity."""
    try:
        # For now, use a default username since we don't have user context
        target_username = username or 'demo-user'
        activity = await github_service.get_user_activity(token, target_username, page, per_page)
        
        return ActivityResponse(
            activity=activity,
            pagination={
                'username': target_username,
                'page': page,
                'per_page': per_page,
                'total': len(activity)
            }
        )
    except Exception as e:
        logger.error(f"Error fetching user activity: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/starred", response_model=RepositoriesResponse)
async def get_user_starred_repositories(
    token: str = Depends(require_auth),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(100, ge=1, le=100, description="Items per page")
):
    """Get user starred repositories."""
    try:
        # Handle demo mode
        if token == 'demo-github-token':
            starred_repos = get_demo_starred_repositories()
            
            # Apply pagination
            start_index = (page - 1) * per_page
            end_index = start_index + per_page
            paginated_repos = starred_repos[start_index:end_index]
            
            return RepositoriesResponse(
                repositories=paginated_repos,
                pagination={
                    'page': page,
                    'per_page': per_page,
                    'total': len(starred_repos)
                }
            )
        
        starred_repos = await github_service.get_user_starred(token, page, per_page)
        
        return RepositoriesResponse(
            repositories=starred_repos,
            pagination={
                'page': page,
                'per_page': per_page,
                'total': len(starred_repos)
            }
        )
    except Exception as e:
        logger.error(f"Error fetching starred repositories: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/trending", response_model=RepositoriesResponse)
async def get_trending_repositories(
    token: str = Depends(require_auth),
    since: str = Query("weekly", description="Time period"),
    language: Optional[str] = Query(None, description="Programming language"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(30, ge=1, le=100, description="Items per page")
):
    """Get trending repositories."""
    try:
        # Handle demo mode
        if token == 'demo-github-token':
            logger.info('Demo mode: returning fallback trending repositories')
            fallback_repos = get_fallback_trending_repositories(language, page, per_page)
            
            return RepositoriesResponse(
                repositories=fallback_repos,
                pagination={
                    'since': since,
                    'language': language,
                    'page': page,
                    'per_page': per_page,
                    'total': len(get_fallback_trending_repositories(language))
                }
            )
        
        trending_data = await github_service.get_trending_repositories(token, since, language, page, per_page)
        
        return RepositoriesResponse(
            repositories=trending_data['repositories'],
            pagination={
                'since': since,
                'language': language,
                'page': page,
                'per_page': per_page,
                'total': trending_data['total']
            }
        )
    except Exception as e:
        logger.error(f"Error fetching trending repositories: {e}")
        
        # Fallback to curated list on API error
        fallback_repos = get_fallback_trending_repositories(language, page, per_page)
        
        return RepositoriesResponse(
            repositories=fallback_repos,
            pagination={
                'since': since,
                'language': language,
                'page': page,
                'per_page': per_page,
                'total': len(get_fallback_trending_repositories(language))
            }
        )


@router.get("/search/repositories", response_model=SearchResponse)
async def search_repositories(
    token: str = Depends(require_auth),
    q: str = Query(..., description="Search query"),
    sort: str = Query("stars", description="Sort field"),
    order: str = Query("desc", description="Sort order"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(30, ge=1, le=100, description="Items per page")
):
    """Search repositories (authenticated)."""
    try:
        search_result = await github_service.search_repositories(token, q, sort, order, page, per_page)
        
        return SearchResponse(
            total_count=search_result.get('total_count', 0),
            incomplete_results=search_result.get('incomplete_results', False),
            items=search_result.get('items', []),
            query=q,
            pagination={'sort': sort, 'order': order, 'page': page, 'per_page': per_page}
        )
    except Exception as e:
        logger.error(f"Error searching repositories: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search/users", response_model=SearchResponse)
async def search_users(
    token: str = Depends(require_auth),
    q: str = Query(..., description="Search query"),
    sort: str = Query("followers", description="Sort field"),
    order: str = Query("desc", description="Sort order"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(30, ge=1, le=100, description="Items per page")
):
    """Search users (authenticated)."""
    try:
        search_result = await github_service.search_users(token, q, sort, order, page, per_page)
        
        return SearchResponse(
            total_count=search_result.get('total_count', 0),
            incomplete_results=search_result.get('incomplete_results', False),
            items=search_result.get('items', []),
            query=q,
            pagination={'sort': sort, 'order': order, 'page': page, 'per_page': per_page}
        )
    except Exception as e:
        logger.error(f"Error searching users: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search/organizations", response_model=SearchResponse)
async def search_organizations(
    token: str = Depends(require_auth),
    q: str = Query(..., description="Search query"),
    sort: str = Query("repositories", description="Sort field"),
    order: str = Query("desc", description="Sort order"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(30, ge=1, le=100, description="Items per page")
):
    """Search organizations (authenticated)."""
    try:
        search_result = await github_service.search_organizations(token, q, sort, order, page, per_page)
        
        return SearchResponse(
            total_count=search_result.get('total_count', 0),
            incomplete_results=search_result.get('incomplete_results', False),
            items=search_result.get('items', []),
            query=q,
            pagination={'sort': sort, 'order': order, 'page': page, 'per_page': per_page}
        )
    except Exception as e:
        logger.error(f"Error searching organizations: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/repositories/{owner}/{repo}/stats")
async def get_repository_stats(
    owner: str,
    repo: str,
    token: str = Depends(require_auth)
):
    """Get repository statistics."""
    try:
        # Fetch various repository data in parallel
        details = await github_service.get_repository_details(token, owner, repo)
        branches = await github_service.get_repository_branches(token, owner, repo)
        issues = await github_service.get_repository_issues(token, owner, repo, 'open')
        pull_requests = await github_service.get_repository_pull_requests(token, owner, repo, 'open')
        commits = await github_service.get_repository_commits(token, owner, repo, 'main', 1, 100)
        contributors = await github_service.get_repository_contributors(token, owner, repo)
        languages = await github_service.get_repository_languages(token, owner, repo)
        
        # Calculate statistics
        stats = {
            'repository': details,
            'summary': {
                'totalBranches': len(branches),
                'openIssues': len(issues),
                'openPullRequests': len(pull_requests),
                'totalCommits': len(commits),
                'totalContributors': len(contributors),
                'languages': list(languages.keys()),
                'primaryLanguage': details.get('language'),
                'stars': details.get('stargazers_count', 0),
                'forks': details.get('forks_count', 0),
                'watchers': details.get('watchers_count', 0),
                'size': details.get('size', 0),
                'lastUpdated': details.get('updated_at'),
                'createdAt': details.get('created_at')
            },
            'branches': branches[:10],  # Top 10 branches
            'recentIssues': issues[:10],  # Recent 10 issues
            'recentPullRequests': pull_requests[:10],  # Recent 10 PRs
            'recentCommits': commits[:10],  # Recent 10 commits
            'topContributors': contributors[:10],  # Top 10 contributors
            'languages': languages
        }
        
        return stats
    except Exception as e:
        logger.error(f"Error fetching repository statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dashboard")
async def get_dashboard_data(token: str = Depends(require_auth)):
    """Get user dashboard data."""
    try:
        # Fetch user repositories and activity
        repositories = await github_service.get_user_repositories(token, 1, 50)
        
        # Calculate dashboard statistics
        dashboard_stats = {
            'totalRepositories': len(repositories),
            'totalStars': sum(repo.get('stargazers_count', 0) for repo in repositories),
            'totalForks': sum(repo.get('forks_count', 0) for repo in repositories),
            'totalIssues': sum(repo.get('open_issues_count', 0) for repo in repositories),
            'recentActivity': [],  # Would need activity data
            'topRepositories': sorted(
                repositories, 
                key=lambda x: x.get('stargazers_count', 0), 
                reverse=True
            )[:10],
            'recentRepositories': sorted(
                repositories,
                key=lambda x: x.get('updated_at', ''),
                reverse=True
            )[:10],
            'languages': {}
        }
        
        # Calculate language distribution
        for repo in repositories:
            language = repo.get('language')
            if language:
                dashboard_stats['languages'][language] = dashboard_stats['languages'].get(language, 0) + 1
        
        return dashboard_stats
    except Exception as e:
        logger.error(f"Error fetching dashboard data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/repositories/{owner}/{repo}/branches/{branch}")
async def get_branch_data(
    owner: str,
    repo: str,
    branch: str,
    token: str = Depends(require_auth),
    since: Optional[str] = Query(None, description="Since date for commits")
):
    """Get branch-specific data for Beetle."""
    try:
        # Fetch branch-specific data
        branches = await github_service.get_repository_branches(token, owner, repo)
        commits = await github_service.get_repository_commits(token, owner, repo, branch, 1, 100, since)
        issues = await github_service.get_repository_issues(token, owner, repo, 'all', 1, 100)
        pull_requests = await github_service.get_repository_pull_requests(token, owner, repo, 'all', 1, 100)
        
        # Find the specific branch
        branch_data = next((b for b in branches if b['name'] == branch), None)
        
        if not branch_data:
            raise HTTPException(status_code=404, detail=f"Branch '{branch}' not found")
        
        # For now, return all issues and PRs since branch-specific filtering is complex
        branch_issues = issues
        branch_pull_requests = pull_requests
        
        branch_stats = {
            'branch': branch_data,
            'commits': commits,
            'issues': branch_issues,
            'pullRequests': branch_pull_requests,
            'summary': {
                'totalCommits': len(commits),
                'totalIssues': len(branch_issues),
                'totalPullRequests': len(branch_pull_requests),
                'lastCommit': commits[0] if commits else None,
                'lastActivity': branch_data.get('commit', {}).get('committer', {}).get('date')
            }
        }
        
        return branch_stats
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching branch data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/repositories/{owner}/{repo}/tree", response_model=TreeResponse)
async def get_repository_tree(
    owner: str,
    repo: str,
    token: str = Depends(require_auth),
    branch: str = Query("main", description="Branch name")
):
    """Get repository tree (file/folder structure)."""
    try:
        tree = await github_service.get_repository_tree(token, owner, repo, branch)
        return TreeResponse(tree=tree)
    except Exception as e:
        logger.error(f"Error fetching repository tree: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/repositories/{owner}/{repo}/trees", response_model=TreesByBranchResponse)
async def get_repository_trees_for_all_branches(
    owner: str,
    repo: str,
    token: str = Depends(require_auth)
):
    """Get file trees from all branches for a repository."""
    try:
        if not github_service.is_valid_owner(owner):
            raise HTTPException(status_code=400, detail="Invalid owner parameter")
        
        trees_by_branch = await github_service.get_repository_trees_for_all_branches(token, owner, repo)
        return TreesByBranchResponse(trees_by_branch=trees_by_branch)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching repository trees: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/repositories/{owner}/{repo}/contents/{path:path}", response_model=FileContentResponse)
async def get_file_content(
    owner: str,
    repo: str,
    path: str,
    token: str = Depends(require_auth),
    ref: str = Query("main", description="Branch or commit ref")
):
    """Get file content from a repository."""
    try:
        content = await github_service.get_file_content(token, owner, repo, path, ref)
        return FileContentResponse(content=content)
    except Exception as e:
        logger.error(f"Error fetching file content: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/repositories/{owner}/{repo}/branches-with-trees", response_model=BranchesWithTreesResponse)
async def get_branches_with_trees(
    owner: str,
    repo: str,
    token: str = Depends(require_auth)
):
    """Get all branches with their file trees (comprehensive endpoint)."""
    try:
        branches = await github_service.get_repository_branches(token, owner, repo)
        trees_by_branch = await github_service.get_repository_trees_for_all_branches(token, owner, repo)
        
        result = BranchesWithTreesResponse(
            branches=branches,
            trees_by_branch=trees_by_branch,
            summary={
                'totalBranches': len(branches),
                'branchesWithTrees': len([t for t in trees_by_branch.values() if not isinstance(t, dict) or 'error' not in t]),
                'branchesWithErrors': len([t for t in trees_by_branch.values() if isinstance(t, dict) and 'error' in t])
            }
        )
        
        return result
    except Exception as e:
        logger.error(f"Error fetching branches with trees: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/rate-limit", response_model=RateLimitResponse)
async def get_rate_limit_status(token: str = Depends(require_auth)):
    """Get GitHub API rate limit status."""
    try:
        status = github_service.get_rate_limit_status(token)
        stats = github_service.get_statistics()
        cache_stats = github_service.get_cache_statistics()
        
        return RateLimitResponse(
            rate_limit=status,
            statistics=stats,
            cache=cache_stats,
            recommendations={
                'shouldThrottle': status['is_near_limit'],
                'nextResetIn': max(0, status['reset'] - int(__import__('time').time())),
                'percentageUsed': ((status['limit'] - status['remaining']) / status['limit'] * 100) if status['limit'] > 0 else 0
            }
        )
    except Exception as e:
        logger.error(f"Error fetching rate limit status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/cache", response_model=CacheResponse)
async def clear_github_cache(
    token: str = Depends(require_auth),
    type: Optional[str] = Query(None, description="Cache type to clear")
):
    """Clear GitHub API cache."""
    try:
        if type:
            return CacheResponse(message=f"Cache type '{type}' clearing not implemented")
        else:
            github_service.clear_cache()
            return CacheResponse(message="All GitHub API cache cleared successfully")
    except Exception as e:
        logger.error(f"Error clearing cache: {e}")
        raise HTTPException(status_code=500, detail=str(e))
