from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.domain import models, events
from .orm import RewardEvent

class ConcurrencyError(Exception):
    """Custom exception for version conflicts."""
    pass

class RewardAccountRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def save(self, account: models.RewardAccount) -> list[events.Event]:
        """
        Saves uncommitted events from the aggregate to the event store.
        """
        if not account._uncommitted_events:
            return []

        # Convert domain events to ORM model instances
        orm_events = []
        for i, event in enumerate(account._uncommitted_events):
            # Calculate the correct version for each event in the batch
            event_version = (account.version - len(account._uncommitted_events)) + i + 1
            orm_events.append(
                RewardEvent(
                    event_id=event.event_id,
                    aggregate_id=account.id,
                    event_type=type(event).__name__,
                    payload=event.model_dump(mode="json"),
                    version=event_version,
                    timestamp=event.timestamp,
                )
            )
        
        # Add all new ORM event objects to the session
        self.session.add_all(orm_events)
        
        try:
            await self.session.flush()
        except IntegrityError as e:
            raise ConcurrencyError(f"Version conflict for account {account.id}") from e

        saved_events = list(account._uncommitted_events)
        account._uncommitted_events.clear()
        return saved_events

    async def load(self, user_id: str) -> models.RewardAccount:
        """
        Loads an aggregate's current state by replaying all its events.
        """
        # Use the ORM model in the select statement
        stmt = (
            select(RewardEvent)
            .where(RewardEvent.aggregate_id == user_id)
            .order_by(RewardEvent.version)
        )
        
        result = await self.session.execute(stmt)
        # .scalars().all() directly returns a list of OrmEvent objects
        orm_event_rows = result.scalars().all()

        if not orm_event_rows:
            raise ValueError(f"Account for user {user_id} not found.")

        # Recreate domain events from the ORM model's payload
        domain_events = []
        for row in orm_event_rows:
            event_class = getattr(events, row.event_type)
            domain_events.append(event_class(**row.payload))

        # Use the class method to replay events and build the aggregate state
        return models.RewardAccount.replay_from_events(domain_events)