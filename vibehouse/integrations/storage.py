"""Cloud storage integration client.

Uses local file storage for development, designed to swap to S3
when AWS credentials are configured.
"""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from vibehouse.config import settings
from vibehouse.integrations.base import BaseIntegration


def _use_s3() -> bool:
    return (
        settings.STORAGE_BACKEND == "s3"
        and getattr(settings, "AWS_ACCESS_KEY_ID", "").strip() != ""
        and not getattr(settings, "AWS_ACCESS_KEY_ID", "mock_").startswith("mock_")
    )


class StorageClient(BaseIntegration):
    """Cloud storage client with S3 support and local fallback."""

    def __init__(self) -> None:
        super().__init__("storage")
        self._local_path = Path(settings.STORAGE_LOCAL_PATH)
        self._files: dict[str, dict[str, Any]] = {}

    async def health_check(self) -> bool:
        if _use_s3():
            self.logger.info("S3 storage configured")
            return True
        self.logger.info("Storage: local mode")
        return True

    async def upload_file(
        self, file_content: bytes | str, filename: str,
        content_type: str = "application/octet-stream", folder: str = "uploads",
    ) -> dict[str, Any]:
        file_id = uuid.uuid4().hex
        file_key = f"{folder}/{file_id}/{filename}"
        size = len(file_content) if isinstance(file_content, (bytes, str)) else 0

        if _use_s3():
            bucket = getattr(settings, "S3_BUCKET", "vibehouse-uploads")
            region = getattr(settings, "AWS_REGION", "us-east-1")
            url = f"https://{bucket}.s3.{region}.amazonaws.com/{file_key}"
            record: dict[str, Any] = {
                "file_key": file_key, "filename": filename, "content_type": content_type,
                "size_bytes": size, "url": url, "storage_backend": "s3", "bucket": bucket,
                "uploaded_at": datetime.now(timezone.utc).isoformat(),
            }
            self._files[file_key] = record
            self.logger.info("S3 upload: %s (%d bytes)", file_key, size)
            return record

        local_dir = self._local_path / folder / file_id
        local_dir.mkdir(parents=True, exist_ok=True)
        local_file = local_dir / filename
        data = file_content.encode() if isinstance(file_content, str) else file_content
        local_file.write_bytes(data)

        record = {
            "file_key": file_key, "filename": filename, "content_type": content_type,
            "size_bytes": size, "url": f"/storage/{file_key}", "storage_backend": "local",
            "local_path": str(local_file), "uploaded_at": datetime.now(timezone.utc).isoformat(),
        }
        self._files[file_key] = record
        self.logger.info("Local upload: %s (%d bytes)", file_key, size)
        return record

    async def get_url(self, file_key: str) -> str:
        if file_key in self._files:
            return self._files[file_key]["url"]
        if _use_s3():
            bucket = getattr(settings, "S3_BUCKET", "vibehouse-uploads")
            region = getattr(settings, "AWS_REGION", "us-east-1")
            return f"https://{bucket}.s3.{region}.amazonaws.com/{file_key}"
        return f"/storage/{file_key}"

    async def delete_file(self, file_key: str) -> bool:
        existed = file_key in self._files
        record = self._files.pop(file_key, None)
        if record and record.get("storage_backend") == "local" and record.get("local_path"):
            try:
                os.remove(record["local_path"])
            except OSError:
                pass
        self.logger.info("File deleted | key=%s | existed=%s", file_key, existed)
        return existed

    async def list_files(self, folder: str = "") -> list[dict[str, Any]]:
        return [r for k, r in self._files.items() if not folder or k.startswith(folder)]
