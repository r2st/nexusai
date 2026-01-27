"""File manager for code interpreter sessions."""

import base64
import hashlib
import mimetypes
import os
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

import aiofiles
import structlog

from app.core.config import settings

logger = structlog.get_logger()


@dataclass
class CodeFile:
    """Represents a file in the code interpreter session."""

    id: str
    session_id: str
    filename: str
    content_type: str
    size_bytes: int
    hash_sha256: str
    created_at: datetime
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "session_id": self.session_id,
            "filename": self.filename,
            "content_type": self.content_type,
            "size_bytes": self.size_bytes,
            "hash_sha256": self.hash_sha256,
            "created_at": self.created_at.isoformat(),
            "metadata": self.metadata,
        }


class CodeInterpreterFileManager:
    """Manages files for code interpreter sessions."""

    def __init__(self, base_dir: str | None = None):
        self.base_dir = Path(base_dir or settings.UPLOAD_DIR) / "code_interpreter"
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self._files: dict[str, CodeFile] = {}
        self._session_files: dict[str, list[str]] = {}  # session_id -> [file_ids]

    def _get_session_dir(self, session_id: str) -> Path:
        """Get the directory for a session."""
        session_dir = self.base_dir / session_id
        session_dir.mkdir(parents=True, exist_ok=True)
        return session_dir

    def _get_file_path(self, session_id: str, file_id: str, filename: str) -> Path:
        """Get the full path for a file."""
        session_dir = self._get_session_dir(session_id)
        # Use file_id prefix to avoid collisions
        safe_filename = f"{file_id[:8]}_{filename}"
        return session_dir / safe_filename

    async def upload_file(
        self,
        session_id: str,
        filename: str,
        content: bytes,
        metadata: dict[str, Any] | None = None,
    ) -> CodeFile:
        """Upload a file to a session."""
        file_id = str(uuid4())

        # Determine content type
        content_type, _ = mimetypes.guess_type(filename)
        if not content_type:
            content_type = "application/octet-stream"

        # Calculate hash
        hash_sha256 = hashlib.sha256(content).hexdigest()

        # Save file
        file_path = self._get_file_path(session_id, file_id, filename)
        async with aiofiles.open(file_path, "wb") as f:
            await f.write(content)

        # Create file record
        code_file = CodeFile(
            id=file_id,
            session_id=session_id,
            filename=filename,
            content_type=content_type,
            size_bytes=len(content),
            hash_sha256=hash_sha256,
            created_at=datetime.now(UTC),
            metadata=metadata or {},
        )

        # Store in memory
        self._files[file_id] = code_file
        if session_id not in self._session_files:
            self._session_files[session_id] = []
        self._session_files[session_id].append(file_id)

        logger.info(
            "File uploaded",
            file_id=file_id,
            session_id=session_id,
            filename=filename,
            size_bytes=len(content),
        )

        return code_file

    async def get_file(self, file_id: str) -> tuple[CodeFile, bytes] | None:
        """Get a file by ID."""
        code_file = self._files.get(file_id)
        if not code_file:
            return None

        file_path = self._get_file_path(
            code_file.session_id,
            file_id,
            code_file.filename,
        )

        if not file_path.exists():
            return None

        async with aiofiles.open(file_path, "rb") as f:
            content = await f.read()

        return code_file, content

    async def get_file_as_base64(self, file_id: str) -> tuple[CodeFile, str] | None:
        """Get a file as base64-encoded string."""
        result = await self.get_file(file_id)
        if not result:
            return None

        code_file, content = result
        return code_file, base64.b64encode(content).decode("utf-8")

    async def delete_file(self, file_id: str) -> bool:
        """Delete a file by ID."""
        code_file = self._files.get(file_id)
        if not code_file:
            return False

        file_path = self._get_file_path(
            code_file.session_id,
            file_id,
            code_file.filename,
        )

        if file_path.exists():
            os.remove(file_path)

        # Remove from memory
        del self._files[file_id]
        if code_file.session_id in self._session_files:
            self._session_files[code_file.session_id].remove(file_id)

        logger.info("File deleted", file_id=file_id)
        return True

    def list_session_files(self, session_id: str) -> list[CodeFile]:
        """List all files in a session."""
        file_ids = self._session_files.get(session_id, [])
        return [self._files[fid] for fid in file_ids if fid in self._files]

    async def cleanup_session(self, session_id: str) -> int:
        """Clean up all files in a session."""
        file_ids = self._session_files.get(session_id, []).copy()
        deleted_count = 0

        for file_id in file_ids:
            if await self.delete_file(file_id):
                deleted_count += 1

        # Remove session directory
        session_dir = self._get_session_dir(session_id)
        if session_dir.exists():
            import shutil
            shutil.rmtree(session_dir, ignore_errors=True)

        # Remove session from tracking
        if session_id in self._session_files:
            del self._session_files[session_id]

        logger.info(
            "Session files cleaned up",
            session_id=session_id,
            deleted_count=deleted_count,
        )

        return deleted_count

    async def save_execution_output(
        self,
        session_id: str,
        filename: str,
        content: bytes,
        execution_id: str,
    ) -> CodeFile:
        """Save output file from code execution."""
        return await self.upload_file(
            session_id=session_id,
            filename=filename,
            content=content,
            metadata={
                "source": "execution_output",
                "execution_id": execution_id,
            },
        )

    def get_files_for_execution(
        self,
        session_id: str,
    ) -> dict[str, str]:
        """Get all files as base64 for passing to execution."""
        files = self.list_session_files(session_id)
        result = {}

        for code_file in files:
            file_path = self._get_file_path(
                session_id,
                code_file.id,
                code_file.filename,
            )

            if file_path.exists():
                with open(file_path, "rb") as f:
                    content = f.read()
                result[code_file.filename] = base64.b64encode(content).decode("utf-8")

        return result


# Global file manager instance
code_file_manager = CodeInterpreterFileManager()
