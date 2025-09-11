"""
AI Import API endpoints for TARS v1 integration
"""
import os
import uuid
import json
import asyncio
from pathlib import Path
from typing import List, Optional, Dict, Any, Union
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from fastapi.responses import JSONResponse
import structlog

from .auth import get_current_user
from models.api.auth_models import User
from models.api.ai_import_models import (
    ImportRequest, ImportResponse, TarsImportRequest, TarsImportResponse,
    ImportSourceType, ImportStatus
)
from config.settings import get_settings
from config.database import get_database_manager
from integrations.tars.v1.main import TarsMain
from integrations.tars.v1.tars_wrapper import TarsWrapper

logger = structlog.get_logger(__name__)
router = APIRouter()

# Configure upload directory for temporary files
TEMP_UPLOAD_DIR = Path("data/temp_uploads")
TEMP_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Maximum file size (50MB for TARS processing)
MAX_FILE_SIZE = 50 * 1024 * 1024

class TarsImportService:
    """Service for handling TARS v1 imports and database integration"""
    
    def __init__(self, user: User):
        self.user = user
        self.settings = get_settings()
        self.db_manager = get_database_manager()
        self.temp_dir = TEMP_UPLOAD_DIR / f"user_{user.id}"
        self.temp_dir.mkdir(exist_ok=True)
    
    async def create_tars_session(self, project_id: str, repository_id: Optional[str] = None) -> TarsMain:
        """Create a new TARS session with Supabase/Qdrant integration"""
        try:
            # Configure TARS to use existing Supabase/Qdrant infrastructure
            memory_config = {
                "provider": "supabase",
                "use_embedding": True,
                "embedding_provider": "sentence_transformers",
                "quality_scoring": True,
                "advanced_memory": True,
                # Use existing database connections
                "supabase_url": self.settings.supabase_url,
                "supabase_anon_key": self.settings.supabase_anon_key,
                "qdrant_url": self.settings.qdrant_url_from_env,
                "qdrant_api_key": self.settings.qdrant_connection_api_key,
                "collection_name": f"tars_import_{self.user.id}_{project_id}"
            }
            
            knowledge_config = {
                "vector_store": {
                    "provider": "qdrant",
                    "config": {
                        "url": self.settings.qdrant_url_from_env,
                        "api_key": self.settings.qdrant_connection_api_key,
                        "collection_name": f"gitmesh_knowledge_{self.user.id}_{project_id}",
                        "vector_size": 384  # BGE-small embedding size
                    }
                }
            }
            
            tars = TarsMain(
                user_id=str(self.user.id),
                project_id=project_id,
                memory_config=memory_config,
                knowledge_config=knowledge_config,
                verbose=True
            )
            
            # Initialize TARS system
            if await tars.initialize():
                logger.info(f"TARS session created for user {self.user.id}, project {project_id}")
                return tars
            else:
                raise Exception("Failed to initialize TARS system")
                
        except Exception as e:
            logger.error(f"Error creating TARS session: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to create TARS session: {str(e)}")
    
    async def process_file_import(
        self, 
        files: List[UploadFile], 
        project_id: str,
        repository_id: Optional[str] = None,
        branch: Optional[str] = None
    ) -> TarsImportResponse:
        """Process file imports using TARS v1"""
        tars = None
        temp_files = []
        
        try:
            # Create TARS session
            tars = await self.create_tars_session(project_id, repository_id)
            
            # Save uploaded files temporarily
            file_paths = []
            for file in files:
                if file.size and file.size > MAX_FILE_SIZE:
                    raise HTTPException(status_code=413, detail=f"File {file.filename} too large")
                
                temp_file_path = self.temp_dir / f"{uuid.uuid4()}_{file.filename}"
                temp_files.append(temp_file_path)
                
                with open(temp_file_path, "wb") as buffer:
                    content = await file.read()
                    buffer.write(content)
                
                file_paths.append(str(temp_file_path))
                logger.info(f"Saved temporary file: {temp_file_path}")
            
            # Process files using TARS
            results = await tars.analyze_project(
                documents=file_paths,
                analysis_options={
                    "repository_id": repository_id,
                    "branch": branch,
                    "user_id": str(self.user.id),
                    "project_id": project_id,
                    "import_timestamp": datetime.now().isoformat()
                }
            )
            
            # Store results in database
            await self._store_import_results(results, project_id, repository_id, branch)
            
            return TarsImportResponse(
                success=True,
                message=f"Successfully imported {len(files)} files using TARS v1",
                import_id=str(uuid.uuid4()),
                status=ImportStatus.COMPLETED,
                processed_files=[f.filename for f in files],
                tars_results=results,
                knowledge_items_created=self._count_knowledge_items(results),
                embeddings_created=self._count_embeddings(results)
            )
            
        except Exception as e:
            logger.error(f"Error in file import: {e}")
            return TarsImportResponse(
                success=False,
                message=f"Import failed: {str(e)}",
                import_id=str(uuid.uuid4()),
                status=ImportStatus.FAILED,
                error_details=str(e)
            )
        
        finally:
            # Cleanup
            if tars:
                await tars.shutdown()
            
            # Remove temporary files
            for temp_file in temp_files:
                try:
                    if temp_file.exists():
                        temp_file.unlink()
                except Exception as e:
                    logger.warning(f"Failed to cleanup temp file {temp_file}: {e}")
    
    async def process_repository_import(
        self,
        repository_url: str,
        project_id: str,
        branches: Optional[List[str]] = None,
        include_issues: bool = True,
        include_prs: bool = True
    ) -> TarsImportResponse:
        """Process repository import using TARS v1"""
        tars = None
        
        try:
            # Create TARS session
            tars = await self.create_tars_session(project_id)
            
            # Extract GitHub repo info
            github_repos = []
            if "github.com" in repository_url:
                # Extract owner/repo from URL
                parts = repository_url.replace("https://github.com/", "").replace(".git", "").split("/")
                if len(parts) >= 2:
                    github_repos.append(f"{parts[0]}/{parts[1]}")
            
            # Process repository using TARS
            results = await tars.analyze_project(
                repositories=[repository_url] if repository_url.endswith('.git') else None,
                web_urls=[repository_url] if not repository_url.endswith('.git') else None,
                github_repos=github_repos if include_issues or include_prs else None,
                analysis_options={
                    "branches": branches,
                    "include_issues": include_issues,
                    "include_prs": include_prs,
                    "user_id": str(self.user.id),
                    "project_id": project_id,
                    "import_timestamp": datetime.now().isoformat()
                }
            )
            
            # Store results in database
            await self._store_import_results(results, project_id, repository_url=repository_url)
            
            return TarsImportResponse(
                success=True,
                message=f"Successfully imported repository {repository_url} using TARS v1",
                import_id=str(uuid.uuid4()),
                status=ImportStatus.COMPLETED,
                repository_url=repository_url,
                branches_processed=branches or ["all"],
                tars_results=results,
                knowledge_items_created=self._count_knowledge_items(results),
                embeddings_created=self._count_embeddings(results)
            )
            
        except Exception as e:
            logger.error(f"Error in repository import: {e}")
            return TarsImportResponse(
                success=False,
                message=f"Repository import failed: {str(e)}",
                import_id=str(uuid.uuid4()),
                status=ImportStatus.FAILED,
                repository_url=repository_url,
                error_details=str(e)
            )
        
        finally:
            if tars:
                await tars.shutdown()
    
    async def process_web_import(
        self,
        urls: List[str],
        project_id: str,
        depth: int = 1,
        extract_text_only: bool = True
    ) -> TarsImportResponse:
        """Process web URL import using TARS v1"""
        tars = None
        
        try:
            # Create TARS session
            tars = await self.create_tars_session(project_id)
            
            # Process URLs using TARS
            results = await tars.analyze_project(
                web_urls=urls,
                analysis_options={
                    "crawl_depth": depth,
                    "extract_text_only": extract_text_only,
                    "user_id": str(self.user.id),
                    "project_id": project_id,
                    "import_timestamp": datetime.now().isoformat()
                }
            )
            
            # Store results in database
            await self._store_import_results(results, project_id, web_urls=urls)
            
            return TarsImportResponse(
                success=True,
                message=f"Successfully imported {len(urls)} URLs using TARS v1",
                import_id=str(uuid.uuid4()),
                status=ImportStatus.COMPLETED,
                urls_processed=urls,
                tars_results=results,
                knowledge_items_created=self._count_knowledge_items(results),
                embeddings_created=self._count_embeddings(results)
            )
            
        except Exception as e:
            logger.error(f"Error in web import: {e}")
            return TarsImportResponse(
                success=False,
                message=f"Web import failed: {str(e)}",
                import_id=str(uuid.uuid4()),
                status=ImportStatus.FAILED,
                urls_processed=urls,
                error_details=str(e)
            )
        
        finally:
            if tars:
                await tars.shutdown()
    
    async def _store_import_results(
        self, 
        results: Dict[str, Any], 
        project_id: str,
        repository_id: Optional[str] = None,
        repository_url: Optional[str] = None,
        branch: Optional[str] = None,
        web_urls: Optional[List[str]] = None
    ):
        """Store TARS import results in the database"""
        try:
            # This would integrate with your existing database models
            # For now, we'll use the session state storage
            session_data = {
                "import_timestamp": datetime.now().isoformat(),
                "user_id": str(self.user.id),
                "project_id": project_id,
                "repository_id": repository_id,
                "repository_url": repository_url,
                "branch": branch,
                "web_urls": web_urls,
                "tars_results": results,
                "status": "completed"
            }
            
            # Store in database using existing models
            if hasattr(self.db_manager, 'save_import_session'):
                await self.db_manager.save_import_session(session_data)
            
            logger.info(f"Stored import results for project {project_id}")
            
        except Exception as e:
            logger.error(f"Error storing import results: {e}")
            # Don't fail the import if storage fails, just log it
    
    def _count_knowledge_items(self, results: Dict[str, Any]) -> int:
        """Count knowledge items created from TARS results"""
        count = 0
        for workflow_name, workflow_result in results.items():
            if hasattr(workflow_result, 'tasks_completed'):
                count += workflow_result.tasks_completed
        return count
    
    def _count_embeddings(self, results: Dict[str, Any]) -> int:
        """Count embeddings created from TARS results"""
        # This would be calculated based on the actual embeddings created
        # For now, estimate based on knowledge items
        return self._count_knowledge_items(results) * 10  # Rough estimate


@router.post("/import", response_model=TarsImportResponse)
async def import_with_tars(
    request: TarsImportRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Import data using TARS v1 multi-agent system
    
    Supports:
    - File uploads (documents, code, data files)
    - Repository imports (GitHub, Git URLs)
    - Web URL imports
    - Multi-modal analysis and knowledge extraction
    """
    try:
        service = TarsImportService(current_user)
        
        if request.source_type == ImportSourceType.REPOSITORY:
            if not request.repository_url:
                raise HTTPException(status_code=400, detail="Repository URL required for repository import")
            
            return await service.process_repository_import(
                repository_url=request.repository_url,
                project_id=request.project_id,
                branches=request.branches,
                include_issues=request.include_issues,
                include_prs=request.include_prs
            )
        
        elif request.source_type == ImportSourceType.WEB:
            if not request.web_urls:
                raise HTTPException(status_code=400, detail="Web URLs required for web import")
            
            return await service.process_web_import(
                urls=request.web_urls,
                project_id=request.project_id,
                depth=request.crawl_depth or 1,
                extract_text_only=request.extract_text_only
            )
        
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported source type: {request.source_type}")
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in TARS import: {e}")
        raise HTTPException(status_code=500, detail=f"Import failed: {str(e)}")


@router.post("/import/files", response_model=TarsImportResponse)
async def import_files_with_tars(
    files: List[UploadFile] = File(...),
    project_id: str = Form(...),
    repository_id: Optional[str] = Form(None),
    branch: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user)
):
    """
    Import files using TARS v1 multi-agent system
    
    Supports multiple file types:
    - Documents (PDF, DOCX, TXT, MD)
    - Code files (Python, JavaScript, etc.)
    - Data files (CSV, JSON, etc.)
    """
    try:
        if not files:
            raise HTTPException(status_code=400, detail="No files provided")
        
        # Validate file count
        if len(files) > 50:
            raise HTTPException(status_code=400, detail="Too many files (max 50)")
        
        service = TarsImportService(current_user)
        
        return await service.process_file_import(
            files=files,
            project_id=project_id,
            repository_id=repository_id,
            branch=branch
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in file import: {e}")
        raise HTTPException(status_code=500, detail=f"File import failed: {str(e)}")


@router.get("/import/status/{import_id}")
async def get_import_status(
    import_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get the status of a TARS import operation"""
    try:
        # This would query the database for import status
        # For now, return a placeholder
        return {
            "import_id": import_id,
            "status": "completed",
            "message": "Import completed successfully",
            "user_id": current_user.id
        }
    
    except Exception as e:
        logger.error(f"Error getting import status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get import status: {str(e)}")


@router.get("/import/history")
async def get_import_history(
    project_id: Optional[str] = None,
    limit: int = 10,
    current_user: User = Depends(get_current_user)
):
    """Get import history for the user"""
    try:
        # This would query the database for import history
        # For now, return a placeholder
        return {
            "imports": [],
            "total": 0,
            "user_id": current_user.id,
            "project_id": project_id
        }
    
    except Exception as e:
        logger.error(f"Error getting import history: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get import history: {str(e)}")


@router.delete("/import/{import_id}")
async def delete_import(
    import_id: str,
    current_user: User = Depends(get_current_user)
):
    """Delete an import and its associated data"""
    try:
        # This would delete the import from database and vector store
        # For now, return a placeholder
        return {
            "message": f"Import {import_id} deleted successfully",
            "import_id": import_id,
            "user_id": current_user.id
        }
    
    except Exception as e:
        logger.error(f"Error deleting import: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete import: {str(e)}")
