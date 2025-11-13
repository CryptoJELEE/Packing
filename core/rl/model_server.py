"""
RL 모델 서빙 모듈

학습된 RL 모델을 로드하고 실시간 예측을 제공합니다.
"""

import os
import json
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime

from py3dbp import Packer, Bin, Item


class RLModelServer:
    """RL 모델을 서빙하는 클래스"""

    def __init__(
        self,
        model_path: Optional[str] = None,
        fallback_to_baseline: bool = True
    ):
        """
        Args:
            model_path: 학습된 모델 경로
            fallback_to_baseline: 모델이 없으면 기존 알고리즘 사용
        """
        self.model_path = model_path
        self.fallback_to_baseline = fallback_to_baseline
        self.model = None
        self.model_loaded = False
        self.model_metadata = {}

        # 모델 로드 시도
        if model_path and os.path.exists(model_path):
            self._load_model()

    def _load_model(self):
        """학습된 모델 로드"""
        try:
            # stable-baselines3가 설치되어 있는 경우만 로드
            from stable_baselines3 import PPO

            self.model = PPO.load(self.model_path)
            self.model_loaded = True

            # 메타데이터 로드
            metadata_path = Path(self.model_path).parent / 'metadata.json'
            if metadata_path.exists():
                with open(metadata_path, 'r') as f:
                    self.model_metadata = json.load(f)

            print(f"✓ RL model loaded from: {self.model_path}")

        except ImportError:
            print("⚠ stable-baselines3 not installed. Using baseline algorithm.")
            self.model_loaded = False

        except Exception as e:
            print(f"⚠ Failed to load RL model: {e}")
            self.model_loaded = False

    def predict(
        self,
        container_dims: Tuple[float, float, float],
        items: List[Dict],
        max_weight: float,
        **kwargs
    ) -> Dict:
        """
        적재 예측 수행

        Args:
            container_dims: 컨테이너 크기 (width, height, depth)
            items: 아이템 리스트
            max_weight: 최대 하중
            **kwargs: 추가 파라미터

        Returns:
            적재 결과 딕셔너리
        """
        # RL 모델이 로드되어 있으면 사용
        if self.model_loaded and self.model is not None:
            try:
                return self._predict_with_rl(container_dims, items, max_weight, **kwargs)
            except Exception as e:
                print(f"⚠ RL prediction failed: {e}")
                if self.fallback_to_baseline:
                    print("  Falling back to baseline algorithm...")
                    return self._predict_with_baseline(container_dims, items, max_weight, **kwargs)
                else:
                    raise

        # 기존 알고리즘 사용
        else:
            return self._predict_with_baseline(container_dims, items, max_weight, **kwargs)

    def _predict_with_rl(
        self,
        container_dims: Tuple[float, float, float],
        items: List[Dict],
        max_weight: float,
        **kwargs
    ) -> Dict:
        """RL 모델로 예측"""
        # TODO: 실제 RL 예측 구현
        # 현재는 baseline으로 fallback
        print("RL prediction not fully implemented yet. Using baseline.")
        return self._predict_with_baseline(container_dims, items, max_weight, **kwargs)

    def _predict_with_baseline(
        self,
        container_dims: Tuple[float, float, float],
        items: List[Dict],
        max_weight: float,
        **kwargs
    ) -> Dict:
        """기존 py3dbp 알고리즘으로 예측"""
        # Packer 초기화
        packer = Packer()

        # 컨테이너 추가
        packer.addBin(Bin(
            partno='Container',
            WHD=container_dims,
            max_weight=max_weight
        ))

        # 아이템 추가
        for item_data in items:
            packer.addItem(Item(
                partno=item_data.get('name', item_data.get('partno', 'Unknown')),
                name=item_data.get('name', item_data.get('partno', 'Unknown')),
                typeof=item_data.get('typeof', 'cube'),
                WHD=(
                    item_data.get('width', item_data.get('WHD', [0, 0, 0])[0]),
                    item_data.get('height', item_data.get('WHD', [0, 0, 0])[1]),
                    item_data.get('depth', item_data.get('WHD', [0, 0, 0])[2])
                ),
                weight=item_data.get('weight', 1),
                level=item_data.get('level', 1),
                loadbear=item_data.get('loadbear', 100),
                updown=item_data.get('updown', True),
                color=item_data.get('color', 'red')
            ))

        # 패킹 실행
        packer.pack(
            bigger_first=kwargs.get('bigger_first', True),
            distribute_items=kwargs.get('distribute_items', True),
            fix_point=kwargs.get('fix_point', True),
            check_stable=kwargs.get('check_stable', True),
            support_surface_ratio=kwargs.get('support_surface_ratio', 0.75),
            number_of_decimals=kwargs.get('number_of_decimals', 3)
        )

        # 결과 수집
        return self._collect_results(packer, algorithm='baseline')

    def _collect_results(self, packer: Packer, algorithm: str = 'baseline') -> Dict:
        """패킹 결과 수집"""
        container = packer.bins[0]

        # 적재된 아이템
        packed_items = []
        for item in container.items:
            packed_items.append({
                'name': item.partno,
                'position': list(item.position),
                'rotation_type': item.rotation_type,
                'dimensions': [item.width, item.height, item.depth],
                'weight': float(item.weight),
                'color': item.color
            })

        # 적재되지 않은 아이템
        unpacked_items = []
        for item in container.unfitted_items:
            unpacked_items.append({
                'name': item.partno,
                'dimensions': [item.width, item.height, item.depth],
                'weight': float(item.weight)
            })

        # 메트릭 계산
        container_volume = container.width * container.height * container.depth
        packed_volume = sum([
            item['dimensions'][0] * item['dimensions'][1] * item['dimensions'][2]
            for item in packed_items
        ])
        space_utilization = packed_volume / container_volume if container_volume > 0 else 0

        return {
            'success': True,
            'algorithm': algorithm,
            'model_version': self.model_metadata.get('version', 'baseline'),
            'container': {
                'dimensions': [container.width, container.height, container.depth],
                'max_weight': container.max_weight
            },
            'packed_items': packed_items,
            'unpacked_items': unpacked_items,
            'metrics': {
                'num_packed': len(packed_items),
                'num_unpacked': len(unpacked_items),
                'space_utilization': float(space_utilization),
                'packing_rate': len(packed_items) / (len(packed_items) + len(unpacked_items)) if (len(packed_items) + len(unpacked_items)) > 0 else 0,
                'packed_volume': float(packed_volume),
                'container_volume': float(container_volume)
            },
            'timestamp': datetime.now().isoformat()
        }

    def compare_algorithms(
        self,
        container_dims: Tuple[float, float, float],
        items: List[Dict],
        max_weight: float,
        **kwargs
    ) -> Dict:
        """
        RL과 기존 알고리즘 비교

        Returns:
            양쪽 결과를 포함하는 딕셔너리
        """
        # 기존 알고리즘 실행
        baseline_result = self._predict_with_baseline(
            container_dims, items, max_weight, **kwargs
        )

        # RL 모델이 있으면 실행
        if self.model_loaded and self.model is not None:
            try:
                rl_result = self._predict_with_rl(
                    container_dims, items, max_weight, **kwargs
                )
            except Exception as e:
                rl_result = {
                    'success': False,
                    'error': str(e),
                    'algorithm': 'rl'
                }
        else:
            rl_result = {
                'success': False,
                'error': 'RL model not loaded',
                'algorithm': 'rl'
            }

        # 비교 결과
        comparison = {
            'baseline': baseline_result,
            'rl': rl_result,
            'comparison': self._compute_comparison(baseline_result, rl_result)
        }

        return comparison

    def _compute_comparison(self, baseline: Dict, rl: Dict) -> Dict:
        """알고리즘 비교 메트릭 계산"""
        if not rl.get('success'):
            return {
                'available': False,
                'reason': rl.get('error', 'RL model not available')
            }

        baseline_metrics = baseline.get('metrics', {})
        rl_metrics = rl.get('metrics', {})

        return {
            'available': True,
            'space_utilization_diff': rl_metrics.get('space_utilization', 0) - baseline_metrics.get('space_utilization', 0),
            'packing_rate_diff': rl_metrics.get('packing_rate', 0) - baseline_metrics.get('packing_rate', 0),
            'winner': 'rl' if rl_metrics.get('space_utilization', 0) > baseline_metrics.get('space_utilization', 0) else 'baseline',
            'improvement_pct': (
                (rl_metrics.get('space_utilization', 0) - baseline_metrics.get('space_utilization', 0)) /
                baseline_metrics.get('space_utilization', 1) * 100
            ) if baseline_metrics.get('space_utilization', 0) > 0 else 0
        }

    def get_status(self) -> Dict:
        """모델 상태 조회"""
        return {
            'model_loaded': self.model_loaded,
            'model_path': self.model_path,
            'model_metadata': self.model_metadata,
            'fallback_enabled': self.fallback_to_baseline,
            'available_modes': ['baseline', 'rl'] if self.model_loaded else ['baseline']
        }


class HybridModelServer(RLModelServer):
    """RL과 규칙 기반 알고리즘을 혼합하는 하이브리드 서버"""

    def __init__(
        self,
        model_path: Optional[str] = None,
        rl_probability: float = 0.5,
        performance_threshold: float = 0.6
    ):
        """
        Args:
            model_path: RL 모델 경로
            rl_probability: RL 사용 확률 (0-1)
            performance_threshold: RL 성능 임계값 (이하면 baseline 사용)
        """
        super().__init__(model_path, fallback_to_baseline=True)
        self.rl_probability = rl_probability
        self.performance_threshold = performance_threshold
        self.performance_history = []

    def predict(
        self,
        container_dims: Tuple[float, float, float],
        items: List[Dict],
        max_weight: float,
        force_mode: Optional[str] = None,
        **kwargs
    ) -> Dict:
        """
        하이브리드 예측

        Args:
            force_mode: 'rl' 또는 'baseline'으로 강제 지정
        """
        # 강제 모드가 지정되면 해당 방식 사용
        if force_mode == 'rl':
            if not self.model_loaded:
                return {
                    'success': False,
                    'error': 'RL model not loaded',
                    'algorithm': 'rl'
                }
            result = self._predict_with_rl(container_dims, items, max_weight, **kwargs)
            result['mode'] = 'forced_rl'
            return result

        elif force_mode == 'baseline':
            result = self._predict_with_baseline(container_dims, items, max_weight, **kwargs)
            result['mode'] = 'forced_baseline'
            return result

        # 하이브리드: 확률과 성능 기반 선택
        use_rl = self._should_use_rl()

        if use_rl and self.model_loaded:
            result = self._predict_with_rl(container_dims, items, max_weight, **kwargs)
            result['mode'] = 'hybrid_rl'

            # 성능 기록
            self.performance_history.append({
                'algorithm': 'rl',
                'space_utilization': result['metrics']['space_utilization'],
                'timestamp': datetime.now().isoformat()
            })

        else:
            result = self._predict_with_baseline(container_dims, items, max_weight, **kwargs)
            result['mode'] = 'hybrid_baseline'

            # 성능 기록
            self.performance_history.append({
                'algorithm': 'baseline',
                'space_utilization': result['metrics']['space_utilization'],
                'timestamp': datetime.now().isoformat()
            })

        # 최근 100개만 유지
        if len(self.performance_history) > 100:
            self.performance_history = self.performance_history[-100:]

        return result

    def _should_use_rl(self) -> bool:
        """RL 사용 여부 결정"""
        # 모델이 없으면 baseline
        if not self.model_loaded:
            return False

        # 확률 기반 선택
        if np.random.random() > self.rl_probability:
            return False

        # 최근 성능이 임계값 이하면 baseline
        recent_rl_performance = [
            p['space_utilization']
            for p in self.performance_history[-10:]
            if p['algorithm'] == 'rl'
        ]

        if recent_rl_performance:
            avg_performance = np.mean(recent_rl_performance)
            if avg_performance < self.performance_threshold:
                return False

        return True

    def get_performance_stats(self) -> Dict:
        """성능 통계 조회"""
        if not self.performance_history:
            return {'available': False}

        rl_perfs = [p['space_utilization'] for p in self.performance_history if p['algorithm'] == 'rl']
        baseline_perfs = [p['space_utilization'] for p in self.performance_history if p['algorithm'] == 'baseline']

        return {
            'available': True,
            'total_predictions': len(self.performance_history),
            'rl_count': len(rl_perfs),
            'baseline_count': len(baseline_perfs),
            'rl_stats': {
                'mean': float(np.mean(rl_perfs)) if rl_perfs else 0,
                'std': float(np.std(rl_perfs)) if rl_perfs else 0,
                'min': float(np.min(rl_perfs)) if rl_perfs else 0,
                'max': float(np.max(rl_perfs)) if rl_perfs else 0
            } if rl_perfs else None,
            'baseline_stats': {
                'mean': float(np.mean(baseline_perfs)) if baseline_perfs else 0,
                'std': float(np.std(baseline_perfs)) if baseline_perfs else 0,
                'min': float(np.min(baseline_perfs)) if baseline_perfs else 0,
                'max': float(np.max(baseline_perfs)) if baseline_perfs else 0
            } if baseline_perfs else None
        }


# 전역 인스턴스 (싱글톤 패턴)
_model_server_instance = None


def get_model_server(
    model_path: Optional[str] = None,
    mode: str = 'hybrid'
) -> RLModelServer:
    """
    모델 서버 인스턴스 가져오기 (싱글톤)

    Args:
        model_path: 모델 경로
        mode: 'standard' 또는 'hybrid'
    """
    global _model_server_instance

    if _model_server_instance is None:
        # 환경 변수에서 모델 경로 확인
        if model_path is None:
            model_path = os.environ.get('RL_MODEL_PATH', 'models/imitation/best_model.zip')

        # 모드에 따라 서버 생성
        if mode == 'hybrid':
            _model_server_instance = HybridModelServer(
                model_path=model_path if os.path.exists(model_path) else None,
                rl_probability=float(os.environ.get('RL_PROBABILITY', '0.5')),
                performance_threshold=float(os.environ.get('RL_THRESHOLD', '0.6'))
            )
        else:
            _model_server_instance = RLModelServer(
                model_path=model_path if os.path.exists(model_path) else None,
                fallback_to_baseline=True
            )

    return _model_server_instance


if __name__ == '__main__':
    # 테스트
    print("=== RL Model Server Test ===\n")

    server = get_model_server(mode='hybrid')
    status = server.get_status()

    print("Model Status:")
    print(f"  Loaded: {status['model_loaded']}")
    print(f"  Available modes: {status['available_modes']}")

    # 테스트 데이터
    test_items = [
        {'name': 'Box1', 'width': 50, 'height': 50, 'depth': 50, 'weight': 10, 'level': 1, 'loadbear': 100, 'updown': True},
        {'name': 'Box2', 'width': 40, 'height': 40, 'depth': 40, 'weight': 8, 'level': 1, 'loadbear': 100, 'updown': True},
    ]

    result = server.predict(
        container_dims=(400, 200, 200),
        items=test_items,
        max_weight=1000
    )

    print(f"\nPrediction Result:")
    print(f"  Algorithm: {result['algorithm']}")
    print(f"  Mode: {result.get('mode', 'N/A')}")
    print(f"  Packed: {result['metrics']['num_packed']}")
    print(f"  Space utilization: {result['metrics']['space_utilization']:.2%}")
