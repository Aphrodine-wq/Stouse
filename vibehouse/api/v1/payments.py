import uuid
from decimal import Decimal

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel as PydanticModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from vibehouse.api.deps import get_current_user, get_db, require_role
from vibehouse.common.enums import UserRole
from vibehouse.common.exceptions import BadRequestError, NotFoundError, PermissionDeniedError
from vibehouse.db.models.payment import Invoice, Payment
from vibehouse.db.models.project import Project
from vibehouse.db.models.user import User
from vibehouse.integrations.stripe_client import StripeClient

router = APIRouter(prefix="/payments", tags=["Payments"])


# ---------- Schemas ----------


class CreatePaymentIntentRequest(PydanticModel):
    project_id: uuid.UUID
    amount: Decimal
    description: str = ""


class PaymentResponse(PydanticModel):
    id: uuid.UUID
    project_id: uuid.UUID
    amount: Decimal
    currency: str
    status: str
    stripe_payment_intent_id: str | None
    description: str | None
    created_at: str
    model_config = {"from_attributes": True}


class CreateInvoiceRequest(PydanticModel):
    project_id: uuid.UUID
    vendor_id: uuid.UUID | None = None
    contract_id: uuid.UUID | None = None
    description: str = ""
    line_items: list[dict] = []
    due_days: int = 30


class InvoiceResponse(PydanticModel):
    id: uuid.UUID
    project_id: uuid.UUID
    invoice_number: str
    amount: Decimal
    status: str
    description: str | None
    hosted_url: str | None
    pdf_url: str | None
    created_at: str
    model_config = {"from_attributes": True}


# ---------- Endpoints ----------


@router.post("/intent", response_model=PaymentResponse, status_code=201)
async def create_payment_intent(
    body: CreatePaymentIntentRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Verify project access
    result = await db.execute(
        select(Project).where(Project.id == body.project_id, Project.is_deleted.is_(False))
    )
    project = result.scalar_one_or_none()
    if not project:
        raise NotFoundError("Project", str(body.project_id))
    if current_user.role != UserRole.ADMIN.value and project.owner_id != current_user.id:
        raise PermissionDeniedError("You do not have access to this project")

    stripe = StripeClient()
    intent = await stripe.create_payment_intent(
        amount_cents=int(body.amount * 100),
        description=body.description,
        metadata={"project_id": str(body.project_id), "user_id": str(current_user.id)},
    )

    payment = Payment(
        project_id=body.project_id,
        user_id=current_user.id,
        amount=body.amount,
        stripe_payment_intent_id=intent["id"],
        stripe_customer_id=intent.get("customer"),
        status=intent.get("status", "pending"),
        description=body.description,
    )
    db.add(payment)
    await db.flush()
    await db.refresh(payment)
    return PaymentResponse(
        id=payment.id, project_id=payment.project_id, amount=payment.amount,
        currency=payment.currency, status=payment.status,
        stripe_payment_intent_id=payment.stripe_payment_intent_id,
        description=payment.description, created_at=payment.created_at.isoformat(),
    )


@router.get("/{project_id}", response_model=list[PaymentResponse])
async def list_payments(
    project_id: uuid.UUID,
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

    result = await db.execute(
        select(Payment).where(Payment.project_id == project_id, Payment.is_deleted.is_(False))
        .order_by(Payment.created_at.desc())
    )
    payments = result.scalars().all()
    return [
        PaymentResponse(
            id=p.id, project_id=p.project_id, amount=p.amount, currency=p.currency,
            status=p.status, stripe_payment_intent_id=p.stripe_payment_intent_id,
            description=p.description, created_at=p.created_at.isoformat(),
        )
        for p in payments
    ]


@router.post("/invoices", response_model=InvoiceResponse, status_code=201)
async def create_invoice(
    body: CreateInvoiceRequest,
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.CONTRACTOR)),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Project).where(Project.id == body.project_id, Project.is_deleted.is_(False))
    )
    project = result.scalar_one_or_none()
    if not project:
        raise NotFoundError("Project", str(body.project_id))

    total = sum(item.get("amount_cents", 0) for item in body.line_items) / 100
    inv_number = f"VH-{uuid.uuid4().hex[:8].upper()}"

    stripe = StripeClient()
    stripe_inv = await stripe.create_invoice(
        customer_id=f"cus_project_{body.project_id}",
        items=body.line_items,
        description=body.description,
        due_days=body.due_days,
    )

    invoice = Invoice(
        project_id=body.project_id,
        vendor_id=body.vendor_id,
        contract_id=body.contract_id,
        stripe_invoice_id=stripe_inv.get("id"),
        invoice_number=inv_number,
        amount=Decimal(str(total)),
        status=stripe_inv.get("status", "draft"),
        description=body.description,
        line_items=body.line_items,
        hosted_url=stripe_inv.get("hosted_invoice_url"),
        pdf_url=stripe_inv.get("invoice_pdf"),
    )
    db.add(invoice)
    await db.flush()
    await db.refresh(invoice)
    return InvoiceResponse(
        id=invoice.id, project_id=invoice.project_id, invoice_number=invoice.invoice_number,
        amount=invoice.amount, status=invoice.status, description=invoice.description,
        hosted_url=invoice.hosted_url, pdf_url=invoice.pdf_url,
        created_at=invoice.created_at.isoformat(),
    )


@router.get("/invoices/{project_id}", response_model=list[InvoiceResponse])
async def list_invoices(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Invoice).where(Invoice.project_id == project_id, Invoice.is_deleted.is_(False))
        .order_by(Invoice.created_at.desc())
    )
    invoices = result.scalars().all()
    return [
        InvoiceResponse(
            id=inv.id, project_id=inv.project_id, invoice_number=inv.invoice_number,
            amount=inv.amount, status=inv.status, description=inv.description,
            hosted_url=inv.hosted_url, pdf_url=inv.pdf_url,
            created_at=inv.created_at.isoformat(),
        )
        for inv in invoices
    ]


@router.post("/webhook")
async def stripe_webhook(request: Request):
    """Handle Stripe webhook events."""
    payload = await request.body()
    sig = request.headers.get("stripe-signature", "")

    stripe = StripeClient()
    try:
        event = stripe.verify_webhook_signature(payload, sig)
    except ValueError:
        raise BadRequestError("Invalid webhook signature")

    event_type = event.get("type", "")

    if event_type == "payment_intent.succeeded":
        # Update payment status
        pass
    elif event_type == "invoice.paid":
        # Update invoice status
        pass
    elif event_type == "payment_intent.payment_failed":
        # Handle failure
        pass

    return {"status": "received"}
