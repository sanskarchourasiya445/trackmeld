import pytest
import pytest_asyncio
from typing import AsyncGenerator
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool
from backend.app.config import get_settings
from backend.app.main import app
from backend.app.db.session import get_db_session

settings = get_settings()


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    engine = create_async_engine(
        settings.DATABASE_URL,
        poolclass=NullPool,
    )
    session_factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    async with session_factory() as session:
        yield session
    await engine.dispose()


@pytest.fixture(autouse=True)
def configure_test_demo_auth(request, monkeypatch):
    """Explicitly enable demo authentication in the test environment for integration suites,
    unless the test is marked with production or no_demo_auth."""
    s = get_settings()
    if request.node.get_closest_marker("production") or request.node.get_closest_marker("no_demo_auth"):
        monkeypatch.setattr(s, "ENABLE_DEMO_AUTH", False)
        monkeypatch.setattr(s, "ENVIRONMENT", "production")
        return

    monkeypatch.setattr(s, "ENABLE_DEMO_AUTH", True)
    monkeypatch.setattr(s, "ENVIRONMENT", "test")


class AuthAwareAsyncClient(AsyncClient):
    """AsyncClient that defaults to planner credentials for legacy tests when no
    explicit authentication headers (Authorization or X-API-Key) are provided, while
    strictly preserving explicit authentication headers and allowing explicitly
    header-free requests (headers={}).
    """
    async def request(self, method: str, url, **kwargs):
        headers = kwargs.get("headers")
        if headers is not None:
            # If the caller explicitly provided auth headers or an empty dict to test unauthenticated
            if (
                "Authorization" in headers
                or "authorization" in headers
                or "X-API-Key" in headers
                or "x-api-key" in headers
                or len(headers) == 0
            ):
                return await super().request(method, url, **kwargs)

        headers_dict = dict(headers or {})
        headers_dict.setdefault("Authorization", "Bearer planner-token-2026")
        kwargs["headers"] = headers_dict
        return await super().request(method, url, **kwargs)


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    async def override_get_db_session():
        yield db_session

    app.dependency_overrides[get_db_session] = override_get_db_session
    transport = ASGITransport(app=app)
    async with AuthAwareAsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def unauthenticated_client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    async def override_get_db_session():
        yield db_session

    app.dependency_overrides[get_db_session] = override_get_db_session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def authenticated_client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    async def override_get_db_session():
        yield db_session

    app.dependency_overrides[get_db_session] = override_get_db_session
    transport = ASGITransport(app=app)
    headers = {"Authorization": "Bearer planner-token-2026"}
    async with AsyncClient(transport=transport, base_url="http://test", headers=headers) as ac:
        yield ac
    app.dependency_overrides.clear()
