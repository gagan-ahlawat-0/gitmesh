"""
API endpoints for search functionality.
"""
import structlog
from fastapi import APIRouter, Query, HTTPException, Depends, Request
from typing import Annotated

from backend.preloaded_modules import search_github
from backend.models.api.hub_models import SearchResult
from backend.api.v1.routes.dependencies import get_github_token

router = APIRouter()
logger = structlog.get_logger(__name__)

@router.get("/search", response_model=SearchResult)
async def search(
    request: Request,
    q: Annotated[str, Query(min_length=1, max_length=255)],
    token: str = Depends(get_github_token),
):
    """
    Search for repositories, organizations, and users on GitHub.
    """
    logger.info("Searching GitHub", query=q)
    try:
        db_manager = request.app.state.db_manager
        results = await search_github(q, token, db_manager)
        logger.info("Search successful", query=q, result_counts={
            'repositories': len(results.repositories),
            'users': len(results.users),
            'organizations': len(results.organizations)
        })
        return results
    except Exception as e:
        logger.error("Search failed", query=q, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to fetch search results from GitHub.")
