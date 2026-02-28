import datetime
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from vibehouse.api.middleware import AuditMiddleware
from vibehouse.api.v1.router import v1_router
from vibehouse.api.v1.ws import router as ws_router
from vibehouse.common.logging import setup_logging
from vibehouse.config import settings

BASE_DIR = Path(__file__).resolve().parent


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    # Ensure local storage directory exists
    storage_path = Path(settings.STORAGE_LOCAL_PATH)
    storage_path.mkdir(parents=True, exist_ok=True)
    yield


app = FastAPI(
    title="VibeHouse API",
    description="AI-Powered Home Construction Platform",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS
origins = settings.ALLOWED_ORIGINS.split(",") if settings.ALLOWED_ORIGINS != "*" else ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(AuditMiddleware)

# Static files & templates
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")

# API routes
app.include_router(v1_router, prefix="/api/v1")
app.include_router(ws_router, prefix="/api/v1")


# --- Page routes ---


def _greeting() -> str:
    hour = datetime.datetime.now().hour
    if hour < 12:
        return "morning"
    elif hour < 17:
        return "afternoon"
    return "evening"


@app.get("/", response_class=HTMLResponse)
async def landing_page(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request, "time_of_day": _greeting()})


@app.get("/projects/new", response_class=HTMLResponse)
async def new_project_page(request: Request):
    return templates.TemplateResponse("new_project.html", {"request": request})


@app.get("/projects/{project_id}", response_class=HTMLResponse)
async def project_detail_page(request: Request, project_id: str):
    return templates.TemplateResponse("project_detail.html", {"request": request, "project_id": project_id})


@app.get("/projects/{project_id}/designs", response_class=HTMLResponse)
async def designs_page(request: Request, project_id: str):
    return templates.TemplateResponse("designs.html", {"request": request, "project_id": project_id})


@app.get("/projects/{project_id}/vendors", response_class=HTMLResponse)
async def vendors_page(request: Request, project_id: str):
    return templates.TemplateResponse("vendors.html", {"request": request, "project_id": project_id})


@app.get("/projects/{project_id}/budget", response_class=HTMLResponse)
async def budget_page(request: Request, project_id: str):
    return templates.TemplateResponse("budget.html", {"request": request, "project_id": project_id})


@app.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    return templates.TemplateResponse("settings.html", {"request": request})


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "vibehouse",
        "version": "1.0.0",
        "env": settings.APP_ENV,
    }
