"""
MinIO storage service for file uploads and management.
"""
import os
from typing import Optional
from datetime import datetime, timedelta
from urllib.parse import urljoin

from minio import Minio
from minio.error import S3Error
from fastapi import UploadFile

from src.core.config import settings


class StorageService:
    """MinIO storage service for handling file uploads and downloads."""

    def __init__(self):
        """Initialize MinIO client."""
        self.client = Minio(
            settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_secure
        )
        self.bucket_name = settings.minio_bucket_name
        self._ensure_bucket_exists()

    def _ensure_bucket_exists(self):
        """Ensure the bucket exists, create if it doesn't."""
        try:
            if not self.client.bucket_exists(self.bucket_name):
                self.client.make_bucket(self.bucket_name)
        except S3Error as e:
            raise Exception(f"Failed to create/access bucket: {e}")

    async def upload_file(
        self,
        file: UploadFile,
        folder: str = "",
        content_type: Optional[str] = None
    ) -> str:
        """Upload a file to MinIO and return the URL."""
        try:
            # Generate unique filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            original_filename = file.filename or "unknown"
            file_extension = os.path.splitext(original_filename)[1]
            unique_filename = f"{timestamp}_{os.urandom(8).hex()}{file_extension}"

            # Create full object name with folder
            object_name = f"{folder}/{unique_filename}" if folder else unique_filename

            # Read file content
            file_content = await file.read()

            # Determine content type
            if not content_type:
                content_type = file.content_type or "application/octet-stream"

            # Upload to MinIO
            self.client.put_object(
                bucket_name=self.bucket_name,
                object_name=object_name,
                data=file_content,
                length=len(file_content),
                content_type=content_type
            )

            # Generate URL
            if settings.minio_secure:
                base_url = f"https://{settings.minio_endpoint}"
            else:
                base_url = f"http://{settings.minio_endpoint}"

            file_url = f"{base_url}/{self.bucket_name}/{object_name}"

            return file_url

        except S3Error as e:
            raise Exception(f"Failed to upload file: {e}")
        except Exception as e:
            raise Exception(f"Unexpected error during upload: {e}")

    def generate_presigned_url(
        self,
        object_name: str,
        expires: timedelta = timedelta(hours=1)
    ) -> str:
        """Generate a presigned URL for accessing a file."""
        try:
            url = self.client.presigned_get_object(
                bucket_name=self.bucket_name,
                object_name=object_name,
                expires=expires
            )
            return url
        except S3Error as e:
            raise Exception(f"Failed to generate presigned URL: {e}")

    def delete_file(self, object_name: str) -> bool:
        """Delete a file from MinIO."""
        try:
            self.client.remove_object(self.bucket_name, object_name)
            return True
        except S3Error as e:
            print(f"Failed to delete file {object_name}: {e}")
            return False

    def get_file_info(self, object_name: str) -> Optional[dict]:
        """Get file information."""
        try:
            stat = self.client.stat_object(self.bucket_name, object_name)
            return {
                "size": stat.size,
                "last_modified": stat.last_modified,
                "content_type": stat.content_type,
                "etag": stat.etag
            }
        except S3Error as e:
            print(f"Failed to get file info for {object_name}: {e}")
            return None

    def list_files(self, prefix: str = "", recursive: bool = False) -> list:
        """List files in the bucket with optional prefix."""
        try:
            objects = self.client.list_objects(
                self.bucket_name,
                prefix=prefix,
                recursive=recursive
            )
            return [obj.object_name for obj in objects]
        except S3Error as e:
            print(f"Failed to list files with prefix {prefix}: {e}")
            return []
