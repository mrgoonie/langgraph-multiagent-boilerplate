"""
Storage service for managing files in Cloudflare R2
"""
import os
import boto3
from botocore.exceptions import ClientError
from typing import BinaryIO, Dict, List, Optional, Union
import uuid

from app.core.config import settings


class StorageService:
    """Service for cloud storage operations using Cloudflare R2"""
    
    def __init__(self):
        """Initialize the R2 client and check required settings"""
        if not all([
            settings.r2_endpoint,
            settings.r2_bucket_name,
            settings.r2_access_key_id,
            settings.r2_secret_access_key
        ]):
            self.client = None
            self.bucket_name = None
        else:
            self.client = boto3.client(
                's3',
                endpoint_url=settings.r2_endpoint,
                aws_access_key_id=settings.r2_access_key_id,
                aws_secret_access_key=settings.r2_secret_access_key,
                region_name='auto'  # Cloudflare R2 uses 'auto' as region name
            )
            self.bucket_name = settings.r2_bucket_name
    
    def is_configured(self) -> bool:
        """Check if storage is properly configured"""
        return self.client is not None and self.bucket_name is not None
    
    def generate_key(self, folder: str, filename: str) -> str:
        """
        Generate a storage key for a file
        
        Args:
            folder: The folder to store the file in
            filename: The original filename
            
        Returns:
            A unique key for the file
        """
        # Extract file extension
        ext = os.path.splitext(filename)[1].lower()
        
        # Generate a UUID as the base filename
        unique_id = str(uuid.uuid4())
        
        # Combine folder, UUID, and extension
        return f"{folder}/{unique_id}{ext}"
    
    async def upload_file(
        self, 
        file_content: Union[BinaryIO, bytes], 
        folder: str,
        filename: str, 
        content_type: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None
    ) -> Optional[str]:
        """
        Upload a file to R2 storage
        
        Args:
            file_content: The file content as bytes or file-like object
            folder: The folder to store the file in
            filename: The original filename
            content_type: The MIME type of the file
            metadata: Additional metadata to store with the file
            
        Returns:
            The storage key if successful, None otherwise
        """
        if not self.is_configured():
            raise ValueError("Storage is not configured properly")
        
        key = self.generate_key(folder, filename)
        
        extra_args = {}
        if content_type:
            extra_args['ContentType'] = content_type
        if metadata:
            extra_args['Metadata'] = metadata
        
        try:
            self.client.upload_fileobj(
                file_content if hasattr(file_content, 'read') else BytesIO(file_content),
                self.bucket_name,
                key,
                ExtraArgs=extra_args
            )
            return key
        except ClientError as e:
            print(f"Error uploading file to R2: {e}")
            return None
    
    async def download_file(self, key: str) -> Optional[bytes]:
        """
        Download a file from R2 storage
        
        Args:
            key: The storage key of the file
            
        Returns:
            The file content as bytes if successful, None otherwise
        """
        if not self.is_configured():
            raise ValueError("Storage is not configured properly")
        
        try:
            response = self.client.get_object(Bucket=self.bucket_name, Key=key)
            return response['Body'].read()
        except ClientError as e:
            print(f"Error downloading file from R2: {e}")
            return None
    
    async def delete_file(self, key: str) -> bool:
        """
        Delete a file from R2 storage
        
        Args:
            key: The storage key of the file
            
        Returns:
            True if deletion was successful, False otherwise
        """
        if not self.is_configured():
            raise ValueError("Storage is not configured properly")
        
        try:
            self.client.delete_object(Bucket=self.bucket_name, Key=key)
            return True
        except ClientError as e:
            print(f"Error deleting file from R2: {e}")
            return False
    
    async def get_file_url(self, key: str, expiration: int = 3600) -> Optional[str]:
        """
        Generate a presigned URL for a file
        
        Args:
            key: The storage key of the file
            expiration: The URL expiration time in seconds
            
        Returns:
            A presigned URL if successful, None otherwise
        """
        if not self.is_configured():
            raise ValueError("Storage is not configured properly")
        
        try:
            url = self.client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': self.bucket_name,
                    'Key': key
                },
                ExpiresIn=expiration
            )
            return url
        except ClientError as e:
            print(f"Error generating presigned URL: {e}")
            return None
    
    async def list_files(self, prefix: str = "") -> List[Dict]:
        """
        List files in the bucket with an optional prefix
        
        Args:
            prefix: The prefix to filter files by
            
        Returns:
            A list of file information dictionaries
        """
        if not self.is_configured():
            raise ValueError("Storage is not configured properly")
        
        try:
            response = self.client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=prefix
            )
            
            files = []
            if 'Contents' in response:
                for obj in response['Contents']:
                    files.append({
                        'key': obj['Key'],
                        'size': obj['Size'],
                        'last_modified': obj['LastModified'],
                    })
            
            return files
        except ClientError as e:
            print(f"Error listing files from R2: {e}")
            return []


# Create a singleton instance
storage_service = StorageService()
