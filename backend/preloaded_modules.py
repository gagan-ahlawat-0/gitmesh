import asyncio
from sqlalchemy import select
from backend.models.api.hub_models import SearchResult
from backend.utils.github_utils import github_service
from backend.models.database.search_cache import SearchCache
from backend.config.database import DatabaseManager

async def search_github(query: str, token: str, db_manager: DatabaseManager) -> SearchResult:
    """Search for repositories, organizations, and users on GitHub."""
    async with db_manager.get_async_session() as session:
        # Exact match
        cached_results = await session.execute(
            select(SearchCache).where(SearchCache.query == query)
        )
        cached_results = cached_results.scalar_one_or_none()

        if cached_results:
            return SearchResult(**cached_results.results)

        # Prefix search for recommendation
        cached_results = await session.execute(
            select(SearchCache).where(SearchCache.query.like(f"{query}%"))
        )
        cached_results = cached_results.first()
        if cached_results:
            return SearchResult(**cached_results[0].results)

        repos_future = github_service.search_repositories(query, token=token)
        users_future = github_service.search_users(query, token=token)
        orgs_future = github_service.search_organizations(query, token=token)

        results = await asyncio.gather(repos_future, users_future, orgs_future)

        search_result_data = {
            "repositories": results[0].get("items", []),
            "users": results[1].get("items", []),
            "organizations": results[2].get("items", []),
        }

        new_cache_entry = SearchCache(
            query=query,
            results=search_result_data
        )
        session.add(new_cache_entry)
        await session.commit()

        return SearchResult(**search_result_data)