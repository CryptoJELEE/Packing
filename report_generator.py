"""
상세 보고서 생성 모듈
- 파레트 단별 제품 목록
- 적재 도면 생성
- HTML 보고서 생성
"""
from typing import Dict, List
from collections import defaultdict
import json
from pathlib import Path
from datetime import datetime
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from decimal import Decimal

def convert_decimal_to_float(obj):
    """Decimal 타입을 float로 변환"""
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

class ReportGenerator:
    """보고서 생성 클래스"""
    
    def __init__(self, bin, items):
        self.bin = bin
        self.items = items
        self.layers = []
    
    def analyze_layers(self, layer_height_threshold: float = 2.0) -> List[Dict]:
        """x-y 단면이 z축으로 확장되는 레이어 분석
        - 레이어 = x-y 평면의 단면이 z축(깊이) 방향으로 확장
        - 같은 x-y 위치에 있는 아이템들이 z축 방향으로 쌓이는 것
        """
        # 아이템을 z 좌표(깊이) 기준으로 정렬
        sorted_items = sorted(self.items, key=lambda x: float(x.position[2]))
        
        layers = []
        processed_items = set()  # 이미 레이어에 포함된 아이템 추적
        
        # z축 방향으로 한 층씩 처리
        current_layer_z = 0.0  # 현재 레이어의 z 좌표 (깊이)
        layer_num = 1
        
        while len(processed_items) < len(sorted_items):
            # 현재 레이어에 포함될 아이템들 찾기
            layer_items = []
            layer_z_start = current_layer_z
            layer_z_end = current_layer_z
            
            for item in sorted_items:
                if item in processed_items:
                    continue
                
                item_z = float(item.position[2])
                item_depth = float(item.getDimension()[2])  # z축 방향 크기 (깊이)
                item_z_end = item_z + item_depth
                
                # 현재 레이어의 z 좌표 범위에 있는 아이템인지 확인
                # (약간의 오차 허용: layer_height_threshold)
                if item_z <= current_layer_z + layer_height_threshold:
                    layer_items.append(item)
                    processed_items.add(item)
                    # 레이어의 최대 z 좌표 업데이트
                    if item_z_end > layer_z_end:
                        layer_z_end = item_z_end
            
            # 레이어에 아이템이 없으면 종료
            if not layer_items:
                break
            
            # 레이어 내 아이템들을 위치 순서로 정렬 (x, y 순서)
            layer_items_sorted = sorted(layer_items, 
                                       key=lambda x: (float(x.position[0]), float(x.position[1])))
            
            # 레이어의 실제 z 범위 계산
            min_z = min(float(i.position[2]) for i in layer_items)
            max_z = max(float(i.position[2]) + float(i.getDimension()[2]) for i in layer_items)
            
            # 레이어의 x-y 평면 범위 계산
            min_x = min(float(i.position[0]) for i in layer_items)
            max_x = max(float(i.position[0]) + float(i.getDimension()[0]) for i in layer_items)
            min_y = min(float(i.position[1]) for i in layer_items)
            max_y = max(float(i.position[1]) + float(i.getDimension()[1]) for i in layer_items)
            
            layers.append({
                'layer_number': layer_num,
                'z_range': (min_z, max_z),  # z축(깊이) 범위
                'xy_range': ((min_x, max_x), (min_y, max_y)),  # x-y 평면 범위
                'base_height': min_y,  # 호환성을 위한 y축 최소값 (바닥 높이)
                'height_range': (min_y, max_y),  # 호환성을 위한 y축 범위
                'items': layer_items_sorted
            })
            
            # 다음 레이어의 z 좌표는 현재 레이어의 최대 z 좌표
            current_layer_z = layer_z_end
            layer_num += 1
        
        self.layers = layers
        return layers
    
    def get_layer_summary(self, layer: Dict) -> Dict:
        """레이어별 요약 정보"""
        items_by_name = defaultdict(lambda: {'count': 0, 'total_weight': 0.0, 'items': []})
        
        for item in layer['items']:
            name = item.name
            items_by_name[name]['count'] += 1
            items_by_name[name]['total_weight'] += float(item.weight)
            items_by_name[name]['items'].append({
                'partno': item.partno,
                'position': [float(p) for p in item.position],
                'rotation_type': item.rotation_type,
                'weight': float(item.weight),
                'dimensions': [float(d) for d in item.getDimension()]
            })
        
        return {
            'layer_number': layer['layer_number'],
            'z_range': layer.get('z_range', (0, 0)),  # z축(깊이) 범위
            'xy_range': layer.get('xy_range', ((0, 0), (0, 0))),  # x-y 평면 범위
            'base_height': layer.get('base_height', layer.get('height_range', (0, 0))[0]),  # 호환성을 위한 y축 최소값
            'height_range': layer.get('height_range', (0, 0)),  # 호환성을 위한 y축 범위
            'total_items': len(layer['items']),
            'total_weight': sum(float(item.weight) for item in layer['items']),
            'products': [
                {
                    'name': name,
                    'count': data['count'],
                    'total_weight': round(data['total_weight'], 2),
                    'items': data['items']
                }
                for name, data in items_by_name.items()
            ]
        }
    
    def generate_detailed_report(self) -> Dict:
        """상세 보고서 생성"""
        layers = self.analyze_layers()
        
        report = {
            'bin_info': {
                'partno': self.bin.partno,
                'dimensions': {
                    'width': float(self.bin.width),
                    'height': float(self.bin.height),
                    'depth': float(self.bin.depth)
                },
                'max_weight': float(self.bin.max_weight),
                'total_weight': float(self.bin.getTotalWeight()),
                'space_utilization': self._calculate_utilization()
            },
            'layers': [self.get_layer_summary(layer) for layer in layers],
            'loading_order': self._get_loading_order(),
            'gravity_distribution': [float(g) for g in self.bin.gravity] if hasattr(self.bin, 'gravity') and self.bin.gravity else [],
            'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        # Decimal 타입 변환
        report = convert_decimal_to_float(report)
        
        return report
    
    def _calculate_utilization(self) -> float:
        """공간 활용률 계산"""
        total_volume = float(self.bin.width) * float(self.bin.height) * float(self.bin.depth)
        used_volume = sum(
            float(item.width) * float(item.height) * float(item.depth) 
            for item in self.items
        )
        return round(used_volume / total_volume * 100, 2) if total_volume > 0 else 0.0
    
    def _get_loading_order(self) -> List[Dict]:
        """적재 순서 (하단부터 상단까지)"""
        loading_order = []
        for layer in self.layers:
            # 각 레이어 내에서도 위치 순서 정렬 (z, x 순서)
            layer_items = sorted(layer['items'], 
                               key=lambda x: (float(x.position[2]), float(x.position[0])))
            
            for idx, item in enumerate(layer_items):
                loading_order.append({
                    'sequence': len(loading_order) + 1,
                    'layer': layer['layer_number'],
                    'partno': item.partno,
                    'name': item.name,
                    'position': [float(p) for p in item.position],
                    'rotation_type': item.rotation_type,
                    'dimensions': [float(d) for d in item.getDimension()]
                })
        
        return loading_order
    
    def generate_html_report(self, output_path: str, image_paths: List[str] = None) -> str:
        """HTML 보고서 생성"""
        report_data = self.generate_detailed_report()
        
        html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>패킹 시뮬레이션 보고서 - {report_data['bin_info']['partno']}</title>
    <style>
        body {{ font-family: 'Malgun Gothic', Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 8px; margin-bottom: 30px; }}
        .header h1 {{ margin: 0 0 10px 0; }}
        .section {{ margin: 25px 0; padding: 20px; border: 1px solid #ddd; border-radius: 8px; background: #fafafa; }}
        .section h2 {{ color: #667eea; margin-top: 0; border-bottom: 2px solid #667eea; padding-bottom: 10px; }}
        .layer {{ margin: 15px 0; padding: 15px; background: white; border-radius: 6px; border-left: 4px solid #667eea; }}
        .layer h3 {{ color: #667eea; margin-top: 0; }}
        table {{ width: 100%; border-collapse: collapse; margin: 15px 0; background: white; }}
        th, td {{ padding: 12px; text-align: left; border: 1px solid #ddd; }}
        th {{ background: #667eea; color: white; font-weight: bold; }}
        tr:nth-child(even) {{ background: #f9f9f9; }}
        .image-container {{ text-align: center; margin: 20px 0; }}
        .image-container img {{ max-width: 100%; height: auto; border: 2px solid #ddd; border-radius: 4px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
        .stat-box {{ display: inline-block; margin: 10px; padding: 15px; background: #667eea; color: white; border-radius: 6px; min-width: 150px; text-align: center; }}
        .stat-box strong {{ display: block; font-size: 1.5em; margin-bottom: 5px; }}
        .layer-diagram {{ margin-top: 15px; padding: 15px; background: white; border-radius: 6px; border: 1px solid #ddd; }}
        .layer-diagram h4 {{ margin-top: 0; color: #667eea; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📦 패킹 시뮬레이션 보고서</h1>
            <p>생성일시: {report_data['generated_at']}</p>
        </div>
        
        <div class="section">
            <h2>📋 박스 정보</h2>
            <div style="display: flex; flex-wrap: wrap; justify-content: space-around;">
                <div class="stat-box">
                    <strong>{report_data['bin_info']['partno']}</strong>
                    <span>박스명</span>
                </div>
                <div class="stat-box">
                    <strong>{report_data['bin_info']['dimensions']['width']} × {report_data['bin_info']['dimensions']['height']} × {report_data['bin_info']['dimensions']['depth']}</strong>
                    <span>크기 (cm)</span>
                </div>
                <div class="stat-box">
                    <strong>{report_data['bin_info']['total_weight']:.1f} / {report_data['bin_info']['max_weight']}</strong>
                    <span>무게 (kg)</span>
                </div>
                <div class="stat-box">
                    <strong>{report_data['bin_info']['space_utilization']}%</strong>
                    <span>공간 활용률</span>
                </div>
            </div>
        </div>
        
        <div class="section">
            <h2>📊 레이어별 적재 현황</h2>
            {self._generate_layers_html(report_data['layers'], image_paths, report_data['bin_info']['partno'])}
        </div>
        
        <div class="section">
            <h2>🔄 적재 순서</h2>
            <table>
                <tr>
                    <th>순서</th><th>레이어</th><th>제품번호</th><th>제품명</th>
                    <th>위치 (X, Y, Z)</th><th>크기 (W×H×D)</th><th>회전</th>
                </tr>
                {self._generate_loading_order_html(report_data['loading_order'])}
            </table>
        </div>
        
        {self._generate_images_html(image_paths) if image_paths else ''}
        
        <div class="section">
            <h2>⚖️ 중력 분포</h2>
            <p>4분할 무게 분포: {report_data['gravity_distribution']}%</p>
            <p style="color: #666; font-size: 0.9em;">각 영역의 무게 비율이 균등할수록 안정적입니다.</p>
        </div>
    </div>
</body>
</html>"""
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html)
        
        return output_path
    
    def _generate_layers_html(self, layers: List[Dict], layer_images: List[str] = None, bin_name: str = None) -> str:
        """레이어별 HTML 생성 (탑뷰 이미지 포함)"""
        html = ""
        # 레이어별로 다른 색상 사용
        colors = ['#667eea', '#f093fb', '#4facfe', '#43e97b', '#fa709a', '#fee140', '#30cfd0', '#a8edea']
        
        for layer in layers:
            layer_num = layer['layer_number']
            base_height = layer.get('base_height', layer['height_range'][0])
            layer_color = colors[(layer_num - 1) % len(colors)]
            
            # 해당 레이어의 이미지 찾기
            layer_image_html = ""
            if layer_images and bin_name:
                layer_image_name = f"{bin_name}_layer_{layer_num}.png"
                if layer_image_name in layer_images:
                    layer_image_html = f'''
                    <div class="layer-diagram" style="margin-top: 15px; padding: 15px; background: white; border-radius: 6px; border: 2px solid {layer_color};">
                        <h4 style="margin-top: 0; color: {layer_color}; font-size: 16pt;">📐 레이어 {layer_num} 탑뷰</h4>
                        <div class="image-container">
                            <img src="/api/image/{layer_image_name}" alt="Layer {layer_num} Top View" style="max-width: 100%; border: 2px solid {layer_color}; border-radius: 4px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
                        </div>
                    </div>
                    '''
            
            html += f"""
            <div class="layer" style="border: 4px solid {layer_color}; margin: 40px 0; padding: 25px; background: linear-gradient(to right, {layer_color}15, white); border-radius: 10px; box-shadow: 0 4px 12px rgba(0,0,0,0.15);">
                <div style="background: {layer_color}; color: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; text-align: center;">
                    <h2 style="margin: 0; color: white; font-size: 24pt; font-weight: bold;">
                        ═════ 레이어 {layer_num} ═════
                    </h2>
                    <p style="margin: 10px 0 0 0; font-size: 14pt;">바닥 높이: {base_height:.1f} cm</p>
                    <p style="margin: 5px 0; font-size: 12pt;">
                        높이 범위: {layer['height_range'][0]:.1f} ~ {layer['height_range'][1]:.1f} cm | 
                        아이템: {layer['total_items']}개 | 
                        무게: {layer['total_weight']:.2f} kg
                    </p>
                </div>
                <table>
                    <tr>
                        <th>제품명</th><th>개수</th><th>총 무게 (kg)</th>
                    </tr>
                    {''.join(f"<tr><td>{p['name']}</td><td>{p['count']}개</td><td>{p['total_weight']:.2f}</td></tr>" for p in layer['products'])}
                </table>
                {layer_image_html}
            </div>
            """
        return html
    
    def _generate_loading_order_html(self, loading_order: List[Dict]) -> str:
        """적재 순서 HTML 생성"""
        return ''.join(
            f"<tr>"
            f"<td>{item['sequence']}</td>"
            f"<td>{item['layer']}</td>"
            f"<td>{item['partno']}</td>"
            f"<td>{item['name']}</td>"
            f"<td>({item['position'][0]:.1f}, {item['position'][1]:.1f}, {item['position'][2]:.1f})</td>"
            f"<td>{item['dimensions'][0]:.1f}×{item['dimensions'][1]:.1f}×{item['dimensions'][2]:.1f}</td>"
            f"<td>{item['rotation_type']}</td>"
            f"</tr>"
            for item in loading_order
        )
    
    def _generate_images_html(self, image_paths: List[str]) -> str:
        """이미지 HTML 생성"""
        if not image_paths:
            return ""
        
        html = '<div class="section"><h2>📐 적재 도면</h2>'
        for img_path in image_paths:
            # 상대 경로로 변환
            img_name = Path(img_path).name
            html += f'<div class="image-container"><img src="/api/image/{img_name}" alt="Packing Diagram"></div>'
        html += '</div>'
        return html
    
    def generate_layer_diagram(self, layer_number: int, output_path: str):
        """레이어별 평면도 생성 (위에서 본 모습 - x-y 평면: 가로 x 세로)"""
        if layer_number > len(self.layers):
            return
        
        layer = self.layers[layer_number - 1]
        
        fig, ax = plt.subplots(1, 1, figsize=(14, 10))
        
        # 박스 외곽선 (x-y 평면: 가로 x 세로)
        rect = patches.Rectangle((0, 0), float(self.bin.width), float(self.bin.height), 
                               linewidth=3, edgecolor='black', facecolor='none', linestyle='-')
        ax.add_patch(rect)
        
        # 레이어 아이템 그리기
        colors = plt.cm.tab20(range(len(layer['items'])))
        for idx, item in enumerate(layer['items']):
            x, y, z = [float(p) for p in item.position]
            dim = item.getDimension()  # [x방향크기, y방향크기, z방향크기]
            
            # 위에서 본 모습 (x-y 평면: 가로 x 세로)
            # x 방향 크기 = dimension[0], y 방향 크기 = dimension[1]
            x_size = float(dim[0])  # x축 방향 크기 (가로)
            y_size = float(dim[1])  # y축 방향 크기 (세로)
            
            rect = patches.Rectangle((x, y), x_size, y_size, 
                                   linewidth=2, edgecolor='black', 
                                   facecolor=colors[idx], alpha=0.7)
            ax.add_patch(rect)
            
            # 제품명 표시
            ax.text(x + x_size/2, y + y_size/2, f"{item.name[:12]}\n({item.partno})", 
                   ha='center', va='center', fontsize=9, fontweight='bold',
                   bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.8))
        
        ax.set_xlim(-10, float(self.bin.width) + 10)
        ax.set_ylim(-10, float(self.bin.height) + 10)
        ax.set_aspect('equal')
        ax.set_xlabel('가로축 (X축, Width, cm)', fontsize=14, fontweight='bold')
        ax.set_ylabel('세로축 (Y축, Height, cm)', fontsize=14, fontweight='bold')
        
        # 좌표축 선 그리기 (명확한 단면도)
        ax.axhline(y=0, color='red', linewidth=2, linestyle='-', alpha=0.7, zorder=0)
        ax.axvline(x=0, color='blue', linewidth=2, linestyle='-', alpha=0.7, zorder=0)
        
        # 축 화살표 추가
        ax.annotate('', xy=(float(self.bin.width) + 5, 0), xytext=(float(self.bin.width) - 5, 0),
                   arrowprops=dict(arrowstyle='->', color='red', lw=2, zorder=10))
        ax.annotate('X', xy=(float(self.bin.width) + 8, 0), ha='left', va='center',
                   fontsize=14, fontweight='bold', color='red',
                   bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.8))
        
        ax.annotate('', xy=(0, float(self.bin.height) + 5), xytext=(0, float(self.bin.height) - 5),
                   arrowprops=dict(arrowstyle='->', color='blue', lw=2, zorder=10))
        ax.annotate('Y', xy=(0, float(self.bin.height) + 8), ha='center', va='bottom',
                   fontsize=14, fontweight='bold', color='blue',
                   bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.8))
        
        # 원점 표시
        ax.plot(0, 0, 'ko', markersize=8, zorder=10)
        ax.text(-5, -5, 'O(0,0)', fontsize=10, fontweight='bold', 
               bbox=dict(boxstyle='round,pad=0.3', facecolor='yellow', alpha=0.7))
        
        # 좌표 눈금 표시 개선
        ax.tick_params(axis='both', which='major', labelsize=10, width=1.5)
        ax.minorticks_on()
        ax.grid(True, alpha=0.3, linestyle='--', linewidth=0.5, which='major')
        ax.grid(True, alpha=0.15, linestyle=':', linewidth=0.3, which='minor')
        
        base_height = layer.get('base_height', layer.get('height_range', (0, 0))[0])
        z_range = layer.get('z_range', (0, 0))
        height_range = layer.get('height_range', (0, 0))
        ax.set_title(f'레이어 {layer_number} 탑뷰 단면도 (X-Y 평면, Z축 범위: {z_range[0]:.1f} ~ {z_range[1]:.1f} cm)\nY축 범위: {height_range[0]:.1f} ~ {height_range[1]:.1f} cm', 
                    fontsize=16, fontweight='bold', pad=20)
        
        # 방향 표시 추가
        ax.annotate('앞쪽', xy=(float(self.bin.width)/2, -7), ha='center', 
                   fontsize=12, fontweight='bold', color='blue',
                   bbox=dict(boxstyle='round,pad=0.5', facecolor='lightblue', alpha=0.7))
        ax.annotate('뒤쪽', xy=(float(self.bin.width)/2, float(self.bin.height) + 7), ha='center', 
                   fontsize=12, fontweight='bold', color='blue',
                   bbox=dict(boxstyle='round,pad=0.5', facecolor='lightblue', alpha=0.7))
        ax.annotate('왼쪽', xy=(-7, float(self.bin.height)/2), ha='center', va='center',
                   fontsize=12, fontweight='bold', color='blue', rotation=90,
                   bbox=dict(boxstyle='round,pad=0.5', facecolor='lightblue', alpha=0.7))
        ax.annotate('오른쪽', xy=(float(self.bin.width) + 7, float(self.bin.height)/2), ha='center', va='center',
                   fontsize=12, fontweight='bold', color='blue', rotation=90,
                   bbox=dict(boxstyle='round,pad=0.5', facecolor='lightblue', alpha=0.7))
        
        # 범례 추가
        from matplotlib.lines import Line2D
        legend_elements = [
            Line2D([0], [0], color='red', lw=2, label='X축 (가로축)'),
            Line2D([0], [0], color='blue', lw=2, label='Y축 (세로축)')
        ]
        ax.legend(handles=legend_elements, loc='upper right', fontsize=10, framealpha=0.9)
        
        plt.tight_layout()
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
    
    def generate_work_instruction_report(self, output_path: str, image_paths: List[str] = None) -> str:
        """작업 지시서 형태의 보고서 생성 (인쇄용)"""
        report_data = self.generate_detailed_report()
        bin_name = report_data['bin_info']['partno']
        
        html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <title>적재 작업 지시서 - {bin_name}</title>
    <style>
        @media print {{
            @page {{
                size: A4;
                margin: 1.5cm;
            }}
            .page-break {{
                page-break-after: always;
            }}
            .no-print {{
                display: none;
            }}
            body {{
                background: white;
            }}
        }}
        
        body {{
            font-family: 'Malgun Gothic', Arial, sans-serif;
            font-size: 11pt;
            line-height: 1.6;
            margin: 0;
            padding: 0;
            background: #f5f5f5;
        }}
        
        .work-page {{
            width: 21cm;
            min-height: 29.7cm;
            padding: 1.5cm;
            margin: 0 auto 20px;
            background: white;
            box-shadow: 0 0 10px rgba(0,0,0,0.1);
        }}
        
        .work-header {{
            border-bottom: 3px solid #333;
            padding-bottom: 15px;
            margin-bottom: 20px;
        }}
        
        .work-header h1 {{
            margin: 0 0 10px 0;
            font-size: 24pt;
            color: #333;
        }}
        
        .work-header p {{
            margin: 5px 0;
            font-size: 12pt;
        }}
        
        .layer-info {{
            background: #f5f5f5;
            padding: 15px;
            margin: 15px 0;
            border-left: 5px solid #667eea;
        }}
        
        .work-steps {{
            margin: 20px 0;
        }}
        
        .work-steps h2 {{
            font-size: 16pt;
            color: #667eea;
            border-bottom: 2px solid #667eea;
            padding-bottom: 5px;
            margin-bottom: 15px;
        }}
        
        .work-step {{
            display: flex;
            align-items: start;
            margin: 12px 0;
            padding: 12px;
            border: 1px solid #ddd;
            border-radius: 4px;
            background: white;
        }}
        
        .step-number {{
            background: #667eea;
            color: white;
            width: 35px;
            height: 35px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: bold;
            font-size: 14pt;
            margin-right: 15px;
            flex-shrink: 0;
        }}
        
        .step-content {{
            flex: 1;
        }}
        
        .step-item {{
            font-weight: bold;
            font-size: 12pt;
            margin-bottom: 5px;
            color: #333;
        }}
        
        .step-position {{
            color: #666;
            font-size: 10pt;
            margin-top: 5px;
        }}
        
        .checklist {{
            margin: 20px 0;
        }}
        
        .checklist h2 {{
            font-size: 16pt;
            color: #667eea;
            border-bottom: 2px solid #667eea;
            padding-bottom: 5px;
            margin-bottom: 15px;
        }}
        
        .checklist-item {{
            display: flex;
            align-items: center;
            padding: 10px;
            border-bottom: 1px solid #eee;
            font-size: 11pt;
        }}
        
        .checklist-item input[type="checkbox"] {{
            width: 20px;
            height: 20px;
            margin-right: 12px;
            cursor: pointer;
        }}
        
        .top-view-diagram {{
            text-align: center;
            margin: 25px 0;
            page-break-inside: avoid;
        }}
        
        .top-view-diagram h3 {{
            font-size: 14pt;
            color: #667eea;
            margin-bottom: 10px;
        }}
        
        .top-view-diagram img {{
            max-width: 100%;
            height: auto;
            border: 2px solid #333;
            box-shadow: 0 2px 8px rgba(0,0,0,0.2);
        }}
        
        .summary-box {{
            background: #f9f9f9;
            padding: 15px;
            border: 2px solid #333;
            margin: 20px 0;
            page-break-inside: avoid;
        }}
        
        .summary-box h2, .summary-box h3 {{
            margin-top: 0;
            color: #333;
            font-size: 14pt;
        }}
        
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 10px 0;
        }}
        
        table th, table td {{
            padding: 10px;
            border: 1px solid #333;
            text-align: left;
        }}
        
        table th {{
            background: #667eea;
            color: white;
            font-weight: bold;
        }}
        
        .print-btn {{
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 10px 20px;
            background: #667eea;
            color: white;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-size: 14pt;
            z-index: 1000;
        }}
        
        .print-btn:hover {{
            background: #5568d3;
        }}
    </style>
    <script>
        function printReport() {{
            window.print();
        }}
    </script>
</head>
<body>
    <button class="print-btn no-print" onclick="printReport()">🖨️ 인쇄</button>
    {self._generate_work_pages(report_data, image_paths, bin_name)}
</body>
</html>"""
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html)
        
        return output_path
    
    def _generate_work_pages(self, report_data: Dict, image_paths: List[str] = None, bin_name: str = None) -> str:
        """작업 페이지 생성"""
        pages_html = ""
        
        # 표지 페이지
        pages_html += f"""
    <div class="work-page">
        <div class="work-header">
            <h1>적재 작업 지시서</h1>
            <p><strong>박스명:</strong> {bin_name}</p>
            <p><strong>크기:</strong> {report_data['bin_info']['dimensions']['width']} × {report_data['bin_info']['dimensions']['height']} × {report_data['bin_info']['dimensions']['depth']} cm</p>
            <p><strong>최대 무게:</strong> {report_data['bin_info']['max_weight']} kg</p>
            <p><strong>생성일:</strong> {report_data['generated_at']}</p>
        </div>
        <div class="summary-box">
            <h2>작업 요약</h2>
            <p><strong>총 레이어 수:</strong> {len(report_data['layers'])}개</p>
            <p><strong>총 아이템 수:</strong> {sum(layer['total_items'] for layer in report_data['layers'])}개</p>
            <p><strong>총 무게:</strong> {report_data['bin_info']['total_weight']:.1f} kg / {report_data['bin_info']['max_weight']} kg</p>
            <p><strong>공간 활용률:</strong> {report_data['bin_info']['space_utilization']}%</p>
        </div>
        <div style="margin-top: 30px; padding: 20px; background: #fff3cd; border: 2px solid #ffc107; border-radius: 5px;">
            <h3 style="margin-top: 0; color: #856404;">⚠️ 작업 시 주의사항</h3>
            <ul style="line-height: 1.8;">
                <li>작업 순서를 반드시 지켜주세요.</li>
                <li>각 아이템의 위치를 정확히 확인하고 적재하세요.</li>
                <li>무게 제한을 초과하지 않도록 주의하세요.</li>
                <li>작업 완료 후 체크리스트에 체크하세요.</li>
            </ul>
        </div>
    </div>
    <div class="page-break"></div>
    """
        
        # 각 레이어별 작업 페이지
        for layer in report_data['layers']:
            layer_num = layer['layer_number']
            pages_html += self._generate_layer_work_page(layer, layer_num, image_paths, bin_name)
            if layer_num < len(report_data['layers']):
                pages_html += '<div class="page-break"></div>'
        
        return pages_html
    
    def _generate_layer_work_page(self, layer: Dict, layer_num: int, image_paths: List[str] = None, bin_name: str = None) -> str:
        """단일 레이어 작업 페이지 생성"""
        # 레이어의 아이템들 가져오기 (self.layers에서 가져오기)
        layer_items = []
        if self.layers and layer_num <= len(self.layers):
            layer_data = self.layers[layer_num - 1]
            layer_items = layer_data.get('items', [])
        
        # 탑뷰 이미지 찾기
        layer_image_html = ""
        if image_paths and bin_name:
            layer_image_name = f"{bin_name}_layer_{layer_num}.png"
            if layer_image_name in image_paths:
                layer_image_html = f'''
            <div class="top-view-diagram">
                <h3>레이어 {layer_num} 탑뷰 (위에서 본 모습)</h3>
                <img src="/api/image/{layer_image_name}" alt="Layer {layer_num} Top View">
            </div>
            '''
        
        # 작업 단계 생성 (위치 순서대로 정렬)
        steps_html = ""
        if layer_items:
            # z, x 순서로 정렬
            sorted_items = sorted(layer_items, 
                                key=lambda x: (float(x.position[2]), float(x.position[0])))
            
            for idx, item in enumerate(sorted_items, 1):
                pos = item.position
                dim = item.getDimension()
                steps_html += f"""
            <div class="work-step">
                <div class="step-number">{idx}</div>
                <div class="step-content">
                    <div class="step-item">{item.name} ({item.partno})</div>
                    <div class="step-position">
                        위치: X={float(pos[0]):.1f}cm, Y={float(pos[1]):.1f}cm, Z={float(pos[2]):.1f}cm | 
                        크기: {float(dim[0]):.1f}×{float(dim[1]):.1f}×{float(dim[2]):.1f}cm | 
                        무게: {float(item.weight):.1f}kg
                    </div>
                </div>
            </div>
            """
        
        # 체크리스트 생성
        checklist_html = ""
        for product in layer['products']:
            items_list = product.get('items', [])
            for i in range(product['count']):
                item_info = items_list[i] if i < len(items_list) else {}
                partno = item_info.get('partno', '') if item_info else ''
                checklist_html += f"""
            <div class="checklist-item">
                <input type="checkbox">
                <span><strong>{product['name']}</strong> {f'({partno})' if partno else ''}</span>
            </div>
            """
        
        base_height = layer.get('base_height', layer['height_range'][0])
        
        return f"""
    <div class="work-page">
        <div class="work-header" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 25px; border-radius: 8px; margin-bottom: 25px; border: 3px solid #333;">
            <h1 style="color: white; margin: 0 0 15px 0; font-size: 28pt; text-align: center; font-weight: bold;">
                ═════ 레이어 {layer_num} ═════
            </h1>
            <div style="text-align: center; font-size: 14pt;">
                <p style="margin: 8px 0; font-weight: bold;"><strong>바닥 높이:</strong> {base_height:.1f} cm</p>
                <p style="margin: 8px 0; font-size: 12pt;">
                    높이 범위: {layer['height_range'][0]:.1f} ~ {layer['height_range'][1]:.1f} cm | 
                    아이템: {layer['total_items']}개 | 
                    무게: {layer['total_weight']:.2f} kg
                </p>
            </div>
        </div>
        
        {layer_image_html}
        
        <div class="work-steps">
            <h2>📋 작업 순서 (아래 순서대로 적재하세요)</h2>
            {steps_html if steps_html else '<p>작업 순서 정보가 없습니다.</p>'}
        </div>
        
        <div class="checklist">
            <h2>✅ 작업 체크리스트</h2>
            {checklist_html if checklist_html else '<p>체크리스트 항목이 없습니다.</p>'}
        </div>
        
        <div class="summary-box">
            <h3>레이어 {layer_num} 제품 목록</h3>
            <table>
                <tr>
                    <th>제품명</th>
                    <th>개수</th>
                    <th>총 무게 (kg)</th>
                </tr>
                {''.join(f"<tr><td>{p['name']}</td><td>{p['count']}개</td><td>{p['total_weight']:.2f}</td></tr>" for p in layer['products'])}
            </table>
        </div>
    </div>
    """

