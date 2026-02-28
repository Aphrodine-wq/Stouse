# VibeHouse - AI-Powered Home Construction Platform

VibeHouse transforms home construction from overwhelming complexity into a guided, AI-orchestrated experience. Describe your dream home in natural language and get buildable designs, automated vendor procurement, real-time Trello-based project tracking, daily build reports, and structured dispute resolution.

## Features

### Core Platform
- **Vibe Code Engine** - Natural language to buildable floor plans with structural engineering and cost estimation
- **Design Refinement Loop** - Iterative feedback on designs with side-by-side comparison
- **Project Lifecycle Management** - Full state machine from draft through completion
- **Trello Board Auto-Creation** - 9 construction phases with 40+ pre-built tasks, real-time sync via webhooks

### Construction Management
- **Vendor Discovery & Matching** - Geospatial search, composite scoring, automated RFQ generation
- **Daily Build Reports** - Automated compilation of task progress, schedule health, risk alerts, budget tracking
- **Budget Burn-Down Tracking** - Real-time spend tracking with 75/90/100% threshold alerts
- **Site Photo Gallery** - Upload, tag, and track construction progress through photos

### Collaboration
- **4-Stage Dispute Resolution** - Identified > Direct Resolution > AI Mediation > External Mediation with auto-escalation timers
- **Change Order Management** - Request, approve/reject, implement with automatic budget adjustment
- **Team Invitations** - Invite contractors and inspectors via email with role-based access
- **Real-Time WebSocket Updates** - Live project events pushed to connected clients
- **Notification Center** - In-app, email, SMS notifications with configurable preferences

### Compliance
- **Permit Tracking** - Status tracking with validated state transitions
- **Jurisdiction-Specific Checklists** - Auto-generated permit checklists based on project location (state-specific requirements for CA, FL, TX, NY, etc.)

### Analytics
- **Project Dashboard** - Phase progress, task summary, financial summary, timeline overview, activity feed, weather
- **Gantt Timeline** - Phase/task timeline with estimated dates, critical path analysis, milestones

## Tech Stack

| Layer | Technology |
|-------|-----------|
| API | FastAPI 0.115+ (async) |
| ORM | SQLAlchemy 2.0 (async, mapped_column) |
| Database | PostgreSQL 16 (JSONB) |
| Migrations | Alembic |
| Task Queue | Celery 5.3+ with Redis broker |
| Auth | JWT (python-jose) + bcrypt (passlib) |
| Validation | Pydantic v2 |
| Container | Docker + Docker Compose |
| Testing | pytest + pytest-asyncio + SQLite |

## Quick Start

### Docker (Recommended)

```bash
cp .env.example .env
docker-compose up --build
```

This starts:
- **API Server** at `http://localhost:8000`
- **PostgreSQL** on port 5432
- **Redis** on port 6379
- **Celery Worker** (task processing)
- **Celery Beat** (scheduled tasks - daily reports, dispute escalation, board sync)

### Local Development

```bash
# Install dependencies
pip install -e ".[dev]"

# Set up environment
cp .env.example .env

# Run migrations
alembic upgrade head

# Seed demo data (optional)
python -m vibehouse.scripts.seed

# Start the API server
uvicorn vibehouse.main:app --reload

# Start Celery worker (separate terminal)
celery -A vibehouse.tasks.celery_app worker -l info

# Start Celery beat (separate terminal)
celery -A vibehouse.tasks.celery_app beat -l info
```

### API Documentation

Visit `http://localhost:8000/docs` for interactive Swagger UI.

## API Endpoints

### Authentication
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/auth/register` | Create user account |
| POST | `/api/v1/auth/login` | Login with email/password |
| POST | `/api/v1/auth/refresh` | Refresh access token |
| GET | `/api/v1/auth/me` | Get current user profile |

### Projects
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/projects` | Create project |
| GET | `/api/v1/projects` | List user's projects |
| GET | `/api/v1/projects/{id}` | Get project details |
| PATCH | `/api/v1/projects/{id}` | Update project |

### Designs
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/projects/{id}/vibe` | Submit vibe description |
| GET | `/api/v1/projects/{id}/designs` | List generated designs |
| POST | `/api/v1/projects/{id}/designs/{did}/select` | Select a design |
| POST | `/api/v1/projects/{id}/designs/{did}/refine` | Refine with feedback |
| GET | `/api/v1/projects/{id}/designs/compare?design_ids=a,b` | Compare designs |

### Board (Trello)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/projects/{id}/board` | Get board state |
| POST | `/api/v1/webhooks/trello` | Trello webhook receiver |

### Vendors
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/projects/{id}/vendors/search` | Search vendors |
| GET | `/api/v1/projects/{id}/vendors/bids` | List bids |
| POST | `/api/v1/projects/{id}/vendors/{vid}/select` | Select vendor |

### Disputes
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/projects/{id}/disputes` | File dispute |
| GET | `/api/v1/projects/{id}/disputes` | List disputes |
| PATCH | `/api/v1/projects/{id}/disputes/{did}` | Update (respond/escalate/resolve) |

### Reports
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/projects/{id}/reports/daily` | List daily reports |
| GET | `/api/v1/projects/{id}/reports/daily/latest` | Get latest report |
| GET | `/api/v1/projects/{id}/budget` | Get budget summary |

### Dashboard & Timeline
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/projects/{id}/dashboard` | Full project dashboard |
| GET | `/api/v1/projects/{id}/timeline` | Gantt timeline data |
| GET | `/api/v1/projects/{id}/timeline/milestones` | Project milestones |

### Photos
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/projects/{id}/photos` | Upload photo |
| GET | `/api/v1/projects/{id}/photos` | List photos (paginated) |
| GET | `/api/v1/projects/{id}/photos/progress` | Progress summary |

### Change Orders
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/projects/{id}/change-orders` | Create change order |
| GET | `/api/v1/projects/{id}/change-orders` | List change orders |
| PATCH | `/api/v1/projects/{id}/change-orders/{cid}` | Approve/reject/implement |

### Notifications
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/notifications` | List notifications |
| POST | `/api/v1/notifications/{nid}/read` | Mark as read |
| POST | `/api/v1/notifications/read-all` | Mark all as read |
| GET | `/api/v1/notifications/preferences` | Get preferences |
| PUT | `/api/v1/notifications/preferences` | Update preferences |

### Invitations
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/projects/{id}/invitations` | Send invitation |
| GET | `/api/v1/projects/{id}/invitations` | List invitations |
| POST | `/api/v1/projects/{id}/invitations/{iid}/resend` | Resend |
| DELETE | `/api/v1/projects/{id}/invitations/{iid}` | Revoke |

### Permits
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/projects/{id}/permits` | Create permit record |
| GET | `/api/v1/projects/{id}/permits` | List permits |
| PATCH | `/api/v1/projects/{id}/permits/{pid}` | Update permit status |
| GET | `/api/v1/projects/{id}/permits/checklist` | Get/generate checklist |

### WebSocket
| Path | Description |
|------|-------------|
| `ws://host/api/v1/ws/projects/{id}?token=JWT` | Real-time project events |

### Health
| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Service health check |

## Project Structure

```
vibehouse/
├── main.py                    # FastAPI app factory
├── config.py                  # Pydantic Settings
├── api/
│   ├── deps.py                # Dependencies (auth, DB, RBAC)
│   ├── middleware.py           # Audit logging
│   ├── ws.py                  # WebSocket connection manager
│   └── v1/                    # 15 endpoint modules
├── core/
│   ├── vibe_engine/           # NL parsing, floor plans, engineering, cost estimation
│   ├── trello_sync/           # Board management, webhook handling
│   ├── orchestration/         # Vendor discovery, outreach, RFQ
│   ├── reporting/             # Daily reports, budget tracking
│   └── disputes/              # 4-stage resolution workflow
├── db/
│   ├── models/                # 17 SQLAlchemy models
│   └── migrations/            # Alembic versions
├── tasks/                     # 6 Celery task modules
├── integrations/              # Mock clients (Trello, Email, SMS, AI, Maps, Storage)
├── common/                    # Enums, security, exceptions, pagination, events
├── scripts/
│   └── seed.py                # Demo data seeder (5 users, 15 vendors, 4 projects)
└── tests/                     # 60 tests across 14 test files
```

## Testing

```bash
# Run all 60 tests
python -m pytest vibehouse/tests/ -v

# Run specific module
python -m pytest vibehouse/tests/test_dashboard.py -v

# With coverage
python -m pytest vibehouse/tests/ --cov=vibehouse
```

## User Roles

| Role | Capabilities |
|------|-------------|
| **Homeowner** | Create projects, submit vibes, select designs, file disputes, manage change orders, invite team members |
| **Contractor** | View assigned projects, update task status, submit bids |
| **Inspector** | View projects, submit inspection reports |
| **Admin** | Full access to all projects and administrative functions |

## Architecture Notes

- **All external integrations use mock clients** behind abstract interfaces (`vibehouse/integrations/base.py`). Swap in real implementations (Trello API, SendGrid, Twilio, OpenAI, Google Maps, S3) by implementing the same interface.
- **Async-first**: FastAPI + SQLAlchemy async sessions + Celery for background work
- **Celery Beat schedules**: Daily reports at 6:30 AM, dispute escalation checks hourly, board sync every 15 minutes
- **Pagination** is available on all list endpoints via `?page=1&page_size=20&sort_by=created_at&sort_order=desc`
- **WebSocket events** are emitted from API handlers and can be consumed by frontend clients for real-time updates
