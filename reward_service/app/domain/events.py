from pydantic import BaseModel, Field
from datetime import datetime
from uuid import UUID, uuid4

class Event(BaseModel):
    """Base class for all events."""
    event_id: UUID = Field(default_factory=uuid4)
    timestamp: datetime = Field(default_factory=datetime.now)

class RewardPointsGranted(Event):
    """Event for when points are granted to a user."""
    user_id: str
    review_id: str  # The review that triggered this grant
    points: int
    reason: str

class RewardPointsRefunded(Event):
    """Event for when points are refunded (spent)."""
    user_id: str
    order_id: str  # The order where points were used
    points: int
    reason: str

class RewardPointsRevoked(Event):
    """Event for when granted points are clawed back (e.g., fraudulent review)."""
    user_id: str
    review_id: str # The review that caused the revocation
    points: int
    reason: str