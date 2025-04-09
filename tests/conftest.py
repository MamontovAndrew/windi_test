import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.database import engine, async_session
from app.models import Base

@pytest_asyncio.fixture(scope="session")
async def prepare_database():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

@pytest_asyncio.fixture
async def db_session(prepare_database):
    async with async_session() as session:
        yield session

@pytest_asyncio.fixture
async def client(prepare_database):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
