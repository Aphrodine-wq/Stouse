import uuid

from fastapi import APIRouter, Depends, File, Form, UploadFile
from pydantic import BaseModel as PydanticModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from vibehouse.api.deps import get_current_user, get_db
from vibehouse.common.enums import UserRole
from vibehouse.common.exceptions import NotFoundError, PermissionDeniedError
from vibehouse.db.models.document import Document
from vibehouse.db.models.project import Project
from vibehouse.db.models.user import User
from vibehouse.integrations.storage import StorageClient

router = APIRouter(prefix="/documents", tags=["Documents"])

ALLOWED_TYPES = {
    "application/pdf", "image/jpeg", "image/png", "image/webp",
    "application/msword", "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.ms-excel", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "text/plain", "text/csv",
}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB


# ---------- Schemas ----------


class DocumentResponse(PydanticModel):
    id: uuid.UUID
    project_id: uuid.UUID
    filename: str
    content_type: str
    size_bytes: int
    category: str
    description: str | None
    url: str
    created_at: str
    model_config = {"from_attributes": True}


# ---------- Endpoints ----------


@router.post("/{project_id}/upload", response_model=DocumentResponse, status_code=201)
async def upload_document(
    project_id: uuid.UUID,
    file: UploadFile = File(...),
    category: str = Form("general"),
    description: str = Form(""),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Verify project access
    result = await db.execute(
        select(Project).where(Project.id == project_id, Project.is_deleted.is_(False))
    )
    project = result.scalar_one_or_none()
    if not project:
        raise NotFoundError("Project", str(project_id))
    if current_user.role != UserRole.ADMIN.value and project.owner_id != current_user.id:
        raise PermissionDeniedError("You do not have access to this project")

    # Read and validate file
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise PermissionDeniedError(f"File exceeds max size of {MAX_FILE_SIZE // (1024*1024)} MB")

    content_type = file.content_type or "application/octet-stream"
    if content_type not in ALLOWED_TYPES:
        raise PermissionDeniedError(f"File type '{content_type}' is not allowed")

    # Upload to storage
    storage = StorageClient()
    result_data = await storage.upload_file(
        file_content=content,
        filename=file.filename or "unnamed",
        content_type=content_type,
        folder=f"projects/{project_id}",
    )

    # Create DB record
    doc = Document(
        project_id=project_id,
        uploaded_by=current_user.id,
        filename=file.filename or "unnamed",
        file_key=result_data["file_key"],
        content_type=content_type,
        size_bytes=len(content),
        category=category,
        description=description or None,
        url=result_data["url"],
    )
    db.add(doc)
    await db.flush()
    await db.refresh(doc)
    return DocumentResponse(
        id=doc.id, project_id=doc.project_id, filename=doc.filename,
        content_type=doc.content_type, size_bytes=doc.size_bytes,
        category=doc.category, description=doc.description, url=doc.url,
        created_at=doc.created_at.isoformat(),
    )


@router.get("/{project_id}", response_model=list[DocumentResponse])
async def list_documents(
    project_id: uuid.UUID,
    category: str | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Project).where(Project.id == project_id, Project.is_deleted.is_(False))
    )
    project = result.scalar_one_or_none()
    if not project:
        raise NotFoundError("Project", str(project_id))
    if current_user.role != UserRole.ADMIN.value and project.owner_id != current_user.id:
        raise PermissionDeniedError("You do not have access to this project")

    query = select(Document).where(
        Document.project_id == project_id, Document.is_deleted.is_(False)
    )
    if category:
        query = query.where(Document.category == category)
    query = query.order_by(Document.created_at.desc())

    result = await db.execute(query)
    docs = result.scalars().all()
    return [
        DocumentResponse(
            id=d.id, project_id=d.project_id, filename=d.filename,
            content_type=d.content_type, size_bytes=d.size_bytes,
            category=d.category, description=d.description, url=d.url,
            created_at=d.created_at.isoformat(),
        )
        for d in docs
    ]


@router.delete("/{document_id}", status_code=204)
async def delete_document(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Document).where(Document.id == document_id, Document.is_deleted.is_(False))
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise NotFoundError("Document", str(document_id))

    # Check project access
    result = await db.execute(select(Project).where(Project.id == doc.project_id))
    project = result.scalar_one_or_none()
    if project and current_user.role != UserRole.ADMIN.value and project.owner_id != current_user.id:
        raise PermissionDeniedError("You do not have access to this document")

    storage = StorageClient()
    await storage.delete_file(doc.file_key)
    doc.is_deleted = True
    await db.flush()
