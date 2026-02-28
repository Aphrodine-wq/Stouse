"""Reusable pagination, filtering and sorting for list endpoints."""

from __future__ import annotations

from typing import Any, Generic, TypeVar

from fastapi import Query
from pydantic import BaseModel
from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

T = TypeVar("T")


class PaginationParams:
    """Inject as a FastAPI dependency for any list endpoint."""

    def __init__(
        self,
        page: int = Query(1, ge=1, description="Page number"),
        page_size: int = Query(20, ge=1, le=100, description="Items per page"),
        sort_by: str | None = Query(None, description="Column to sort by"),
        sort_order: str = Query("desc", pattern="^(asc|desc)$", description="asc or desc"),
        search: str | None = Query(None, description="Free-text search"),
    ):
        self.page = page
        self.page_size = page_size
        self.sort_by = sort_by
        self.sort_order = sort_order
        self.search = search

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int
    total_pages: int


async def paginate(
    db: AsyncSession,
    query: Select,
    params: PaginationParams,
    model: Any = None,
) -> tuple[list[Any], int]:
    """Apply pagination to a query and return (items, total_count)."""
    # Count total
    count_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    # Sort
    if params.sort_by and model:
        col = getattr(model, params.sort_by, None)
        if col is not None:
            if params.sort_order == "asc":
                query = query.order_by(col.asc())
            else:
                query = query.order_by(col.desc())

    # Paginate
    query = query.offset(params.offset).limit(params.page_size)

    result = await db.execute(query)
    items = list(result.scalars().all())
    return items, total
