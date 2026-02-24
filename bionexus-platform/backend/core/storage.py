"""Storage abstraction layer for file management.

Supports local (SQLite/PostgreSQL) storage for development
and S3/GCS for production. Files are NEVER deleted -- only soft-deleted.

Usage:
    from core.storage import storage_service

    # Upload
    raw_file = storage_service.store_file(file_bytes, filename, tenant, user)

    # Retrieve
    content = storage_service.get_file_content(raw_file)

    # Verify integrity
    is_valid = storage_service.verify_integrity(raw_file)
"""

import hashlib
from django.conf import settings


class StorageService:
    """Abstraction layer for file storage (local dev / S3 production)."""

    def get_backend(self):
        """Return the configured storage backend."""
        return getattr(settings, 'FILE_STORAGE_BACKEND', 'local')

    def compute_hash(self, content: bytes) -> str:
        """Compute SHA-256 hash of file content."""
        return hashlib.sha256(content).hexdigest()

    def store_file(self, content: bytes, filename: str, tenant, user=None):
        """Store a file using the configured backend.

        Returns a RawFile instance.
        """
        from core.models import RawFile

        file_hash = self.compute_hash(content)
        backend = self.get_backend()

        # Check for duplicate
        existing = RawFile.objects.filter(file_hash=file_hash).first()
        if existing:
            return existing

        raw_file = RawFile(
            tenant=tenant,
            user=user,
            filename=filename,
            file_hash=file_hash,
            file_size=len(content),
            mime_type=self._guess_mime(filename),
            storage_backend=backend,
        )

        if backend == 'local':
            raw_file.file_content = content
            raw_file.storage_path = ''
        elif backend == 's3':
            path = self._upload_to_s3(content, filename, tenant)
            raw_file.storage_path = path
            raw_file.file_content = None
        elif backend == 'gcs':
            path = self._upload_to_gcs(content, filename, tenant)
            raw_file.storage_path = path
            raw_file.file_content = None

        raw_file.save()
        return raw_file

    def get_file_content(self, raw_file) -> bytes:
        """Retrieve file content from storage."""
        if raw_file.storage_backend == 'local':
            return bytes(raw_file.file_content)
        elif raw_file.storage_backend == 's3':
            return self._download_from_s3(raw_file.storage_path)
        elif raw_file.storage_backend == 'gcs':
            return self._download_from_gcs(raw_file.storage_path)
        raise ValueError(f"Unknown storage backend: {raw_file.storage_backend}")

    def verify_integrity(self, raw_file) -> bool:
        """Verify that stored file matches its SHA-256 hash."""
        content = self.get_file_content(raw_file)
        actual_hash = self.compute_hash(content)
        return actual_hash == raw_file.file_hash

    def _guess_mime(self, filename: str) -> str:
        ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
        return {
            'csv': 'text/csv',
            'pdf': 'application/pdf',
            'json': 'application/json',
            'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'txt': 'text/plain',
        }.get(ext, 'application/octet-stream')

    def _upload_to_s3(self, content, filename, tenant):
        """Upload to S3. Requires boto3 + AWS credentials in settings."""
        import boto3
        bucket = getattr(settings, 'AWS_S3_BUCKET', 'bionexus-files')
        key = f"{tenant.slug}/{filename}"
        client = boto3.client('s3')
        client.put_object(Bucket=bucket, Key=key, Body=content)
        return f"s3://{bucket}/{key}"

    def _download_from_s3(self, path):
        """Download from S3."""
        import boto3
        parts = path.replace('s3://', '').split('/', 1)
        bucket, key = parts[0], parts[1]
        client = boto3.client('s3')
        response = client.get_object(Bucket=bucket, Key=key)
        return response['Body'].read()

    def _upload_to_gcs(self, content, filename, tenant):
        """Upload to Google Cloud Storage."""
        from google.cloud import storage as gcs_storage
        bucket_name = getattr(settings, 'GCS_BUCKET', 'bionexus-files')
        client = gcs_storage.Client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(f"{tenant.slug}/{filename}")
        blob.upload_from_string(content)
        return f"gcs://{bucket_name}/{tenant.slug}/{filename}"

    def _download_from_gcs(self, path):
        """Download from Google Cloud Storage."""
        from google.cloud import storage as gcs_storage
        parts = path.replace('gcs://', '').split('/', 1)
        bucket_name, key = parts[0], parts[1]
        client = gcs_storage.Client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(key)
        return blob.download_as_bytes()


# Singleton
storage_service = StorageService()
