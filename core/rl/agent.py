"""
강화학습 에이전트 모듈

PPO, DQN 등 다양한 알고리즘 지원
"""
from typing import Dict, Optional, Tuple, Any
import numpy as np
from pathlib import Path

from core.utils.logger import get_logger

logger = get_logger(__name__)


class PackingAgent:
    """
    패킹 에이전트 베이스 클래스
    """

    def __init__(
        self,
        observation_space: Any,
        action_space: Any,
        model_path: Optional[str] = None
    ):
        """
        에이전트 초기화

        Args:
            observation_space: 관찰 공간
            action_space: 행동 공간
            model_path: 모델 파일 경로
        """
        self.observation_space = observation_space
        self.action_space = action_space
        self.model_path = model_path
        self.model = None

        logger.info(f"{self.__class__.__name__} initialized")

    def predict(
        self,
        observation: Dict,
        deterministic: bool = False
    ) -> Tuple[Dict, Optional[Dict]]:
        """
        행동 예측

        Args:
            observation: 현재 관찰
            deterministic: 결정론적 예측 여부

        Returns:
            (행동, 상태 정보)
        """
        raise NotImplementedError

    def learn(
        self,
        total_timesteps: int,
        callback: Optional[Any] = None
    ):
        """
        학습 실행

        Args:
            total_timesteps: 총 타임스텝
            callback: 콜백 함수
        """
        raise NotImplementedError

    def save(self, path: str):
        """모델 저장"""
        raise NotImplementedError

    def load(self, path: str):
        """모델 로드"""
        raise NotImplementedError


class PPOPackingAgent(PackingAgent):
    """
    PPO (Proximal Policy Optimization) 에이전트

    장점:
    - 안정적인 학습
    - 샘플 효율성
    - 연속/이산 행동 공간 모두 지원
    """

    def __init__(
        self,
        env,
        policy: str = 'MultiInputPolicy',
        learning_rate: float = 3e-4,
        n_steps: int = 2048,
        batch_size: int = 64,
        n_epochs: int = 10,
        gamma: float = 0.99,
        gae_lambda: float = 0.95,
        clip_range: float = 0.2,
        **kwargs
    ):
        """
        PPO 에이전트 초기화

        Args:
            env: 환경 (Gymnasium)
            policy: 정책 네트워크 타입
            learning_rate: 학습률
            n_steps: 수집할 스텝 수
            batch_size: 배치 크기
            n_epochs: 에폭 수
            gamma: 할인율
            gae_lambda: GAE lambda
            clip_range: 클리핑 범위
        """
        super().__init__(env.observation_space, env.action_space)

        try:
            from stable_baselines3 import PPO
            from stable_baselines3.common.vec_env import DummyVecEnv

            # 환경을 벡터화
            if not isinstance(env, DummyVecEnv):
                env = DummyVecEnv([lambda: env])

            self.model = PPO(
                policy=policy,
                env=env,
                learning_rate=learning_rate,
                n_steps=n_steps,
                batch_size=batch_size,
                n_epochs=n_epochs,
                gamma=gamma,
                gae_lambda=gae_lambda,
                clip_range=clip_range,
                verbose=1,
                **kwargs
            )

            logger.info("PPO model created successfully")

        except ImportError:
            logger.error(
                "stable-baselines3 not installed. "
                "Install with: pip install stable-baselines3"
            )
            self.model = None

    def predict(
        self,
        observation: Dict,
        deterministic: bool = False
    ) -> Tuple[Dict, Optional[Dict]]:
        """행동 예측"""
        if self.model is None:
            raise RuntimeError("Model not initialized")

        action, state = self.model.predict(observation, deterministic=deterministic)
        return action, state

    def learn(
        self,
        total_timesteps: int,
        callback: Optional[Any] = None
    ):
        """학습 실행"""
        if self.model is None:
            raise RuntimeError("Model not initialized")

        logger.info(f"Starting PPO training for {total_timesteps} timesteps")
        self.model.learn(total_timesteps=total_timesteps, callback=callback)
        logger.info("PPO training completed")

    def save(self, path: str):
        """모델 저장"""
        if self.model is None:
            raise RuntimeError("Model not initialized")

        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.model.save(path)
        logger.info(f"Model saved to {path}")

    def load(self, path: str):
        """모델 로드"""
        try:
            from stable_baselines3 import PPO

            self.model = PPO.load(path)
            logger.info(f"Model loaded from {path}")
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            raise


class DQNPackingAgent(PackingAgent):
    """
    DQN (Deep Q-Network) 에이전트

    장점:
    - 구현 단순
    - 이산 행동 공간에 효과적
    """

    def __init__(
        self,
        env,
        policy: str = 'MultiInputPolicy',
        learning_rate: float = 1e-4,
        buffer_size: int = 100000,
        learning_starts: int = 50000,
        batch_size: int = 32,
        tau: float = 1.0,
        gamma: float = 0.99,
        **kwargs
    ):
        """DQN 에이전트 초기화"""
        super().__init__(env.observation_space, env.action_space)

        try:
            from stable_baselines3 import DQN
            from stable_baselines3.common.vec_env import DummyVecEnv

            if not isinstance(env, DummyVecEnv):
                env = DummyVecEnv([lambda: env])

            self.model = DQN(
                policy=policy,
                env=env,
                learning_rate=learning_rate,
                buffer_size=buffer_size,
                learning_starts=learning_starts,
                batch_size=batch_size,
                tau=tau,
                gamma=gamma,
                verbose=1,
                **kwargs
            )

            logger.info("DQN model created successfully")

        except ImportError:
            logger.error(
                "stable-baselines3 not installed. "
                "Install with: pip install stable-baselines3"
            )
            self.model = None

    def predict(
        self,
        observation: Dict,
        deterministic: bool = False
    ) -> Tuple[Dict, Optional[Dict]]:
        """행동 예측"""
        if self.model is None:
            raise RuntimeError("Model not initialized")

        action, state = self.model.predict(observation, deterministic=deterministic)
        return action, state

    def learn(
        self,
        total_timesteps: int,
        callback: Optional[Any] = None
    ):
        """학습 실행"""
        if self.model is None:
            raise RuntimeError("Model not initialized")

        logger.info(f"Starting DQN training for {total_timesteps} timesteps")
        self.model.learn(total_timesteps=total_timesteps, callback=callback)
        logger.info("DQN training completed")

    def save(self, path: str):
        """모델 저장"""
        if self.model is None:
            raise RuntimeError("Model not initialized")

        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.model.save(path)
        logger.info(f"Model saved to {path}")

    def load(self, path: str):
        """모델 로드"""
        try:
            from stable_baselines3 import DQN

            self.model = DQN.load(path)
            logger.info(f"Model loaded from {path}")
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            raise


class HybridPackingAgent:
    """
    하이브리드 에이전트

    규칙 기반 + RL 결합
    """

    def __init__(
        self,
        rl_agent: PackingAgent,
        use_rl_threshold: float = 0.8
    ):
        """
        하이브리드 에이전트 초기화

        Args:
            rl_agent: RL 에이전트
            use_rl_threshold: RL 사용 확률 임계값
        """
        self.rl_agent = rl_agent
        self.use_rl_threshold = use_rl_threshold
        self.performance_history = []

        logger.info("HybridPackingAgent initialized")

    def predict(
        self,
        observation: Dict,
        use_rl: Optional[bool] = None
    ) -> Tuple[Dict, str]:
        """
        행동 예측

        Args:
            observation: 관찰
            use_rl: RL 사용 여부 (None이면 자동 선택)

        Returns:
            (행동, 사용된 방법)
        """
        if use_rl is None:
            # 성능 기반 자동 선택
            use_rl = self._should_use_rl()

        if use_rl:
            action, _ = self.rl_agent.predict(observation, deterministic=True)
            method = 'rl'
        else:
            action = self._rule_based_action(observation)
            method = 'rule'

        return action, method

    def _should_use_rl(self) -> bool:
        """RL 사용 여부 결정"""
        if not self.performance_history:
            # 초기에는 규칙 기반 사용
            return False

        # 최근 성능 기반 결정
        recent_performance = self.performance_history[-10:]
        rl_success_rate = sum(1 for p in recent_performance
                              if p['method'] == 'rl' and p['success']) / len(recent_performance)

        return rl_success_rate > self.use_rl_threshold

    def _rule_based_action(self, observation: Dict) -> Dict:
        """
        규칙 기반 행동 생성

        간단한 휴리스틱:
        1. 가장 큰 아이템 선택
        2. 가장 낮은 위치에 배치
        3. 회전 없음
        """
        item_features = observation['item_features']
        height_map = observation['height_map']

        # 가장 큰 아이템 찾기
        volumes = item_features[:, 0] * item_features[:, 1] * item_features[:, 2]
        item_index = int(np.argmax(volumes))

        # 가장 낮은 위치 찾기
        min_height_pos = np.unravel_index(np.argmin(height_map), height_map.shape)

        action = {
            'item_index': item_index,
            'position': np.array([min_height_pos[0], 0, min_height_pos[1]], dtype=np.float32),
            'rotation': 0
        }

        return action

    def update_performance(self, method: str, success: bool, reward: float):
        """성능 기록 업데이트"""
        self.performance_history.append({
            'method': method,
            'success': success,
            'reward': reward
        })

        # 최근 100개만 유지
        if len(self.performance_history) > 100:
            self.performance_history = self.performance_history[-100:]
