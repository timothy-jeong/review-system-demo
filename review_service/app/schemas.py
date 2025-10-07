import random
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

PRODUCT_CANDIDATES = [f"PROD-{i:03}" for i in range(1, 11)] # PROD-001 ~ PROD-010
USER_CANDIDATES = [f"USER-{i:03}" for i in range(1, 21)]    # USER-001 ~ USER-020

class ReviewBase(BaseModel):
    rating: int = Field(..., gt=0, le=5)
    comment: Optional[str] = None

class ReviewCreate(ReviewBase):
    product_id: str = Field(default_factory=lambda: random.choice(PRODUCT_CANDIDATES))
    user_id: str = Field(default_factory=lambda: random.choice(USER_CANDIDATES))

class ReviewUpdate(BaseModel):
    rating: Optional[int] = Field(None, gt=0, le=5)
    comment: Optional[str] = None

class ReviewRead(ReviewBase):
    id: str
    product_id: str
    user_id: str
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(
        from_attributes=True,
        coerce_numbers_to_str=True,
    )