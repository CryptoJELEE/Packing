#!/usr/bin/env python3
"""
RL 학습 데이터 생성 스크립트

기존 py3dbp 시뮬레이션으로부터 학습 데이터를 생성합니다.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import argparse
from core.rl.data_generator import PackingCaseGenerator, SyntheticDataGenerator
from core.rl.data_converter import SimulationToRLConverter, ImitationLearningDataset


def main():
    parser = argparse.ArgumentParser(description='RL 학습 데이터 생성')
    parser.add_argument('--cases', type=int, default=100, help='생성할 케이스 수')
    parser.add_argument('--complexity', type=str, default='mixed',
                        choices=['simple', 'medium', 'hard', 'mixed'],
                        help='케이스 복잡도')
    parser.add_argument('--output', type=str, default='core/rl/data/training_data.pkl',
                        help='출력 파일 경로')
    parser.add_argument('--seed', type=int, default=42, help='랜덤 시드')

    args = parser.parse_args()

    print("=" * 60)
    print("RL 학습 데이터 생성")
    print("=" * 60)
    print(f"생성할 케이스 수: {args.cases}")
    print(f"복잡도: {args.complexity}")
    print(f"출력 경로: {args.output}")
    print()

    # 1. 케이스 생성기 초기화
    print("1. 케이스 생성기 초기화...")
    case_generator = PackingCaseGenerator(seed=args.seed)

    # 2. 시뮬레이션 데이터 생성
    print(f"\n2. {args.cases}개의 시뮬레이션 케이스 생성 중...")
    synthetic_generator = SyntheticDataGenerator(case_generator)

    # generate_training_data 메서드 사용
    training_data = synthetic_generator.generate_training_data(
        num_cases=args.cases,
        output_dir=None  # 나중에 직접 저장
    )

    simulation_results = training_data['cases']
    print(f"\n  ✓ 총 {len(simulation_results)}개 케이스 생성 완료")

    # 통계 출력
    if simulation_results:
        total_items = sum(len(r['packed_items']) for r in simulation_results)
        avg_utilization = sum(r['metrics']['space_utilization'] for r in simulation_results) / len(simulation_results)
        print(f"  - 평균 공간 활용률: {avg_utilization:.2%}")
        print(f"  - 총 아이템 수: {total_items}")

    # 3. RL 데이터로 변환
    print("\n3. RL 학습 데이터로 변환 중...")
    converter = SimulationToRLConverter()
    dataset_dict = converter.convert_batch_to_dataset(simulation_results)

    # 4. 데이터셋 생성 및 저장
    print("\n4. 데이터셋 저장 중...")
    dataset = ImitationLearningDataset(dataset_dict)

    # 통계 출력
    stats = dataset.compute_statistics()
    print("\n=== 데이터셋 통계 ===")
    for key, value in stats.items():
        if isinstance(value, float):
            print(f"  {key}: {value:.4f}")
        else:
            print(f"  {key}: {value}")

    # 저장
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    dataset.save(args.output)

    print(f"\n✓ 학습 데이터가 {args.output}에 저장되었습니다.")
    print("=" * 60)


if __name__ == '__main__':
    main()
