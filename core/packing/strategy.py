"""
안전하고 효율적인 적재를 위한 고급 알고리즘
"""
from py3dbp import Packer, Bin, Item
from typing import List, Dict, Tuple
import copy
import numpy as np

class AdvancedPackingStrategy:
    """고급 패킹 전략 클래스"""
    
    def __init__(self, packer: Packer):
        self.packer = packer
    
    def optimize_weight_distribution(self, bin: Bin) -> float:
        """무게 분산 최적화 점수 계산"""
        if not bin.items:
            return 0.0
        
        # 무게 중심 계산
        total_weight = sum(float(item.weight) for item in bin.items)
        if total_weight == 0:
            return 0.0
        
        # 무게 중심 위치 계산
        center_x = sum(float(item.position[0]) * float(item.weight) for item in bin.items) / total_weight
        center_y = sum(float(item.position[1]) * float(item.weight) for item in bin.items) / total_weight
        center_z = sum(float(item.position[2]) * float(item.weight) for item in bin.items) / total_weight
        
        # 박스 중심과의 거리 (이상적으로는 박스 중심에 가까워야 함)
        box_center_x = float(bin.width) / 2
        box_center_y = float(bin.height) / 2
        box_center_z = float(bin.depth) / 2
        
        distance = ((center_x - box_center_x)**2 + 
                   (center_y - box_center_y)**2 + 
                   (center_z - box_center_z)**2)**0.5
        
        # 거리가 작을수록 좋음 (최대값으로 정규화)
        max_distance = ((float(bin.width)/2)**2 + (float(bin.height)/2)**2 + (float(bin.depth)/2)**2)**0.5
        score = 1.0 - (distance / max_distance) if max_distance > 0 else 1.0
        
        return max(0.0, score)
    
    def calculate_stability_score(self, bin: Bin) -> float:
        """안정성 점수 계산"""
        if not bin.items:
            return 0.0
        
        stability_score = 0.0
        total_items = len(bin.items)
        
        for item in bin.items:
            # 각 아이템의 지지면 비율 계산
            support_ratio = self._calculate_item_support_ratio(bin, item)
            stability_score += support_ratio
        
        return stability_score / total_items if total_items > 0 else 0.0
    
    def _calculate_item_support_ratio(self, bin: Bin, item: Item) -> float:
        """아이템의 지지면 비율 계산"""
        item_bottom_y = float(item.position[1])
        item_bottom_area = float(item.width) * float(item.depth)
        
        # 파레트이고 바닥에 직접 올라가는 경우
        if hasattr(bin, 'is_pallet') and bin.is_pallet and item_bottom_y < 1.0:
            return 1.0  # 파레트 바닥은 완전한 지지면
        
        # 같은 높이에 있는 다른 아이템이나 바닥과의 접촉면 계산
        support_area = 0.0
        
        # 바닥에 닿아있는지 확인 (일반 박스의 경우)
        if item_bottom_y < 1.0:  # 거의 바닥
            return 1.0
        
        # 아래에 있는 아이템들과의 접촉면 계산
        for other_item in bin.items:
            if other_item == item:
                continue
            
            other_top_y = float(other_item.position[1]) + float(other_item.getDimension()[1])
            
            # 다른 아이템 위에 있는지 확인
            if abs(item_bottom_y - other_top_y) < 1.0:  # 거의 같은 높이
                # 겹치는 면적 계산
                item_x1, item_x2 = float(item.position[0]), float(item.position[0]) + float(item.width)
                item_z1, item_z2 = float(item.position[2]), float(item.position[2]) + float(item.depth)
                
                other_x1, other_x2 = float(other_item.position[0]), float(other_item.position[0]) + float(other_item.getDimension()[0])
                other_z1, other_z2 = float(other_item.position[2]), float(other_item.position[2]) + float(other_item.getDimension()[2])
                
                overlap_x = max(0, min(item_x2, other_x2) - max(item_x1, other_x1))
                overlap_z = max(0, min(item_z2, other_z2) - max(item_z1, other_z1))
                overlap_area = overlap_x * overlap_z
                
                support_area += overlap_area
        
        return min(1.0, support_area / item_bottom_area) if item_bottom_area > 0 else 0.0
    
    def optimize_placement_order(self, items: List[Item]) -> List[Item]:
        """배치 순서 최적화"""
        # 복합 점수 (무게 * 부피 * 하중지지력)
        def composite_score(item):
            weight = float(item.weight)
            volume = float(item.getVolume())
            loadbear = float(item.loadbear)
            return weight * volume * loadbear
        
        sorted_by_composite = sorted(items, key=composite_score, reverse=True)
        return sorted_by_composite
    
    def try_multiple_strategies(self, bin: Bin, items: List[Item], 
                                fix_point: bool, check_stable: bool,
                                support_surface_ratio: float) -> Dict:
        """여러 전략을 시도하고 최적의 결과 선택"""
        best_result = None
        best_score = -1
        
        strategies = [
            ('weight_first', lambda x: sorted(x, key=lambda i: float(i.weight), reverse=True)),
            ('volume_first', lambda x: sorted(x, key=lambda i: float(i.getVolume()), reverse=True)),
            ('loadbear_first', lambda x: sorted(x, key=lambda i: float(i.loadbear), reverse=True)),
            ('composite', lambda x: sorted(x, key=lambda i: float(i.weight) * float(i.getVolume()) * float(i.loadbear), reverse=True)),
            ('bottom_heavy', lambda x: sorted(x, key=lambda i: (float(i.weight), float(i.getVolume())), reverse=True)),
        ]
        
        for strategy_name, sort_func in strategies:
            # 테스트용 bin 복사
            test_bin = copy.deepcopy(bin)
            test_bin.items = []
            test_bin.fit_items = np.array([[0, float(test_bin.width), 0, float(test_bin.height), 0, 0]])
            test_bin.unfitted_items = []
            
            # 정렬된 아이템으로 패킹 시도
            sorted_items = sort_func(items)
            
            for item in sorted_items:
                test_item = copy.deepcopy(item)
                self.packer.pack2Bin(test_bin, test_item, fix_point, check_stable, support_surface_ratio)
            
            # 점수 계산
            space_utilization = self._calculate_space_utilization(test_bin)
            weight_score = self.optimize_weight_distribution(test_bin)
            stability_score = self.calculate_stability_score(test_bin)
            
            # 종합 점수 (가중 평균)
            total_score = (
                space_utilization / 100 * 0.4 +  # 공간 활용률 40%
                weight_score * 0.3 +            # 무게 분산 30%
                stability_score * 0.3            # 안정성 30%
            )
            
            if total_score > best_score:
                best_score = total_score
                best_result = {
                    'strategy': strategy_name,
                    'bin': test_bin,
                    'score': total_score,
                    'space_utilization': space_utilization,
                    'weight_score': weight_score,
                    'stability_score': stability_score
                }
        
        return best_result
    
    def _calculate_space_utilization(self, bin: Bin) -> float:
        """공간 활용률 계산"""
        if not bin.items:
            return 0.0
        
        total_volume = float(bin.width) * float(bin.height) * float(bin.depth)
        used_volume = sum(
            float(item.width) * float(item.height) * float(item.depth) 
            for item in bin.items
        )
        
        return (used_volume / total_volume * 100) if total_volume > 0 else 0.0
    
    def optimize_weight_balance(self, items: List[Item]) -> List[Item]:
        """하중 균형 최적화 - 무거운 아이템을 먼저 배치"""
        # 무게와 부피를 고려한 정렬
        def weight_volume_score(item):
            return float(item.weight) * float(item.getVolume())
        
        return sorted(items, key=weight_volume_score, reverse=True)

