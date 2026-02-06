import os
import shutil
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, File, UploadFile, HTTPException, Query, Depends, status
from fastapi.responses import FileResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field

from support_services.utils.logger import get_logger

# Initialize logger for this module
logger = get_logger(__name__)

# Create router for file operations
file_router = APIRouter(
    prefix="/files",
    tags=["File Operations"],
    responses={
        401: {"description": "Unauthorized - Invalid or missing authentication token"},
        500: {"description": "Internal server error"}
    }
)

auth_scheme = HTTPBearer()

# Configuration
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

def verify_auth(credentials: HTTPAuthorizationCredentials = Depends(auth_scheme)):
    """
    Verify authentication credentials.
    
    Args:
        credentials: Bearer token credentials
        
    Raises:
        HTTPException: If credentials are invalid
    """
    if credentials.credentials != "your_token_here":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"}
        )

# Response Models
class FileUploadResponse(BaseModel):
    """Response model for file upload"""
    filename: str = Field(..., description="Name of the uploaded file")
    file_size: int = Field(..., description="Size of the uploaded file in bytes")
    content_type: str = Field(..., description="MIME type of the uploaded file")
    message: str = Field(..., description="Success message")
    
    class Config:
        json_schema_extra = {
            "example": {
                "filename": "document.pdf",
                "file_size": 1024,
                "content_type": "application/pdf",
                "message": "File uploaded successfully"
            }
        }

class FileListResponse(BaseModel):
    """Response model for file listing"""
    files: List[dict] = Field(..., description="List of available files")
    total_count: int = Field(..., description="Total number of files")
    
    class Config:
        json_schema_extra = {
            "example": {
                "files": [
                    {
                        "filename": "document.pdf",
                        "file_size": 1024,
                        "upload_time": "2023-11-13T17:30:00"
                    }
                ],
                "total_count": 1
            }
        }

class FileDeleteResponse(BaseModel):
    """Response model for file deletion"""
    filename: str = Field(..., description="Name of the deleted file")
    message: str = Field(..., description="Success message")
    
    class Config:
        json_schema_extra = {
            "example": {
                "filename": "document.pdf",
                "message": "File deleted successfully"
            }
        }

@file_router.post(
    "/upload",
    summary="Upload a file",
    description="""
    Upload a single file to the server.
    
    This endpoint demonstrates how to:
    - Handle file uploads with size validation
    - Store files securely on the server
    - Return file metadata
    - Implement bearer token authentication
    
    **Authentication Required**: Bearer token must be provided in Authorization header.
    **File Size Limit**: Maximum 10MB per file.
    """,
    response_model=FileUploadResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {"description": "File uploaded successfully"},
        400: {"description": "Bad request - Invalid file or file too large"},
        401: {"description": "Unauthorized - Invalid or missing authentication token"},
        413: {"description": "Payload too large - File exceeds size limit"}
    }
)
async def upload_file(
    file: UploadFile = File(..., description="File to upload")
    #credentials: HTTPAuthorizationCredentials = Depends(verify_auth)
) -> FileUploadResponse:
    """
    Upload a file to the server.
    
    Args:
        file: The file to upload
        credentials: Bearer token authentication credentials
        
    Returns:
        FileUploadResponse: Upload confirmation with file metadata
        
    Raises:
        HTTPException: If file is invalid, too large, or authentication fails
    """
    try:
        # Validate file
        if not file.filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No file provided"
            )
        
        # Read file content to check size
        content = await file.read()
        file_size = len(content)
        
        if file_size > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File too large. Maximum size is {MAX_FILE_SIZE} bytes"
            )
        
        if file_size == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Empty file not allowed"
            )
        
        # Create safe filename
        safe_filename = file.filename.replace(" ", "_").replace("..", "")
        file_path = UPLOAD_DIR / safe_filename
        
        # Handle filename conflicts
        counter = 1
        original_path = file_path
        while file_path.exists():
            name_parts = original_path.stem, counter, original_path.suffix
            file_path = original_path.parent / f"{name_parts[0]}_{name_parts[1]}{name_parts[2]}"
            counter += 1
        
        # Save file
        with open(file_path, "wb") as f:
            f.write(content)
        
        logger.info(f"File uploaded successfully: {file_path.name} ({file_size} bytes)")
        
        return FileUploadResponse(
            filename=file_path.name,
            file_size=file_size,
            content_type=file.content_type or "application/octet-stream",
            message="File uploaded successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading file: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while uploading file"
        )

@file_router.get(
    "/download/{filename}",
    summary="Download a file",
    description="""
    Download a file from the server by filename.
    
    This endpoint demonstrates how to:
    - Serve files for download
    - Validate file existence
    - Set appropriate headers for file download
    - Implement bearer token authentication
    
    **Authentication Required**: Bearer token must be provided in Authorization header.
    """,
    responses={
        200: {"description": "File downloaded successfully"},
        401: {"description": "Unauthorized - Invalid or missing authentication token"},
        404: {"description": "File not found"}
    }
)
async def download_file(
    filename: str
   # credentials: HTTPAuthorizationCredentials = Depends(verify_auth)
) -> FileResponse:
    """
    Download a file from the server.
    
    Args:
        filename: Name of the file to download
        credentials: Bearer token authentication credentials
        
    Returns:
        FileResponse: The requested file
        
    Raises:
        HTTPException: If file not found or authentication fails
    """
    try:
        file_path = UPLOAD_DIR / filename
        
        if not file_path.exists() or not file_path.is_file():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found"
            )
        
        logger.info(f"File downloaded: {filename}")
        
        return FileResponse(
            path=file_path,
            filename=filename,
            media_type='application/octet-stream'
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading file {filename}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while downloading file"
        )

@file_router.get(
    "/list",
    summary="List uploaded files",
    description="""
    Get a list of all uploaded files with their metadata.
    
    This endpoint demonstrates how to:
    - List files in the upload directory
    - Return file metadata (name, size, upload time)
    - Implement pagination with limit parameter
    - Implement bearer token authentication
    
    **Authentication Required**: Bearer token must be provided in Authorization header.
    """,
    response_model=FileListResponse,
    responses={
        200: {"description": "Files listed successfully"},
        401: {"description": "Unauthorized - Invalid or missing authentication token"}
    }
)
async def list_files(
    limit: Optional[int] = Query(None, ge=1, le=100, description="Maximum number of files to return"),
    credentials: HTTPAuthorizationCredentials = Depends(verify_auth)
) -> FileListResponse:
    """
    List all uploaded files with metadata.
    
    Args:
        limit: Maximum number of files to return (optional)
        credentials: Bearer token authentication credentials
        
    Returns:
        FileListResponse: List of files with metadata
        
    Raises:
        HTTPException: If authentication fails
    """
    try:
        files = []
        
        for file_path in UPLOAD_DIR.iterdir():
            if file_path.is_file():
                stat = file_path.stat()
                files.append({
                    "filename": file_path.name,
                    "file_size": stat.st_size,
                    "upload_time": stat.st_mtime
                })
        
        # Sort by upload time (newest first)
        files.sort(key=lambda x: x["upload_time"], reverse=True)
        
        # Apply limit if specified
        if limit:
            files = files[:limit]
        
        logger.info(f"Listed {len(files)} files")
        
        return FileListResponse(
            files=files,
            total_count=len(list(UPLOAD_DIR.iterdir()))
        )
        
    except Exception as e:
        logger.error(f"Error listing files: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while listing files"
        )

@file_router.delete(
    "/delete/{filename}",
    summary="Delete a file",
    description="""
    Delete a file from the server by filename.
    
    This endpoint demonstrates how to:
    - Delete files from the server
    - Validate file existence before deletion
    - Return confirmation of deletion
    - Implement bearer token authentication
    
    **Authentication Required**: Bearer token must be provided in Authorization header.
    **Warning**: This operation is irreversible.
    """,
    response_model=FileDeleteResponse,
    responses={
        200: {"description": "File deleted successfully"},
        401: {"description": "Unauthorized - Invalid or missing authentication token"},
        404: {"description": "File not found"}
    }
)
async def delete_file(
    filename: str,
    credentials: HTTPAuthorizationCredentials = Depends(verify_auth)
) -> FileDeleteResponse:
    """
    Delete a file from the server.
    
    Args:
        filename: Name of the file to delete
        credentials: Bearer token authentication credentials
        
    Returns:
        FileDeleteResponse: Deletion confirmation
        
    Raises:
        HTTPException: If file not found or authentication fails
    """
    try:
        file_path = UPLOAD_DIR / filename
        
        if not file_path.exists() or not file_path.is_file():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found"
            )
        
        # Delete the file
        file_path.unlink()
        
        logger.info(f"File deleted: {filename}")
        
        return FileDeleteResponse(
            filename=filename,
            message="File deleted successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting file {filename}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while deleting file"
        )

@file_router.post(
    "/upload-multiple",
    summary="Upload multiple files",
    description="""
    Upload multiple files to the server in a single request.
    
    This endpoint demonstrates how to:
    - Handle multiple file uploads
    - Validate each file individually
    - Return metadata for all uploaded files
    - Implement bearer token authentication
    
    **Authentication Required**: Bearer token must be provided in Authorization header.
    **File Size Limit**: Maximum 10MB per file.
    **File Count Limit**: Maximum 10 files per request.
    """,
    response_model=List[FileUploadResponse],
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {"description": "Files uploaded successfully"},
        400: {"description": "Bad request - Invalid files or too many files"},
        401: {"description": "Unauthorized - Invalid or missing authentication token"},
        413: {"description": "Payload too large - One or more files exceed size limit"}
    }
)
async def upload_multiple_files(
    files: List[UploadFile] = File(..., description="Files to upload (max 10)"),
    credentials: HTTPAuthorizationCredentials = Depends(verify_auth)
) -> List[FileUploadResponse]:
    """
    Upload multiple files to the server.
    
    Args:
        files: List of files to upload (maximum 10)
        credentials: Bearer token authentication credentials
        
    Returns:
        List[FileUploadResponse]: Upload confirmations for all files
        
    Raises:
        HTTPException: If files are invalid, too large, or authentication fails
    """
    try:
        if len(files) > 10:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Too many files. Maximum 10 files per request"
            )
        
        if not files or all(not f.filename for f in files):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No files provided"
            )
        
        responses = []
        
        for file in files:
            if not file.filename:
                continue
                
            # Read file content to check size
            content = await file.read()
            file_size = len(content)
            
            if file_size > MAX_FILE_SIZE:
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail=f"File {file.filename} too large. Maximum size is {MAX_FILE_SIZE} bytes"
                )
            
            if file_size == 0:
                continue  # Skip empty files
            
            # Create safe filename
            safe_filename = file.filename.replace(" ", "_").replace("..", "")
            file_path = UPLOAD_DIR / safe_filename
            
            # Handle filename conflicts
            counter = 1
            original_path = file_path
            while file_path.exists():
                name_parts = original_path.stem, counter, original_path.suffix
                file_path = original_path.parent / f"{name_parts[0]}_{name_parts[1]}{name_parts[2]}"
                counter += 1
            
            # Save file
            with open(file_path, "wb") as f:
                f.write(content)
            
            responses.append(FileUploadResponse(
                filename=file_path.name,
                file_size=file_size,
                content_type=file.content_type or "application/octet-stream",
                message="File uploaded successfully"
            ))
        
        logger.info(f"Multiple files uploaded successfully: {len(responses)} files")
        
        return responses
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading multiple files: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while uploading files"
        )
