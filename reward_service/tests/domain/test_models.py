import pytest
from app.domain.models import RewardAccount
from app.domain.events import RewardPointsGranted, RewardPointsRefunded, RewardPointsRevoked

USER_ID = "user-123"
REVIEW_ID = "review-abc"
ORDER_ID = "order-xyz"

class TestRewardAccount:
    def test_grant_points_creates_event(self):
        """포인트 지급 시 RewardPointsGranted 이벤트가 생성되는지 테스트합니다."""
        # Arrange: 새로운 계정 생성
        account = RewardAccount(user_id=USER_ID)

        # Act: 포인트 지급 명령 실행
        account.grant_points(points=100, reason="신규 가입 보상", review_id=REVIEW_ID)

        # Assert
        # 1. 커밋되지 않은 이벤트가 1개 있는지 확인
        assert len(account._uncommitted_events) == 1
        
        # 2. 생성된 이벤트가 올바른 타입인지 확인
        event = account._uncommitted_events[0]
        assert isinstance(event, RewardPointsGranted)
        
        # 3. 이벤트에 올바른 데이터가 담겼는지 확인
        assert event.points == 100
        assert event.review_id == REVIEW_ID
        
        # 4. 집계의 내부 상태(잔액)가 올바르게 변경되었는지 확인
        assert account.balance == 100

    def test_cannot_grant_negative_points(self):
        """음수 포인트를 지급할 수 없는 비즈니스 규칙을 테스트합니다."""
        # Arrange
        account = RewardAccount(user_id=USER_ID)

        # Act & Assert: ValueError가 발생하는지 확인
        with pytest.raises(ValueError, match="Points to grant must be positive."):
            account.grant_points(points=-50, reason="잘못된 지급", review_id=REVIEW_ID)
        
        # 에러 발생 후 이벤트가 생성되지 않았는지 확인
        assert len(account._uncommitted_events) == 0

    def test_cannot_refund_more_than_balance(self):
        """잔액보다 많은 포인트를 환불(사용)할 수 없는 비즈니스 규칙을 테스트합니다."""
        # Arrange: 50포인트가 있는 계정 준비
        account = RewardAccount(user_id=USER_ID)
        # 테스트를 위해 직접 apply 메서드를 사용하여 초기 상태 설정
        account._apply(RewardPointsGranted(user_id=USER_ID, review_id="initial", points=50, reason=""))
        account.version = 0 # 초기 상태이므로 버전 초기화
        
        # Act & Assert
        with pytest.raises(ValueError, match="Insufficient points for refund."):
            account.refund_points(points=100, reason="포인트 부족", order_id=ORDER_ID)
            
        assert len(account._uncommitted_events) == 0

    def test_revoke_points_can_make_balance_negative(self):
        """포인트 회수는 잔액을 음수로 만들 수 있는지 테스트합니다."""
        # Arrange: 50포인트가 있는 계정
        account = RewardAccount(user_id=USER_ID)
        account._apply(RewardPointsGranted(user_id=USER_ID, review_id=REVIEW_ID, points=50, reason=""))

        # Act: 100포인트를 회수 (사기 행위 등으로 인해)
        account.revoke_points(points=100, reason="가짜 리뷰 회수", review_id=REVIEW_ID)

        # Assert
        assert account.balance == -50
        event = account._uncommitted_events[0]
        assert isinstance(event, RewardPointsRevoked)
        assert event.points == 100

    def test_replay_from_events_reconstructs_state(self):
        """이벤트 기록으로부터 집계의 최종 상태가 올바르게 복원되는지 테스트합니다."""
        # Arrange: 이벤트 발생 히스토리
        history = [
            RewardPointsGranted(user_id=USER_ID, review_id="rev-1", points=100, reason=""),
            RewardPointsGranted(user_id=USER_ID, review_id="rev-2", points=50, reason=""),
            RewardPointsRevoked(user_id=USER_ID, review_id="rev-1", points=100, reason=""),
            RewardPointsRefunded(user_id=USER_ID, order_id="ord-1", points=20, reason=""),
        ]
        
        # Act: 히스토리를 리플레이하여 계정 복원
        account = RewardAccount.replay_from_events(history)

        # Assert: 최종 상태 검증 (100 + 50 - 100 - 20 = -70) -> 비즈니스 규칙에 따라 음수가 불가능하다면 30
        # 위 테스트에서 회수로 음수가 가능하다고 가정했으므로 -70은 틀린 계산 (환불은 잔액 체크)
        # 100 + 50 = 150 -> 100회수 = 50 -> 20환불 = 30
        assert account.balance == 30
        assert account.version == 4
        assert len(account._uncommitted_events) == 0