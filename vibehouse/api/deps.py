import uuid
from collections.abc import AsyncGenerator

from fastapi import Depends, Header
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from vibehouse.common.enums import UserRole
from vibehouse.common.exceptions import NotFoundError, PermissionDeniedError
from vibehouse.common.security import decode_token
from vibehouse.db.models.user import User
from vibehouse.db.session import async_session_factory


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def get_current_user(
    authorization: str = Header(..., description="Bearer <token>"),
    db: AsyncSession = Depends(get_db),
) -> User:
    if not authorization.startswith("Bearer "):
        raise PermissionDeniedError("Invalid authorization header format")

    token = authorization[len("Bearer "):]
    try:
        payload = decode_token(token)
    except ValueError:
        raise PermissionDeniedError("Invalid or expired token")

    if payload.get("type") != "access":
        raise PermissionDeniedError("Invalid token type")

    user_id = payload.get("sub")
    if not user_id:
        raise PermissionDeniedError("Invalid token payload")

    result = await db.execute(
        select(User).where(User.id == uuid.UUID(user_id), User.is_deleted.is_(False))
    )
    user = result.scalar_one_or_none()

    if not user:
        raise NotFoundError("User")
    if not user.is_active:
        raise PermissionDeniedError("User account is inactive")

    return user


def require_role(*roles: UserRole):
    async def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in [r.value for r in roles]:
            raise PermissionDeniedError(
                f"This action requires one of the following roles: {', '.join(r.value for r in roles)}"
            )
        return current_user

    return role_checker
