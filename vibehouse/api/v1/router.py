from fastapi import APIRouter

from vibehouse.api.v1.auth import router as auth_router
from vibehouse.api.v1.board import router as board_router
from vibehouse.api.v1.change_orders import router as change_orders_router
from vibehouse.api.v1.dashboard import router as dashboard_router
from vibehouse.api.v1.designs import router as designs_router
from vibehouse.api.v1.disputes import router as disputes_router
from vibehouse.api.v1.invitations import router as invitations_router
from vibehouse.api.v1.notifications import router as notifications_router
from vibehouse.api.v1.permits import router as permits_router
from vibehouse.api.v1.photos import router as photos_router
from vibehouse.api.v1.projects import router as projects_router
from vibehouse.api.v1.reports import router as reports_router
from vibehouse.api.v1.timeline import router as timeline_router
from vibehouse.api.v1.vendors import router as vendors_router
from vibehouse.api.v1.websocket import router as websocket_router

v1_router = APIRouter()

v1_router.include_router(auth_router)
v1_router.include_router(projects_router)
v1_router.include_router(designs_router)
v1_router.include_router(board_router)
v1_router.include_router(vendors_router)
v1_router.include_router(disputes_router)
v1_router.include_router(reports_router)
v1_router.include_router(dashboard_router)
v1_router.include_router(timeline_router)
v1_router.include_router(photos_router)
v1_router.include_router(change_orders_router)
v1_router.include_router(notifications_router)
v1_router.include_router(invitations_router)
v1_router.include_router(permits_router)
v1_router.include_router(websocket_router)
