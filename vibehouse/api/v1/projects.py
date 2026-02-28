import uuid
from decimal import Decimal

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from vibehouse.api.deps import get_current_user, get_db, require_role
from vibehouse.common.enums import ProjectStatus, UserRole
from vibehouse.common.exceptions import BadRequestError, NotFoundError, PermissionDeniedError
from vibehouse.db.models.project import Project
from vibehouse.db.models.user import User

router = APIRouter(prefix="/projects", tags=["Projects"])

VALID_TRANSITIONS = {
    ProjectStatus.DRAFT: [ProjectStatus.DESIGNING, ProjectStatus.CANCELLED],
    ProjectStatus.DESIGNING: [ProjectStatus.PLANNING, ProjectStatus.DRAFT, ProjectStatus.CANCELLED],
    ProjectStatus.PLANNING: [ProjectStatus.IN_PROGRESS, ProjectStatus.DESIGNING, ProjectStatus.CANCELLED],
    ProjectStatus.IN_PROGRESS: [ProjectStatus.ON_HOLD, ProjectStatus.COMPLETED, ProjectStatus.CANCELLED],
    ProjectStatus.ON_HOLD: [ProjectStatus.IN_PROGRESS, ProjectStatus.CANCELLED],
    ProjectStatus.COMPLETED: [],
    ProjectStatus.CANCELLED: [],
}


# ---------- Schemas ----------


class ProjectCreateRequest(BaseModel):
    title: str
    vibe_description: str | None = None
    address: str | None = None
    budget: Decimal | None = None


class ProjectUpdateRequest(BaseModel):
    title: str | None = None
    status: ProjectStatus | None = None
    address: str | None = None
    budget: Decimal | None = None


class ProjectResponse(BaseModel):
    id: uuid.UUID
    owner_id: uuid.UUID
    title: str
    status: str
    vibe_description: str | None
    address: str | None
    budget: Decimal | None
    budget_spent: Decimal
    trello_board_id: str | None
    created_at: str

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm_instance(cls, project: Project) -> "ProjectResponse":
        return cls(
            id=project.id,
            owner_id=project.owner_id,
            title=project.title,
            status=project.status,
            vibe_description=project.vibe_description,
            address=project.address,
            budget=project.budget,
            budget_spent=project.budget_spent,
            trello_board_id=project.trello_board_id,
            created_at=project.created_at.isoformat(),
        )


class ProjectListResponse(BaseModel):
    projects: list[ProjectResponse]
    total: int


# ---------- Endpoints ----------


@router.post("", response_model=ProjectResponse, status_code=201)
async def create_project(
    body: ProjectCreateRequest,
    current_user: User = Depends(require_role(UserRole.HOMEOWNER, UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    project = Project(
        owner_id=current_user.id,
        title=body.title,
        vibe_description=body.vibe_description,
        address=body.address,
        budget=body.budget,
        status=ProjectStatus.DRAFT.value,
    )
    db.add(project)
    await db.flush()
    await db.refresh(project)
    return ProjectResponse.from_orm_instance(project)


@router.get("", response_model=ProjectListResponse)
async def list_projects(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(Project).where(Project.is_deleted.is_(False))

    if current_user.role != UserRole.ADMIN.value:
        query = query.where(Project.owner_id == current_user.id)

    query = query.order_by(Project.created_at.desc())
    result = await db.execute(query)
    projects = result.scalars().all()

    return ProjectListResponse(
        projects=[ProjectResponse.from_orm_instance(p) for p in projects],
        total=len(projects),
    )


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    project = await _get_project_for_user(project_id, current_user, db)
    return ProjectResponse.from_orm_instance(project)


@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: uuid.UUID,
    body: ProjectUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    project = await _get_project_for_user(project_id, current_user, db)

    if body.title is not None:
        project.title = body.title
    if body.address is not None:
        project.address = body.address
    if body.budget is not None:
        project.budget = body.budget

    if body.status is not None:
        current_status = ProjectStatus(project.status)
        allowed = VALID_TRANSITIONS.get(current_status, [])
        if body.status not in allowed:
            raise BadRequestError(
                f"Cannot transition from '{current_status.value}' to '{body.status.value}'"
            )
        project.status = body.status.value

    await db.flush()
    await db.refresh(project)
    return ProjectResponse.from_orm_instance(project)


async def _get_project_for_user(
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
