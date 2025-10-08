from .events import Event, RewardPointsGranted, RewardPointsRefunded, RewardPointsRevoked

class RewardAccount:
    """The Aggregate Root for a user's reward account."""

    def __init__(self, user_id: str):
        # The current state of the aggregate
        self.user_id: str = user_id
        self.balance: int = 0
        self.version: int = 0
        
        # A list to hold new events that haven't been saved yet
        self._uncommitted_events: list[Event] = []

    # --- Public Command Methods ---
    def grant_points(self, points: int, reason: str, review_id: str):
        """Command to grant new points."""
        if points <= 0:
            raise ValueError("Points to grant must be positive.")
        
        # Create and apply the event.
        self._apply_and_record(
            RewardPointsGranted(
                user_id=self.user_id, review_id=review_id, points=points, reason=reason
            )
        )

    def refund_points(self, points: int, reason: str, order_id: str):
        """Command to refund (spend) points."""
        # Business Rule: Points refunded must be positive.
        if points <= 0:
            raise ValueError("Points to refund must be positive.")
        # Business Rule: Cannot spend more points than the current balance.
        if self.balance < points:
            raise ValueError("Insufficient points for refund.")

        self._apply_and_record(
            RewardPointsRefunded(
                user_id=self.user_id, order_id=order_id, points=points, reason=reason
            )
        )

    def revoke_points(self, points: int, reason: str, review_id: str):
        """Command to revoke previously granted points."""
        if points <= 0:
            raise ValueError("Points to revoke must be positive.")
        
        # Note: We might allow balance to go negative in case of fraud.

        self._apply_and_record(
            RewardPointsRevoked(
                user_id=self.user_id, review_id=review_id, points=points, reason=reason
            )
        )

    def _apply_and_record(self, event: Event):
        """Applies the event to the current state and records it."""
        self._apply(event)
        self._uncommitted_events.append(event)

    def _apply(self, event: Event):
        """The routing logic for applying different events."""
        if isinstance(event, RewardPointsGranted):
            self._apply_points_granted(event)
        elif isinstance(event, RewardPointsRefunded):
            self._apply_points_refunded(event)
        elif isinstance(event, RewardPointsRevoked):
            self._apply_points_revoked(event)
        
        self.version += 1

    def _apply_points_granted(self, event: RewardPointsGranted):
        self.balance += event.points

    def _apply_points_refunded(self, event: RewardPointsRefunded):
        self.balance -= event.points
        
    def _apply_points_revoked(self, event: RewardPointsRevoked):
        self.balance -= event.points

    @classmethod
    def replay_from_events(cls, events: list[Event]):
        """
        Creates an aggregate instance by replaying its entire history of events.
        This is how we load an aggregate from the Event Store.
        """
        if not events:
            raise ValueError("Cannot replay from an empty list of events.")
        
        # Create a new, blank instance
        account = cls(user_id=events[0].user_id)
        
        # Apply each event in order to reconstruct the state
        for event in events:
            account._apply(event)
            
        return account