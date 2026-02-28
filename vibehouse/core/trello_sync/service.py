import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from vibehouse.common.enums import PhaseType
from vibehouse.common.logging import get_logger
from vibehouse.core.trello_sync.board_manager import BoardManager
from vibehouse.core.trello_sync.schemas import BoardConfig, CardData
from vibehouse.core.trello_sync.webhook_handler import handle_webhook_event
from vibehouse.db.models.phase import ProjectPhase
from vibehouse.db.models.project import Project
from vibehouse.db.models.task import Task
from vibehouse.db.models.trello_state import TrelloSyncState

logger = get_logger("trello_sync.service")

# Standard construction tasks by phase
PHASE_TASKS = {
    PhaseType.SITE_PREP: [
        "Survey and stake property boundaries",
        "Clear and grade lot",
        "Install temporary utilities",
        "Set up erosion control",
    ],
    PhaseType.FOUNDATION: [
        "Excavate for foundation",
        "Install footings",
        "Pour foundation walls",
        "Waterproof foundation",
        "Foundation inspection",
    ],
    PhaseType.FRAMING: [
        "Frame first floor walls",
        "Install floor joists/trusses",
        "Frame second floor (if applicable)",
        "Install roof trusses",
        "Sheath exterior walls and roof",
        "Framing inspection",
    ],
    PhaseType.ROOFING: [
        "Install roofing underlayment",
        "Install roofing material",
        "Install flashing and vents",
        "Gutter installation",
    ],
    PhaseType.MEP: [
        "Rough-in plumbing",
        "Rough-in electrical",
        "Install HVAC ductwork",
        "MEP rough-in inspection",
    ],
    PhaseType.INTERIOR: [
        "Install insulation",
        "Hang drywall",
        "Tape and finish drywall",
        "Install interior doors and trim",
        "Paint interior",
        "Install flooring",
        "Install cabinets and countertops",
        "Install fixtures and hardware",
    ],
    PhaseType.EXTERIOR: [
        "Install siding/exterior finish",
        "Install windows and exterior doors",
        "Paint/stain exterior",
        "Concrete flatwork (driveway, walkways)",
    ],
    PhaseType.LANDSCAPE: [
        "Final grading",
        "Install irrigation",
        "Plant landscaping",
        "Install exterior lighting",
    ],
    PhaseType.FINAL: [
        "Final cleaning",
        "Final inspection",
        "Certificate of occupancy",
        "Homeowner walkthrough",
        "Punch list completion",
    ],
}


class TrelloSyncService:
    def __init__(self):
        self.board_manager = BoardManager()

    async def create_build_board(self, project_id: str, db: AsyncSession) -> dict:
        result = await db.execute(
            select(Project).where(Project.id == uuid.UUID(project_id))
        )
        project = result.scalar_one_or_none()
        if not project:
            raise ValueError(f"Project {project_id} not found")

        config = BoardConfig(
            name=f"VibeHouse: {project.title}",
            description=f"Build board for {project.title}. Managed by VibeHouse AI.",
        )

        board_data = await self.board_manager.create_board(config)
        board_id = board_data["board_id"]

        # Create phases and tasks
        for idx, phase_type in enumerate(PhaseType):
            phase = ProjectPhase(
                project_id=uuid.UUID(project_id),
                phase_type=phase_type.value,
                order_index=idx,
            )
            db.add(phase)
            await db.flush()
            await db.refresh(phase)

            task_titles = PHASE_TASKS.get(phase_type, [])
            for task_idx, title in enumerate(task_titles):
                card_data = CardData(
                    name=f"[{phase_type.value.upper()}] {title}",
                    description=f"Phase: {phase_type.value}\nTask: {title}",
                    list_name="Backlog",
                )
                card_result = await self.board_manager.create_card(
                    board_data["lists"], card_data
                )

                task = Task(
                    phase_id=phase.id,
                    trello_card_id=card_result.get("id"),
                    title=title,
                    description=f"Phase: {phase_type.value}",
                    order_index=task_idx,
                )
                db.add(task)

        # Save sync state
        sync_state = TrelloSyncState(
            project_id=uuid.UUID(project_id),
            board_id=board_id,
            last_sync=datetime.now(timezone.utc),
            sync_status="synced",
            board_state=board_data,
        )
        db.add(sync_state)

        project.trello_board_id = board_id

        await db.flush()

        logger.info("Created build board %s for project %s", board_id, project_id)
        return board_data

    async def sync_board_state(self, project_id: str, db: AsyncSession) -> dict:
        result = await db.execute(
            select(TrelloSyncState).where(
                TrelloSyncState.project_id == uuid.UUID(project_id)
            )
        )
        sync_state = result.scalar_one_or_none()
        if not sync_state:
            return {"status": "no_board"}

        board_state = await self.board_manager.get_board_state(sync_state.board_id)
        sync_state.board_state = board_state
        sync_state.last_sync = datetime.now(timezone.utc)
        sync_state.sync_status = "synced"

        await db.flush()
        return board_state

    async def process_webhook(self, payload: dict, db: AsyncSession) -> None:
        await handle_webhook_event(payload, db)
