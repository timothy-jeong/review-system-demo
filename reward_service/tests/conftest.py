import pytest_asyncio
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
import httpx
from httpx import ASGITransport

from app.database import Base, get_db


TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"
engine = create_async_engine(TEST_DATABASE_URL)
TestingSessionLocal = sessionmaker(
    bind=engine, class_=AsyncSession, expire_on_commit=False
)

@pytest_asyncio.fixture(scope="session")
async def db_engine():
    """테스트 DB 테이블을 생성하는 픽스처 (세션 당 한 번 실행)"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine

@pytest_asyncio.fixture(scope="function")
async def db_session(db_engine) -> AsyncGenerator[AsyncSession, None]:
    """
    각 테스트를 위한 격리된 트랜잭션을 제공하고, 테스트 후 롤백합니다.
    """
    connection = await db_engine.connect()
    trans = await connection.begin()
    
    # 트랜잭션에 바인딩된 세션을 생성합니다.
    session = AsyncSession(bind=connection, expire_on_commit=False)

    try:
        yield session
    finally:
        # 테스트가 끝나면 모든 변경사항을 롤백합니다.
        await session.close()
        await trans.rollback()
        await connection.close()