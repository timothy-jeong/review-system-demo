from sqlalchemy.ext.asyncio import AsyncSession

from . import schemas, crud, models
from .messaging.bus import MessageBus

def define_review_type(data: dict) -> models.ReviewType:
    if not data.get("comment"):
        return models.ReviewType.RATING
        
    if data.get("photo_name"):
        return models.ReviewType.PHOTO
    
    return models.ReviewType.NORMAL

async def create_review(
    db: AsyncSession,
    bus: MessageBus,
    review_request: schemas.ReviewCreateRequest,
    ) -> models.Review:
    
    review_type = define_review_type(review_request.model_dump())
    
    internal_review_data = schemas.ReviewCreateInternal(
        **review_request.model_dump(),
        review_type=review_type
    )
    
    created_review = await crud.create_review(db=db, review=internal_review_data)

    event = schemas.ReviewEvent(
        event_type="review.created",
        review=schemas.ReviewRead.model_validate(created_review)
    )
    await bus.publish(topic="review.created", message=event)
    
    return created_review

async def update_review(
    db: AsyncSession, 
    bus: MessageBus,
    review_id: int, 
    review_update: schemas.ReviewUpdateRequest,
    ) -> models.Review:
    
    update_data_dict = review_update.model_dump(exclude_unset=True)
    review_type = define_review_type(update_data_dict)
    
    internal_review_data = schemas.ReviewUpdateInternal(
        **update_data_dict,
        review_type=review_type
    )
    
    updated_review = await crud.update_review(db=db, review_id=review_id, review_update=internal_review_data)

    if updated_review:
        event = schemas.ReviewEvent(
            event_type="review.updated",
            review=schemas.ReviewRead.model_validate(updated_review)
        )
        await bus.publish(topic="review.updated", message=event)
        
    return updated_review