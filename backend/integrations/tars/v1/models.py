"""
TARS v1 Data Models
==================

Pydantic models for structured output and data validation.
"""

from typing import List, Dict, Any, Optional, Literal
from pydantic import BaseModel, Field
from datetime import datetime


class ComparisonResult(BaseModel):
    """Model for code comparison analysis results."""
    differences: List[str] = Field(description="List of identified differences")
    similarities: List[str] = Field(description="List of identified similarities")
    recommendations: List[str] = Field(description="List of recommendations")
    risk_assessment: str = Field(description="Overall risk assessment")
    confidence_score: float = Field(description="Confidence score (0.0-1.0)", ge=0.0, le=1.0)


class ProjectStatus(BaseModel):
    """Model for project insights and status."""
    active_issues: List[Dict[str, Any]] = Field(description="List of active issues with metadata")
    contributor_activity: Dict[str, Any] = Field(description="Contributor activity statistics")
    maintenance_priorities: List[str] = Field(description="Prioritized maintenance tasks")
    contribution_opportunities: List[Dict[str, Any]] = Field(description="Opportunities for contribution")
    health_score: float = Field(description="Project health score (0.0-1.0)", ge=0.0, le=1.0)


class AcquisitionStatus(BaseModel):
    """Model for tracking resource acquisition status."""
    agent_name: str = Field(description="Name of the acquisition agent")
    status: Literal["pending", "running", "completed", "failed"] = Field(description="Current status")
    resources_acquired: int = Field(description="Number of resources successfully acquired")
    resources_failed: int = Field(description="Number of resources that failed to acquire")
    start_time: Optional[datetime] = Field(description="Start time of acquisition")
    end_time: Optional[datetime] = Field(description="End time of acquisition")
    error_message: Optional[str] = Field(description="Error message if failed")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class AnalysisResult(BaseModel):
    """Model for analysis results from various agents."""
    agent_name: str = Field(description="Name of the analysis agent")
    analysis_type: str = Field(description="Type of analysis performed")
    findings: List[str] = Field(description="Key findings from the analysis")
    recommendations: List[str] = Field(description="Actionable recommendations")
    confidence_score: float = Field(description="Confidence in the analysis (0.0-1.0)", ge=0.0, le=1.0)
    supporting_data: Dict[str, Any] = Field(default_factory=dict, description="Supporting data and metrics")
    timestamp: datetime = Field(default_factory=datetime.now, description="Analysis timestamp")


class DocumentAnalysisResult(BaseModel):
    """Model for document analysis results."""
    document_type: str = Field(description="Type of document analyzed")
    key_concepts: List[str] = Field(description="Key concepts identified")
    summary: str = Field(description="Document summary")
    action_items: List[str] = Field(description="Action items identified")
    outdated_sections: List[str] = Field(description="Sections that appear outdated")
    suggested_updates: List[str] = Field(description="Suggested documentation updates")


class CodeAnalysisResult(BaseModel):
    """Model for code analysis results."""
    file_path: str = Field(description="Path to the analyzed file")
    language: str = Field(description="Programming language")
    complexity_score: float = Field(description="Code complexity score", ge=0.0)
    quality_score: float = Field(description="Code quality score (0.0-1.0)", ge=0.0, le=1.0)
    issues: List[Dict[str, str]] = Field(description="Identified issues with severity")
    suggestions: List[str] = Field(description="Improvement suggestions")
    dependencies: List[str] = Field(description="External dependencies identified")


class DataInsight(BaseModel):
    """Model for data analysis insights."""
    metric_name: str = Field(description="Name of the metric")
    metric_value: float = Field(description="Current value of the metric")
    trend: Literal["increasing", "decreasing", "stable"] = Field(description="Trend direction")
    significance: Literal["high", "medium", "low"] = Field(description="Statistical significance")
    interpretation: str = Field(description="Human-readable interpretation")
    recommendations: List[str] = Field(description="Data-driven recommendations")


class KnowledgeEntity(BaseModel):
    """Model for knowledge entities extracted from various sources."""
    entity_id: str = Field(description="Unique identifier for the entity")
    entity_type: str = Field(description="Type of entity (person, project, concept, etc.)")
    name: str = Field(description="Entity name")
    description: str = Field(description="Entity description")
    properties: Dict[str, Any] = Field(default_factory=dict, description="Entity properties")
    relationships: List[Dict[str, str]] = Field(default_factory=list, description="Relationships to other entities")
    confidence: float = Field(description="Confidence in entity extraction (0.0-1.0)", ge=0.0, le=1.0)
    sources: List[str] = Field(description="Sources where this entity was found")


class HandoffRequest(BaseModel):
    """Model for agent handoff requests."""
    from_agent: str = Field(description="Agent requesting the handoff")
    to_agent: str = Field(description="Target agent for handoff")
    task_description: str = Field(description="Description of the task to be handed off")
    context: Dict[str, Any] = Field(default_factory=dict, description="Context data for the handoff")
    priority: Literal["low", "normal", "high", "urgent"] = Field(default="normal", description="Task priority")
    deadline: Optional[datetime] = Field(description="Optional deadline for the task")


class SystemHealth(BaseModel):
    """Model for system health monitoring."""
    overall_status: Literal["healthy", "warning", "critical"] = Field(description="Overall system status")
    agent_statuses: Dict[str, str] = Field(description="Status of each agent")
    memory_usage: Dict[str, float] = Field(description="Memory usage statistics")
    performance_metrics: Dict[str, float] = Field(description="Performance metrics")
    error_count: int = Field(description="Number of errors in last period")
    warning_count: int = Field(description="Number of warnings in last period")
    last_check: datetime = Field(default_factory=datetime.now, description="Last health check timestamp")


class WorkflowResult(BaseModel):
    """Model for workflow execution results."""
    workflow_name: str = Field(description="Name of the executed workflow")
    status: Literal["success", "partial", "failed"] = Field(description="Workflow execution status")
    tasks_completed: int = Field(description="Number of tasks completed successfully")
    tasks_failed: int = Field(description="Number of tasks that failed")
    execution_time: float = Field(description="Total execution time in seconds")
    results: List[AnalysisResult] = Field(description="Results from workflow tasks")
    error_summary: Optional[str] = Field(description="Summary of errors if any occurred")
