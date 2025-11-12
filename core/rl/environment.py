"""
3D Bin Packing 강화학습 환경
Gymnasium (OpenAI Gym) 인터페이스 구현
"""
import gymnasium as gym
import numpy as np
from typing import Dict, Tuple, Optional, Any, List
from dataclasses import dataclass
from py3dbp import Packer, Bin, Item

from core.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class PackingState:
    """패킹 상태 표현"""
    container_occupancy: np.ndarray  # 3D 점유 그리드 [W, H, D]
    height_map: np.ndarray           # 2D 높이 맵 [W, D]
    weight_distribution: np.ndarray  # 2D 무게 분포 [W, D]
    remaining_items: List[Item]      # 남은 아이템 목록
    placed_items_count: int          # 배치된 아이템 수
    total_weight: float              # 현재 총 무게
    center_of_gravity: np.ndarray    # 무게 중심 [x, y, z]
    stability_score: float           # 안정성 점수 (0-1)
    step_count: int                  # 현재 스텝
    time_elapsed: float              # 경과 시간


class PackingEnvironment(gym.Env):
    """
    3D Bin Packing 강화학습 환경

    State Space:
        - container_occupancy: 3D binary grid (occupied or not)
        - height_map: 2D height map
        - item_features: remaining items features
        - physical_constraints: weight, COG, stability

    Action Space:
        - item_index: which item to place (discrete)
        - position: where to place (continuous or discretized)
        - rotation: how to rotate (discrete, 0-5)

    Reward:
        - space_utilization: maximize volume usage
        - stability: minimize COG offset, maximize support
        - efficiency: minimize steps
        - human_feedback: incorporate expert feedback
    """

    metadata = {'render_modes': ['human', 'rgb_array']}

    def __init__(
        self,
        container_dimensions: Tuple[float, float, float] = (589.8, 243.8, 259.1),
        max_weight: float = 28080,
        grid_resolution: int = 10,  # cm per grid cell
        max_items: int = 100,
        reward_weights: Optional[Dict[str, float]] = None
    ):
        """
        환경 초기화

        Args:
            container_dimensions: (width, height, depth) in cm
            max_weight: maximum weight capacity in kg
            grid_resolution: grid cell size in cm
            max_items: maximum number of items
            reward_weights: custom reward function weights
        """
        super().__init__()

        self.container_w, self.container_h, self.container_d = container_dimensions
        self.max_weight = max_weight
        self.grid_resolution = grid_resolution
        self.max_items = max_items

        # 그리드 크기 계산
        self.grid_w = int(np.ceil(self.container_w / grid_resolution))
        self.grid_h = int(np.ceil(self.container_h / grid_resolution))
        self.grid_d = int(np.ceil(self.container_d / grid_resolution))

        # 보상 함수 가중치
        if reward_weights is None:
            self.reward_weights = {
                'space_utilization': 1.0,
                'stability': 0.5,
                'efficiency': 0.3,
                'human_feedback': 0.7
            }
        else:
            self.reward_weights = reward_weights

        # 상태 초기화
        self.state: Optional[PackingState] = None
        self.packer = Packer()
        self.container = None
        self.items_to_pack: List[Item] = []

        # Action Space
        # 복합 행동: [item_index, x, y, z, rotation]
        self.action_space = gym.spaces.Dict({
            'item_index': gym.spaces.Discrete(max_items),
            'position': gym.spaces.Box(
                low=0,
                high=np.array([self.grid_w, self.grid_h, self.grid_d]),
                dtype=np.float32
            ),
            'rotation': gym.spaces.Discrete(6)  # 6가지 회전 타입
        })

        # Observation Space
        self.observation_space = gym.spaces.Dict({
            # 3D 점유 그리드 (0: empty, 1: occupied)
            'occupancy': gym.spaces.Box(
                low=0, high=1,
                shape=(self.grid_w, self.grid_h, self.grid_d),
                dtype=np.uint8
            ),
            # 2D 높이 맵
            'height_map': gym.spaces.Box(
                low=0, high=self.container_h,
                shape=(self.grid_w, self.grid_d),
                dtype=np.float32
            ),
            # 아이템 특징 (최대 max_items개)
            # 각 아이템: [width, height, depth, weight, fragile, updown]
            'item_features': gym.spaces.Box(
                low=0, high=1000,
                shape=(max_items, 6),
                dtype=np.float32
            ),
            # 물리적 제약
            'constraints': gym.spaces.Box(
                low=-1, high=1,
                shape=(7,),  # [weight_ratio, cog_x, cog_y, cog_z, stability, step_ratio, time_ratio]
                dtype=np.float32
            )
        })

        logger.info(
            f"PackingEnvironment initialized: "
            f"container={container_dimensions}, "
            f"grid=({self.grid_w},{self.grid_h},{self.grid_d})"
        )

    def reset(
        self,
        seed: Optional[int] = None,
        options: Optional[dict] = None
    ) -> Tuple[Dict, Dict]:
        """
        환경 리셋

        Args:
            seed: random seed
            options: additional options (items, container config)

        Returns:
            observation, info
        """
        super().reset(seed=seed)

        # 컨테이너 초기화
        self.packer = Packer()
        self.container = Bin(
            partno='Container',
            WHD=(self.container_w, self.container_h, self.container_d),
            max_weight=self.max_weight,
            corner=0,
            put_type=1
        )
        self.packer.addBin(self.container)

        # 아이템 초기화 (options에서 받거나 랜덤 생성)
        if options and 'items' in options:
            self.items_to_pack = options['items']
        else:
            self.items_to_pack = self._generate_random_items()

        # 상태 초기화
        self.state = PackingState(
            container_occupancy=np.zeros((self.grid_w, self.grid_h, self.grid_d), dtype=np.uint8),
            height_map=np.zeros((self.grid_w, self.grid_d), dtype=np.float32),
            weight_distribution=np.zeros((self.grid_w, self.grid_d), dtype=np.float32),
            remaining_items=self.items_to_pack.copy(),
            placed_items_count=0,
            total_weight=0.0,
            center_of_gravity=np.array([0.0, 0.0, 0.0]),
            stability_score=1.0,
            step_count=0,
            time_elapsed=0.0
        )

        observation = self._get_observation()
        info = self._get_info()

        return observation, info

    def step(self, action: Dict) -> Tuple[Dict, float, bool, bool, Dict]:
        """
        행동 실행

        Args:
            action: {item_index, position, rotation}

        Returns:
            observation, reward, terminated, truncated, info
        """
        assert self.state is not None, "Call reset() first"

        self.state.step_count += 1

        # 행동 파싱
        item_index = action['item_index']
        position = action['position']
        rotation = action['rotation']

        # 유효성 검증
        if item_index >= len(self.state.remaining_items):
            # 잘못된 아이템 선택 -> 큰 페널티
            reward = -1.0
            terminated = True
            truncated = False
            observation = self._get_observation()
            info = self._get_info()
            info['error'] = 'invalid_item_index'
            return observation, reward, terminated, truncated, info

        # 아이템 배치 시도
        item = self.state.remaining_items[item_index]
        placement_success = self._try_place_item(item, position, rotation)

        # 보상 계산
        reward = self._calculate_reward(placement_success)

        # 종료 조건 확인
        terminated = len(self.state.remaining_items) == 0  # 모든 아이템 배치 완료
        truncated = self.state.step_count >= self.max_items * 2  # 최대 스텝 초과

        observation = self._get_observation()
        info = self._get_info()
        info['placement_success'] = placement_success

        return observation, reward, terminated, truncated, info

    def _try_place_item(
        self,
        item: Item,
        position: np.ndarray,
        rotation: int
    ) -> bool:
        """
        아이템 배치 시도

        Returns:
            배치 성공 여부
        """
        # TODO: 실제 py3dbp 알고리즘과 통합
        # 현재는 간단한 물리 체크만 수행

        # 위치를 그리드 좌표로 변환
        x, y, z = position * self.grid_resolution

        # 경계 체크
        item_dims = self._get_rotated_dimensions(item, rotation)
        if (x + item_dims[0] > self.container_w or
            y + item_dims[1] > self.container_h or
            z + item_dims[2] > self.container_d):
            return False

        # 충돌 체크 (간소화 버전)
        # TODO: 정확한 3D 충돌 검사

        # 배치 성공 - 상태 업데이트
        self.state.remaining_items.remove(item)
        self.state.placed_items_count += 1
        self.state.total_weight += item.weight

        # 그리드 업데이트
        self._update_occupancy_grid(position, item_dims)
        self._update_height_map(position, item_dims)
        self._update_weight_distribution(position, item.weight)
        self._update_center_of_gravity()

        return True

    def _calculate_reward(self, placement_success: bool) -> float:
        """
        보상 계산

        Args:
            placement_success: 배치 성공 여부

        Returns:
            보상 값
        """
        if not placement_success:
            return -0.5  # 배치 실패 페널티

        # 1. 공간 활용률 보상
        volume_used = np.sum(self.state.container_occupancy) * (self.grid_resolution ** 3)
        total_volume = self.container_w * self.container_h * self.container_d
        space_util = volume_used / total_volume
        space_reward = space_util * self.reward_weights['space_utilization']

        # 2. 안정성 보상
        stability_reward = self.state.stability_score * self.reward_weights['stability']

        # 3. 효율성 보상 (빨리 끝낼수록 좋음)
        efficiency = 1.0 - (self.state.step_count / (self.max_items * 2))
        efficiency_reward = efficiency * self.reward_weights['efficiency']

        # 4. 휴먼 피드백 보상 (나중에 추가)
        human_feedback_reward = 0.0

        total_reward = (
            space_reward +
            stability_reward +
            efficiency_reward +
            human_feedback_reward
        )

        return total_reward

    def _get_observation(self) -> Dict:
        """현재 상태를 observation으로 변환"""
        assert self.state is not None

        # 아이템 특징 벡터 생성
        item_features = np.zeros((self.max_items, 6), dtype=np.float32)
        for i, item in enumerate(self.state.remaining_items[:self.max_items]):
            item_features[i] = [
                item.width / self.container_w,
                item.height / self.container_h,
                item.depth / self.container_d,
                item.weight / self.max_weight,
                float(item.level == 1),  # fragile
                float(item.updown)
            ]

        # 제약 조건 벡터
        constraints = np.array([
            self.state.total_weight / self.max_weight,
            self.state.center_of_gravity[0] / self.container_w,
            self.state.center_of_gravity[1] / self.container_h,
            self.state.center_of_gravity[2] / self.container_d,
            self.state.stability_score,
            self.state.step_count / (self.max_items * 2),
            0.0  # time_ratio (나중에 추가)
        ], dtype=np.float32)

        return {
            'occupancy': self.state.container_occupancy,
            'height_map': self.state.height_map,
            'item_features': item_features,
            'constraints': constraints
        }

    def _get_info(self) -> Dict:
        """추가 정보 반환"""
        return {
            'placed_items': self.state.placed_items_count,
            'remaining_items': len(self.state.remaining_items),
            'total_weight': self.state.total_weight,
            'space_utilization': np.sum(self.state.container_occupancy) / np.prod(self.state.container_occupancy.shape),
            'stability_score': self.state.stability_score,
            'step_count': self.state.step_count
        }

    def _generate_random_items(self, count: int = 20) -> List[Item]:
        """랜덤 아이템 생성 (테스트용)"""
        items = []
        for i in range(count):
            w = np.random.uniform(10, 50)
            h = np.random.uniform(10, 50)
            d = np.random.uniform(10, 50)
            weight = np.random.uniform(1, 20)

            item = Item(
                partno=f'Item-{i}',
                name=f'Item-{i}',
                typeof='cube',
                WHD=(w, h, d),
                weight=weight,
                level=np.random.choice([1, 2]),
                loadbear=100,
                updown=np.random.choice([True, False]),
                color='blue'
            )
            items.append(item)

        return items

    def _get_rotated_dimensions(self, item: Item, rotation: int) -> Tuple[float, float, float]:
        """회전 타입에 따른 치수 반환"""
        from core.packing.helpers import RotationHelper
        mapping = RotationHelper.ROTATION_MAPPING.get(rotation)
        if mapping:
            return mapping['dimensions'](item)
        return (item.width, item.height, item.depth)

    def _update_occupancy_grid(self, position: np.ndarray, dimensions: Tuple):
        """점유 그리드 업데이트"""
        x, y, z = (position * self.grid_resolution / self.grid_resolution).astype(int)
        w, h, d = (np.array(dimensions) / self.grid_resolution).astype(int)

        # 그리드 범위 체크
        x_end = min(x + w, self.grid_w)
        y_end = min(y + h, self.grid_h)
        z_end = min(z + d, self.grid_d)

        self.state.container_occupancy[x:x_end, y:y_end, z:z_end] = 1

    def _update_height_map(self, position: np.ndarray, dimensions: Tuple):
        """높이 맵 업데이트"""
        x, y, z = (position * self.grid_resolution / self.grid_resolution).astype(int)
        w, h, d = (np.array(dimensions) / self.grid_resolution).astype(int)

        x_end = min(x + w, self.grid_w)
        z_end = min(z + d, self.grid_d)

        new_height = (position[1] + dimensions[1]) * self.grid_resolution
        self.state.height_map[x:x_end, z:z_end] = np.maximum(
            self.state.height_map[x:x_end, z:z_end],
            new_height
        )

    def _update_weight_distribution(self, position: np.ndarray, weight: float):
        """무게 분포 업데이트"""
        x, y, z = (position * self.grid_resolution / self.grid_resolution).astype(int)
        if x < self.grid_w and z < self.grid_d:
            self.state.weight_distribution[x, z] += weight

    def _update_center_of_gravity(self):
        """무게 중심 업데이트"""
        if self.state.total_weight > 0:
            # TODO: 정확한 무게 중심 계산
            # 현재는 간소화 버전
            weight_x = np.sum(self.state.weight_distribution * np.arange(self.grid_w)[:, None])
            weight_z = np.sum(self.state.weight_distribution * np.arange(self.grid_d)[None, :])

            self.state.center_of_gravity = np.array([
                weight_x / self.state.total_weight * self.grid_resolution,
                self.container_h / 2,  # 간소화
                weight_z / self.state.total_weight * self.grid_resolution
            ])

    def render(self, mode='human'):
        """환경 렌더링"""
        if mode == 'human':
            print(f"Step: {self.state.step_count}")
            print(f"Placed: {self.state.placed_items_count}")
            print(f"Remaining: {len(self.state.remaining_items)}")
            print(f"Space Utilization: {np.sum(self.state.container_occupancy) / np.prod(self.state.container_occupancy.shape):.2%}")
        # TODO: 3D 시각화

    def close(self):
        """환경 정리"""
        pass
