"""
3D Bin Packing 시뮬레이션 파이프라인
"""
from py3dbp import Packer, Bin, Item, Painter
import json
import time
import os
import shutil
from typing import Dict, List
from pathlib import Path
from decimal import Decimal
import matplotlib
matplotlib.use('Agg')  # GUI 백엔드 없이 사용
import matplotlib.pyplot as plt
from core.packing.strategy import AdvancedPackingStrategy
from core.packing.report_generator import ReportGenerator

def convert_decimal_to_float(obj):
    """Decimal 타입을 float로 변환하는 헬퍼 함수"""
    if isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, dict):
        return {key: convert_decimal_to_float(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_decimal_to_float(item) for item in obj]
    elif isinstance(obj, tuple):
        return tuple(convert_decimal_to_float(item) for item in obj)
    else:
        return obj

class PackingPipeline:
    """패킹 시뮬레이션 파이프라인 클래스"""
    
    def __init__(self):
        """파이프라인 초기화"""
        self.packer = Packer()
        self.results = []
        
    def add_box(self, partno: str, WHD: tuple, max_weight: float, 
                corner: int = 0, put_type: int = 1, is_pallet: bool = False):
        """박스(또는 파레트) 추가"""
        box = Bin(
            partno=partno,
            WHD=WHD,
            max_weight=max_weight,
            corner=corner,
            put_type=put_type,
            is_pallet=is_pallet
        )
        self.packer.addBin(box)
        return box
    
    def add_item(self, partno: str, name: str, typeof: str, 
                 WHD: tuple, weight: float, level: int = 1,
                 loadbear: int = 100, updown: bool = True, color: str = 'red'):
        """아이템 추가"""
        item = Item(
            partno=partno,
            name=name,
            typeof=typeof,
            WHD=WHD,
            weight=weight,
            level=level,
            loadbear=loadbear,
            updown=updown,
            color=color
        )
        self.packer.addItem(item)
        return item
    
    def add_items_from_data(self, items_data: List[Dict], counts: Dict[str, int] = None):
        """데이터 딕셔너리 리스트에서 아이템 추가"""
        for item_data in items_data:
            item_name = item_data['name']
            count = counts.get(item_name, 1) if counts else 1
            
            for i in range(count):
                self.add_item(
                    partno=f"{item_data['partno']}-{i+1}",
                    name=item_data['name'],
                    typeof=item_data['typeof'],
                    WHD=tuple(item_data['WHD']),
                    weight=item_data['weight'],
                    level=item_data['level'],
                    loadbear=item_data['loadbear'],
                    updown=item_data['updown'],
                    color=item_data['color']
                )
    
    def run_simulation(self, 
                      bigger_first: bool = True,
                      distribute_items: bool = True,
                      fix_point: bool = True,
                      check_stable: bool = True,
                      support_surface_ratio: float = 0.75,
                      binding: List = None,
                      number_of_decimals: int = 0,
                      use_advanced_strategy: bool = False,
                      try_multiple_strategies: bool = False) -> Dict:
        """패킹 시뮬레이션 실행"""
        start_time = time.time()
        
        # 고급 전략 사용 여부
        if use_advanced_strategy or try_multiple_strategies:
            # 원본 아이템 백업
            original_items = self.packer.items.copy()
            
            if try_multiple_strategies:
                # 여러 전략 시도
                strategy = AdvancedPackingStrategy(self.packer)
                
                for target_bin in self.packer.bins:
                    # 각 박스에 대해 최적 전략 찾기
                    test_result = strategy.try_multiple_strategies(
                        target_bin, original_items, fix_point, check_stable, support_surface_ratio
                    )
                    
                    if test_result and test_result.get('bin'):
                        # 최적 결과를 실제 packer에 적용
                        target_bin.items = test_result['bin'].items
                        target_bin.unfitted_items = test_result['bin'].unfitted_items
                        target_bin.fit_items = test_result['bin'].fit_items
                
                # 아이템 정렬 (putOrder)
                self.packer.putOrder()
            else:
                # 단일 고급 전략 사용
                strategy = AdvancedPackingStrategy(self.packer)
                optimized_items = strategy.optimize_placement_order(original_items)
                self.packer.items = optimized_items
                
                # 일반 패킹 실행
                self.packer.pack(
                    bigger_first=False,  # 이미 최적화된 순서 사용
                    distribute_items=distribute_items,
                    fix_point=fix_point,
                    check_stable=check_stable,
                    support_surface_ratio=support_surface_ratio,
                    binding=binding or [],
                    number_of_decimals=number_of_decimals
                )
        else:
            # 기본 패킹 알고리즘
            self.packer.pack(
                bigger_first=bigger_first,
                distribute_items=distribute_items,
                fix_point=fix_point,
                check_stable=check_stable,
                support_surface_ratio=support_surface_ratio,
                binding=binding or [],
                number_of_decimals=number_of_decimals
            )
        
        elapsed_time = time.time() - start_time
        
        # 결과 수집
        result = {
            'elapsed_time': elapsed_time,
            'bins': [],
            'unfit_items': len(self.packer.unfit_items),
            'total_items': len(self.packer.items) + len(self.packer.unfit_items)
        }
        
        for bin in self.packer.bins:
            bin_result = self._analyze_bin(bin)
            result['bins'].append(bin_result)
        
        self.results.append(result)
        return result
    
    def _analyze_bin(self, bin: Bin) -> Dict:
        """개별 박스 분석"""
        volume = float(bin.width * bin.height * bin.depth)
        fitted_volume = sum(
            float(item.width * item.height * item.depth)
            for item in bin.items
        )
        total_weight = sum(float(item.weight) for item in bin.items)
        max_weight = float(bin.max_weight)
        
        result = {
            'partno': bin.partno,
            'space_utilization': round(fitted_volume / volume * 100, 2) if volume > 0 else 0,
            'fitted_items': len(bin.items),
            'unfitted_items': len(bin.unfitted_items),
            'total_weight': total_weight,
            'max_weight': max_weight,
            'weight_utilization': round(total_weight / max_weight * 100, 2) if max_weight > 0 else 0,
            'gravity_distribution': [float(g) for g in bin.gravity] if bin.gravity else [],
            'items': [
                {
                    'partno': item.partno,
                    'name': item.name,
                    'position': [float(p) for p in item.position],
                    'rotation_type': item.rotation_type,
                    'WHD': [float(item.width), float(item.height), float(item.depth)],
                    'weight': float(item.weight)
                }
                for item in bin.items
            ],
            'unfitted_items': [
                {
                    'partno': item.partno,
                    'name': item.name,
                    'WHD': [float(item.width), float(item.height), float(item.depth)],
                    'weight': float(item.weight)
                }
                for item in bin.unfitted_items
            ]
        }
        
        # Decimal 타입이 남아있을 수 있으므로 한 번 더 변환
        return convert_decimal_to_float(result)
    
    def visualize_results(self, save_path: str = None, alpha: float = 0.2, 
                         show_plot: bool = False) -> List[str]:
        """결과 시각화 - 이미지 파일 경로 리스트 반환"""
        image_paths = []
        
        for bin in self.packer.bins:
            bin_result = self._analyze_bin(bin)
            painter = Painter(bin)
            # plotBoxAndItems는 plt 모듈을 반환함
            painter.plotBoxAndItems(
                title=f"{bin.partno} - 활용률: {bin_result['space_utilization']}%",
                alpha=alpha,
                write_num=True,
                fontsize=10
            )
            
            if save_path:
                save_path_obj = Path(save_path)
                save_path_obj.mkdir(parents=True, exist_ok=True)
                filename = f"{bin.partno.replace(' ', '_')}.png"
                filepath = str(save_path_obj / filename)
                # 현재 figure를 가져와서 저장
                current_fig = plt.gcf()
                current_fig.savefig(filepath, dpi=300, bbox_inches='tight')
                image_paths.append(filename)
                plt.close(current_fig)
            else:
                if not show_plot:
                    plt.close('all')
            
            if show_plot:
                plt.show()
            elif not save_path:
                plt.close('all')
        
        return image_paths
    
    def generate_report(self, output_path: str = None) -> Dict:
        """결과 리포트 생성"""
        report = {
            'summary': {
                'total_simulations': len(self.results),
                'total_bins': len(self.packer.bins),
                'total_unfit_items': len(self.packer.unfit_items),
                'total_fitted_items': sum(len(target_bin.items) for target_bin in self.packer.bins)
            },
            'bins': []
        }
        
        for target_bin in self.packer.bins:
            bin_result = self._analyze_bin(target_bin)
            report['bins'].append(bin_result)
        
        # Decimal 타입을 모두 float로 변환
        report = convert_decimal_to_float(report)
        
        if output_path:
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
        
        return report
    
    def generate_detailed_report(self, output_dir: str = None, 
                                 include_layer_diagrams: bool = True) -> Dict:
        """상세 보고서 생성 (레이어별 정보 포함)"""
        reports = []
        
        for target_bin in self.packer.bins:
            generator = ReportGenerator(target_bin, target_bin.items)
            detailed_report = generator.generate_detailed_report()
            
            # 레이어별 도면 생성
            layer_images = []
            if include_layer_diagrams and output_dir:
                output_path = Path(output_dir)
                output_path.mkdir(parents=True, exist_ok=True)
                layers = generator.analyze_layers()
                
                # images 디렉토리도 생성 (API에서 접근 가능하도록)
                # output_dir이 output/reports/{session_id} 형태이므로
                # 상위 디렉토리로 가서 images 디렉토리 찾기
                base_output_dir = output_path.parent.parent
                images_dir = base_output_dir / 'images'
                images_dir.mkdir(parents=True, exist_ok=True)
                
                for layer in layers:
                    layer_num = layer['layer_number']
                    # 보고서 디렉토리에 저장
                    diagram_path = str(output_path / f"{target_bin.partno}_layer_{layer_num}.png")
                    generator.generate_layer_diagram(layer_num, diagram_path)
                    
                    # images 디렉토리에도 복사 (API 접근용)
                    image_filename = f"{target_bin.partno}_layer_{layer_num}.png"
                    image_dest = images_dir / image_filename
                    shutil.copy2(diagram_path, image_dest)
                    
                    layer_images.append(image_filename)  # 파일명만 저장
            
            # HTML 보고서 생성
            html_path = None
            if output_dir:
                html_path = str(output_path / f"{target_bin.partno}_report.html")
                # 이미지 경로를 상대 경로로 변환
                generator.generate_html_report(html_path, layer_images)
            
            detailed_report['html_report'] = Path(html_path).name if html_path else None
            detailed_report['layer_diagrams'] = layer_images
            
            # 작업 지시서 생성
            work_instruction_path = None
            if output_dir:
                work_instruction_path = str(output_path / f"{target_bin.partno}_work_instruction.html")
                generator.generate_work_instruction_report(work_instruction_path, layer_images)
            
            detailed_report['work_instruction'] = Path(work_instruction_path).name if work_instruction_path else None
            
            reports.append(detailed_report)
        
        return {
            'reports': reports,
            'total_bins': len(self.packer.bins)
        }
    
    def reset(self):
        """파이프라인 초기화"""
        self.packer = Packer()
        self.results = []
