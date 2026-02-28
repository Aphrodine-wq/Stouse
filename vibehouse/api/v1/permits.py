import uuid
from datetime import date

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from vibehouse.api.deps import get_current_user, get_db
from vibehouse.common.enums import UserRole
from vibehouse.common.exceptions import BadRequestError, NotFoundError, PermissionDeniedError
from vibehouse.db.models.permit import Permit, PermitChecklist
from vibehouse.db.models.project import Project
from vibehouse.db.models.user import User

router = APIRouter(prefix="/projects/{project_id}/permits", tags=["Permits"])

# Valid permit status transitions
_VALID_PERMIT_STATUSES = {
    "not_applied",
    "applied",
    "under_review",
    "approved",
    "denied",
    "expired",
}

_VALID_PERMIT_TRANSITIONS: dict[str, list[str]] = {
    "not_applied": ["applied"],
    "applied": ["under_review", "denied"],
    "under_review": ["approved", "denied"],
    "approved": ["expired"],
    "denied": ["applied"],  # allow re-application
    "expired": ["applied"],  # allow renewal
}


# ---------- Schemas ----------


class PermitCreateRequest(BaseModel):
    permit_type: str  # building, electrical, plumbing, mechanical, grading
    jurisdiction: str
    application_number: str | None = None
    applied_date: date | None = None
    fee: float | None = None
    notes: str | None = None


class PermitUpdateRequest(BaseModel):
    status: str | None = None
    application_number: str | None = None
    applied_date: date | None = None
    approved_date: date | None = None
    expiry_date: date | None = None
    fee: float | None = None
    notes: str | None = None


class PermitResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    permit_type: str
    jurisdiction: str
    status: str
    application_number: str | None
    applied_date: str | None
    approved_date: str | None
    expiry_date: str | None
    requirements: list | None
    documents: list | None
    notes: str | None
    fee: float | None
    created_at: str

    model_config = {"from_attributes": True}


class PermitListResponse(BaseModel):
    permits: list[PermitResponse]
    total: int


class ChecklistItem(BaseModel):
    name: str
    description: str
    required: bool
    status: str  # "not_started", "in_progress", "complete"
    documents_needed: list[str]


class PermitChecklistResponse(BaseModel):
    project_id: uuid.UUID
    jurisdiction: str
    items: list[ChecklistItem]
    completion_percent: float


# ---------- Endpoints ----------


@router.get("", response_model=PermitListResponse)
async def list_permits(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _verify_project_access(project_id, current_user, db)

    result = await db.execute(
        select(Permit)
        .where(Permit.project_id == project_id, Permit.is_deleted.is_(False))
        .order_by(Permit.created_at.desc())
    )
    permits = result.scalars().all()

    return PermitListResponse(
        permits=[_permit_to_response(p) for p in permits],
        total=len(permits),
    )


@router.post("", response_model=PermitResponse, status_code=201)
async def create_permit(
    project_id: uuid.UUID,
    body: PermitCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _verify_project_access(project_id, current_user, db)

    permit = Permit(
        project_id=project_id,
        permit_type=body.permit_type,
        jurisdiction=body.jurisdiction,
        status="not_applied",
        application_number=body.application_number,
        applied_date=body.applied_date,
        fee=body.fee,
        notes=body.notes,
        requirements=[],
        documents=[],
    )
    db.add(permit)
    await db.flush()
    await db.refresh(permit)

    return _permit_to_response(permit)


@router.patch("/{permit_id}", response_model=PermitResponse)
async def update_permit(
    project_id: uuid.UUID,
    permit_id: uuid.UUID,
    body: PermitUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _verify_project_access(project_id, current_user, db)

    result = await db.execute(
        select(Permit).where(
            Permit.id == permit_id,
            Permit.project_id == project_id,
            Permit.is_deleted.is_(False),
        )
    )
    permit = result.scalar_one_or_none()
    if not permit:
        raise NotFoundError("Permit", str(permit_id))

    # Validate status transition if status is being changed
    if body.status is not None:
        if body.status not in _VALID_PERMIT_STATUSES:
            raise BadRequestError(f"Invalid permit status: '{body.status}'")
        allowed = _VALID_PERMIT_TRANSITIONS.get(permit.status, [])
        if body.status not in allowed:
            raise BadRequestError(
                f"Cannot transition permit from '{permit.status}' to '{body.status}'"
            )
        permit.status = body.status

    if body.application_number is not None:
        permit.application_number = body.application_number
    if body.applied_date is not None:
        permit.applied_date = body.applied_date
    if body.approved_date is not None:
        permit.approved_date = body.approved_date
    if body.expiry_date is not None:
        permit.expiry_date = body.expiry_date
    if body.fee is not None:
        permit.fee = body.fee
    if body.notes is not None:
        permit.notes = body.notes

    await db.flush()
    await db.refresh(permit)

    return _permit_to_response(permit)


@router.get("/checklist", response_model=PermitChecklistResponse)
async def get_permit_checklist(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    project = await _verify_project_access(project_id, current_user, db)

    # Try to load existing checklist for this project
    result = await db.execute(
        select(PermitChecklist).where(
            PermitChecklist.project_id == project_id,
            PermitChecklist.is_deleted.is_(False),
        )
    )
    checklist = result.scalar_one_or_none()

    if checklist:
        # Return existing checklist
        items = [ChecklistItem(**item) for item in (checklist.checklist_items or [])]
        return PermitChecklistResponse(
            project_id=project_id,
            jurisdiction=checklist.jurisdiction,
            items=items,
            completion_percent=checklist.completion_percent,
        )

    # Generate a new checklist based on project address / jurisdiction
    jurisdiction = _parse_jurisdiction(project.address)
    items = _generate_permit_checklist(jurisdiction, project.address)

    # Persist the generated checklist
    new_checklist = PermitChecklist(
        project_id=project_id,
        jurisdiction=jurisdiction,
        checklist_items=[item.model_dump() for item in items],
        completion_percent=0.0,
    )
    db.add(new_checklist)
    await db.flush()
    await db.refresh(new_checklist)

    return PermitChecklistResponse(
        project_id=project_id,
        jurisdiction=jurisdiction,
        items=items,
        completion_percent=0.0,
    )


# ---------- Helpers ----------


def _permit_to_response(permit: Permit) -> PermitResponse:
    return PermitResponse(
        id=permit.id,
        project_id=permit.project_id,
        permit_type=permit.permit_type,
        jurisdiction=permit.jurisdiction,
        status=permit.status,
        application_number=permit.application_number,
        applied_date=permit.applied_date.isoformat() if permit.applied_date else None,
        approved_date=permit.approved_date.isoformat() if permit.approved_date else None,
        expiry_date=permit.expiry_date.isoformat() if permit.expiry_date else None,
        requirements=permit.requirements,
        documents=permit.documents,
        notes=permit.notes,
        fee=permit.fee,
        created_at=permit.created_at.isoformat(),
    )


def _parse_jurisdiction(address: str | None) -> str:
    """Extract a state abbreviation from the project address.

    Uses a simple heuristic: looks for a two-letter US state code in the
    address string.  Falls back to a generic jurisdiction if nothing is
    found.
    """
    if not address:
        return "General"

    us_states = {
        "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
        "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
        "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
        "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
        "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY",
        "DC",
    }

    # Tokenize and look for a state code (commonly appears after city, before zip)
    parts = address.replace(",", " ").split()
    for part in parts:
        upper = part.strip().upper()
        if upper in us_states:
            return upper

    return "General"


def _generate_permit_checklist(jurisdiction: str, address: str | None) -> list[ChecklistItem]:
    """Generate a jurisdiction-aware permit checklist.

    This is a mock implementation that returns realistic permit
    requirements customised by state.  In production this would call a
    jurisdiction API or an AI model.
    """
    items: list[ChecklistItem] = []

    # ---- Core permits (always required) ----

    items.append(ChecklistItem(
        name="Building Permit Application",
        description="Primary building permit required by the local building department before construction begins.",
        required=True,
        status="not_started",
        documents_needed=[
            "Completed permit application form",
            "Proof of property ownership or authorization",
            "Site plan / plot plan",
            "Construction drawings (architectural)",
            "Application fee payment",
        ],
    ))

    items.append(ChecklistItem(
        name="Site Plan Review",
        description="Review of the proposed site plan by the planning/zoning department to ensure compliance with setback, lot coverage, and land use requirements.",
        required=True,
        status="not_started",
        documents_needed=[
            "Scaled site plan showing property boundaries",
            "Existing and proposed structures",
            "Setback dimensions",
            "Driveway and parking layout",
            "Drainage plan",
        ],
    ))

    items.append(ChecklistItem(
        name="Structural Engineering Review",
        description="Structural analysis and stamped engineering drawings must be submitted and approved before framing begins.",
        required=True,
        status="not_started",
        documents_needed=[
            "Stamped structural engineering drawings",
            "Foundation design calculations",
            "Framing plans and details",
            "Load calculations",
            "Engineer's letter of certification",
        ],
    ))

    items.append(ChecklistItem(
        name="Electrical Permit",
        description="Separate electrical permit for all electrical work including service panels, wiring, and fixtures.",
        required=True,
        status="not_started",
        documents_needed=[
            "Electrical plan showing panel location and circuits",
            "Load calculation sheet",
            "Licensed electrician information",
            "Permit application form",
        ],
    ))

    items.append(ChecklistItem(
        name="Plumbing Permit",
        description="Permit covering all plumbing installations including water supply, drainage, and fixture connections.",
        required=True,
        status="not_started",
        documents_needed=[
            "Plumbing riser diagram",
            "Fixture schedule",
            "Licensed plumber information",
            "Water heater specifications",
            "Permit application form",
        ],
    ))

    items.append(ChecklistItem(
        name="Mechanical/HVAC Permit",
        description="Permit for heating, ventilation, and air conditioning system installation.",
        required=True,
        status="not_started",
        documents_needed=[
            "HVAC system design and layout",
            "Manual J load calculation",
            "Duct layout drawings",
            "Equipment specifications",
            "Licensed HVAC contractor information",
        ],
    ))

    # ---- Conditional permits based on jurisdiction ----

    # Grading permit -- typically required in states with hillside / erosion concerns
    grading_states = {"CA", "WA", "OR", "CO", "AZ", "NV", "UT", "HI", "NC", "VA", "MD"}
    needs_grading = jurisdiction in grading_states or jurisdiction == "General"
    items.append(ChecklistItem(
        name="Grading Permit",
        description="Required when the project involves significant earth-moving, grading, or changes to existing drainage patterns.",
        required=needs_grading,
        status="not_started",
        documents_needed=[
            "Grading plan prepared by a civil engineer",
            "Erosion and sediment control plan",
            "Stormwater management plan",
            "Soil report / geotechnical study",
            "SWPPP (if disturbing > 1 acre)",
        ],
    ))

    # Environmental review -- more common in coastal and environmentally sensitive states
    env_states = {"CA", "WA", "OR", "NY", "CT", "MA", "HI", "FL", "NJ", "MD", "ME", "RI"}
    needs_env = jurisdiction in env_states
    items.append(ChecklistItem(
        name="Environmental Review",
        description="Environmental impact assessment required for projects near wetlands, waterways, or protected habitats.",
        required=needs_env,
        status="not_started",
        documents_needed=[
            "Environmental impact questionnaire",
            "Wetland delineation report (if applicable)",
            "Endangered species survey (if applicable)",
            "Tree survey and removal plan",
            "Stormwater pollution prevention plan",
        ],
    ))

    # HOA approval -- not jurisdiction-mandated but commonly required
    # We flag this as conditionally required (not enforced by law, but often needed)
    items.append(ChecklistItem(
        name="HOA Approval",
        description="If the property is within a Homeowners Association, architectural review and approval may be required before permitting.",
        required=False,
        status="not_started",
        documents_needed=[
            "HOA architectural review application",
            "Exterior material and color samples",
            "Landscape plan",
            "Project description and timeline",
            "Neighbor notification (if required by HOA)",
        ],
    ))

    # State-specific extras
    if jurisdiction == "CA":
        items.append(ChecklistItem(
            name="Title 24 Energy Compliance",
            description="California Title 24 energy efficiency standards compliance documentation.",
            required=True,
            status="not_started",
            documents_needed=[
                "CF-1R compliance forms",
                "Energy calculation report",
                "Solar-ready zone documentation",
                "Cool roof specifications (Climate Zones 10-15)",
                "HERS rater registration",
            ],
        ))
    elif jurisdiction == "FL":
        items.append(ChecklistItem(
            name="Wind Mitigation Inspection",
            description="Florida wind mitigation verification for hurricane-resistant construction.",
            required=True,
            status="not_started",
            documents_needed=[
                "Wind mitigation inspection form (OIR-B1-1802)",
                "Product approval documentation for windows/doors",
                "Roof-to-wall connection details",
                "Impact-rated opening protection specs",
                "FBC (Florida Building Code) compliance letter",
            ],
        ))
    elif jurisdiction == "TX":
        items.append(ChecklistItem(
            name="Foundation Soil Report",
            description="Texas expansive soil assessment and foundation design review.",
            required=True,
            status="not_started",
            documents_needed=[
                "Geotechnical soil investigation report",
                "Foundation design recommendation",
                "Soil moisture management plan",
                "Pier and beam or slab design calculations",
            ],
        ))
    elif jurisdiction == "NY":
        items.append(ChecklistItem(
            name="NYC DOB Filing (if applicable)",
            description="New York City Department of Buildings filing and professional certification.",
            required=False,
            status="not_started",
            documents_needed=[
                "DOB NOW filing application",
                "Professional certification (PE/RA)",
                "Zoning analysis (ZR compliance)",
                "Landmarks Preservation Commission approval (if historic district)",
                "Asbestos survey (ACP-5 form for pre-1985 buildings)",
            ],
        ))

    return items


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
