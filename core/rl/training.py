"""
학습 파이프라인 모듈
"""
from typing import Optional, Dict, Callable
from pathlib import Path
import json
from datetime import datetime

from core.utils.logger import get_logger
from .environment import PackingEnvironment
from .agent import PPOPackingAgent, DQNPackingAgent
from .reward import RewardFunction, AdaptiveRewardFunction
from .feedback import FeedbackManager

logger = get_logger(__name__)


class TrainingPipeline:
    """
    RL 학습 파이프라인

    구성:
    1. 환경 생성
    2. 에이전트 초기화
    3. 학습 실행
    4. 평가 및 저장
    5. 모니터링
    """

    def __init__(
        self,
        env_config: Optional[Dict] = None,
        agent_type: str = 'ppo',
        agent_config: Optional[Dict] = None,
        reward_config: Optional[Dict] = None,
        output_dir: str = 'models/rl'
    ):
        """
        학습 파이프라인 초기화

        Args:
            env_config: 환경 설정
            agent_type: 에이전트 타입 ('ppo', 'dqn')
            agent_config: 에이전트 설정
            reward_config: 보상 함수 설정
            output_dir: 출력 디렉토리
        """
        self.env_config = env_config or {}
        self.agent_type = agent_type
        self.agent_config = agent_config or {}
        self.reward_config = reward_config or {}
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # 환경 생성
        self.env = PackingEnvironment(**self.env_config)

        # 보상 함수
        self.reward_function = RewardFunction(**self.reward_config)

        # 에이전트 생성
        self.agent = self._create_agent()

        # 피드백 매니저
        self.feedback_manager = FeedbackManager()

        # 학습 기록
        self.training_history = []

        logger.info(f"TrainingPipeline initialized with {agent_type} agent")

    def _create_agent(self):
        """에이전트 생성"""
        if self.agent_type == 'ppo':
            return PPOPackingAgent(self.env, **self.agent_config)
        elif self.agent_type == 'dqn':
            return DQNPackingAgent(self.env, **self.agent_config)
        else:
            raise ValueError(f"Unknown agent type: {self.agent_type}")

    def train(
        self,
        total_timesteps: int = 100000,
        eval_freq: int = 5000,
        save_freq: int = 10000,
        callback: Optional[Callable] = None
    ) -> Dict:
        """
        학습 실행

        Args:
            total_timesteps: 총 타임스텝
            eval_freq: 평가 주기
            save_freq: 저장 주기
            callback: 커스텀 콜백

        Returns:
            학습 결과 딕셔너리
        """
        logger.info(f"Starting training for {total_timesteps} timesteps")

        try:
            from stable_baselines3.common.callbacks import (
                CheckpointCallback,
                EvalCallback
            )

            # 체크포인트 콜백
            checkpoint_callback = CheckpointCallback(
                save_freq=save_freq,
                save_path=str(self.output_dir / 'checkpoints'),
                name_prefix='rl_model'
            )

            # 평가 콜백
            eval_callback = EvalCallback(
                self.env,
                best_model_save_path=str(self.output_dir / 'best_model'),
                log_path=str(self.output_dir / 'logs'),
                eval_freq=eval_freq,
                deterministic=True,
                render=False
            )

            # 학습 실행
            self.agent.learn(
                total_timesteps=total_timesteps,
                callback=[checkpoint_callback, eval_callback]
            )

            # 최종 모델 저장
            final_model_path = self.output_dir / 'final_model.zip'
            self.agent.save(str(final_model_path))

            # 학습 기록 저장
            training_result = {
                'agent_type': self.agent_type,
                'total_timesteps': total_timesteps,
                'final_model_path': str(final_model_path),
                'timestamp': datetime.now().isoformat()
            }

            self.training_history.append(training_result)
            self._save_training_history()

            logger.info("Training completed successfully")
            return training_result

        except Exception as e:
            logger.error(f"Training failed: {e}", exc_info=True)
            raise

    def evaluate(
        self,
        n_episodes: int = 10,
        deterministic: bool = True
    ) -> Dict:
        """
        모델 평가

        Args:
            n_episodes: 평가 에피소드 수
            deterministic: 결정론적 예측 여부

        Returns:
            평가 결과
        """
        logger.info(f"Evaluating model for {n_episodes} episodes")

        episode_rewards = []
        episode_lengths = []
        episode_metrics = []

        for episode in range(n_episodes):
            obs, info = self.env.reset()
            done = False
            episode_reward = 0
            episode_length = 0

            while not done:
                action, _ = self.agent.predict(obs, deterministic=deterministic)
                obs, reward, terminated, truncated, info = self.env.step(action)
                done = terminated or truncated

                episode_reward += reward
                episode_length += 1

            episode_rewards.append(episode_reward)
            episode_lengths.append(episode_length)
            episode_metrics.append(info)

        # 통계 계산
        import numpy as np

        results = {
            'mean_reward': float(np.mean(episode_rewards)),
            'std_reward': float(np.std(episode_rewards)),
            'mean_length': float(np.mean(episode_lengths)),
            'mean_space_utilization': float(np.mean([m['space_utilization']
                                                     for m in episode_metrics])),
            'mean_stability': float(np.mean([m['stability_score']
                                            for m in episode_metrics])),
            'n_episodes': n_episodes
        }

        logger.info(f"Evaluation results: {results}")
        return results

    def collect_human_feedback(
        self,
        n_samples: int = 10,
        show_both: bool = True
    ):
        """
        휴먼 피드백 수집

        Args:
            n_samples: 샘플 수
            show_both: RL과 규칙 기반 둘 다 보여줄지
        """
        logger.info(f"Collecting human feedback for {n_samples} samples")

        for i in range(n_samples):
            # RL 결과 생성
            obs, info = self.env.reset()
            rl_result = self._run_episode(deterministic=True)

            if show_both:
                # 규칙 기반 결과 생성
                # TODO: 규칙 기반 알고리즘 실행
                rule_result = None

                # 비교 제시
                print(f"\n=== Sample {i+1}/{n_samples} ===")
                print("RL Result:")
                print(f"  Space Utilization: {rl_result['space_utilization']:.2%}")
                print(f"  Stability: {rl_result['stability']:.2f}")

                if rule_result:
                    print("\nRule-based Result:")
                    print(f"  Space Utilization: {rule_result['space_utilization']:.2%}")
                    print(f"  Stability: {rule_result['stability']:.2f}")

            # 피드백 입력 (실제로는 웹 UI에서)
            print("\nPlease provide feedback (1-5 for each):")
            feedback = {
                'overall': int(input("Overall Score: ")),
                'stability': int(input("Stability Score: ")),
                'workability': int(input("Workability Score: ")),
                'space_utilization': int(input("Space Utilization Score: ")),
                'practicality': int(input("Practicality Score: "))
            }

            # 피드백 저장
            self.feedback_manager.collect_feedback(
                session_id=f'eval_{i}',
                packing_result_id=f'rl_result_{i}',
                algorithm_type='rl_model',
                scores=feedback
            )

        logger.info("Human feedback collection completed")

    def _run_episode(self, deterministic: bool = True) -> Dict:
        """에피소드 실행"""
        obs, info = self.env.reset()
        done = False
        total_reward = 0

        while not done:
            action, _ = self.agent.predict(obs, deterministic=deterministic)
            obs, reward, terminated, truncated, info = self.env.step(action)
            done = terminated or truncated
            total_reward += reward

        return info

    def _save_training_history(self):
        """학습 기록 저장"""
        history_path = self.output_dir / 'training_history.json'
        with open(history_path, 'w') as f:
            json.dump(self.training_history, f, indent=2)

    def export_model_for_serving(
        self,
        model_version: str = 'v1.0'
    ) -> str:
        """
        서빙용 모델 내보내기

        Args:
            model_version: 모델 버전

        Returns:
            내보낸 모델 경로
        """
        export_dir = self.output_dir / 'serving' / model_version
        export_dir.mkdir(parents=True, exist_ok=True)

        # 모델 저장
        model_path = export_dir / 'model.zip'
        self.agent.save(str(model_path))

        # 메타데이터 저장
        metadata = {
            'model_version': model_version,
            'agent_type': self.agent_type,
            'env_config': self.env_config,
            'created_at': datetime.now().isoformat()
        }

        metadata_path = export_dir / 'metadata.json'
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)

        logger.info(f"Model exported to {export_dir}")
        return str(export_dir)


class ABTestRunner:
    """
    A/B 테스트 러너

    RL vs 규칙 기반 알고리즘 비교
    """

    def __init__(
        self,
        rl_agent: PPOPackingAgent,
        baseline_algorithm: Callable
    ):
        """
        A/B 테스트 러너 초기화

        Args:
            rl_agent: RL 에이전트
            baseline_algorithm: 베이스라인 알고리즘 (규칙 기반)
        """
        self.rl_agent = rl_agent
        self.baseline = baseline_algorithm
        self.results = {
            'rl': [],
            'baseline': []
        }

        logger.info("ABTestRunner initialized")

    def run_test(
        self,
        test_cases: list,
        split_ratio: float = 0.5
    ) -> Dict:
        """
        A/B 테스트 실행

        Args:
            test_cases: 테스트 케이스 리스트
            split_ratio: RL 사용 비율

        Returns:
            테스트 결과
        """
        import random

        logger.info(f"Running A/B test with {len(test_cases)} cases")

        for case in test_cases:
            if random.random() < split_ratio:
                # RL 사용
                result = self._run_rl(case)
                self.results['rl'].append(result)
            else:
                # 베이스라인 사용
                result = self._run_baseline(case)
                self.results['baseline'].append(result)

        # 통계 분석
        analysis = self._analyze_results()

        logger.info(f"A/B test completed: {analysis}")
        return analysis

    def _run_rl(self, case: Dict) -> Dict:
        """RL로 케이스 실행"""
        # TODO: 실제 실행 로직
        return {'algorithm': 'rl', 'score': 0.0}

    def _run_baseline(self, case: Dict) -> Dict:
        """베이스라인으로 케이스 실행"""
        # TODO: 실제 실행 로직
        return {'algorithm': 'baseline', 'score': 0.0}

    def _analyze_results(self) -> Dict:
        """결과 분석"""
        import numpy as np
        from scipy import stats

        rl_scores = [r['score'] for r in self.results['rl']]
        baseline_scores = [r['score'] for r in self.results['baseline']]

        # t-test
        t_stat, p_value = stats.ttest_ind(rl_scores, baseline_scores)

        return {
            'rl_mean': float(np.mean(rl_scores)),
            'rl_std': float(np.std(rl_scores)),
            'baseline_mean': float(np.mean(baseline_scores)),
            'baseline_std': float(np.std(baseline_scores)),
            'improvement': float((np.mean(rl_scores) - np.mean(baseline_scores)) / np.mean(baseline_scores) * 100),
            't_statistic': float(t_stat),
            'p_value': float(p_value),
            'significant': p_value < 0.05
        }
