"""
Models for the Hub API.
"""
from pydantic import BaseModel
from typing import List, Optional

class RepositorySearchResult(BaseModel):
    id: int
    name: str
    full_name: str
    description: Optional[str]
    stars: int
    forks: int
    language: Optional[str]
    owner: str

class UserSearchResult(BaseModel):
    id: int
    login: str
    avatar_url: str
    html_url: str

class OrganizationSearchResult(BaseModel):
    id: int
    login: str
    avatar_url: str
    description: Optional[str]

class SearchResult(BaseModel):
    repositories: List[RepositorySearchResult]
    users: List[UserSearchResult]
    organizations: List[OrganizationSearchResult]
