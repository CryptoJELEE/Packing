"""
보상 함수 모듈
"""
import numpy as np
from typing import Dict, Optional, Tuple
from dataclasses import dataclass

from core.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class RewardComponents:
    """보상 컴포넌트"""
    space_utilization: float = 0.0
    stability: float = 0.0
    efficiency: float = 0.0
    constraint_satisfaction: float = 0.0
    human_feedback: float = 0.0
    total: float = 0.0


class RewardFunction:
    """
    복합 보상 함수

    보상 구성:
    1. Space Utilization: 공간 활용률
    2. Stability: 안정성 (무게 중심, 지지율)
    3. Efficiency: 효율성 (시간, 스텝 수)
    4. Constraint Satisfaction: 제약 조건 만족도
    5. Human Feedback: 휴먼 피드백 점수
    """

    def __init__(
        self,
        weights: Optional[Dict[str, float]] = None,
        penalties: Optional[Dict[str, float]] = None
    ):
        """
        보상 함수 초기화

        Args:
            weights: 각 컴포넌트의 가중치
            penalties: 페널티 값
        """
        # 기본 가중치
        if weights is None:
            self.weights = {
                'space_utilization': 1.0,
                'stability': 0.5,
                'efficiency': 0.3,
                'constraint_satisfaction': 0.4,
                'human_feedback': 0.7
            }
        else:
            self.weights = weights

        # 기본 페널티
        if penalties is None:
            self.penalties = {
                'placement_failure': -0.5,
                'constraint_violation': -1.0,
                'instability': -0.8,
                'time_exceeded': -0.3
            }
        else:
            self.penalties = penalties

        logger.info(f"RewardFunction initialized with weights: {self.weights}")

    def compute(
        self,
        state_before: Dict,
        action: Dict,
        state_after: Dict,
        placement_success: bool,
        human_feedback: Optional[Dict] = None
    ) -> Tuple[float, RewardComponents]:
        """
        보상 계산

        Args:
            state_before: 행동 전 상태
            action: 실행한 행동
            state_after: 행동 후 상태
            placement_success: 배치 성공 여부
            human_feedback: 휴먼 피드백 데이터

        Returns:
            (총 보상, 보상 컴포넌트)
        """
        components = RewardComponents()

        # 배치 실패 시 페널티
        if not placement_success:
            components.total = self.penalties['placement_failure']
            return components.total, components

        # 1. 공간 활용률 보상
        components.space_utilization = self._compute_space_utilization_reward(
            state_after
        )

        # 2. 안정성 보상
        components.stability = self._compute_stability_reward(
            state_after
        )

        # 3. 효율성 보상
        components.efficiency = self._compute_efficiency_reward(
            state_before,
            state_after
        )

        # 4. 제약 조건 만족도 보상
        components.constraint_satisfaction = self._compute_constraint_reward(
            state_after
        )

        # 5. 휴먼 피드백 보상
        if human_feedback:
            components.human_feedback = self._compute_human_feedback_reward(
                human_feedback
            )

        # 총 보상 계산
        components.total = (
            components.space_utilization * self.weights['space_utilization'] +
            components.stability * self.weights['stability'] +
            components.efficiency * self.weights['efficiency'] +
            components.constraint_satisfaction * self.weights['constraint_satisfaction'] +
            components.human_feedback * self.weights['human_feedback']
        )

        return components.total, components

    def _compute_space_utilization_reward(self, state: Dict) -> float:
        """
        공간 활용률 보상

        목표: 최대한 많은 공간 활용
        """
        occupancy = state.get('occupancy', np.array([]))
        if occupancy.size == 0:
            return 0.0

        # 점유율 계산
        utilization = np.sum(occupancy) / np.prod(occupancy.shape)

        # Reward shaping: 비선형 보상
        # 60% 이상부터 가속화
        if utilization > 0.6:
            reward = utilization + (utilization - 0.6) * 2
        else:
            reward = utilization

        return float(reward)

    def _compute_stability_reward(self, state: Dict) -> float:
        """
        안정성 보상

        고려 사항:
        1. 무게 중심이 컨테이너 중앙에 가까울수록 좋음
        2. 안정성 점수가 높을수록 좋음
        3. 무게 분포가 균일할수록 좋음
        """
        constraints = state.get('constraints', np.zeros(7))

        # 무게 중심 편차
        cog_x = constraints[1]  # 정규화된 값 (0-1)
        cog_z = constraints[3]

        # 중앙(0.5)에서의 거리
        cog_offset = np.sqrt((cog_x - 0.5)**2 + (cog_z - 0.5)**2)
        cog_reward = 1.0 - cog_offset  # 중앙에 가까울수록 1.0

        # 안정성 점수
        stability_score = constraints[4]

        # 종합 안정성 보상
        stability_reward = (cog_reward * 0.5 + stability_score * 0.5)

        return float(stability_reward)

    def _compute_efficiency_reward(
        self,
        state_before: Dict,
        state_after: Dict
    ) -> float:
        """
        효율성 보상

        고려 사항:
        1. 빠르게 완료할수록 좋음 (적은 스텝)
        2. 진행도에 따른 보상
        """
        constraints_after = state_after.get('constraints', np.zeros(7))
        step_ratio = constraints_after[5]  # 현재 스텝 / 최대 스텝

        # 스텝 효율성: 적을수록 좋음
        step_efficiency = 1.0 - step_ratio

        # 진행도 보상: 아이템을 배치할 때마다 보너스
        progress_bonus = 0.1

        efficiency_reward = step_efficiency + progress_bonus

        return float(efficiency_reward)

    def _compute_constraint_reward(self, state: Dict) -> float:
        """
        제약 조건 만족도 보상

        고려 사항:
        1. 무게 제한 만족
        2. 크기 제한 만족
        3. 물리적 안정성
        """
        constraints = state.get('constraints', np.zeros(7))

        # 무게 비율 (1.0에 가까울수록 좋지만 초과하면 안 됨)
        weight_ratio = constraints[0]

        if weight_ratio > 1.0:
            # 무게 초과 - 큰 페널티
            weight_reward = self.penalties['constraint_violation']
        elif weight_ratio > 0.95:
            # 거의 최대 - 보너스
            weight_reward = 1.0 + (weight_ratio - 0.95) * 10
        else:
            # 정상 범위
            weight_reward = weight_ratio

        return float(weight_reward)

    def _compute_human_feedback_reward(self, feedback: Dict) -> float:
        """
        휴먼 피드백 보상

        Args:
            feedback: {
                'overall_score': 1-5,
                'stability_score': 1-5,
                'workability_score': 1-5,
                'practicality_score': 1-5
            }

        Returns:
            정규화된 보상 (0-1)
        """
        # 전체 점수
        overall = feedback.get('overall_score', 3) / 5.0

        # 세부 점수 (가중 평균)
        stability = feedback.get('stability_score', 3) / 5.0
        workability = feedback.get('workability_score', 3) / 5.0
        practicality = feedback.get('practicality_score', 3) / 5.0

        detailed_score = (
            stability * 0.4 +
            workability * 0.3 +
            practicality * 0.3
        )

        # 종합 점수 (전체와 세부의 가중 평균)
        feedback_reward = overall * 0.6 + detailed_score * 0.4

        return float(feedback_reward)

    def update_weights(self, new_weights: Dict[str, float]):
        """보상 가중치 업데이트 (온라인 학습)"""
        self.weights.update(new_weights)
        logger.info(f"Reward weights updated: {self.weights}")

    def get_reward_breakdown(self, components: RewardComponents) -> str:
        """보상 분해 정보 문자열 반환"""
        return (
            f"Total: {components.total:.3f} = "
            f"Space: {components.space_utilization:.3f} + "
            f"Stability: {components.stability:.3f} + "
            f"Efficiency: {components.efficiency:.3f} + "
            f"Constraints: {components.constraint_satisfaction:.3f} + "
            f"Human: {components.human_feedback:.3f}"
        )


class AdaptiveRewardFunction(RewardFunction):
    """
    적응형 보상 함수

    휴먼 피드백을 통해 보상 가중치를 자동으로 조정
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.feedback_history = []
        self.weight_update_frequency = 100  # 100개 피드백마다 가중치 업데이트

    def add_feedback(self, feedback: Dict, components: RewardComponents):
        """피드백 추가 및 가중치 업데이트"""
        self.feedback_history.append({
            'feedback': feedback,
            'components': components
        })

        # 주기적으로 가중치 업데이트
        if len(self.feedback_history) >= self.weight_update_frequency:
            self._update_weights_from_feedback()
            self.feedback_history = []  # 리셋

    def _update_weights_from_feedback(self):
        """
        피드백 데이터로부터 가중치 학습

        방법: Inverse Reinforcement Learning (간소화 버전)
        - 높은 피드백을 받은 경우의 보상 컴포넌트 패턴 학습
        """
        if not self.feedback_history:
            return

        # 피드백 점수별 컴포넌트 평균 계산
        high_feedback = [h for h in self.feedback_history
                        if h['feedback'].get('overall_score', 0) >= 4]

        if not high_feedback:
            return

        # 높은 피드백 케이스의 컴포넌트 평균
        avg_components = {
            'space_utilization': np.mean([h['components'].space_utilization
                                          for h in high_feedback]),
            'stability': np.mean([h['components'].stability
                                 for h in high_feedback]),
            'efficiency': np.mean([h['components'].efficiency
                                  for h in high_feedback]),
            'constraint_satisfaction': np.mean([h['components'].constraint_satisfaction
                                               for h in high_feedback])
        }

        # 컴포넌트 중요도에 따라 가중치 조정
        total = sum(avg_components.values())
        if total > 0:
            for key in avg_components:
                self.weights[key] = avg_components[key] / total

        logger.info(f"Adaptive weights updated: {self.weights}")
