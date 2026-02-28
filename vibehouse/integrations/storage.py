"""Mock file-storage integration client.

Simulates a cloud storage service (S3 / GCS style) by returning
realistic fake upload URLs and file metadata without touching any
real object store.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from vibehouse.integrations.base import BaseIntegration


class StorageClient(BaseIntegration):
    """Mock cloud storage client returning realistic fake data."""

    STORAGE_BASE = "/storage"

    def __init__(self) -> None:
        super().__init__("storage")
        # In-memory registry so get_url / delete can reference prior uploads.
        self._files: dict[str, dict[str, Any]] = {}

    async def health_check(self) -> bool:
        self.logger.info("Storage client health check: OK (mock)")
        return True

    # ------------------------------------------------------------------
    # Upload
    # ------------------------------------------------------------------

    async def upload_file(
        self,
        file_content: bytes | str,
        filename: str,
        content_type: str = "application/octet-stream",
    ) -> dict[str, Any]:
        """Upload a file and return its storage metadata.

        The mock implementation does *not* persist the bytes -- it simply
        generates a storage key and records the metadata so that
        subsequent ``get_url`` and ``delete_file`` calls can reference
        the upload.
        """
        file_id = uuid.uuid4().hex
        file_key = f"{file_id}/{filename}"
        size = len(file_content) if isinstance(file_content, (bytes, str)) else 0

        record: dict[str, Any] = {
            "file_key": file_key,
            "filename": filename,
            "content_type": content_type,
            "size_bytes": size,
            "url": f"{self.STORAGE_BASE}/{file_key}",
            "uploaded_at": datetime.now(timezone.utc).isoformat(),
        }

        self._files[file_key] = record

        self.logger.info(
            "Mock file uploaded | key=%s | filename=%s | content_type=%s | size=%d bytes",
            file_key,
            filename,
            content_type,
            size,
        )

        return record

    # ------------------------------------------------------------------
    # Retrieve URL
    # ------------------------------------------------------------------

    async def get_url(self, file_key: str) -> str:
        """Return the access URL for a previously uploaded file.

        If the key is not found in the in-memory registry the method
        still returns a valid-looking URL (useful for tests that skip
        the upload step).
        """
        if file_key in self._files:
            url = self._files[file_key]["url"]
        else:
            url = f"{self.STORAGE_BASE}/{file_key}"

        self.logger.info("Resolved URL for key=%s -> %s", file_key, url)
        return url

    # ------------------------------------------------------------------
    # Delete
    # ------------------------------------------------------------------

    async def delete_file(self, file_key: str) -> bool:
        """Delete a file from storage.

        Returns ``True`` if the file existed (and was removed) or
        ``False`` if the key was not found.
        """
        existed = file_key in self._files
        self._files.pop(file_key, None)

        self.logger.info(
            "Mock file deleted | key=%s | existed=%s",
            file_key,
            existed,
        )
        return existed
