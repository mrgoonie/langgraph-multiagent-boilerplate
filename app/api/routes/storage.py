"""
API routes for storage operations
"""
from typing import List, Optional
import uuid
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
import io

from app.db.base import get_db
from app.services.storage_service import storage_service
from app.schemas.storage import FileResponse, PresignedUrlResponse


router = APIRouter(prefix="/storage", tags=["storage"])


@router.post("/upload", response_model=FileResponse, status_code=status.HTTP_201_CREATED)
async def upload_file(
    file: UploadFile = File(...),
    folder: str = Form("default"),
    metadata: Optional[str] = Form(None),
):
    """
    Upload a file to cloud storage
    
    - **file**: The file to upload
    - **folder**: The folder to store the file in (default: "default")
    - **metadata**: Optional JSON string of metadata to store with the file
    """
    # Check if storage is configured
    if not storage_service.is_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Cloud storage is not configured"
        )
    
    # Process metadata if provided
    file_metadata = {}
    if metadata:
        try:
            file_metadata = json.loads(metadata)
        except json.JSONDecodeError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid metadata JSON format"
            )
    
    # Get content type
    content_type = file.content_type
    
    # Read file content
    file_content = await file.read()
    
    # Upload file to storage
    key = await storage_service.upload_file(
        file_content=io.BytesIO(file_content),
        folder=folder,
        filename=file.filename,
        content_type=content_type,
        metadata=file_metadata
    )
    
    if not key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload file to storage"
        )
    
    # Generate URL
    url = await storage_service.get_file_url(key)
    
    return FileResponse(
        key=key,
        filename=file.filename,
        content_type=content_type,
        size=len(file_content),
        url=url,
        metadata=file_metadata
    )


@router.get("/files/{key}", response_model=None)
async def download_file(key: str):
    """
    Download a file from storage
    
    - **key**: The storage key of the file
    """
    # Check if storage is configured
    if not storage_service.is_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Cloud storage is not configured"
        )
    
    # Download file content
    content = await storage_service.download_file(key)
    
    if not content:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found or access denied"
        )
    
    # Extract filename from key
    filename = key.split("/")[-1]
    
    # Create a streaming response
    return StreamingResponse(
        io.BytesIO(content),
        media_type="application/octet-stream",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/urls/{key}", response_model=PresignedUrlResponse)
async def get_file_url(key: str, expiration: int = 3600):
    """
    Get a presigned URL for a file
    
    - **key**: The storage key of the file
    - **expiration**: URL expiration time in seconds (default: 3600)
    """
    # Check if storage is configured
    if not storage_service.is_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Cloud storage is not configured"
        )
    
    # Generate URL
    url = await storage_service.get_file_url(key, expiration)
    
    if not url:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found or access denied"
        )
    
    return PresignedUrlResponse(url=url, expires_in=expiration)


@router.delete("/files/{key}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_file(key: str):
    """
    Delete a file from storage
    
    - **key**: The storage key of the file
    """
    # Check if storage is configured
    if not storage_service.is_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Cloud storage is not configured"
        )
    
    # Delete the file
    success = await storage_service.delete_file(key)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found or deletion failed"
        )
    
    return None


@router.get("/files", response_model=List[FileResponse])
async def list_files(prefix: str = ""):
    """
    List files in storage
    
    - **prefix**: Optional prefix to filter files by
    """
    # Check if storage is configured
    if not storage_service.is_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Cloud storage is not configured"
        )
    
    # List files
    files = await storage_service.list_files(prefix)
    
    # Get URLs for each file
    response_files = []
    for file in files:
        url = await storage_service.get_file_url(file['key'])
        filename = file['key'].split("/")[-1]
        
        response_files.append(
            FileResponse(
                key=file['key'],
                filename=filename,
                size=file['size'],
                url=url,
                last_modified=file['last_modified']
            )
        )
    
    return response_files
