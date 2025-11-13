#!/usr/bin/env python3
"""
간단한 RL 모델 학습 스크립트
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import argparse
from core.rl.data_converter import ImitationLearningDataset
from core.rl.simple_model import SimplePackingModel


def main():
    parser = argparse.ArgumentParser(description='간단한 RL 모델 학습')
    parser.add_argument('--data', type=str, default='core/rl/data/training_data.pkl',
                        help='학습 데이터 경로')
    parser.add_argument('--output', type=str, default='core/rl/models/simple_packing_model.pkl',
                        help='모델 저장 경로')

    args = parser.parse_args()

    print("=" * 60)
    print("간단한 RL 모델 학습")
    print("=" * 60)
    print(f"데이터 경로: {args.data}")
    print(f"모델 저장 경로: {args.output}")
    print()

    # 1. 데이터셋 로드
    print("1. 학습 데이터 로드 중...")
    try:
        dataset = ImitationLearningDataset.load(args.data)
        print(f"  ✓ {len(dataset)} transitions 로드 완료")

        stats = dataset.compute_statistics()
        print("\n  데이터셋 통계:")
        print(f"    - 에피소드 수: {stats['num_episodes']}")
        print(f"    - 평균 에피소드 길이: {stats['avg_episode_length']:.1f}")
        print(f"    - 평균 보상: {stats['reward_mean']:.4f}")

    except FileNotFoundError:
        print(f"  ✗ 데이터 파일을 찾을 수 없습니다: {args.data}")
        print("  먼저 generate_training_data.py를 실행하세요.")
        return

    # 2. 모델 생성 및 학습
    print("\n2. 모델 학습 시작...")
    model = SimplePackingModel()

    model.train({
        'states': dataset.states,
        'actions': dataset.actions,
        'rewards': dataset.rewards
    })

    # 3. 모델 저장
    print(f"\n3. 모델 저장 중: {args.output}")
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    model.save(args.output)

    # 4. 간단한 검증
    print("\n4. 모델 검증 중...")
    n_test = min(10, len(dataset))
    correct_rotations = 0
    total_position_error = 0.0

    import numpy as np

    for i in range(n_test):
        test_state = dataset.states[i]
        predicted_pos, predicted_rot = model.predict(test_state)

        actual_pos = np.array(dataset.actions[i]['position'], dtype=float)
        actual_rot = dataset.actions[i]['rotation']

        pos_error = float(np.linalg.norm(predicted_pos - actual_pos))
        total_position_error += pos_error

        if predicted_rot == actual_rot:
            correct_rotations += 1

    avg_pos_error = total_position_error / n_test
    rot_accuracy = correct_rotations / n_test

    print(f"  평균 위치 오차: {avg_pos_error:.2f}")
    print(f"  회전 정확도: {rot_accuracy:.2%}")

    print("\n" + "=" * 60)
    print("✓ 모델 학습 완료!")
    print("=" * 60)


if __name__ == '__main__':
    main()
