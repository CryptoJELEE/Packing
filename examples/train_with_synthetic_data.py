"""
합성 데이터를 사용한 RL 학습 전체 파이프라인

이 스크립트는:
1. 합성 데이터 생성 (기존 py3dbp 알고리즘 사용)
2. RL 학습 데이터로 변환
3. 초기 모델 학습 (Imitation Learning)
4. 성능 평가 및 개선
"""

import os
import sys
import argparse
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.rl.data_generator import (
    PackingCaseGenerator,
    SyntheticDataGenerator,
    ExperienceReplayBuffer
)
from core.rl.data_converter import (
    SimulationToRLConverter,
    ImitationLearningDataset
)
from core.rl.environment import PackingEnvironment
from core.rl.agent import PPOPackingAgent, HybridPackingAgent
from core.rl.training import TrainingPipeline


def step1_generate_synthetic_data(
    num_cases: int = 100,
    output_dir: str = 'data/synthetic',
    seed: int = 42
):
    """Step 1: 합성 데이터 생성"""
    print("=" * 60)
    print("Step 1: Generating Synthetic Data")
    print("=" * 60)

    # 케이스 생성기
    case_generator = PackingCaseGenerator(seed=seed)

    # 데이터 생성기
    data_generator = SyntheticDataGenerator(case_generator)

    # 시뮬레이션 실행
    results = data_generator.generate_training_data(
        num_cases=num_cases,
        output_dir=output_dir
    )

    print("\n=== Generation Summary ===")
    summary = results['summary']
    for key, value in summary.items():
        if isinstance(value, float):
            print(f"{key}: {value:.4f}")
        else:
            print(f"{key}: {value}")

    return results['cases']


def step2_convert_to_rl_data(
    simulation_results,
    output_dir: str = 'data/rl_dataset'
):
    """Step 2: RL 학습 데이터로 변환"""
    print("\n" + "=" * 60)
    print("Step 2: Converting to RL Training Data")
    print("=" * 60)

    # 변환기 생성
    converter = SimulationToRLConverter(
        container_dimensions=(589.8, 243.8, 259.1),
        grid_resolution=10
    )

    # 배치 변환
    dataset_dict = converter.convert_batch_to_dataset(simulation_results)

    # ImitationLearningDataset 생성
    dataset = ImitationLearningDataset(dataset_dict)

    # 통계 출력
    print("\n=== Dataset Statistics ===")
    stats = dataset.compute_statistics()
    for key, value in stats.items():
        if isinstance(value, float):
            print(f"{key}: {value:.4f}")
        else:
            print(f"{key}: {value}")

    # 저장
    os.makedirs(output_dir, exist_ok=True)
    dataset_path = os.path.join(output_dir, 'imitation_dataset.pkl')
    dataset.save(dataset_path)

    return dataset


def step3_train_with_imitation_learning(
    dataset: ImitationLearningDataset,
    num_epochs: int = 10,
    batch_size: int = 32,
    output_dir: str = 'models/imitation'
):
    """Step 3: Imitation Learning으로 초기 모델 학습"""
    print("\n" + "=" * 60)
    print("Step 3: Imitation Learning (Behavior Cloning)")
    print("=" * 60)

    print(f"\nTraining with {len(dataset)} expert transitions...")
    print(f"Epochs: {num_epochs}, Batch size: {batch_size}")

    # 환경 생성
    env = PackingEnvironment(
        container_dimensions=(589.8, 243.8, 259.1),
        grid_resolution=10,
        max_items=50
    )

    # PPO 에이전트 생성
    agent = PPOPackingAgent(
        env=env,
        learning_rate=3e-4,
        n_steps=2048,
        batch_size=64
    )

    # Imitation Learning 시뮬레이션
    # (실제로는 Behavioral Cloning을 위한 별도 학습이 필요)
    print("\nNote: Full Behavioral Cloning implementation requires:")
    print("  1. State-action pair extraction from dataset")
    print("  2. Supervised learning setup")
    print("  3. Policy network training with expert actions as labels")
    print("\nFor now, we'll demonstrate with standard RL training...")

    # 일단 표준 RL 학습으로 시작 (실제로는 BC -> RL fine-tuning)
    training_pipeline = TrainingPipeline(
        agent=agent,
        env=env,
        checkpoint_dir=output_dir
    )

    print("\n=== Starting Training ===")
    training_pipeline.train(
        total_timesteps=10000,  # 짧은 테스트
        eval_freq=2000,
        save_freq=5000
    )

    return agent, training_pipeline


def step4_evaluate_and_compare(
    agent,
    pipeline: TrainingPipeline,
    num_eval_episodes: int = 10
):
    """Step 4: 평가 및 기존 알고리즘과 비교"""
    print("\n" + "=" * 60)
    print("Step 4: Evaluation and Comparison")
    print("=" * 60)

    # RL 에이전트 평가
    print("\n=== Evaluating RL Agent ===")
    rl_metrics = pipeline.evaluate(n_episodes=num_eval_episodes)

    print("\nRL Agent Performance:")
    for key, value in rl_metrics.items():
        if isinstance(value, float):
            print(f"  {key}: {value:.4f}")
        else:
            print(f"  {key}: {value}")

    # 하이브리드 접근법 테스트
    print("\n=== Testing Hybrid Approach ===")
    print("(Combining RL with rule-based fallback)")

    hybrid_agent = HybridPackingAgent(
        rl_agent=agent,
        rl_threshold=0.6  # 60% 확률로 RL 사용
    )

    print("Hybrid agent created successfully!")
    print(f"  RL usage threshold: 0.6")
    print(f"  Will use RL 60% of the time, rule-based 40%")

    return {
        'rl_metrics': rl_metrics,
        'hybrid_agent': hybrid_agent
    }


def main():
    """전체 파이프라인 실행"""
    parser = argparse.ArgumentParser(description='Train RL packing agent with synthetic data')
    parser.add_argument('--num-cases', type=int, default=100,
                        help='Number of synthetic cases to generate')
    parser.add_argument('--num-epochs', type=int, default=10,
                        help='Number of training epochs')
    parser.add_argument('--eval-episodes', type=int, default=10,
                        help='Number of evaluation episodes')
    parser.add_argument('--seed', type=int, default=42,
                        help='Random seed for reproducibility')
    parser.add_argument('--skip-generation', action='store_true',
                        help='Skip data generation and use existing data')

    args = parser.parse_args()

    print("=" * 60)
    print("RL Packing Optimization Training Pipeline")
    print("=" * 60)
    print(f"\nConfiguration:")
    print(f"  Synthetic cases: {args.num_cases}")
    print(f"  Training epochs: {args.num_epochs}")
    print(f"  Evaluation episodes: {args.eval_episodes}")
    print(f"  Random seed: {args.seed}")
    print()

    try:
        # Step 1: 데이터 생성
        if not args.skip_generation:
            simulation_results = step1_generate_synthetic_data(
                num_cases=args.num_cases,
                seed=args.seed
            )
        else:
            print("Skipping data generation (using existing data)")
            # 기존 데이터 로드 로직 필요
            simulation_results = None

        # Step 2: RL 데이터 변환
        if simulation_results:
            dataset = step2_convert_to_rl_data(simulation_results)
        else:
            # 저장된 데이터셋 로드
            dataset_path = 'data/rl_dataset/imitation_dataset.pkl'
            if os.path.exists(dataset_path):
                dataset = ImitationLearningDataset.load(dataset_path)
            else:
                raise FileNotFoundError(
                    "No existing dataset found. Run without --skip-generation first."
                )

        # Step 3: Imitation Learning
        agent, pipeline = step3_train_with_imitation_learning(
            dataset=dataset,
            num_epochs=args.num_epochs
        )

        # Step 4: 평가
        results = step4_evaluate_and_compare(
            agent=agent,
            pipeline=pipeline,
            num_eval_episodes=args.eval_episodes
        )

        print("\n" + "=" * 60)
        print("Training Pipeline Completed Successfully!")
        print("=" * 60)

        print("\n=== Next Steps ===")
        print("1. Review training logs in: models/imitation/")
        print("2. Collect human feedback on predictions")
        print("3. Fine-tune with human feedback (RLHF)")
        print("4. Run A/B tests against baseline algorithm")
        print("5. Deploy to production with gradual rollout")

        print("\n=== Model Files ===")
        print("  - Best model: models/imitation/best_model.zip")
        print("  - Checkpoints: models/imitation/checkpoints/")
        print("  - Training history: models/imitation/training_history.json")

    except KeyboardInterrupt:
        print("\n\nTraining interrupted by user.")
        sys.exit(1)

    except Exception as e:
        print(f"\n\nError occurred: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
