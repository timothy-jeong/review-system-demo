import pytest
from datetime import datetime
from uuid import uuid4
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.services.projectors import PointProjector
from app.domain import events
from app.adapters.orm import RewardBalance, ReviewRewardSummary, ReviewPointHistory

# 모든 테스트 함수를 async로 실행하도록 설정
pytestmark = pytest.mark.asyncio

# --- 테스트용 데이터 ---
USER_ID = "user-123"
REVIEW_ID_A = "review-abc"
REVIEW_ID_B = "review-xyz"

# --- 테스트 시작 ---

async def test_handle_first_grant_event(db_session: AsyncSession):
    """
    첫 번째 RewardPointsGranted 이벤트가 발생했을 때,
    3개의 읽기 모델 테이블이 모두 올바르게 생성되는지 테스트합니다.
    """
    # Arrange: 이벤트와 프로젝터 준비
    projector = PointProjector(db_session)
    event = events.RewardPointsGranted(
        user_id=USER_ID,
        review_id=REVIEW_ID_A,
        points=50,
        reason="포토 리뷰 보상"
    )

    # Act: 이벤트 처리
    await projector.handle(event)
    await db_session.commit()

    # Assert: 각 테이블의 상태 확인
    # 1. 유저 총 잔액 확인
    balance_result = await db_session.execute(
        select(RewardBalance).where(RewardBalance.user_id == USER_ID)
    )
    user_balance = balance_result.scalars().one()
    assert user_balance.balance == 50

    # 2. 리뷰별 요약 확인
    summary_result = await db_session.execute(
        select(ReviewRewardSummary).where(ReviewRewardSummary.review_id == REVIEW_ID_A)
    )
    review_summary = summary_result.scalars().one()
    assert review_summary.net_points == 50

    # 3. 리뷰별 히스토리 확인
    history_result = await db_session.execute(
        select(ReviewPointHistory).where(ReviewPointHistory.review_id == REVIEW_ID_A)
    )
    history_log = history_result.scalars().one()
    assert history_log.points_change == 50
    assert history_log.reason == "포토 리뷰 보상"


async def test_handle_multiple_events_for_user(db_session: AsyncSession):
    """
    한 유저에게 여러 이벤트가 발생했을 때,
    총 잔액은 합산되고, 리뷰별 요약은 분리되는지 테스트합니다.
    """
    # Arrange
    projector = PointProjector(db_session)
    event_a = events.RewardPointsGranted(user_id=USER_ID, review_id=REVIEW_ID_A, points=50, reason="A")
    event_b = events.RewardPointsGranted(user_id=USER_ID, review_id=REVIEW_ID_B, points=10, reason="B")

    # Act
    await projector.handle(event_a)
    await projector.handle(event_b)
    await db_session.commit()

    # Assert
    # 1. 유저 총 잔액은 50 + 10 = 60
    balance_result = await db_session.execute(
        select(RewardBalance).where(RewardBalance.user_id == USER_ID)
    )
    user_balance = balance_result.scalars().one()
    assert user_balance.balance == 60

    # 2. 리뷰 A의 요약은 50
    summary_a = (await db_session.execute(
        select(ReviewRewardSummary).where(ReviewRewardSummary.review_id == REVIEW_ID_A)
    )).scalars().one()
    assert summary_a.net_points == 50

    # 3. 리뷰 B의 요약은 10
    summary_b = (await db_session.execute(
        select(ReviewRewardSummary).where(ReviewRewardSummary.review_id == REVIEW_ID_B)
    )).scalars().one()
    assert summary_b.net_points == 10


async def test_handle_revoke_event(db_session: AsyncSession):
    """
    포인트 지급 후 회수(Revoke) 이벤트가 발생했을 때,
    모든 읽기 모델이 올바르게 차감되는지 테스트합니다.
    """
    # Arrange: 먼저 50포인트를 지급
    projector = PointProjector(db_session)
    grant_event = events.RewardPointsGranted(user_id=USER_ID, review_id=REVIEW_ID_A, points=50, reason="보상")
    await projector.handle(grant_event)

    # 이제 20포인트를 회수하는 이벤트 생성
    revoke_event = events.RewardPointsRevoked(user_id=USER_ID, review_id=REVIEW_ID_A, points=20, reason="가짜 리뷰")

    # Act
    await projector.handle(revoke_event)
    await db_session.commit()

    # Assert
    # 1. 유저 총 잔액은 50 - 20 = 30
    user_balance = (await db_session.execute(
        select(RewardBalance).where(RewardBalance.user_id == USER_ID)
    )).scalars().one()
    assert user_balance.balance == 30

    # 2. 리뷰 A의 순수 포인트도 50 - 20 = 30
    review_summary = (await db_session.execute(
        select(ReviewRewardSummary).where(ReviewRewardSummary.review_id == REVIEW_ID_A)
    )).scalars().one()
    assert review_summary.net_points == 30

    # 3. 히스토리에는 2개의 로그(지급, 회수)가 있어야 함
    history_logs = (await db_session.execute(
        select(ReviewPointHistory).where(ReviewPointHistory.review_id == REVIEW_ID_A)
    )).scalars().all()
    assert len(history_logs) == 2
    assert history_logs[0].points_change == 50
    assert history_logs[1].points_change == -20