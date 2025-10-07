# tests/conftest.py
import pytest_asyncio
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
import httpx
from httpx import ASGITransport

# We need the actual message_bus instance and its dependency getter
from app.messaging.bus import message_bus, get_message_bus, MessageBus
from app.database import Base, get_db
from app.main import app

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

engine = create_async_engine(TEST_DATABASE_URL)
TestingSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

@pytest_asyncio.fixture(scope="session")
async def db_engine():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine

@pytest_asyncio.fixture(scope="function")
async def db_session(db_engine) -> AsyncGenerator[AsyncSession, None]:
    async with TestingSessionLocal() as session:
        yield session

@pytest_asyncio.fixture(scope="function")
async def bus() -> AsyncGenerator[MessageBus, None]:
    """Fixture to connect and disconnect the message bus for each test."""
    await message_bus.connect()
    yield message_bus
    await message_bus.disconnect()

@pytest_asyncio.fixture(scope="function")
async def client(db_session: AsyncSession, bus: MessageBus) -> AsyncGenerator[httpx.AsyncClient, None]:
    """Fixture to create a test client that overrides dependencies."""
    
    # Override database dependency
    def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session
    
    # Override message bus dependency
    def override_get_bus() -> MessageBus:
        return bus

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_message_bus] = override_get_bus

    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c

    # Clean up overrides
    del app.dependency_overrides[get_db]
    del app.dependency_overrides[get_message_bus]