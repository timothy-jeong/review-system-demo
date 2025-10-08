from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert

from app.domain import events
from app.adapters.orm import RewardBalance, ReviewRewardSummary, ReviewPointHistory

class PointProjector:
    """
    포인트 관련 이벤트를 받아 모든 관련 읽기 모델을 업데이트합니다.
    """
    def __init__(self, session: AsyncSession):
        self.session = session

    async def handle(self, event: events.Event):
        """
        하나의 이벤트를 받아 관련된 모든 프로젝션 메서드를 호출합니다.
        """
        # 1. 유저의 총 잔액 업데이트
        await self._project_user_total_balance(event)

        # 2. 리뷰 관련 이벤트일 경우, 리뷰별 읽기 모델도 업데이트
        if hasattr(event, "review_id"):
            await self._project_review_summary(event)
            await self._project_review_history(event)

    async def _project_user_total_balance(self, event: events.Event):
        """RewardBalance 테이블 (유저의 총 잔액)을 업데이트합니다."""
        points_change = event.points
        if not isinstance(event, events.RewardPointsGranted):
            points_change = -event.points

        stmt = insert(RewardBalance.__table__).values(
            user_id=event.user_id,
            balance=points_change,
            last_updated_at=event.timestamp,
        )
        update_stmt = stmt.on_conflict_do_update(
            index_elements=["user_id"],
            set_={
                "balance": RewardBalance.__table__.c.balance + points_change,
                "last_updated_at": event.timestamp,
            },
        )
        await self.session.execute(update_stmt)

    async def _project_review_summary(self, event: events.Event):
        """ReviewRewardSummary 테이블 (리뷰별 순수 포인트)을 업데이트합니다."""
        points_change = event.points
        if not isinstance(event, events.RewardPointsGranted):
            points_change = -event.points
            
        stmt = insert(ReviewRewardSummary.__table__).values(
            review_id=event.review_id,
            user_id=event.user_id,

            net_points=points_change,
            last_updated_at=event.timestamp
        )
        update_stmt = stmt.on_conflict_do_update(
            index_elements=['review_id'],
            set_={
                "net_points": ReviewRewardSummary.__table__.c.net_points + points_change,
                "last_updated_at": event.timestamp
            }
        )
        await self.session.execute(update_stmt)

    async def _project_review_history(self, event: events.Event):
        """OrmReviewPointHistory 테이블 (리뷰별 거래 내역)에 로그를 추가합니다."""
        points_change = event.points
        if not isinstance(event, events.RewardPointsGranted):
            points_change = -event.points
        
        history_record = ReviewPointHistory(
            user_id=event.user_id,
            review_id=event.review_id,
            points_change=points_change,
            reason=event.reason,
            event_timestamp=event.timestamp,
        )
        self.session.add(history_record)