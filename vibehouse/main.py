from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from vibehouse.api.middleware import AuditMiddleware
from vibehouse.api.v1.router import v1_router
from vibehouse.api.ws import manager
from vibehouse.common.logging import setup_logging


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    yield


app = FastAPI(
    title="VibeHouse API",
    description="AI-Powered Home Construction Platform — manage projects from vibe "
    "to keys with AI-generated designs, Trello-based orchestration, vendor "
    "procurement, daily reporting, and structured dispute resolution.",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(AuditMiddleware)

app.include_router(v1_router, prefix="/api/v1")


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "vibehouse",
        "version": "2.0.0",
        "ws_connections": manager.active_connections,
    }
