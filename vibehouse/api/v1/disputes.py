import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from vibehouse.api.deps import get_current_user, get_db
from vibehouse.common.enums import DisputeStatus, DisputeType, UserRole
from vibehouse.common.exceptions import BadRequestError, NotFoundError, PermissionDeniedError
from vibehouse.db.models.dispute import Dispute
from vibehouse.db.models.project import Project
from vibehouse.db.models.user import User

router = APIRouter(prefix="/projects/{project_id}/disputes", tags=["Disputes"])


# ---------- Schemas ----------


class DisputeCreateRequest(BaseModel):
    title: str
    description: str
    dispute_type: DisputeType
    parties: list[str] | None = None


class DisputeUpdateRequest(BaseModel):
    action: str  # "respond", "escalate", "resolve"
    response_text: str | None = None
    resolution: str | None = None


class DisputeResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    filed_by_id: uuid.UUID
    status: str
    dispute_type: str
    title: str
    description: str
    resolution: str | None
    resolution_options: list | None
    created_at: str

    model_config = {"from_attributes": True}


class DisputeListResponse(BaseModel):
    disputes: list[DisputeResponse]
    total: int


# ---------- Endpoints ----------


@router.post("", response_model=DisputeResponse, status_code=201)
async def file_dispute(
    project_id: uuid.UUID,
    body: DisputeCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _verify_project_access(project_id, current_user, db)

    dispute = Dispute(
        project_id=project_id,
        filed_by_id=current_user.id,
        title=body.title,
        description=body.description,
        dispute_type=body.dispute_type.value,
        status=DisputeStatus.IDENTIFIED.value,
        parties=body.parties or [],
        history=[
            {
                "action": "filed",
                "by": str(current_user.id),
                "description": body.description,
            }
        ],
    )
    db.add(dispute)
    await db.flush()
    await db.refresh(dispute)

    # Generate resolution options async
    from vibehouse.tasks.dispute_tasks import generate_resolution_options

    generate_resolution_options.delay(str(dispute.id))

    return _dispute_to_response(dispute)


@router.get("", response_model=DisputeListResponse)
async def list_disputes(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _verify_project_access(project_id, current_user, db)

    result = await db.execute(
        select(Dispute)
        .where(Dispute.project_id == project_id, Dispute.is_deleted.is_(False))
        .order_by(Dispute.created_at.desc())
    )
    disputes = result.scalars().all()

    return DisputeListResponse(
        disputes=[_dispute_to_response(d) for d in disputes],
        total=len(disputes),
    )


@router.patch("/{dispute_id}", response_model=DisputeResponse)
async def update_dispute(
    project_id: uuid.UUID,
    dispute_id: uuid.UUID,
    body: DisputeUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _verify_project_access(project_id, current_user, db)

    result = await db.execute(
        select(Dispute).where(
            Dispute.id == dispute_id,
            Dispute.project_id == project_id,
            Dispute.is_deleted.is_(False),
        )
    )
    dispute = result.scalar_one_or_none()
    if not dispute:
        raise NotFoundError("Dispute", str(dispute_id))

    history = dispute.history or []

    if body.action == "respond":
        history.append({
            "action": "response",
            "by": str(current_user.id),
            "text": body.response_text,
        })
        if dispute.status == DisputeStatus.IDENTIFIED.value:
            dispute.status = DisputeStatus.DIRECT_RESOLUTION.value

    elif body.action == "escalate":
        current_status = DisputeStatus(dispute.status)
        escalation_map = {
            DisputeStatus.IDENTIFIED: DisputeStatus.DIRECT_RESOLUTION,
            DisputeStatus.DIRECT_RESOLUTION: DisputeStatus.AI_MEDIATION,
            DisputeStatus.AI_MEDIATION: DisputeStatus.EXTERNAL_MEDIATION,
        }
        next_status = escalation_map.get(current_status)
        if not next_status:
            raise BadRequestError("Cannot escalate dispute further")
        dispute.status = next_status.value
        history.append({
            "action": "escalated",
            "by": str(current_user.id),
            "from": current_status.value,
            "to": next_status.value,
        })

    elif body.action == "resolve":
        if not body.resolution:
            raise BadRequestError("Resolution text is required when resolving a dispute")
        dispute.status = DisputeStatus.RESOLVED.value
        dispute.resolution = body.resolution
        history.append({
            "action": "resolved",
            "by": str(current_user.id),
            "resolution": body.resolution,
        })

    else:
        raise BadRequestError(f"Unknown action: {body.action}")

    dispute.history = history
    await db.flush()
    await db.refresh(dispute)

    return _dispute_to_response(dispute)


def _dispute_to_response(dispute: Dispute) -> DisputeResponse:
    return DisputeResponse(
        id=dispute.id,
        project_id=dispute.project_id,
        filed_by_id=dispute.filed_by_id,
        status=dispute.status,
        dispute_type=dispute.dispute_type,
        title=dispute.title,
        description=dispute.description,
        resolution=dispute.resolution,
        resolution_options=dispute.resolution_options,
        created_at=dispute.created_at.isoformat(),
    )


async def _verify_project_access(
    project_id: uuid.UUID, user: User, db: AsyncSession
) -> Project:
    result = await db.execute(
        select(Project).where(Project.id == project_id, Project.is_deleted.is_(False))
    )
    project = result.scalar_one_or_none()
    if not project:
        raise NotFoundError("Project", str(project_id))
    if user.role != UserRole.ADMIN.value and project.owner_id != user.id:
        raise PermissionDeniedError("You do not have access to this project")
    return project
