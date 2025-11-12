"""
강화학습 기본 사용 예제
"""
import sys
from pathlib import Path

# 프로젝트 루트 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.rl.environment import PackingEnvironment
from core.rl.agent import PPOPackingAgent, HybridPackingAgent
from core.rl.training import TrainingPipeline
from core.rl.feedback import FeedbackManager


def example_1_basic_environment():
    """예제 1: 기본 환경 사용"""
    print("=== Example 1: Basic Environment ===\n")

    # 환경 생성
    env = PackingEnvironment(
        container_dimensions=(589.8, 243.8, 259.1),
        max_weight=28080,
        grid_resolution=10
    )

    # 환경 리셋
    obs, info = env.reset()
    print(f"Initial observation keys: {obs.keys()}")
    print(f"Initial info: {info}\n")

    # 랜덤 행동으로 몇 스텝 실행
    for step in range(5):
        action = env.action_space.sample()
        obs, reward, terminated, truncated, info = env.step(action)

        print(f"Step {step + 1}:")
        print(f"  Reward: {reward:.3f}")
        print(f"  Terminated: {terminated}")
        print(f"  Info: {info}\n")

        if terminated or truncated:
            break

    env.close()


def example_2_train_ppo_agent():
    """예제 2: PPO 에이전트 학습"""
    print("=== Example 2: Train PPO Agent ===\n")

    # 학습 파이프라인 생성
    pipeline = TrainingPipeline(
        agent_type='ppo',
        agent_config={
            'learning_rate': 3e-4,
            'n_steps': 2048,
            'batch_size': 64
        },
        output_dir='models/rl/ppo_v1'
    )

    # 학습 실행 (짧은 데모)
    result = pipeline.train(total_timesteps=10000)
    print(f"Training result: {result}\n")

    # 평가
    eval_result = pipeline.evaluate(n_episodes=5)
    print(f"Evaluation result: {eval_result}\n")


def example_3_hybrid_agent():
    """예제 3: 하이브리드 에이전트"""
    print("=== Example 3: Hybrid Agent ===\n")

    # 환경 생성
    env = PackingEnvironment()

    # PPO 에이전트 생성
    ppo_agent = PPOPackingAgent(env)

    # 하이브리드 에이전트 (RL + 규칙)
    hybrid_agent = HybridPackingAgent(
        rl_agent=ppo_agent,
        use_rl_threshold=0.8
    )

    # 예측
    obs, _ = env.reset()
    action, method = hybrid_agent.predict(obs)

    print(f"Predicted action: {action}")
    print(f"Method used: {method}\n")


def example_4_human_feedback():
    """예제 4: 휴먼 피드백 수집"""
    print("=== Example 4: Human Feedback ===\n")

    # 피드백 매니저 생성
    feedback_manager = FeedbackManager()

    # 피드백 수집
    feedback = feedback_manager.collect_feedback(
        session_id='test_session_1',
        packing_result_id='result_1',
        algorithm_type='rl_model',
        scores={
            'overall': 4,
            'stability': 5,
            'workability': 4,
            'space_utilization': 4,
            'practicality': 4
        },
        worker_id='worker_001',
        comments='Very stable packing. Good space utilization.'
    )

    print(f"Feedback collected: {feedback.feedback_id}")
    print(f"Overall score: {feedback.overall_score}\n")

    # 평균 점수 조회
    avg_scores = feedback_manager.get_average_scores(days=30)
    print(f"Average scores: {avg_scores}\n")


def example_5_full_pipeline():
    """예제 5: 전체 파이프라인"""
    print("=== Example 5: Full Pipeline ===\n")

    # 1. 학습
    print("Step 1: Training...")
    pipeline = TrainingPipeline(
        agent_type='ppo',
        output_dir='models/rl/full_pipeline'
    )

    # 간단한 학습 (데모)
    pipeline.train(total_timesteps=5000)

    # 2. 평가
    print("\nStep 2: Evaluation...")
    eval_result = pipeline.evaluate(n_episodes=3)
    print(f"Evaluation: {eval_result}")

    # 3. 모델 내보내기
    print("\nStep 3: Exporting model...")
    export_path = pipeline.export_model_for_serving(model_version='v1.0')
    print(f"Model exported to: {export_path}\n")


def main():
    """메인 함수"""
    print("강화학습 기반 3D Bin Packing 예제\n")
    print("=" * 60)

    # 예제 선택
    examples = {
        '1': ('Basic Environment', example_1_basic_environment),
        '2': ('Train PPO Agent', example_2_train_ppo_agent),
        '3': ('Hybrid Agent', example_3_hybrid_agent),
        '4': ('Human Feedback', example_4_human_feedback),
        '5': ('Full Pipeline', example_5_full_pipeline)
    }

    print("\n사용 가능한 예제:")
    for key, (name, _) in examples.items():
        print(f"  {key}. {name}")

    choice = input("\n실행할 예제 번호 (1-5, 0은 전체): ")

    if choice == '0':
        for _, func in examples.values():
            func()
            print("\n" + "=" * 60 + "\n")
    elif choice in examples:
        examples[choice][1]()
    else:
        print("잘못된 선택입니다.")


if __name__ == '__main__':
    main()
