import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from vibehouse.api.deps import get_current_user, get_db, require_role
from vibehouse.common.enums import DesignArtifactType, ProjectStatus, UserRole
from vibehouse.common.exceptions import BadRequestError, NotFoundError, PermissionDeniedError
from vibehouse.db.models.design import DesignArtifact
from vibehouse.db.models.project import Project
from vibehouse.db.models.user import User

router = APIRouter(prefix="/projects/{project_id}", tags=["Designs"])


# ---------- Schemas ----------


class VibeSubmitRequest(BaseModel):
    vibe_description: str


class VibeSubmitResponse(BaseModel):
    message: str
    project_id: uuid.UUID
    status: str


class DesignResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    artifact_type: str
    version: int
    title: str
    description: str | None
    file_url: str | None
    metadata: dict | None
    is_selected: bool

    model_config = {"from_attributes": True}


class DesignListResponse(BaseModel):
    designs: list[DesignResponse]
    total: int


# ---------- Endpoints ----------


@router.post("/vibe", response_model=VibeSubmitResponse)
async def submit_vibe(
    project_id: uuid.UUID,
    body: VibeSubmitRequest,
    current_user: User = Depends(require_role(UserRole.HOMEOWNER, UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    project = await _get_user_project(project_id, current_user, db)

    if project.status not in (ProjectStatus.DRAFT.value, ProjectStatus.DESIGNING.value):
        raise BadRequestError("Can only submit vibe descriptions for draft or designing projects")

    project.vibe_description = body.vibe_description
    project.status = ProjectStatus.DESIGNING.value
    await db.flush()

    # Trigger async design generation via Celery
    from vibehouse.tasks.vibe_tasks import process_vibe_description

    process_vibe_description.delay(str(project_id), body.vibe_description)

    return VibeSubmitResponse(
        message="Design generation started. Check back for results.",
        project_id=project_id,
        status=ProjectStatus.DESIGNING.value,
    )


@router.get("/designs", response_model=DesignListResponse)
async def list_designs(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _get_user_project(project_id, current_user, db)

    result = await db.execute(
        select(DesignArtifact)
        .where(
            DesignArtifact.project_id == project_id,
            DesignArtifact.is_deleted.is_(False),
        )
        .order_by(DesignArtifact.artifact_type, DesignArtifact.version)
    )
    designs = result.scalars().all()

    return DesignListResponse(
        designs=[
            DesignResponse(
                id=d.id,
                project_id=d.project_id,
                artifact_type=d.artifact_type,
                version=d.version,
                title=d.title,
                description=d.description,
                file_url=d.file_url,
                metadata=d.metadata_,
                is_selected=d.is_selected,
            )
            for d in designs
        ],
        total=len(designs),
    )


@router.post("/designs/{design_id}/select", response_model=DesignResponse)
async def select_design(
    project_id: uuid.UUID,
    design_id: uuid.UUID,
    current_user: User = Depends(require_role(UserRole.HOMEOWNER, UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    project = await _get_user_project(project_id, current_user, db)

    result = await db.execute(
        select(DesignArtifact).where(
            DesignArtifact.id == design_id,
            DesignArtifact.project_id == project_id,
            DesignArtifact.is_deleted.is_(False),
        )
    )
    design = result.scalar_one_or_none()
    if not design:
        raise NotFoundError("Design", str(design_id))

    if design.artifact_type != DesignArtifactType.FLOOR_PLAN.value:
        raise BadRequestError("Can only select floor plan designs")

    # Deselect all other floor plans for this project
    await db.execute(
        update(DesignArtifact)
        .where(
            DesignArtifact.project_id == project_id,
            DesignArtifact.artifact_type == DesignArtifactType.FLOOR_PLAN.value,
        )
        .values(is_selected=False)
    )

    design.is_selected = True
    project.status = ProjectStatus.PLANNING.value

    await db.flush()
    await db.refresh(design)

    # Trigger board creation and schedule generation
    from vibehouse.tasks.trello_tasks import create_project_board

    create_project_board.delay(str(project_id))

    return DesignResponse(
        id=design.id,
        project_id=design.project_id,
        artifact_type=design.artifact_type,
        version=design.version,
        title=design.title,
        description=design.description,
        file_url=design.file_url,
        metadata=design.metadata_,
        is_selected=design.is_selected,
    )


async def _get_user_project(
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
