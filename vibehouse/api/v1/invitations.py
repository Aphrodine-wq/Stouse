"""Contractor and inspector invitation flow."""

from __future__ import annotations

import secrets
import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from vibehouse.api.deps import get_current_user, get_db, require_role
from vibehouse.common.enums import UserRole
from vibehouse.common.events import emit
from vibehouse.common.exceptions import BadRequestError, NotFoundError, PermissionDeniedError
from vibehouse.db.models.notification import Invitation
from vibehouse.db.models.project import Project
from vibehouse.db.models.user import User

router = APIRouter(prefix="/projects/{project_id}/invitations", tags=["Invitations"])


# ---------- Schemas ----------

class InvitationCreate(BaseModel):
    email: EmailStr
    role: str  # contractor, inspector
    vendor_id: uuid.UUID | None = None
    message: str | None = None


class InvitationResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    email: str
    role: str
    status: str
    vendor_id: uuid.UUID | None
    message: str | None
    created_at: str
    model_config = {"from_attributes": True}


class InvitationAcceptRequest(BaseModel):
    token: str


class InvitationListResponse(BaseModel):
    invitations: list[InvitationResponse]
    total: int


# ---------- Endpoints ----------

@router.post("", response_model=InvitationResponse, status_code=201)
async def create_invitation(
    project_id: uuid.UUID,
    body: InvitationCreate,
    current_user: User = Depends(require_role(UserRole.HOMEOWNER, UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    project = await _verify_access(project_id, current_user, db)

    if body.role not in ("contractor", "inspector"):
        raise BadRequestError("role must be 'contractor' or 'inspector'")

    # Check for existing pending invitation
    existing = await db.execute(
        select(Invitation).where(
            Invitation.project_id == project_id,
            Invitation.email == body.email,
            Invitation.status == "pending",
            Invitation.is_deleted.is_(False),
        )
    )
    if existing.scalar_one_or_none():
        raise BadRequestError(f"A pending invitation already exists for {body.email}")

    token = secrets.token_urlsafe(32)

    invitation = Invitation(
        project_id=project_id,
        invited_by_id=current_user.id,
        email=body.email,
        role=body.role,
        vendor_id=body.vendor_id,
        token=token,
        message=body.message,
    )
    db.add(invitation)
    await db.flush()
    await db.refresh(invitation)

    # Send invitation email (mock)
    from vibehouse.integrations.sendgrid import EmailClient
    email_client = EmailClient()
    await email_client.send_email(
        to=body.email,
        subject=f"You've been invited to join {project.title} on VibeHouse",
        html_body=f"""
        <h2>Project Invitation</h2>
        <p>You've been invited to join <strong>{project.title}</strong> as a {body.role}.</p>
        {f'<p>Message: {body.message}</p>' if body.message else ''}
        <p>Accept your invitation: https://app.vibehouse.io/invite/{token}</p>
        """,
    )

    await emit(str(project_id), "invitation.sent", {
        "email": body.email,
        "role": body.role,
        "invited_by": current_user.full_name,
    })

    return _invite_response(invitation)


@router.get("", response_model=InvitationListResponse)
async def list_invitations(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _verify_access(project_id, current_user, db)

    result = await db.execute(
        select(Invitation)
        .where(Invitation.project_id == project_id, Invitation.is_deleted.is_(False))
        .order_by(Invitation.created_at.desc())
    )
    invitations = result.scalars().all()

    return InvitationListResponse(
        invitations=[_invite_response(i) for i in invitations],
        total=len(invitations),
    )


@router.post("/{invitation_id}/resend")
async def resend_invitation(
    project_id: uuid.UUID,
    invitation_id: uuid.UUID,
    current_user: User = Depends(require_role(UserRole.HOMEOWNER, UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    await _verify_access(project_id, current_user, db)

    result = await db.execute(
        select(Invitation).where(
            Invitation.id == invitation_id,
            Invitation.project_id == project_id,
            Invitation.status == "pending",
        )
    )
    invitation = result.scalar_one_or_none()
    if not invitation:
        raise NotFoundError("Invitation", str(invitation_id))

    from vibehouse.integrations.sendgrid import EmailClient
    email_client = EmailClient()
    await email_client.send_email(
        to=invitation.email,
        subject="Reminder: You have a pending VibeHouse invitation",
        html_body=f"<p>Accept your invitation: https://app.vibehouse.io/invite/{invitation.token}</p>",
    )

    return {"message": "Invitation resent"}


@router.delete("/{invitation_id}")
async def revoke_invitation(
    project_id: uuid.UUID,
    invitation_id: uuid.UUID,
    current_user: User = Depends(require_role(UserRole.HOMEOWNER, UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    await _verify_access(project_id, current_user, db)

    result = await db.execute(
        select(Invitation).where(
            Invitation.id == invitation_id,
            Invitation.project_id == project_id,
        )
    )
    invitation = result.scalar_one_or_none()
    if not invitation:
        raise NotFoundError("Invitation", str(invitation_id))

    invitation.status = "expired"
    await db.flush()
    return {"message": "Invitation revoked"}


def _invite_response(inv: Invitation) -> InvitationResponse:
    return InvitationResponse(
        id=inv.id, project_id=inv.project_id, email=inv.email,
        role=inv.role, status=inv.status, vendor_id=inv.vendor_id,
        message=inv.message, created_at=inv.created_at.isoformat(),
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
