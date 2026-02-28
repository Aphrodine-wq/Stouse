# VibeHouse

You describe the house. We figure out the rest.

VibeHouse is a construction management platform that takes a plain-English description of a home and turns it into architectural plans, contractor bids, a live project board, and daily progress reports. The backend is Python/FastAPI; the frontend is a lightweight iOS-inspired interface served by the same app.

---

## What it does

- **Vibe-to-blueprint** — Write something like "3-bedroom ranch, open kitchen, big porch" and get back floor plans, structural specs, material lists, and three cost options (budget / balanced / premium).
- **Contractor matching** — Automatically finds vetted local contractors for every trade your project needs. They bid; you pick.
- **Live build board** — A Trello board that stays in sync with the actual build. Tasks move themselves as work gets done.
- **Daily reports** — Every morning: what happened yesterday, what's on deck today, where the budget stands.
- **Dispute resolution** — Spots contractor conflicts, budget overruns, and scheduling problems before they blow up. When something does go sideways, there's a structured workflow to fix it.

## Quick start

```bash
cp .env.example .env          # fill in your keys (or keep the mocks for dev)
docker compose up --build     # starts postgres, redis, api, worker, beat
```

The app runs at `http://localhost:8000`. Hit `/` for the landing page, `/dashboard` for the project view, `/docs` for the API.

## Stack

| Layer | Tech |
|-------|------|
| API | FastAPI, Uvicorn |
| DB | PostgreSQL, SQLAlchemy (async) |
| Queue | Celery + Redis |
| Auth | JWT (python-jose), bcrypt |
| Frontend | Jinja2 templates, vanilla CSS/JS, iOS design system |

## Project layout

```
vibehouse/
  main.py              # app entry, page routes, static mount
  config.py            # pydantic-settings config
  api/v1/              # REST endpoints (auth, projects, designs, vendors, disputes, reports, board)
  core/                # business logic (vibe engine, orchestration, trello sync, reporting, disputes)
  db/models/           # SQLAlchemy ORM models
  db/migrations/       # Alembic migrations
  integrations/        # external service clients (mocked for dev)
  tasks/               # Celery async tasks
  templates/           # Jinja2 HTML (landing, dashboard)
  static/              # CSS, JS
  tests/               # pytest suite
```

## Running tests

```bash
pip install -e ".[dev]"
pytest
```

## API overview

All endpoints live under `/api/v1`. Auth is JWT bearer tokens.

| Endpoint | What it does |
|----------|-------------|
| `POST /auth/register` | Create an account |
| `POST /auth/login` | Get access + refresh tokens |
| `POST /projects` | Start a new project |
| `POST /designs/vibe` | Submit a vibe description, kick off plan generation |
| `GET /vendors/search` | Find contractors by trade and location |
| `POST /disputes` | File a dispute |
| `GET /reports/daily/{project_id}` | Get latest daily report |

Full interactive docs at `/docs` (Swagger) or `/redoc`.

## License

Not yet decided. Reach out if you're interested.
