import enum

from tsidpy import TSID
from sqlalchemy import Column, Integer, String, Text, DateTime, Enum
from sqlalchemy.sql import func
from .database import Base

class ReviewType(str, enum.Enum):
    NORMAL = "NORMAL"
    PHOTO = "PHOTO"

class Review(Base):
    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True, default=TSID.create().number)
    product_id = Column(String, nullable=False, index=True)
    user_id = Column(String, nullable=False, index=True)
    rating = Column(Integer, nullable=False, default=0)
    comment = Column(Text, nullable=True)
    review_type = Column(Enum(ReviewType), nullable=False, default=ReviewType.NORMAL)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())