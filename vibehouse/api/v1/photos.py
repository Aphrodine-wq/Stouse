"""Site photo upload and progress tracking."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from vibehouse.api.deps import get_current_user, get_db
from vibehouse.common.enums import UserRole
from vibehouse.common.events import emit
from vibehouse.common.exceptions import NotFoundError, PermissionDeniedError
from vibehouse.common.pagination import PaginatedResponse, PaginationParams, paginate
from vibehouse.db.models.photo import SitePhoto
from vibehouse.db.models.project import Project
from vibehouse.db.models.user import User

router = APIRouter(prefix="/projects/{project_id}/photos", tags=["Photos"])


# ---------- Schemas ----------

class PhotoUploadRequest(BaseModel):
    file_url: str
    thumbnail_url: str | None = None
    caption: str | None = None
    phase_id: uuid.UUID | None = None
    task_id: uuid.UUID | None = None
    tags: list[str] | None = None
    location_lat: float | None = None
    location_lng: float | None = None


class PhotoResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    uploaded_by_id: uuid.UUID
    file_url: str
    thumbnail_url: str | None
    caption: str | None
    tags: list | None
    phase_id: uuid.UUID | None
    task_id: uuid.UUID | None
    created_at: str
    model_config = {"from_attributes": True}


class PhotoGalleryResponse(PaginatedResponse[PhotoResponse]):
    pass


class ProgressSummary(BaseModel):
    total_photos: int
    photos_this_week: int
    photos_by_phase: dict[str, int]
    latest_photo: PhotoResponse | None


# ---------- Endpoints ----------

@router.post("", response_model=PhotoResponse, status_code=201)
async def upload_photo(
    project_id: uuid.UUID,
    body: PhotoUploadRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _verify_access(project_id, current_user, db)

    photo = SitePhoto(
        project_id=project_id,
        uploaded_by_id=current_user.id,
        file_url=body.file_url,
        thumbnail_url=body.thumbnail_url,
        caption=body.caption,
        phase_id=body.phase_id,
        task_id=body.task_id,
        tags=body.tags or [],
        location_lat=body.location_lat,
        location_lng=body.location_lng,
    )
    db.add(photo)
    await db.flush()
    await db.refresh(photo)

    await emit(str(project_id), "photo.uploaded", {
        "photo_id": str(photo.id),
        "caption": photo.caption,
        "uploaded_by": current_user.full_name,
    })

    return _photo_response(photo)


@router.get("", response_model=PhotoGalleryResponse)
async def list_photos(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    params: PaginationParams = Depends(),
):
    await _verify_access(project_id, current_user, db)

    query = (
        select(SitePhoto)
        .where(SitePhoto.project_id == project_id, SitePhoto.is_deleted.is_(False))
        .order_by(SitePhoto.created_at.desc())
    )

    items, total = await paginate(db, query, params, SitePhoto)
    total_pages = (total + params.page_size - 1) // params.page_size

    return PhotoGalleryResponse(
        items=[_photo_response(p) for p in items],
        total=total,
        page=params.page,
        page_size=params.page_size,
        total_pages=total_pages,
    )


@router.get("/progress", response_model=ProgressSummary)
async def get_progress_summary(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _verify_access(project_id, current_user, db)

    from datetime import datetime, timedelta, timezone

    week_ago = datetime.now(timezone.utc) - timedelta(days=7)

    # Total photos
    total_q = await db.execute(
        select(func.count(SitePhoto.id)).where(
            SitePhoto.project_id == project_id, SitePhoto.is_deleted.is_(False)
        )
    )
    total_photos = total_q.scalar() or 0

    # Photos this week
    week_q = await db.execute(
        select(func.count(SitePhoto.id)).where(
            SitePhoto.project_id == project_id,
            SitePhoto.is_deleted.is_(False),
            SitePhoto.created_at >= week_ago,
        )
    )
    photos_this_week = week_q.scalar() or 0

    # Latest photo
    latest_q = await db.execute(
        select(SitePhoto)
        .where(SitePhoto.project_id == project_id, SitePhoto.is_deleted.is_(False))
        .order_by(SitePhoto.created_at.desc())
        .limit(1)
    )
    latest = latest_q.scalar_one_or_none()

    return ProgressSummary(
        total_photos=total_photos,
        photos_this_week=photos_this_week,
        photos_by_phase={},
        latest_photo=_photo_response(latest) if latest else None,
    )


def _photo_response(photo: SitePhoto) -> PhotoResponse:
    return PhotoResponse(
        id=photo.id,
        project_id=photo.project_id,
        uploaded_by_id=photo.uploaded_by_id,
        file_url=photo.file_url,
        thumbnail_url=photo.thumbnail_url,
        caption=photo.caption,
        tags=photo.tags,
        phase_id=photo.phase_id,
        task_id=photo.task_id,
        created_at=photo.created_at.isoformat(),
    )


async def _verify_access(project_id: uuid.UUID, user: User, db: AsyncSession) -> Project:
    result = await db.execute(
        select(Project).where(Project.id == project_id, Project.is_deleted.is_(False))
    )
    project = result.scalar_one_or_none()
    if not project:
        raise NotFoundError("Project", str(project_id))
    if user.role != UserRole.ADMIN.value and project.owner_id != user.id:
        raise PermissionDeniedError("You do not have access to this project")
    return project
