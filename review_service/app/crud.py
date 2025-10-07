# app/crud.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from . import models, schemas


async def create_review(db: AsyncSession, review: schemas.ReviewCreateInternal):
    db_review = models.Review(**review.model_dump())
    
    db.add(db_review)
    await db.commit()
    
    await db.refresh(db_review)
    return db_review


async def get_review(db: AsyncSession, review_id: int):
    result = await db.execute(select(models.Review).filter(models.Review.id == review_id))
    return result.scalars().first()


async def get_reviews(db: AsyncSession, skip: int = 0, limit: int = 100):
    result = await db.execute(
        select(models.Review)
        .order_by(models.Review.id.desc())
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()


async def update_review(db: AsyncSession, review_id: int, review_update: schemas.ReviewUpdateInternal):
    db_review = await get_review(db, review_id)
    if not db_review:
        return None

    update_data = review_update.model_dump(exclude_unset=True)

    for key, value in update_data.items():
        setattr(db_review, key, value)
    
    db.add(db_review)
    await db.commit()
    await db.refresh(db_review)
    return db_review


async def delete_review(db: AsyncSession, review_id: int):
    """ID를 기준으로 리뷰를 삭제합니다."""
    db_review = await get_review(db, review_id)
    if not db_review:
        return None  # 리뷰가 없으면 None 반환

    # 객체 삭제 후 커밋
    await db.delete(db_review)
    await db.commit()
    return db_review