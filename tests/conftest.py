import os

os.environ.setdefault("BOT_TOKEN", "123456:test-token")
os.environ.setdefault("BOT_USERNAME", "test_bot")
os.environ.setdefault("API_ID", "1")
os.environ.setdefault("API_HASH", "test-hash")
os.environ.setdefault("ENCRYPTION_KEY", "5c1MlveGejx_zjt42rCPhtKNiZamVKlLmk7BnNy24Yc=")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")

from collections.abc import AsyncIterator  # noqa: E402

import pytest  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine  # noqa: E402


@pytest.fixture
async def db_sessionmaker():
    """In-memory SQLite with the full schema — enough to exercise the API
    end to end without PostgreSQL."""
    from backend.models import Base

    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield async_sessionmaker(engine, expire_on_commit=False)
    await engine.dispose()


@pytest.fixture
async def api(db_sessionmaker, monkeypatch) -> AsyncIterator[AsyncClient]:
    from backend.core import rate_limit
    from backend.db.session import get_db
    from backend.main import app

    async def _get_db():
        async with db_sessionmaker() as session:
            yield session

    async def _no_limit(*_args, **_kwargs) -> bool:
        return True

    monkeypatch.setattr(rate_limit, "hit", _no_limit)
    app.dependency_overrides[get_db] = _get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()
