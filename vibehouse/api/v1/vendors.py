import uuid
from decimal import Decimal

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from vibehouse.api.deps import get_current_user, get_db, require_role
from vibehouse.common.enums import ContractStatus, UserRole
from vibehouse.common.exceptions import NotFoundError, PermissionDeniedError
from vibehouse.db.models.contract import Contract
from vibehouse.db.models.project import Project
from vibehouse.db.models.user import User
from vibehouse.db.models.vendor import Bid, Vendor

router = APIRouter(prefix="/projects/{project_id}", tags=["Vendors"])


# ---------- Schemas ----------


class VendorSearchRequest(BaseModel):
    trade: str
    radius_miles: int = 50


class VendorSearchResponse(BaseModel):
    message: str
    project_id: uuid.UUID


class VendorResponse(BaseModel):
    id: uuid.UUID
    company_name: str
    contact_name: str | None
    email: str
    phone: str | None
    trades: list | None
    rating: float
    is_verified: bool

    model_config = {"from_attributes": True}


class BidResponse(BaseModel):
    id: uuid.UUID
    vendor_id: uuid.UUID
    vendor_name: str
    amount: Decimal
    scope_description: str | None
    timeline_days: int | None
    status: str

    model_config = {"from_attributes": True}


class BidListResponse(BaseModel):
    bids: list[BidResponse]
    total: int


class VendorSelectRequest(BaseModel):
    scope: str
    amount: Decimal


class ContractResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    vendor_id: uuid.UUID
    scope: str
    amount: Decimal
    status: str

    model_config = {"from_attributes": True}


# ---------- Endpoints ----------


@router.post("/vendors/search", response_model=VendorSearchResponse)
async def search_vendors(
    project_id: uuid.UUID,
    body: VendorSearchRequest,
    current_user: User = Depends(require_role(UserRole.HOMEOWNER, UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    await _verify_project_access(project_id, current_user, db)

    from vibehouse.tasks.vendor_tasks import discover_vendors_for_project

    discover_vendors_for_project.delay(str(project_id), body.trade, body.radius_miles)

    return VendorSearchResponse(
        message="Vendor discovery started. Check back for results.",
        project_id=project_id,
    )


@router.get("/vendors/bids", response_model=BidListResponse)
async def list_bids(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _verify_project_access(project_id, current_user, db)

    result = await db.execute(
        select(Bid, Vendor)
        .join(Vendor, Bid.vendor_id == Vendor.id)
        .where(Bid.project_id == project_id, Bid.is_deleted.is_(False))
        .order_by(Bid.amount)
    )
    rows = result.all()

    bids = [
        BidResponse(
            id=bid.id,
            vendor_id=bid.vendor_id,
            vendor_name=vendor.company_name,
            amount=bid.amount,
            scope_description=bid.scope_description,
            timeline_days=bid.timeline_days,
            status=bid.status,
        )
        for bid, vendor in rows
    ]

    return BidListResponse(bids=bids, total=len(bids))


@router.post("/vendors/{vendor_id}/select", response_model=ContractResponse)
async def select_vendor(
    project_id: uuid.UUID,
    vendor_id: uuid.UUID,
    body: VendorSelectRequest,
    current_user: User = Depends(require_role(UserRole.HOMEOWNER, UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    await _verify_project_access(project_id, current_user, db)

    result = await db.execute(select(Vendor).where(Vendor.id == vendor_id))
    vendor = result.scalar_one_or_none()
    if not vendor:
        raise NotFoundError("Vendor", str(vendor_id))

    contract = Contract(
        project_id=project_id,
        vendor_id=vendor_id,
        scope=body.scope,
        amount=body.amount,
        status=ContractStatus.DRAFT.value,
    )
    db.add(contract)
    await db.flush()
    await db.refresh(contract)

    return ContractResponse(
        id=contract.id,
        project_id=contract.project_id,
        vendor_id=contract.vendor_id,
        scope=contract.scope,
        amount=contract.amount,
        status=contract.status,
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
