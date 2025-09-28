"""
Data models for Cosmos response and repository context.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any, Optional, List


@dataclass
class FileLocation:
    """Location information for indexed files."""
    start_offset: int
    end_offset: int
    size: int
    checksum: str


@dataclass
class RepositoryContext:
    """Complete repository context for Cosmos processing."""
    repo_url: str
    repo_name: str
    summary: str
    content: str
    tree_structure: str
    metadata: Dict[str, Any]
    file_index: Dict[str, FileLocation]
    total_files: int
    total_size: int


@dataclass
class VirtualFile:
    """Virtual file representation for the intelligent VFS."""
    path: str
    content: str
    size: int
    last_modified: datetime
    file_type: str
    encoding: str = "utf-8"


@dataclass
class ModelInfo:
    """Information about available AI models."""
    name: str
    provider: str
    max_tokens: int
    supports_streaming: bool = False


@dataclass
class PerformanceMetrics:
    """Performance metrics for monitoring."""
    response_time: float
    memory_usage: float
    redis_operations: int
    file_accesses: int
    timestamp: datetime


@dataclass
class CosmosMessageRequest:
    """Request model for Cosmos chat messages."""
    message: str
    session_id: Optional[str] = None
    context_files: Optional[Dict[str, Any]] = None
    user_id: Optional[str] = None


@dataclass
class CosmosMessageResponse:
    """Response model for Cosmos chat messages."""
    response: str
    session_id: str
    timestamp: datetime
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class ProcessedCosmosResponse:
    """Processed Cosmos response with additional metadata."""
    original_response: str
    processed_response: str
    session_id: str
    processing_time: float
    metadata: Dict[str, Any]
    timestamp: datetime


@dataclass
class AddContextFilesRequest:
    """Request to add context files."""
    files: Dict[str, str]
    session_id: Optional[str] = None


@dataclass
class AddContextFilesResponse:
    """Response for adding context files."""
    success: bool
    message: str
    files_added: int


@dataclass
class RemoveContextFilesRequest:
    """Request to remove context files."""
    file_paths: List[str]
    session_id: Optional[str] = None


@dataclass
class RemoveContextFilesResponse:
    """Response for removing context files."""
    success: bool
    message: str
    files_removed: int


@dataclass
class ContextStatsResponse:
    """Context statistics response."""
    total_files: int
    total_size: int
    file_types: Dict[str, int]


@dataclass
class AvailableModelsResponse:
    """Available models response."""
    models: List[ModelInfo]


@dataclass
class SetModelRequest:
    """Request to set the active model."""
    model_name: str
    session_id: Optional[str] = None


@dataclass
class SetModelResponse:
    """Response for setting the active model."""
    success: bool
    message: str
    active_model: str


@dataclass
class ConversionStatusResponse:
    """Conversion status response."""
    is_converting: bool
    progress: float
    message: str


@dataclass
class CosmosErrorResponse:
    """Error response from Cosmos."""
    error: str
    error_code: str
    timestamp: datetime