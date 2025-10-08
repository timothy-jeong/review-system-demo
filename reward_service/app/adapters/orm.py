# reward_service/app/adapters/orm.py
from sqlalchemy import (
    Column, UUID as UUID_TYPE, String, Integer, TIMESTAMP, Text, UniqueConstraint, JSON
)
from sqlalchemy.dialects.postgresql import JSONB

from app.database import Base

class RewardEvent(Base):
    """Event 테이블에 매핑되는 ORM 모델"""
    __tablename__ = "reward_events"
    aggregate_id = Column(String(255), nullable=False, index=True)
    event_id = Column(UUID_TYPE, primary_key=True)
    event_type = Column(String(255), nullable=False)
    payload = Column(JSON, nullable=False)
    version = Column(Integer, nullable=False)
    timestamp = Column(TIMESTAMP(timezone=True), nullable=False)

    __table_args__ = (
        UniqueConstraint("aggregate_id", "version", name="uq_events_aggregate_version"),
    )

class RewardBalance(Base):
    """reward_balances 테이블 (유저의 총 잔액 지갑)"""
    __tablename__ = "reward_balances"

    user_id = Column(String(255), primary_key=True)
    balance = Column(Integer, nullable=False, default=0)
    last_updated_at = Column(TIMESTAMP(timezone=True))
    
class ReviewRewardSummary(Base):
    """review_reward_summary 테이블에 매핑되는 ORM 모델"""
    __tablename__ = "review_reward_summary"

    review_id = Column(String(255), primary_key=True)

    user_id = Column(String(255), nullable=False, index=True)
    net_points = Column(Integer, nullable=False, default=0)
    last_updated_at = Column(TIMESTAMP(timezone=True))

class ReviewPointHistory(Base):
    """review_point_history 읽기 모델 테이블에 매핑되는 ORM 모델"""
    __tablename__ = "review_point_history"

    id = Column(Integer, primary_key=True) # SERIAL PRIMARY KEY
    user_id = Column(String(255), nullable=False)
    review_id = Column(String(255), nullable=False, index=True)
    points_change = Column(Integer, nullable=False)
    reason = Column(Text)
    event_timestamp = Column(TIMESTAMP(timezone=True), nullable=False)