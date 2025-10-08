import pytest_asyncio
from typing import AsyncGenerator, List 

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
import httpx
from httpx import ASGITransport
from pydantic import BaseModel

# We need the actual message_bus instance and its dependency getter
from app.messaging.bus import MessageBus, get_message_bus
from app.database import Base, get_db
from app.main import app

class FakeMessageBus(MessageBus):
    """테스트용 가짜 메시지 버스. 메시지를 보내는 척하고 내부에 저장만 합니다."""
    def __init__(self):
        self.messages: List[BaseModel] = []

    async def connect(self):
        print("Fake bus connected (no real connection).")

    async def disconnect(self):
        print("Fake bus disconnected.")

    async def publish(self, topic: str, message: BaseModel):
        print(f"Fake bus captured message on topic '{topic}'")
        self.messages.append(message)

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
async def bus() -> FakeMessageBus:
    """FakeMessageBus 인스턴스를 제공하는 픽스처."""
    return FakeMessageBus()

@pytest_asyncio.fixture(scope="function")
async def client(db_session: AsyncSession, bus: FakeMessageBus) -> AsyncGenerator[httpx.AsyncClient, None]:
    """DB와 Bus 의존성이 모두 오버라이드된 테스트 클라이언트를 생성합니다."""
    
    def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session
    
    def override_get_bus() -> MessageBus:
        return bus

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_message_bus] = override_get_bus

    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c

    del app.dependency_overrides[get_db]
    del app.dependency_overrides[get_message_bus]