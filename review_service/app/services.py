from sqlalchemy.ext.asyncio import AsyncSession

from . import schemas, crud, models

def define_review_type(data: dict) -> models.ReviewType:
    if not data.get("comment"):
        return models.ReviewType.RATING
        
    if data.get("photo_name"):
        return models.ReviewType.PHOTO
    
    return models.ReviewType.NORMAL

async def create_review(db: AsyncSession, review_request: schemas.ReviewCreateRequest) -> models.Review:
    review_type = define_review_type(review_request.model_dump())
    
    internal_review_data = schemas.ReviewCreateInternal(
        **review_request.model_dump(),
        review_type=review_type
    )

    return await crud.create_review(db=db, review=internal_review_data)

async def update_review(db: AsyncSession, review_id: int, review_update: schemas.ReviewUpdateRequest) -> models.Review:
    """리뷰 수정 서비스"""
    
    update_data_dict = review_update.model_dump(exclude_unset=True)
    review_type = define_review_type(update_data_dict)
    
    internal_review_data = schemas.ReviewUpdateInternal(
        **update_data_dict,
        review_type=review_type
    )

    return await crud.update_review(db=db, review_id=review_id, review_update=internal_review_data)