import asyncio
import uuid
from collections.abc import AsyncGenerator
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import JSON, event
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from vibehouse.common.enums import UserRole
from vibehouse.common.security import create_access_token, get_password_hash
from vibehouse.db.base import Base
from vibehouse.db.models import *  # noqa: F401,F403 - ensure all models loaded

# Use SQLite for testing - remap JSONB to JSON
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"


# Make JSONB render as JSON for SQLite
@event.listens_for(Base.metadata, "before_create")
def _remap_jsonb(target, connection, **kw):
    if connection.dialect.name == "sqlite":
        for table in target.tables.values():
            for column in table.columns:
                if isinstance(column.type, JSONB):
                    column.type = JSON()


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def test_engine():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    session_factory = async_sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with session_factory() as session:
        yield session
        await session.rollback()


@pytest.fixture
async def client(db_session):
    from vibehouse.api.deps import get_db
    from vibehouse.main import app

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture
async def homeowner_user(db_session):
    from vibehouse.db.models.user import User

    user = User(
        id=uuid.uuid4(),
        email=f"homeowner_{uuid.uuid4().hex[:8]}@test.com",
        hashed_password=get_password_hash("testpass123"),
        full_name="Test Homeowner",
        role=UserRole.HOMEOWNER.value,
    )
    db_session.add(user)
    await db_session.flush()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def admin_user(db_session):
    from vibehouse.db.models.user import User

    user = User(
        id=uuid.uuid4(),
        email=f"admin_{uuid.uuid4().hex[:8]}@test.com",
        hashed_password=get_password_hash("adminpass123"),
        full_name="Test Admin",
        role=UserRole.ADMIN.value,
    )
    db_session.add(user)
    await db_session.flush()
    await db_session.refresh(user)
    return user


@pytest.fixture
def homeowner_token(homeowner_user):
    return create_access_token({"sub": str(homeowner_user.id)})


@pytest.fixture
def admin_token(admin_user):
    return create_access_token({"sub": str(admin_user.id)})


@pytest.fixture
def auth_headers(homeowner_token):
    return {"Authorization": f"Bearer {homeowner_token}"}


@pytest.fixture
def admin_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture(autouse=True)
def mock_celery_tasks():
    """Mock all Celery task.delay() calls to prevent actual task execution in tests."""
    with (
        patch("vibehouse.tasks.vibe_tasks.process_vibe_description.delay"),
        patch("vibehouse.tasks.trello_tasks.create_project_board.delay"),
        patch("vibehouse.tasks.trello_tasks.process_trello_webhook.delay"),
        patch("vibehouse.tasks.vendor_tasks.discover_vendors_for_project.delay"),
        patch("vibehouse.tasks.vendor_tasks.send_vendor_rfqs.delay"),
        patch("vibehouse.tasks.dispute_tasks.generate_resolution_options.delay"),
    ):
        yield


@pytest.fixture(autouse=True)
def mock_integrations():
    """Mock external integration clients used in endpoint handlers."""
    with (
        patch("vibehouse.integrations.sendgrid.EmailClient.send_email", return_value={"message_id": "mock-123", "status": "sent"}),
        patch("vibehouse.common.events.emit", return_value=None),
    ):
        yield
