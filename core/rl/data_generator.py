"""
합성 데이터 생성 모듈

기존 py3dbp 알고리즘을 사용하여 다양한 적재 케이스를 시뮬레이션하고,
RL 학습에 사용할 수 있는 데이터를 생성합니다.
"""

import json
import random
import numpy as np
from typing import List, Dict, Tuple, Optional
from datetime import datetime
from pathlib import Path

from py3dbp import Packer, Bin, Item


class PackingCaseGenerator:
    """다양한 적재 케이스를 자동으로 생성하는 클래스"""

    # 표준 컨테이너 크기들
    CONTAINER_TYPES = {
        'standard_20ft': (589.8, 243.8, 259.1),
        'standard_40ft': (1203.2, 243.8, 259.1),
        'high_cube_40ft': (1203.2, 243.8, 289.6),
        'small': (400.0, 200.0, 200.0),
        'medium': (800.0, 300.0, 250.0),
    }

    # 일반적인 박스 크기 범위들
    BOX_SIZE_PROFILES = {
        'small_boxes': {
            'width': (20, 50),
            'height': (20, 50),
            'depth': (20, 50),
            'weight': (1, 10)
        },
        'medium_boxes': {
            'width': (40, 100),
            'height': (40, 100),
            'depth': (40, 100),
            'weight': (10, 50)
        },
        'large_boxes': {
            'width': (80, 150),
            'height': (80, 150),
            'depth': (80, 150),
            'weight': (50, 150)
        },
        'mixed': {
            'width': (20, 150),
            'height': (20, 150),
            'depth': (20, 150),
            'weight': (1, 150)
        }
    }

    def __init__(self, seed: Optional[int] = None):
        """
        Args:
            seed: 재현 가능한 랜덤 데이터 생성을 위한 시드
        """
        self.seed = seed
        if seed is not None:
            random.seed(seed)
            np.random.seed(seed)

    def generate_case(
        self,
        container_type: str = 'standard_20ft',
        box_profile: str = 'mixed',
        num_items: Optional[int] = None,
        complexity: str = 'medium'
    ) -> Dict:
        """
        하나의 적재 케이스를 생성합니다.

        Args:
            container_type: 컨테이너 타입
            box_profile: 박스 크기 프로필
            num_items: 아이템 개수 (None이면 자동 결정)
            complexity: 난이도 ('easy', 'medium', 'hard')

        Returns:
            케이스 정보 딕셔너리
        """
        container_dims = self.CONTAINER_TYPES[container_type]

        # 난이도에 따라 아이템 개수 결정
        if num_items is None:
            num_items = self._get_num_items_by_complexity(complexity, container_dims)

        # 아이템 생성
        items = self._generate_items(box_profile, num_items)

        return {
            'case_id': f"case_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}",
            'container': {
                'type': container_type,
                'dimensions': container_dims,
                'max_weight': container_dims[0] * container_dims[1] * container_dims[2] / 1000  # 간단한 추정
            },
            'items': items,
            'metadata': {
                'box_profile': box_profile,
                'complexity': complexity,
                'num_items': num_items,
                'generated_at': datetime.now().isoformat()
            }
        }

    def generate_batch(
        self,
        num_cases: int,
        distribution: Optional[Dict] = None
    ) -> List[Dict]:
        """
        여러 케이스를 한 번에 생성합니다.

        Args:
            num_cases: 생성할 케이스 개수
            distribution: 케이스 타입 분포 설정

        Returns:
            케이스 리스트
        """
        if distribution is None:
            # 기본 분포: 다양한 조합
            distribution = {
                'container_types': list(self.CONTAINER_TYPES.keys()),
                'box_profiles': list(self.BOX_SIZE_PROFILES.keys()),
                'complexities': ['easy', 'medium', 'hard'],
                'weights': [0.3, 0.5, 0.2]  # easy 30%, medium 50%, hard 20%
            }

        cases = []
        for i in range(num_cases):
            container_type = random.choice(distribution['container_types'])
            box_profile = random.choice(distribution['box_profiles'])
            complexity = random.choices(
                distribution['complexities'],
                weights=distribution['weights']
            )[0]

            case = self.generate_case(container_type, box_profile, complexity=complexity)
            case['case_id'] = f"batch_case_{i:04d}"
            cases.append(case)

        return cases

    def _get_num_items_by_complexity(self, complexity: str, container_dims: Tuple) -> int:
        """난이도에 따른 아이템 개수 결정"""
        container_volume = np.prod(container_dims)

        if complexity == 'easy':
            # 컨테이너의 30-50% 정도만 채우는 수량
            return random.randint(5, 15)
        elif complexity == 'medium':
            # 컨테이너의 60-80% 정도 채우는 수량
            return random.randint(15, 30)
        else:  # hard
            # 컨테이너의 80-100% 이상 채우는 수량 (일부는 못 넣을 수도)
            return random.randint(30, 50)

    def _generate_items(self, box_profile: str, num_items: int) -> List[Dict]:
        """아이템 리스트 생성"""
        profile = self.BOX_SIZE_PROFILES[box_profile]
        items = []

        for i in range(num_items):
            item = {
                'name': f"Item_{i:03d}",
                'width': random.uniform(*profile['width']),
                'height': random.uniform(*profile['height']),
                'depth': random.uniform(*profile['depth']),
                'weight': random.uniform(*profile['weight']),
                'quantity': 1,
                'updown': random.choice([True, False]),  # 회전 가능 여부
                'level': random.randint(1, 3),  # 적재 우선순위
                'loadbear': random.uniform(50, 200)  # 적재 하중
            }
            items.append(item)

        return items


class SyntheticDataGenerator:
    """기존 알고리즘을 사용해 합성 데이터를 생성하는 클래스"""

    def __init__(self, case_generator: PackingCaseGenerator):
        self.case_generator = case_generator
        self.experiences = []  # State-Action-Reward 경험 저장

    def run_simulation(
        self,
        case: Dict,
        rotation_types: List[int] = [0, 1, 2, 3, 4, 5]
    ) -> Dict:
        """
        하나의 케이스를 시뮬레이션합니다.

        Args:
            case: 적재 케이스
            rotation_types: 사용할 회전 타입 리스트

        Returns:
            시뮬레이션 결과
        """
        # Packer 초기화
        packer = Packer()

        # 컨테이너 추가
        container_dims = case['container']['dimensions']
        packer.addBin(Bin(
            partno='Container',
            WHD=container_dims,
            max_weight=case['container']['max_weight']
        ))

        # 아이템 추가
        for item_data in case['items']:
            packer.addItem(Item(
                partno=item_data['name'],
                name=item_data['name'],
                typeof='cube',
                WHD=(item_data['width'], item_data['height'], item_data['depth']),
                weight=item_data['weight'],
                level=item_data['level'],
                loadbear=item_data['loadbear'],
                updown=item_data['updown'],
                color='red'
            ))

        # 패킹 실행
        packer.pack(
            bigger_first=True,
            distribute_items=True,
            fix_point=True,
            check_stable=True,
            support_surface_ratio=0.75,
            number_of_decimals=3
        )

        # 결과 수집
        result = self._collect_results(packer, case)

        return result

    def generate_training_data(
        self,
        num_cases: int,
        output_dir: Optional[str] = None
    ) -> Dict:
        """
        학습 데이터를 생성합니다.

        Args:
            num_cases: 생성할 케이스 개수
            output_dir: 결과 저장 디렉토리

        Returns:
            생성된 데이터 요약
        """
        print(f"Generating {num_cases} training cases...")

        # 케이스 생성
        cases = self.case_generator.generate_batch(num_cases)

        # 시뮬레이션 실행
        results = []
        for i, case in enumerate(cases):
            print(f"Simulating case {i+1}/{num_cases}...", end='\r')
            result = self.run_simulation(case)
            results.append(result)

        print(f"\nCompleted {num_cases} simulations!")

        # 통계 계산
        summary = self._compute_summary(results)

        # 저장
        if output_dir:
            self._save_results(results, summary, output_dir)

        return {
            'cases': results,
            'summary': summary
        }

    def _collect_results(self, packer: Packer, case: Dict) -> Dict:
        """시뮬레이션 결과 수집"""
        container = packer.bins[0]

        # 적재된 아이템
        packed_items = []
        for item in container.items:
            packed_items.append({
                'name': item.partno,
                'position': item.position,
                'rotation_type': item.rotation_type,
                'dimensions': (item.width, item.height, item.depth),
                'weight': item.weight
            })

        # 적재되지 않은 아이템
        unpacked_items = []
        for item in container.unfitted_items:
            unpacked_items.append({
                'name': item.partno,
                'dimensions': (item.width, item.height, item.depth),
                'weight': item.weight
            })

        # 메트릭 계산
        total_volume = float(np.prod(case['container']['dimensions']))
        packed_volume = float(sum([np.prod(item['dimensions']) for item in packed_items]))
        space_utilization = packed_volume / total_volume if total_volume > 0 else 0

        packed_weight = float(sum([item['weight'] for item in packed_items]))

        return {
            'case_id': case['case_id'],
            'metadata': case['metadata'],
            'packed_items': packed_items,
            'unpacked_items': unpacked_items,
            'metrics': {
                'num_packed': len(packed_items),
                'num_unpacked': len(unpacked_items),
                'space_utilization': space_utilization,
                'packed_volume': packed_volume,
                'total_volume': total_volume,
                'packed_weight': packed_weight,
                'packing_rate': len(packed_items) / len(case['items']) if case['items'] else 0
            }
        }

    def _compute_summary(self, results: List[Dict]) -> Dict:
        """결과 통계 계산"""
        metrics = [r['metrics'] for r in results]

        return {
            'total_cases': len(results),
            'avg_space_utilization': np.mean([m['space_utilization'] for m in metrics]),
            'avg_packing_rate': np.mean([m['packing_rate'] for m in metrics]),
            'avg_packed_items': np.mean([m['num_packed'] for m in metrics]),
            'avg_unpacked_items': np.mean([m['num_unpacked'] for m in metrics]),
            'space_utilization_std': np.std([m['space_utilization'] for m in metrics]),
            'min_space_utilization': np.min([m['space_utilization'] for m in metrics]),
            'max_space_utilization': np.max([m['space_utilization'] for m in metrics])
        }

    def _save_results(self, results: List[Dict], summary: Dict, output_dir: str):
        """결과 저장"""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        # 개별 케이스 저장
        cases_file = output_path / f'training_cases_{timestamp}.json'
        with open(cases_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        # 요약 저장
        summary_file = output_path / f'summary_{timestamp}.json'
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)

        print(f"\nResults saved to:")
        print(f"  - Cases: {cases_file}")
        print(f"  - Summary: {summary_file}")


class ExperienceReplayBuffer:
    """RL 학습을 위한 Experience Replay Buffer"""

    def __init__(self, max_size: int = 10000):
        self.max_size = max_size
        self.buffer = []
        self.position = 0

    def add(
        self,
        state: np.ndarray,
        action: Dict,
        reward: float,
        next_state: np.ndarray,
        done: bool,
        info: Dict
    ):
        """경험 추가"""
        experience = {
            'state': state,
            'action': action,
            'reward': reward,
            'next_state': next_state,
            'done': done,
            'info': info
        }

        if len(self.buffer) < self.max_size:
            self.buffer.append(experience)
        else:
            self.buffer[self.position] = experience

        self.position = (self.position + 1) % self.max_size

    def sample(self, batch_size: int) -> List[Dict]:
        """랜덤 샘플링"""
        return random.sample(self.buffer, min(batch_size, len(self.buffer)))

    def size(self) -> int:
        """현재 버퍼 크기"""
        return len(self.buffer)

    def save(self, filepath: str):
        """버퍼 저장"""
        # numpy 배열을 리스트로 변환하여 JSON 저장 가능하게
        serializable_buffer = []
        for exp in self.buffer:
            serializable_exp = {
                'state': exp['state'].tolist() if isinstance(exp['state'], np.ndarray) else exp['state'],
                'action': exp['action'],
                'reward': float(exp['reward']),
                'next_state': exp['next_state'].tolist() if isinstance(exp['next_state'], np.ndarray) else exp['next_state'],
                'done': bool(exp['done']),
                'info': exp['info']
            }
            serializable_buffer.append(serializable_exp)

        with open(filepath, 'w') as f:
            json.dump({
                'max_size': self.max_size,
                'buffer': serializable_buffer
            }, f, indent=2)

        print(f"Experience buffer saved to {filepath}")

    def load(self, filepath: str):
        """버퍼 로드"""
        with open(filepath, 'r') as f:
            data = json.load(f)

        self.max_size = data['max_size']
        self.buffer = []

        for exp in data['buffer']:
            self.buffer.append({
                'state': np.array(exp['state']),
                'action': exp['action'],
                'reward': exp['reward'],
                'next_state': np.array(exp['next_state']),
                'done': exp['done'],
                'info': exp['info']
            })

        self.position = len(self.buffer) % self.max_size
        print(f"Loaded {len(self.buffer)} experiences from {filepath}")


if __name__ == '__main__':
    # 테스트 실행
    print("=== Packing Case Generator Test ===\n")

    # 케이스 생성기
    generator = PackingCaseGenerator(seed=42)

    # 단일 케이스 생성
    case = generator.generate_case(
        container_type='standard_20ft',
        box_profile='mixed',
        complexity='medium'
    )
    print(f"Generated case: {case['case_id']}")
    print(f"  Items: {len(case['items'])}")
    print(f"  Complexity: {case['metadata']['complexity']}\n")

    # 배치 생성 및 시뮬레이션
    print("=== Synthetic Data Generation Test ===\n")
    data_gen = SyntheticDataGenerator(generator)

    # 10개 케이스 생성
    results = data_gen.generate_training_data(
        num_cases=10,
        output_dir='data/synthetic'
    )

    print("\n=== Summary ===")
    for key, value in results['summary'].items():
        print(f"{key}: {value:.4f}" if isinstance(value, float) else f"{key}: {value}")
