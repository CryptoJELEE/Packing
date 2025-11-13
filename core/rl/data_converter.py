"""
시뮬레이션 데이터를 RL 학습 데이터로 변환하는 모듈

기존 py3dbp 시뮬레이션 결과를 RL Environment의
state-action-reward 형태로 변환합니다.
"""

import numpy as np
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass

# 선택적 import
try:
    from core.rl.environment import PackingEnvironment
except ImportError:
    PackingEnvironment = None

try:
    from core.rl.reward import RewardFunction
except ImportError:
    RewardFunction = None


@dataclass
class Transition:
    """RL 전환(transition) 데이터"""
    state: np.ndarray
    action: Dict
    reward: float
    next_state: np.ndarray
    done: bool
    info: Dict


class SimulationToRLConverter:
    """시뮬레이션 결과를 RL 데이터로 변환"""

    def __init__(
        self,
        container_dimensions: Tuple[float, float, float] = (589.8, 243.8, 259.1),
        grid_resolution: int = 10
    ):
        """
        Args:
            container_dimensions: 컨테이너 크기
            grid_resolution: 그리드 해상도
        """
        self.container_dimensions = container_dimensions
        self.grid_resolution = grid_resolution
        # RewardFunction은 선택적 (간단한 보상 계산만 사용)
        self.reward_function = RewardFunction() if RewardFunction is not None else None

    def convert_case_to_transitions(self, simulation_result: Dict) -> List[Transition]:
        """
        하나의 시뮬레이션 결과를 transition 리스트로 변환

        Args:
            simulation_result: data_generator에서 생성된 시뮬레이션 결과

        Returns:
            Transition 리스트 (각 아이템 배치마다 하나씩)
        """
        transitions = []

        packed_items = simulation_result['packed_items']
        if not packed_items:
            return transitions

        # 초기 상태 생성
        state = self._create_initial_state()

        # 각 아이템 배치를 하나의 transition으로 변환
        for i, item in enumerate(packed_items):
            # 현재 상태에서의 action
            action = {
                'item_index': i,  # 순서대로 배치했다고 가정
                'position': np.array(item['position']),
                'rotation': item['rotation_type']
            }

            # 상태 업데이트
            next_state = self._update_state(state.copy(), item)

            # 보상 계산
            reward = self._calculate_step_reward(
                state,
                action,
                next_state,
                item,
                i,
                len(packed_items)
            )

            # Done 플래그 (마지막 아이템이거나 더 이상 넣을 수 없으면)
            done = (i == len(packed_items) - 1)

            # 추가 정보
            info = {
                'item_name': item['name'],
                'step': i,
                'total_steps': len(packed_items),
                'space_utilization': simulation_result['metrics']['space_utilization']
            }

            transitions.append(Transition(
                state=state,
                action=action,
                reward=reward,
                next_state=next_state,
                done=done,
                info=info
            ))

            # 다음 스텝을 위해 상태 업데이트
            state = next_state

        return transitions

    def convert_batch_to_dataset(
        self,
        simulation_results: List[Dict]
    ) -> Dict[str, List]:
        """
        여러 시뮬레이션 결과를 학습 데이터셋으로 변환

        Args:
            simulation_results: 시뮬레이션 결과 리스트

        Returns:
            학습 데이터셋 (states, actions, rewards, next_states, dones)
        """
        all_states = []
        all_actions = []
        all_rewards = []
        all_next_states = []
        all_dones = []
        all_infos = []

        print(f"Converting {len(simulation_results)} simulation results...")

        for i, sim_result in enumerate(simulation_results):
            print(f"Converting case {i+1}/{len(simulation_results)}...", end='\r')

            transitions = self.convert_case_to_transitions(sim_result)

            for trans in transitions:
                all_states.append(trans.state)
                all_actions.append(trans.action)
                all_rewards.append(trans.reward)
                all_next_states.append(trans.next_state)
                all_dones.append(trans.done)
                all_infos.append(trans.info)

        print(f"\nConverted {len(all_states)} transitions!")

        return {
            'states': np.array(all_states),
            'actions': all_actions,
            'rewards': np.array(all_rewards),
            'next_states': np.array(all_next_states),
            'dones': np.array(all_dones),
            'infos': all_infos,
            'metadata': {
                'num_episodes': len(simulation_results),
                'num_transitions': len(all_states),
                'avg_reward': np.mean(all_rewards),
                'avg_episode_length': len(all_states) / len(simulation_results)
            }
        }

    def _create_initial_state(self) -> np.ndarray:
        """빈 컨테이너 초기 상태 생성"""
        grid_w, grid_h, grid_d = self._get_grid_dimensions()

        # 간단한 상태 표현: occupancy grid
        # 실제로는 PackingEnvironment의 state space와 일치해야 함
        occupancy_grid = np.zeros((grid_w, grid_h, grid_d), dtype=np.float32)

        return occupancy_grid

    def _update_state(self, state: np.ndarray, item: Dict) -> np.ndarray:
        """아이템 배치 후 상태 업데이트"""
        position = item['position']
        dimensions = item['dimensions']

        # 그리드 좌표로 변환
        grid_pos = self._world_to_grid(position)
        grid_dims = self._world_to_grid_dims(dimensions)

        # occupancy grid 업데이트
        try:
            x, y, z = grid_pos
            w, h, d = grid_dims

            # 그리드 범위 내에서 업데이트
            grid_w, grid_h, grid_d = state.shape
            x_end = min(x + w, grid_w)
            y_end = min(y + h, grid_h)
            z_end = min(z + d, grid_d)

            state[x:x_end, y:y_end, z:z_end] = 1.0  # 점유됨으로 표시
        except Exception as e:
            print(f"Warning: Failed to update state: {e}")

        return state

    def _calculate_step_reward(
        self,
        state: np.ndarray,
        action: Dict,
        next_state: np.ndarray,
        item: Dict,
        step: int,
        total_steps: int
    ) -> float:
        """각 스텝의 보상 계산"""

        # 1. 공간 활용률 증가
        space_before = np.sum(state) / state.size
        space_after = np.sum(next_state) / next_state.size
        space_reward = (space_after - space_before) * 100.0

        # 2. 안정성 보상 (높이가 낮을수록 좋음)
        position = item['position']
        height_penalty = -float(position[2]) / self.container_dimensions[2] * 10.0

        # 3. 효율성 보상 (빨리 배치할수록 좋음)
        efficiency_reward = 1.0

        # 4. 완료 보너스
        completion_bonus = 10.0 if step == total_steps - 1 else 0.0

        total_reward = (
            space_reward +
            height_penalty +
            efficiency_reward +
            completion_bonus
        )

        return total_reward

    def _get_grid_dimensions(self) -> Tuple[int, int, int]:
        """그리드 차원 계산"""
        return (
            self.grid_resolution,
            self.grid_resolution,
            self.grid_resolution
        )

    def _world_to_grid(self, position: Tuple[float, float, float]) -> Tuple[int, int, int]:
        """월드 좌표를 그리드 좌표로 변환"""
        grid_w, grid_h, grid_d = self._get_grid_dimensions()

        x = int(float(position[0]) / self.container_dimensions[0] * grid_w)
        y = int(float(position[1]) / self.container_dimensions[1] * grid_h)
        z = int(float(position[2]) / self.container_dimensions[2] * grid_d)

        return (
            max(0, min(x, grid_w - 1)),
            max(0, min(y, grid_h - 1)),
            max(0, min(z, grid_d - 1))
        )

    def _world_to_grid_dims(self, dimensions: Tuple[float, float, float]) -> Tuple[int, int, int]:
        """월드 크기를 그리드 크기로 변환"""
        grid_w, grid_h, grid_d = self._get_grid_dimensions()

        w = max(1, int(float(dimensions[0]) / self.container_dimensions[0] * grid_w))
        h = max(1, int(float(dimensions[1]) / self.container_dimensions[1] * grid_h))
        d = max(1, int(float(dimensions[2]) / self.container_dimensions[2] * grid_d))

        return (w, h, d)


class ImitationLearningDataset:
    """Imitation Learning을 위한 데이터셋"""

    def __init__(self, dataset: Dict):
        """
        Args:
            dataset: convert_batch_to_dataset에서 반환된 데이터셋
        """
        self.states = dataset['states']
        self.actions = dataset['actions']
        self.rewards = dataset['rewards']
        self.next_states = dataset['next_states']
        self.dones = dataset['dones']
        self.infos = dataset['infos']
        self.metadata = dataset['metadata']

    def __len__(self) -> int:
        return len(self.states)

    def __getitem__(self, idx: int) -> Transition:
        """인덱스로 transition 가져오기"""
        return Transition(
            state=self.states[idx],
            action=self.actions[idx],
            reward=self.rewards[idx],
            next_state=self.next_states[idx],
            done=self.dones[idx],
            info=self.infos[idx]
        )

    def get_expert_actions(self) -> List[Dict]:
        """전문가(기존 알고리즘) 행동 리스트"""
        return self.actions

    def get_successful_episodes(self, min_reward: float = 0.0) -> List[List[Transition]]:
        """성공적인 에피소드만 추출"""
        episodes = []
        current_episode = []

        for i in range(len(self)):
            transition = self[i]
            current_episode.append(transition)

            if transition.done:
                # 에피소드 총 보상 계산
                episode_reward = sum([t.reward for t in current_episode])

                if episode_reward >= min_reward:
                    episodes.append(current_episode)

                current_episode = []

        return episodes

    def compute_statistics(self) -> Dict:
        """데이터셋 통계"""
        return {
            'total_transitions': len(self),
            'num_episodes': self.metadata['num_episodes'],
            'avg_episode_length': self.metadata['avg_episode_length'],
            'reward_mean': np.mean(self.rewards),
            'reward_std': np.std(self.rewards),
            'reward_min': np.min(self.rewards),
            'reward_max': np.max(self.rewards),
            'done_ratio': np.mean(self.dones)
        }

    def save(self, filepath: str):
        """데이터셋 저장"""
        import pickle

        with open(filepath, 'wb') as f:
            pickle.dump({
                'states': self.states,
                'actions': self.actions,
                'rewards': self.rewards,
                'next_states': self.next_states,
                'dones': self.dones,
                'infos': self.infos,
                'metadata': self.metadata
            }, f)

        print(f"Dataset saved to {filepath}")

    @classmethod
    def load(cls, filepath: str) -> 'ImitationLearningDataset':
        """데이터셋 로드"""
        import pickle

        with open(filepath, 'rb') as f:
            dataset = pickle.load(f)

        print(f"Dataset loaded from {filepath}")
        return cls(dataset)


if __name__ == '__main__':
    print("=== Data Converter Test ===\n")

    # 테스트용 시뮬레이션 결과 생성
    test_result = {
        'case_id': 'test_001',
        'metadata': {'complexity': 'medium'},
        'packed_items': [
            {
                'name': 'Item_001',
                'position': [10.0, 10.0, 0.0],
                'rotation_type': 0,
                'dimensions': (50.0, 50.0, 50.0),
                'weight': 10.0
            },
            {
                'name': 'Item_002',
                'position': [70.0, 10.0, 0.0],
                'rotation_type': 1,
                'dimensions': (60.0, 40.0, 30.0),
                'weight': 15.0
            }
        ],
        'unpacked_items': [],
        'metrics': {
            'space_utilization': 0.65,
            'num_packed': 2
        }
    }

    # 변환기 생성
    converter = SimulationToRLConverter()

    # 변환 테스트
    transitions = converter.convert_case_to_transitions(test_result)

    print(f"Converted {len(transitions)} transitions")
    for i, trans in enumerate(transitions):
        print(f"\nTransition {i}:")
        print(f"  State shape: {trans.state.shape}")
        print(f"  Action: {trans.action}")
        print(f"  Reward: {trans.reward:.2f}")
        print(f"  Done: {trans.done}")

    # 배치 변환 테스트
    batch_results = [test_result, test_result]  # 동일한 결과 2개
    dataset_dict = converter.convert_batch_to_dataset(batch_results)

    print(f"\n=== Dataset Statistics ===")
    for key, value in dataset_dict['metadata'].items():
        print(f"{key}: {value}")

    # ImitationLearningDataset 테스트
    dataset = ImitationLearningDataset(dataset_dict)
    stats = dataset.compute_statistics()

    print(f"\n=== Dataset Object Statistics ===")
    for key, value in stats.items():
        print(f"{key}: {value:.4f}" if isinstance(value, float) else f"{key}: {value}")
