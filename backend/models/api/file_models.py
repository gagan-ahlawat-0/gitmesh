"""
File processing models for the system.
Handles file metadata and processing status.
"""

import hashlib
import uuid
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, validator
from datetime import datetime
from enum import Enum


class FileStatus(str, Enum):
    """File processing status enumeration."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class FileType(str, Enum):
    """Supported file types."""
    TEXT = "text"
    CODE = "code"
    DOCUMENT = "document"
    IMAGE = "image"
    UNKNOWN = "unknown"


class FileMetadata(BaseModel):
    """File metadata model."""
    filename: str = Field(..., description="Original filename")
    file_id: str = Field(..., description="Unique file identifier")
    content_type: str = Field(..., description="MIME type")
    size: int = Field(..., description="File size in bytes")
    file_type: FileType = Field(..., description="Detected file type")
    language: Optional[str] = Field(default=None, description="Programming language (for code files)")
    checksum: str = Field(..., description="File content checksum")
    uploaded_at: datetime = Field(default_factory=datetime.now, description="Upload timestamp")
    processed_at: Optional[datetime] = Field(default=None, description="Processing completion timestamp")
    status: FileStatus = Field(default=FileStatus.PENDING, description="Processing status")
    error_message: Optional[str] = Field(default=None, description="Error message if processing failed")
    
    @validator('file_id')
    def generate_file_id(cls, v, values):
        if v:
            return v
        # Generate file ID from filename and timestamp
        filename = values.get('filename', 'unknown')
        timestamp = datetime.now().isoformat()
        content = f"{filename}_{timestamp}".encode()
        return hashlib.sha256(content).hexdigest()[:16]
    
    @validator('checksum')
    def generate_checksum(cls, v, values):
        if v:
            return v
        # This will be set when file content is available
        return ""


class FileProcessingResult(BaseModel):
    """File processing result model."""
    file_id: str = Field(..., description="Unique file identifier")
    status: str = Field(..., description="Processing status")
    file_metadata: FileMetadata = Field(..., description="File metadata")
    chunk_count: int = Field(default=0, description="Number of chunks processed")
    processed_at: str = Field(..., description="Processing timestamp")
    error: Optional[str] = Field(default=None, description="Error message if processing failed")


class FileUploadResponse(BaseModel):
    """File upload response model."""
    success: bool = Field(..., description="Operation success status")
    message: str = Field(..., description="Response message")
    file_id: str = Field(..., description="File identifier")
    filename: str = Field(..., description="Original filename")
    status: str = Field(..., description="Processing status")
    size: int = Field(..., description="File size in bytes")
    file_type: FileType = Field(..., description="Detected file type")
    language: Optional[str] = Field(default=None, description="Programming language (for code files)")
    processed_at: Optional[str] = Field(default=None, description="Processing timestamp")
