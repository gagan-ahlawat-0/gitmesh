"""
AI Import API data models for TARS v1 integration
"""
from typing import List, Optional, Dict, Any, Union
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field, HttpUrl


class ImportSourceType(str, Enum):
    """Types of import sources supported by TARS v1"""
    FILE = "file"
    REPOSITORY = "repository"
    WEB = "web"
    GITHUB = "github"
    API = "api"
    TEXT = "text"


class ImportStatus(str, Enum):
    """Import operation status"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ImportRequest(BaseModel):
    """Base import request model"""
    source_type: ImportSourceType = Field(..., description="Type of import source")
    project_id: str = Field(..., description="Project ID for import")
    repository_id: Optional[str] = Field(None, description="Repository ID (optional)")
    branch: Optional[str] = Field(None, description="Branch name (optional)")
    description: Optional[str] = Field(None, description="Import description")


class TarsImportRequest(ImportRequest):
    """TARS v1 import request with extended options"""
    
    # Repository import options
    repository_url: Optional[HttpUrl] = Field(None, description="Repository URL for cloning")
    branches: Optional[List[str]] = Field(None, description="Specific branches to import")
    include_issues: bool = Field(True, description="Include GitHub issues in analysis")
    include_prs: bool = Field(True, description="Include pull requests in analysis")
    
    # Web import options
    web_urls: Optional[List[HttpUrl]] = Field(None, description="Web URLs to crawl and analyze")
    crawl_depth: Optional[int] = Field(1, description="Crawling depth for web URLs")
    extract_text_only: bool = Field(True, description="Extract only text content")
    
    # File import options (handled separately in multipart form)
    file_types: Optional[List[str]] = Field(None, description="Allowed file types")
    max_file_size: Optional[int] = Field(None, description="Maximum file size in bytes")
    
    # Text import options
    text_content: Optional[str] = Field(None, description="Direct text content to import")
    text_title: Optional[str] = Field(None, description="Title for text content")
    
    # Analysis options
    analysis_options: Optional[Dict[str, Any]] = Field(None, description="Custom analysis configuration")
    enable_embedding: bool = Field(True, description="Generate embeddings for content")
    enable_knowledge_graph: bool = Field(True, description="Build knowledge graph")
    quality_threshold: float = Field(0.7, description="Quality threshold for content inclusion")


class WorkflowResultSummary(BaseModel):
    """Summary of a TARS workflow execution"""
    workflow_name: str = Field(..., description="Name of the workflow")
    status: str = Field(..., description="Workflow execution status")
    tasks_completed: int = Field(..., description="Number of tasks completed")
    tasks_failed: int = Field(..., description="Number of tasks failed")
    execution_time: float = Field(..., description="Execution time in seconds")
    error_summary: Optional[str] = Field(None, description="Error summary if failed")


class TarsImportResponse(BaseModel):
    """TARS v1 import response with detailed results"""
    success: bool = Field(..., description="Whether import was successful")
    message: str = Field(..., description="Human-readable message")
    import_id: str = Field(..., description="Unique import identifier")
    status: ImportStatus = Field(..., description="Import status")
    
    # Input tracking
    processed_files: Optional[List[str]] = Field(None, description="List of processed file names")
    repository_url: Optional[str] = Field(None, description="Repository URL processed")
    branches_processed: Optional[List[str]] = Field(None, description="Branches processed")
    urls_processed: Optional[List[str]] = Field(None, description="URLs processed")
    
    # Results summary
    tars_results: Optional[Dict[str, Any]] = Field(None, description="Full TARS workflow results")
    workflow_summaries: Optional[List[WorkflowResultSummary]] = Field(None, description="Workflow summaries")
    knowledge_items_created: Optional[int] = Field(None, description="Number of knowledge items created")
    embeddings_created: Optional[int] = Field(None, description="Number of embeddings created")
    processing_time: Optional[float] = Field(None, description="Total processing time in seconds")
    
    # Error details
    error_details: Optional[str] = Field(None, description="Detailed error information")
    failed_items: Optional[List[str]] = Field(None, description="List of failed items")
    warnings: Optional[List[str]] = Field(None, description="Processing warnings")
    
    # Timestamps
    started_at: Optional[datetime] = Field(None, description="Import start timestamp")
    completed_at: Optional[datetime] = Field(None, description="Import completion timestamp")


class ImportResponse(BaseModel):
    """Generic import response (for compatibility)"""
    success: bool = Field(..., description="Whether import was successful")
    message: str = Field(..., description="Human-readable message")
    data: Optional[Dict[str, Any]] = Field(None, description="Import result data")
    error: Optional[str] = Field(None, description="Error message if failed")


class ImportHistoryItem(BaseModel):
    """Import history item"""
    import_id: str = Field(..., description="Import identifier")
    source_type: ImportSourceType = Field(..., description="Type of import source")
    status: ImportStatus = Field(..., description="Import status")
    project_id: str = Field(..., description="Project ID")
    description: Optional[str] = Field(None, description="Import description")
    created_at: datetime = Field(..., description="Import creation timestamp")
    completed_at: Optional[datetime] = Field(None, description="Import completion timestamp")
    items_processed: Optional[int] = Field(None, description="Number of items processed")
    error_message: Optional[str] = Field(None, description="Error message if failed")


class ImportHistoryResponse(BaseModel):
    """Import history response"""
    imports: List[ImportHistoryItem] = Field(..., description="List of import history items")
    total: int = Field(..., description="Total number of imports")
    page: int = Field(1, description="Current page number")
    per_page: int = Field(10, description="Items per page")
    has_more: bool = Field(False, description="Whether there are more pages")


class ImportStatusResponse(BaseModel):
    """Import status response"""
    import_id: str = Field(..., description="Import identifier")
    status: ImportStatus = Field(..., description="Current status")
    progress: Optional[float] = Field(None, description="Progress percentage (0-100)")
    message: Optional[str] = Field(None, description="Status message")
    current_task: Optional[str] = Field(None, description="Currently executing task")
    estimated_time_remaining: Optional[int] = Field(None, description="Estimated seconds remaining")
    results_preview: Optional[Dict[str, Any]] = Field(None, description="Preview of results so far")


class ImportDeleteResponse(BaseModel):
    """Import deletion response"""
    success: bool = Field(..., description="Whether deletion was successful")
    message: str = Field(..., description="Deletion result message")
    import_id: str = Field(..., description="Deleted import identifier")
    items_deleted: Optional[int] = Field(None, description="Number of items deleted")


# TARS-specific models for advanced features

class TarsAgentStatus(BaseModel):
    """Status of a TARS agent"""
    agent_name: str = Field(..., description="Agent name")
    status: str = Field(..., description="Agent status")
    tasks_completed: int = Field(0, description="Tasks completed")
    tasks_failed: int = Field(0, description="Tasks failed")
    last_activity: Optional[datetime] = Field(None, description="Last activity timestamp")


class TarsSystemHealth(BaseModel):
    """TARS system health status"""
    overall_status: str = Field(..., description="Overall system status")
    agent_statuses: Dict[str, str] = Field(..., description="Status of each agent")
    memory_usage: Dict[str, Any] = Field(..., description="Memory usage statistics")
    performance_metrics: Dict[str, Any] = Field(..., description="Performance metrics")
    error_count: int = Field(0, description="Total error count")
    warning_count: int = Field(0, description="Total warning count")
    last_check: datetime = Field(..., description="Last health check timestamp")


class TarsKnowledgeItem(BaseModel):
    """TARS knowledge base item"""
    id: str = Field(..., description="Knowledge item ID")
    title: str = Field(..., description="Item title")
    content: str = Field(..., description="Item content")
    source_type: str = Field(..., description="Source type")
    source_url: Optional[str] = Field(None, description="Source URL")
    embeddings: Optional[List[float]] = Field(None, description="Content embeddings")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    created_at: datetime = Field(..., description="Creation timestamp")
    quality_score: Optional[float] = Field(None, description="Quality score")


class TarsAnalysisResult(BaseModel):
    """TARS analysis result"""
    analysis_type: str = Field(..., description="Type of analysis performed")
    confidence_score: float = Field(..., description="Confidence score (0-1)")
    findings: List[str] = Field(..., description="Key findings")
    recommendations: List[str] = Field(..., description="Recommendations")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Analysis metadata")
    created_at: datetime = Field(..., description="Analysis timestamp")


class TarsImportSummary(BaseModel):
    """Comprehensive TARS import summary"""
    import_id: str = Field(..., description="Import identifier")
    summary: str = Field(..., description="Human-readable summary")
    statistics: Dict[str, Any] = Field(..., description="Import statistics")
    knowledge_items: List[TarsKnowledgeItem] = Field(..., description="Created knowledge items")
    analysis_results: List[TarsAnalysisResult] = Field(..., description="Analysis results")
    system_health: TarsSystemHealth = Field(..., description="System health at completion")
    recommendations: List[str] = Field(..., description="Post-import recommendations")


# Database integration models

class ImportSession(BaseModel):
    """Database model for import sessions"""
    id: str = Field(..., description="Session identifier")
    user_id: str = Field(..., description="User identifier")
    project_id: str = Field(..., description="Project identifier")
    source_type: ImportSourceType = Field(..., description="Import source type")
    status: ImportStatus = Field(..., description="Session status")
    configuration: Dict[str, Any] = Field(..., description="Import configuration")
    results: Optional[Dict[str, Any]] = Field(None, description="Import results")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    completed_at: Optional[datetime] = Field(None, description="Completion timestamp")


class ImportMetrics(BaseModel):
    """Import metrics for analytics"""
    import_id: str = Field(..., description="Import identifier")
    total_items: int = Field(..., description="Total items processed")
    successful_items: int = Field(..., description="Successfully processed items")
    failed_items: int = Field(..., description="Failed items")
    processing_time: float = Field(..., description="Total processing time")
    memory_usage: Dict[str, Any] = Field(..., description="Memory usage during import")
    agent_performance: Dict[str, Any] = Field(..., description="Agent performance metrics")
    quality_scores: List[float] = Field(..., description="Quality scores of processed items")
