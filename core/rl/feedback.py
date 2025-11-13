"""
휴먼 피드백 수집 및 관리 모듈
"""
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
import json

from core.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class HumanFeedback:
    """휴먼 피드백 데이터 클래스"""
    # 식별자
    feedback_id: str
    session_id: str
    packing_result_id: str

    # 알고리즘 정보
    algorithm_type: str  # 'rule_based', 'rl_model', 'hybrid'
    model_version: Optional[str] = None

    # 평가 점수 (1-5)
    overall_score: int = 3
    stability_score: int = 3
    workability_score: int = 3
    space_utilization_score: int = 3
    practicality_score: int = 3

    # 비교 평가
    compared_with: Optional[str] = None
    preference: Optional[str] = None  # 'this', 'other', 'similar'

    # 상세 피드백
    comments: Optional[str] = None
    improvement_suggestions: Optional[str] = None

    # 작업자 정보
    worker_id: str = 'anonymous'
    worker_experience_level: str = 'intermediate'  # 'novice', 'intermediate', 'expert'

    # 메타데이터
    created_at: datetime = None
    feedback_duration: int = 0  # 초

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()

        # 점수 유효성 검증
        for score_name in ['overall_score', 'stability_score', 'workability_score',
                          'space_utilization_score', 'practicality_score']:
            score = getattr(self, score_name)
            if not 1 <= score <= 5:
                raise ValueError(f"{score_name} must be between 1 and 5")

    def to_dict(self) -> Dict:
        """딕셔너리로 변환"""
        data = asdict(self)
        data['created_at'] = self.created_at.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: Dict) -> 'HumanFeedback':
        """딕셔너리에서 생성"""
        if 'created_at' in data and isinstance(data['created_at'], str):
            data['created_at'] = datetime.fromisoformat(data['created_at'])
        return cls(**data)


class FeedbackManager:
    """휴먼 피드백 관리 클래스"""

    def __init__(self, storage_backend=None):
        """
        피드백 매니저 초기화

        Args:
            storage_backend: 저장소 백엔드 (Supabase, PostgreSQL 등)
        """
        self.storage = storage_backend
        self.feedback_cache: List[HumanFeedback] = []
        logger.info("FeedbackManager initialized")

    def collect_feedback(
        self,
        session_id: str,
        packing_result_id: str,
        algorithm_type: str,
        scores: Dict[str, int],
        worker_id: str = 'anonymous',
        **kwargs
    ) -> HumanFeedback:
        """
        피드백 수집

        Args:
            session_id: 세션 ID
            packing_result_id: 패킹 결과 ID
            algorithm_type: 알고리즘 타입
            scores: 점수 딕셔너리
            worker_id: 작업자 ID
            **kwargs: 추가 필드

        Returns:
            생성된 HumanFeedback 객체
        """
        import uuid

        feedback = HumanFeedback(
            feedback_id=str(uuid.uuid4()),
            session_id=session_id,
            packing_result_id=packing_result_id,
            algorithm_type=algorithm_type,
            overall_score=scores.get('overall', 3),
            stability_score=scores.get('stability', 3),
            workability_score=scores.get('workability', 3),
            space_utilization_score=scores.get('space_utilization', 3),
            practicality_score=scores.get('practicality', 3),
            worker_id=worker_id,
            **kwargs
        )

        # 캐시에 추가
        self.feedback_cache.append(feedback)

        # 저장소에 저장
        if self.storage:
            try:
                self._save_to_storage(feedback)
                logger.info(f"Feedback saved: {feedback.feedback_id}")
            except Exception as e:
                logger.error(f"Failed to save feedback: {e}")

        return feedback

    def get_feedback(
        self,
        packing_result_id: Optional[str] = None,
        session_id: Optional[str] = None,
        algorithm_type: Optional[str] = None,
        min_score: Optional[int] = None
    ) -> List[HumanFeedback]:
        """
        피드백 조회

        Args:
            packing_result_id: 패킹 결과 ID
            session_id: 세션 ID
            algorithm_type: 알고리즘 타입
            min_score: 최소 점수

        Returns:
            필터링된 피드백 리스트
        """
        # 저장소에서 조회
        if self.storage:
            try:
                return self._query_from_storage(
                    packing_result_id=packing_result_id,
                    session_id=session_id,
                    algorithm_type=algorithm_type,
                    min_score=min_score
                )
            except Exception as e:
                logger.error(f"Failed to query feedback: {e}")

        # 캐시에서 필터링
        results = self.feedback_cache

        if packing_result_id:
            results = [f for f in results if f.packing_result_id == packing_result_id]
        if session_id:
            results = [f for f in results if f.session_id == session_id]
        if algorithm_type:
            results = [f for f in results if f.algorithm_type == algorithm_type]
        if min_score:
            results = [f for f in results if f.overall_score >= min_score]

        return results

    def get_average_scores(
        self,
        algorithm_type: Optional[str] = None,
        days: int = 30
    ) -> Dict[str, float]:
        """
        평균 점수 계산

        Args:
            algorithm_type: 알고리즘 타입
            days: 최근 N일

        Returns:
            평균 점수 딕셔너리
        """
        from datetime import timedelta

        cutoff_date = datetime.now() - timedelta(days=days)

        # 필터링
        feedbacks = [
            f for f in self.feedback_cache
            if f.created_at >= cutoff_date
        ]

        if algorithm_type:
            feedbacks = [f for f in feedbacks if f.algorithm_type == algorithm_type]

        if not feedbacks:
            return {}

        # 평균 계산
        return {
            'overall': sum(f.overall_score for f in feedbacks) / len(feedbacks),
            'stability': sum(f.stability_score for f in feedbacks) / len(feedbacks),
            'workability': sum(f.workability_score for f in feedbacks) / len(feedbacks),
            'space_utilization': sum(f.space_utilization_score for f in feedbacks) / len(feedbacks),
            'practicality': sum(f.practicality_score for f in feedbacks) / len(feedbacks),
            'count': len(feedbacks)
        }

    def compare_algorithms(
        self,
        algorithm_a: str,
        algorithm_b: str,
        days: int = 30
    ) -> Dict:
        """
        두 알고리즘 비교

        Returns:
            비교 결과
        """
        scores_a = self.get_average_scores(algorithm_a, days)
        scores_b = self.get_average_scores(algorithm_b, days)

        if not scores_a or not scores_b:
            return {
                'error': 'Insufficient data for comparison'
            }

        return {
            algorithm_a: scores_a,
            algorithm_b: scores_b,
            'winner': algorithm_a if scores_a['overall'] > scores_b['overall'] else algorithm_b,
            'improvement': abs(scores_a['overall'] - scores_b['overall'])
        }

    def export_for_training(
        self,
        min_score: int = 3,
        output_format: str = 'json'
    ) -> str:
        """
        학습용 데이터 내보내기

        Args:
            min_score: 최소 점수 (고품질 데이터만)
            output_format: 'json' or 'csv'

        Returns:
            데이터 문자열
        """
        high_quality_feedback = [
            f for f in self.feedback_cache
            if f.overall_score >= min_score
        ]

        if output_format == 'json':
            data = [f.to_dict() for f in high_quality_feedback]
            return json.dumps(data, indent=2, default=str)
        elif output_format == 'csv':
            # CSV 변환
            import csv
            import io

            output = io.StringIO()
            if high_quality_feedback:
                fieldnames = high_quality_feedback[0].to_dict().keys()
                writer = csv.DictWriter(output, fieldnames=fieldnames)
                writer.writeheader()
                for feedback in high_quality_feedback:
                    writer.writerow(feedback.to_dict())
            return output.getvalue()
        else:
            raise ValueError(f"Unsupported format: {output_format}")

    def _save_to_storage(self, feedback: HumanFeedback):
        """저장소에 피드백 저장"""
        # TODO: Supabase 또는 PostgreSQL에 저장
        pass

    def _query_from_storage(self, **filters) -> List[HumanFeedback]:
        """저장소에서 피드백 조회"""
        # TODO: Supabase 또는 PostgreSQL 쿼리
        return []


class PreferenceLearning:
    """
    선호도 학습 (Bradley-Terry Model)

    두 결과를 비교하여 선호도를 학습
    """

    def __init__(self):
        """선호도 학습 초기화"""
        self.preferences: List[Dict] = []
        logger.info("PreferenceLearning initialized")

    def add_preference(
        self,
        result_a_id: str,
        result_b_id: str,
        preference: str,  # 'a', 'b', 'similar'
        confidence: float = 1.0
    ):
        """
        선호도 추가

        Args:
            result_a_id: 결과 A ID
            result_b_id: 결과 B ID
            preference: 선호 결과
            confidence: 확신도 (0-1)
        """
        self.preferences.append({
            'result_a': result_a_id,
            'result_b': result_b_id,
            'preference': preference,
            'confidence': confidence,
            'timestamp': datetime.now()
        })

    def compute_elo_ratings(self) -> Dict[str, float]:
        """
        Elo 레이팅 계산

        Returns:
            결과별 Elo 점수
        """
        from collections import defaultdict

        ratings = defaultdict(lambda: 1500.0)  # 초기 Elo 점수
        K = 32  # Elo K-factor

        for pref in self.preferences:
            ra = ratings[pref['result_a']]
            rb = ratings[pref['result_b']]

            # 예상 승률
            qa = 10 ** (ra / 400)
            qb = 10 ** (rb / 400)
            ea = qa / (qa + qb)
            eb = qb / (qa + qb)

            # 실제 결과
            if pref['preference'] == 'a':
                sa, sb = 1.0, 0.0
            elif pref['preference'] == 'b':
                sa, sb = 0.0, 1.0
            else:  # similar
                sa, sb = 0.5, 0.5

            # 레이팅 업데이트
            ratings[pref['result_a']] += K * pref['confidence'] * (sa - ea)
            ratings[pref['result_b']] += K * pref['confidence'] * (sb - eb)

        return dict(ratings)

    def get_best_results(self, top_k: int = 10) -> List[Tuple[str, float]]:
        """
        최고 성능 결과 조회

        Args:
            top_k: 상위 K개

        Returns:
            (결과 ID, 점수) 리스트
        """
        ratings = self.compute_elo_ratings()
        sorted_results = sorted(ratings.items(), key=lambda x: x[1], reverse=True)
        return sorted_results[:top_k]
