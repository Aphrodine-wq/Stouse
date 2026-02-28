import uuid
from datetime import date, timedelta

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from vibehouse.api.deps import get_current_user, get_db
from vibehouse.common.enums import PhaseType, TaskStatus, UserRole
from vibehouse.common.exceptions import NotFoundError, PermissionDeniedError
from vibehouse.db.models.phase import ProjectPhase
from vibehouse.db.models.project import Project
from vibehouse.db.models.task import Task
from vibehouse.db.models.user import User

router = APIRouter(prefix="/projects/{project_id}", tags=["Timeline"])

# Typical construction durations (in days) by phase type, used for estimation
# when phases or tasks lack explicit dates.
_DEFAULT_PHASE_DURATIONS: dict[str, int] = {
    PhaseType.SITE_PREP.value: 14,
    PhaseType.FOUNDATION.value: 21,
    PhaseType.FRAMING.value: 28,
    PhaseType.ROOFING.value: 14,
    PhaseType.MEP.value: 21,
    PhaseType.INTERIOR.value: 30,
    PhaseType.EXTERIOR.value: 21,
    PhaseType.LANDSCAPE.value: 14,
    PhaseType.FINAL.value: 14,
}


# ---------- Schemas ----------


class TimelineTask(BaseModel):
    id: uuid.UUID
    title: str
    status: str
    start_date: date | None
    end_date: date | None
    assignee_name: str | None
    dependencies: list[str]
    is_critical_path: bool


class TimelinePhase(BaseModel):
    phase_type: str
    status: str
    start_date: date | None
    end_date: date | None
    tasks: list[TimelineTask]


class Milestone(BaseModel):
    date: date | None
    name: str
    status: str  # "pending", "reached", "overdue"


class TimelineResponse(BaseModel):
    project_id: uuid.UUID
    project_title: str
    overall_start: date | None
    overall_end: date | None
    phases: list[TimelinePhase]
    critical_path: list[str]
    milestones: list[Milestone]


class MilestoneListResponse(BaseModel):
    project_id: uuid.UUID
    milestones: list[Milestone]


# ---------- Endpoints ----------


@router.get("/timeline", response_model=TimelineResponse)
async def get_project_timeline(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    project = await _verify_project_access(project_id, current_user, db)

    # Fetch phases ordered by index
    phases_result = await db.execute(
        select(ProjectPhase)
        .where(ProjectPhase.project_id == project_id, ProjectPhase.is_deleted.is_(False))
        .order_by(ProjectPhase.order_index)
    )
    phases = list(phases_result.scalars().all())
    phase_ids = [p.id for p in phases]

    # Fetch all tasks across phases
    tasks: list[Task] = []
    if phase_ids:
        tasks_result = await db.execute(
            select(Task).where(Task.phase_id.in_(phase_ids), Task.is_deleted.is_(False))
        )
        tasks = list(tasks_result.scalars().all())

    # Group tasks by phase
    tasks_by_phase: dict[uuid.UUID, list[Task]] = {}
    for t in tasks:
        tasks_by_phase.setdefault(t.phase_id, []).append(t)

    # Sort each group by order_index
    for phase_id in tasks_by_phase:
        tasks_by_phase[phase_id].sort(key=lambda t: t.order_index)

    # Build a task lookup by id for dependency resolution
    task_by_id: dict[uuid.UUID, Task] = {t.id: t for t in tasks}

    # Estimate phase dates when missing, chaining sequentially from the
    # earliest known start date or from today.
    _estimate_phase_dates(phases)

    # Estimate task dates within each phase when missing
    for phase in phases:
        phase_tasks = tasks_by_phase.get(phase.id, [])
        _estimate_task_dates(phase_tasks, phase.start_date, phase.end_date)

    # Determine the critical path: longest chain of dependent incomplete tasks
    critical_path_ids = _compute_critical_path(tasks, task_by_id)
    critical_path_id_set = set(critical_path_ids)

    # Build timeline phases
    timeline_phases: list[TimelinePhase] = []
    for phase in phases:
        phase_tasks = tasks_by_phase.get(phase.id, [])
        timeline_tasks: list[TimelineTask] = []
        for t in phase_tasks:
            # Resolve dependency IDs to strings
            dep_ids = t.dependencies if isinstance(t.dependencies, list) else []
            dep_strs = [str(d) for d in dep_ids]

            assignee_name: str | None = None
            if t.assignee:
                assignee_name = t.assignee.company_name or t.assignee.contact_name

            timeline_tasks.append(
                TimelineTask(
                    id=t.id,
                    title=t.title,
                    status=t.status,
                    start_date=t.due_date - timedelta(days=3) if t.due_date and not getattr(t, "_estimated_start", None) else getattr(t, "_estimated_start", None),
                    end_date=t.due_date,
                    assignee_name=assignee_name,
                    dependencies=dep_strs,
                    is_critical_path=t.id in critical_path_id_set,
                )
            )

        timeline_phases.append(
            TimelinePhase(
                phase_type=phase.phase_type,
                status=phase.status,
                start_date=phase.start_date,
                end_date=phase.end_date,
                tasks=timeline_tasks,
            )
        )

    # Compute overall dates
    all_start_dates = [p.start_date for p in phases if p.start_date is not None]
    all_end_dates = [p.end_date for p in phases if p.end_date is not None]
    overall_start = min(all_start_dates) if all_start_dates else None
    overall_end = max(all_end_dates) if all_end_dates else None

    # Build milestones from phase boundaries
    milestones = _build_milestones(phases, tasks_by_phase)

    return TimelineResponse(
        project_id=project.id,
        project_title=project.title,
        overall_start=overall_start,
        overall_end=overall_end,
        phases=timeline_phases,
        critical_path=[str(tid) for tid in critical_path_ids],
        milestones=milestones,
    )


@router.get("/timeline/milestones", response_model=MilestoneListResponse)
async def get_project_milestones(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    project = await _verify_project_access(project_id, current_user, db)

    # Fetch phases
    phases_result = await db.execute(
        select(ProjectPhase)
        .where(ProjectPhase.project_id == project_id, ProjectPhase.is_deleted.is_(False))
        .order_by(ProjectPhase.order_index)
    )
    phases = list(phases_result.scalars().all())
    phase_ids = [p.id for p in phases]

    # Fetch tasks for milestone status calculation
    tasks: list[Task] = []
    if phase_ids:
        tasks_result = await db.execute(
            select(Task).where(Task.phase_id.in_(phase_ids), Task.is_deleted.is_(False))
        )
        tasks = list(tasks_result.scalars().all())

    tasks_by_phase: dict[uuid.UUID, list[Task]] = {}
    for t in tasks:
        tasks_by_phase.setdefault(t.phase_id, []).append(t)

    _estimate_phase_dates(phases)

    milestones = _build_milestones(phases, tasks_by_phase)

    return MilestoneListResponse(
        project_id=project.id,
        milestones=milestones,
    )


# ---------- Helpers ----------


def _estimate_phase_dates(phases: list[ProjectPhase]) -> None:
    """Fill in missing start/end dates on phases by chaining them sequentially.

    Phases that already have dates are left untouched.  For phases without
    dates the algorithm picks up from the previous phase's end date (or
    from today if no prior date is available) and adds a typical duration
    for the phase type.
    """
    cursor: date | None = None

    # Find the earliest known start across all phases to use as a baseline
    known_starts = [p.start_date for p in phases if p.start_date is not None]
    if known_starts:
        cursor = min(known_starts)

    for phase in phases:
        duration = _DEFAULT_PHASE_DURATIONS.get(phase.phase_type, 14)

        if phase.start_date is None:
            phase.start_date = cursor or date.today()

        if phase.end_date is None:
            phase.end_date = phase.start_date + timedelta(days=duration)

        # Advance cursor past this phase for the next one
        cursor = phase.end_date + timedelta(days=1)


def _estimate_task_dates(
    tasks: list[Task],
    phase_start: date | None,
    phase_end: date | None,
) -> None:
    """Fill estimated start/end attributes on tasks that lack a due_date.

    Distributes tasks evenly across the phase window.  Tasks that already
    have a ``due_date`` keep their existing value.  A private attribute
    ``_estimated_start`` is set on every task for Gantt rendering.
    """
    if not tasks:
        return

    p_start = phase_start or date.today()
    p_end = phase_end or (p_start + timedelta(days=14))

    total_days = max((p_end - p_start).days, 1)
    count = len(tasks)
    slot_days = max(total_days // count, 1)

    for idx, task in enumerate(tasks):
        est_start = p_start + timedelta(days=idx * slot_days)
        est_end = est_start + timedelta(days=max(slot_days - 1, 1))

        # Clamp to phase boundary
        if est_end > p_end:
            est_end = p_end

        # Store estimates; prefer real due_date when available
        object.__setattr__(task, "_estimated_start", est_start)
        if task.due_date is None:
            task.due_date = est_end


def _compute_critical_path(
    tasks: list[Task],
    task_by_id: dict[uuid.UUID, Task],
) -> list[uuid.UUID]:
    """Determine the critical path as the longest chain of dependent,
    incomplete tasks measured by due-date span.

    Uses a simple longest-path algorithm on the task dependency DAG.
    Only incomplete tasks are considered.
    """
    incomplete = {
        t.id for t in tasks if t.status != TaskStatus.COMPLETED.value
    }
    if not incomplete:
        return []

    # Build adjacency: task -> list of tasks that depend on it
    dependents: dict[uuid.UUID, list[uuid.UUID]] = {tid: [] for tid in incomplete}
    for t in tasks:
        if t.id not in incomplete:
            continue
        deps = t.dependencies if isinstance(t.dependencies, list) else []
        for dep_id_raw in deps:
            try:
                dep_id = uuid.UUID(str(dep_id_raw))
            except (ValueError, AttributeError):
                continue
            if dep_id in incomplete:
                dependents.setdefault(dep_id, []).append(t.id)

    # Find the longest path using memoised DFS
    memo: dict[uuid.UUID, list[uuid.UUID]] = {}

    def _longest_from(tid: uuid.UUID) -> list[uuid.UUID]:
        if tid in memo:
            return memo[tid]
        best: list[uuid.UUID] = []
        for child in dependents.get(tid, []):
            candidate = _longest_from(child)
            if len(candidate) > len(best):
                best = candidate
        memo[tid] = [tid] + best
        return memo[tid]

    # Compute from all roots (tasks with no incomplete predecessors)
    tasks_with_deps = set()
    for t in tasks:
        if t.id not in incomplete:
            continue
        deps = t.dependencies if isinstance(t.dependencies, list) else []
        for dep_id_raw in deps:
            try:
                dep_id = uuid.UUID(str(dep_id_raw))
            except (ValueError, AttributeError):
                continue
            if dep_id in incomplete:
                tasks_with_deps.add(t.id)
                break

    roots = incomplete - tasks_with_deps
    if not roots:
        # Fallback: all incomplete tasks are roots
        roots = incomplete

    longest: list[uuid.UUID] = []
    for root in roots:
        candidate = _longest_from(root)
        if len(candidate) > len(longest):
            longest = candidate

    return longest


def _build_milestones(
    phases: list[ProjectPhase],
    tasks_by_phase: dict[uuid.UUID, list[Task]],
) -> list[Milestone]:
    """Generate milestone entries from phase completion boundaries."""
    today = date.today()
    milestones: list[Milestone] = []

    for phase in phases:
        phase_tasks = tasks_by_phase.get(phase.id, [])
        all_complete = (
            len(phase_tasks) > 0
            and all(t.status == TaskStatus.COMPLETED.value for t in phase_tasks)
        )

        milestone_date = phase.end_date

        if all_complete:
            status = "reached"
        elif milestone_date and milestone_date < today:
            status = "overdue"
        else:
            status = "pending"

        # Pretty name from phase type
        phase_label = phase.phase_type.replace("_", " ").title()

        milestones.append(
            Milestone(
                date=milestone_date,
                name=f"{phase_label} Complete",
                status=status,
            )
        )

    # Add a project completion milestone at the very end
    if phases:
        last_phase = phases[-1]
        all_tasks = [t for pts in tasks_by_phase.values() for t in pts]
        all_done = (
            len(all_tasks) > 0
            and all(t.status == TaskStatus.COMPLETED.value for t in all_tasks)
        )
        project_end_date = last_phase.end_date
        if all_done:
            ms_status = "reached"
        elif project_end_date and project_end_date < today:
            ms_status = "overdue"
        else:
            ms_status = "pending"
        milestones.append(
            Milestone(
                date=project_end_date,
                name="Project Complete",
                status=ms_status,
            )
        )

    return milestones


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
