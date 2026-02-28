import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from vibehouse.api.deps import get_current_user, get_db
from vibehouse.common.enums import UserRole
from vibehouse.common.exceptions import BadRequestError, PermissionDeniedError
from vibehouse.common.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_password_hash,
    verify_password,
)
from vibehouse.db.models.user import User

router = APIRouter(prefix="/auth", tags=["Authentication"])


# ---------- Schemas ----------


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    phone: str | None = None
    role: UserRole = UserRole.HOMEOWNER


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class UserResponse(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str
    phone: str | None
    role: str
    is_active: bool

    model_config = {"from_attributes": True}


# ---------- Endpoints ----------


@router.post("/register", response_model=UserResponse, status_code=201)
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == body.email))
    if result.scalar_one_or_none():
        raise BadRequestError("An account with this email already exists")

    user = User(
        email=body.email,
        hashed_password=get_password_hash(body.password),
        full_name=body.full_name,
        phone=body.phone,
        role=body.role.value,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(User).where(User.email == body.email, User.is_deleted.is_(False))
    )
    user = result.scalar_one_or_none()

    if not user or not verify_password(body.password, user.hashed_password):
        raise PermissionDeniedError("Invalid email or password")

    if not user.is_active:
        raise PermissionDeniedError("Account is inactive")

    access_token = create_access_token({"sub": str(user.id)})
    refresh_token = create_refresh_token({"sub": str(user.id)})

    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(body: RefreshRequest, db: AsyncSession = Depends(get_db)):
    try:
        payload = decode_token(body.refresh_token)
    except ValueError:
        raise PermissionDeniedError("Invalid refresh token")

    if payload.get("type") != "refresh":
        raise PermissionDeniedError("Invalid token type")

    user_id = payload.get("sub")
    result = await db.execute(
        select(User).where(User.id == uuid.UUID(user_id), User.is_deleted.is_(False))
    )
    user = result.scalar_one_or_none()
    if not user:
        raise PermissionDeniedError("User not found")

    access_token = create_access_token({"sub": str(user.id)})
    new_refresh_token = create_refresh_token({"sub": str(user.id)})

    return TokenResponse(access_token=access_token, refresh_token=new_refresh_token)


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user
