from fastapi import APIRouter

from vibehouse.api.v1.auth import router as auth_router
from vibehouse.api.v1.board import router as board_router
from vibehouse.api.v1.designs import router as designs_router
from vibehouse.api.v1.disputes import router as disputes_router
from vibehouse.api.v1.projects import router as projects_router
from vibehouse.api.v1.reports import router as reports_router
from vibehouse.api.v1.vendors import router as vendors_router

v1_router = APIRouter()

v1_router.include_router(auth_router)
v1_router.include_router(projects_router)
v1_router.include_router(designs_router)
v1_router.include_router(board_router)
v1_router.include_router(vendors_router)
v1_router.include_router(disputes_router)
v1_router.include_router(reports_router)
