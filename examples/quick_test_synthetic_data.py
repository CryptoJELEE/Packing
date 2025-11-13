"""
빠른 테스트: 합성 데이터 생성 및 확인

전체 학습 파이프라인을 실행하기 전에 데이터 생성이 잘 되는지 테스트
"""

import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.rl.data_generator import PackingCaseGenerator, SyntheticDataGenerator
from core.rl.data_converter import SimulationToRLConverter, ImitationLearningDataset


def test_case_generation():
    """케이스 생성 테스트"""
    print("=" * 60)
    print("Test 1: Packing Case Generation")
    print("=" * 60)

    generator = PackingCaseGenerator(seed=42)

    # 다양한 케이스 생성
    print("\n1-1. Generating easy case...")
    easy_case = generator.generate_case(
        container_type='standard_20ft',
        box_profile='small_boxes',
        complexity='easy'
    )
    print(f"  ✓ Case ID: {easy_case['case_id']}")
    print(f"  ✓ Items: {len(easy_case['items'])}")
    print(f"  ✓ Container: {easy_case['container']['type']}")

    print("\n1-2. Generating medium case...")
    medium_case = generator.generate_case(
        container_type='standard_20ft',
        box_profile='mixed',
        complexity='medium'
    )
    print(f"  ✓ Case ID: {medium_case['case_id']}")
    print(f"  ✓ Items: {len(medium_case['items'])}")

    print("\n1-3. Generating hard case...")
    hard_case = generator.generate_case(
        container_type='standard_40ft',
        box_profile='large_boxes',
        complexity='hard'
    )
    print(f"  ✓ Case ID: {hard_case['case_id']}")
    print(f"  ✓ Items: {len(hard_case['items'])}")

    print("\n1-4. Generating batch (5 cases)...")
    batch = generator.generate_batch(num_cases=5)
    print(f"  ✓ Generated {len(batch)} cases")
    for i, case in enumerate(batch):
        print(f"    - Case {i}: {case['metadata']['complexity']} "
              f"complexity, {len(case['items'])} items")

    return batch


def test_simulation():
    """시뮬레이션 테스트"""
    print("\n" + "=" * 60)
    print("Test 2: Packing Simulation")
    print("=" * 60)

    # 간단한 케이스 생성
    generator = PackingCaseGenerator(seed=42)
    case = generator.generate_case(
        container_type='small',
        box_profile='small_boxes',
        complexity='easy',
        num_items=5  # 작은 테스트
    )

    print(f"\n2-1. Simulating case with {len(case['items'])} items...")

    # 시뮬레이션 실행
    data_gen = SyntheticDataGenerator(generator)
    result = data_gen.run_simulation(case)

    print(f"  ✓ Packed items: {result['metrics']['num_packed']}")
    print(f"  ✓ Unpacked items: {result['metrics']['num_unpacked']}")
    print(f"  ✓ Space utilization: {result['metrics']['space_utilization']:.2%}")
    print(f"  ✓ Packing rate: {result['metrics']['packing_rate']:.2%}")

    return result


def test_batch_simulation():
    """배치 시뮬레이션 테스트"""
    print("\n" + "=" * 60)
    print("Test 3: Batch Simulation")
    print("=" * 60)

    generator = PackingCaseGenerator(seed=42)
    data_gen = SyntheticDataGenerator(generator)

    print("\n3-1. Running 5 simulations...")
    results = data_gen.generate_training_data(
        num_cases=5,
        output_dir=None  # 저장하지 않음
    )

    print("\n  ✓ Summary:")
    summary = results['summary']
    print(f"    - Total cases: {summary['total_cases']}")
    print(f"    - Avg space utilization: {summary['avg_space_utilization']:.2%}")
    print(f"    - Avg packing rate: {summary['avg_packing_rate']:.2%}")
    print(f"    - Space util. range: {summary['min_space_utilization']:.2%} ~ "
          f"{summary['max_space_utilization']:.2%}")

    return results


def test_data_conversion():
    """데이터 변환 테스트"""
    print("\n" + "=" * 60)
    print("Test 4: Data Conversion to RL Format")
    print("=" * 60)

    # 시뮬레이션 결과 생성
    generator = PackingCaseGenerator(seed=42)
    data_gen = SyntheticDataGenerator(generator)

    print("\n4-1. Generating simulation data...")
    results = data_gen.generate_training_data(num_cases=3, output_dir=None)

    print("\n4-2. Converting to RL transitions...")
    converter = SimulationToRLConverter(
        container_dimensions=(400.0, 200.0, 200.0),  # small container
        grid_resolution=10
    )

    dataset_dict = converter.convert_batch_to_dataset(results['cases'])

    print(f"\n  ✓ Conversion complete!")
    print(f"    - Total transitions: {dataset_dict['metadata']['num_transitions']}")
    print(f"    - Episodes: {dataset_dict['metadata']['num_episodes']}")
    print(f"    - Avg episode length: {dataset_dict['metadata']['avg_episode_length']:.1f}")
    print(f"    - Avg reward: {dataset_dict['metadata']['avg_reward']:.2f}")

    # ImitationLearningDataset 생성
    print("\n4-3. Creating ImitationLearningDataset...")
    dataset = ImitationLearningDataset(dataset_dict)

    stats = dataset.compute_statistics()
    print(f"\n  ✓ Dataset statistics:")
    print(f"    - Total transitions: {stats['total_transitions']}")
    print(f"    - Reward mean: {stats['reward_mean']:.2f}")
    print(f"    - Reward std: {stats['reward_std']:.2f}")
    print(f"    - Reward range: [{stats['reward_min']:.2f}, {stats['reward_max']:.2f}]")

    return dataset


def test_full_pipeline():
    """전체 파이프라인 간단 테스트"""
    print("\n" + "=" * 60)
    print("Test 5: Full Pipeline (Mini Version)")
    print("=" * 60)

    print("\n5-1. Generate 3 cases...")
    generator = PackingCaseGenerator(seed=42)
    cases = generator.generate_batch(num_cases=3)
    print(f"  ✓ Generated {len(cases)} cases")

    print("\n5-2. Run simulations...")
    data_gen = SyntheticDataGenerator(generator)
    results = data_gen.generate_training_data(num_cases=3, output_dir=None)
    print(f"  ✓ Simulated {results['summary']['total_cases']} cases")
    print(f"  ✓ Avg utilization: {results['summary']['avg_space_utilization']:.2%}")

    print("\n5-3. Convert to RL format...")
    converter = SimulationToRLConverter()
    dataset_dict = converter.convert_batch_to_dataset(results['cases'])
    print(f"  ✓ Created {dataset_dict['metadata']['num_transitions']} transitions")

    print("\n5-4. Create dataset object...")
    dataset = ImitationLearningDataset(dataset_dict)
    print(f"  ✓ Dataset ready with {len(dataset)} samples")

    print("\n" + "=" * 60)
    print("✓ Full pipeline test successful!")
    print("=" * 60)

    return dataset


def main():
    """모든 테스트 실행"""
    print("\n" + "=" * 60)
    print("Quick Test: Synthetic Data Generation")
    print("=" * 60)
    print("\nThis script tests the data generation pipeline without")
    print("running the full RL training (which requires heavy dependencies).\n")

    try:
        # Test 1: 케이스 생성
        batch = test_case_generation()

        # Test 2: 단일 시뮬레이션
        sim_result = test_simulation()

        # Test 3: 배치 시뮬레이션
        batch_results = test_batch_simulation()

        # Test 4: 데이터 변환
        dataset = test_data_conversion()

        # Test 5: 전체 파이프라인
        final_dataset = test_full_pipeline()

        print("\n" + "=" * 60)
        print("✅ All Tests Passed!")
        print("=" * 60)

        print("\n=== Summary ===")
        print(f"✓ Case generation: Working")
        print(f"✓ Packing simulation: Working")
        print(f"✓ Batch processing: Working")
        print(f"✓ RL data conversion: Working")
        print(f"✓ Dataset creation: Working")

        print("\n=== Next Steps ===")
        print("1. Run with more cases: Modify num_cases in test functions")
        print("2. Save data: Add output_dir parameter to save results")
        print("3. Full training: Run examples/train_with_synthetic_data.py")
        print("4. Install RL dependencies: pip install gymnasium stable-baselines3 torch")

        print("\n=== Ready for Training! ===")
        print("To start full training pipeline:")
        print("  python examples/train_with_synthetic_data.py --num-cases 100")

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == '__main__':
    exit(main())
