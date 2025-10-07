# app/main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, status, Response
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from . import crud, models, schemas, services
from .database import engine, Base, get_db
from .messaging.bus import message_bus, MessageBus, get_message_bus

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 Application startup: Initializing database...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("[infrastructure] Database initialized.")
    
    await message_bus.connect()
    
    yield
    
    await message_bus.disconnect()
    await engine.dispose()

app = FastAPI(
    title="Review Service API",
    lifespan=lifespan,
)


@app.post("/reviews/", response_model=schemas.ReviewRead, status_code=status.HTTP_201_CREATED, tags=["Reviews"])
async def create_review_endpoint(
    review: schemas.ReviewCreateRequest, 
    db: AsyncSession = Depends(get_db),
    bus: MessageBus = Depends(get_message_bus),
):
    """
    새로운 리뷰를 생성합니다.
    """
    return await services.create_review(db=db, bus=bus, review_request=review)


@app.get("/reviews/", response_model=List[schemas.ReviewRead], tags=["Reviews"])
async def read_reviews_endpoint(
    skip: int = 0, 
    limit: int = 100, 
    db: AsyncSession = Depends(get_db)
):
    """
    모든 리뷰 목록을 페이지네이션하여 조회합니다.
    """
    reviews = await crud.get_reviews(db, skip=skip, limit=limit)
    return reviews


@app.get("/reviews/{review_id}", response_model=schemas.ReviewRead, tags=["Reviews"])
async def read_review_endpoint(review_id: int, db: AsyncSession = Depends(get_db)):
    db_review = await crud.get_review(db, review_id=review_id)
    if db_review is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review not found")
    return db_review

@app.put("/reviews/{review_id}", response_model=schemas.ReviewRead, tags=["Reviews"])
async def update_review_endpoint(
    review_id: int, review: schemas.ReviewUpdateRequest, db: AsyncSession = Depends(get_db), bus: MessageBus = Depends(get_message_bus),
):
    db_review = await services.update_review(db=db, bus=bus, review_id=review_id, review_update=review)
    if db_review is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review not found")
    return db_review

@app.delete("/reviews/{review_id}", response_model=None, tags=["Reviews"], status_code=status.HTTP_204_NO_CONTENT)
async def delete_review_endpoint(review_id: int, db: AsyncSession = Depends(get_db)):
    db_review = await crud.delete_review(db, review_id=review_id)
    if db_review is None:
        raise HTTPException(status_code=404, detail="Review not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)