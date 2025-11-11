"""
자재마스터 CSV 파일을 py3dbp 형식으로 변환하는 모듈
"""
import csv
import json
from typing import List, Dict, Any, Optional

class CSVDataProcessor:
    """CSV 데이터 처리 클래스"""
    
    def __init__(self, csv_path: str = None):
        """CSV 파일 경로 초기화"""
        self.csv_path = csv_path
        self.raw_data = []
        self.processed_items = []
        
    def read_csv(self, csv_path: str = None) -> List[Dict]:
        """CSV 파일 읽기 (복잡한 헤더 처리)"""
        if csv_path:
            self.csv_path = csv_path
        
        if not self.csv_path:
            raise ValueError("CSV 파일 경로가 지정되지 않았습니다.")
        
        with open(self.csv_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
            # 헤더는 1-3줄, 실제 데이터는 4줄부터
            # 컬럼명 정의
            columns = [
                '분류', '제품번호', '제품명', '규격', '적재패턴', 
                '박스단위', '파렛트단위', '포장', '가로', '세로', '높이',
                '박스무게', '적재방향제한', '파손취약성'
            ]
            
            # 4줄부터 데이터 읽기 (인덱스 3부터)
            reader = csv.DictReader(lines[3:], fieldnames=columns)
            
            items = []
            for row in reader:
                # 빈 행 스킵
                if not row.get('제품번호') or not row['제품번호'].strip():
                    continue
                    
                items.append(row)
            
            self.raw_data = items
            return items
    
    def process_item(self, row: Dict) -> Optional[Dict]:
        """단일 아이템 데이터를 py3dbp 형식으로 변환"""
        try:
            # 박스 규격 (mm -> cm 변환)
            width_str = row.get('가로', '0').strip()
            height_str = row.get('세로', '0').strip()
            depth_str = row.get('높이', '0').strip()
            
            # 숫자 변환 (빈 값 처리)
            try:
                width = float(width_str) / 10 if width_str else 0
                height = float(height_str) / 10 if height_str else 0
                depth = float(depth_str) / 10 if depth_str else 0
            except ValueError:
                print(f"경고: 제품번호 {row.get('제품번호')}의 크기 정보가 잘못되었습니다.")
                return None
            
            # 크기가 0이면 스킵
            if width == 0 or height == 0 or depth == 0:
                print(f"경고: 제품번호 {row.get('제품번호')}의 크기가 0입니다. 스킵합니다.")
                return None
            
            # 무게 (kg)
            weight_str = row.get('박스무게', '0').strip()
            try:
                weight = float(weight_str) if weight_str else 0
            except ValueError:
                weight = 0
            
            # 적재 방향 제한 처리
            direction_restriction = row.get('적재방향제한', '변경 불가').strip()
            updown = True if '최상단 변경 가능' in direction_restriction else False
            
            # 파손 취약성 처리
            fragility = row.get('파손취약성', '보통').strip()
            # 취약한 제품은 loadbear를 낮게 설정
            loadbear = 50 if fragility == '취약' else 100
            
            # 모든 제품은 사각형 박스(cube)
            packaging = row.get('포장', '').strip()
            item_type = 'cube'
            
            # level 설정 (필수 적재 여부)
            level = 1
            
            # 색상 매핑 (분류별로 다른 색상)
            color_map = {
                '과일음료': 'red',
                '비타민음료': 'yellow',
                '식품쌍화': 'blue',
                '썬키스트': 'green',
                '인홍삼음료': 'purple',
                '일반제품': 'brown',
                '전통음료': 'orange',
                '차음료': '#FF69B4',  # 핑크
                '커피': '#8B4513'     # 갈색
            }
            category = row.get('분류', '').strip()
            color = color_map.get(category, 'gray')
            
            processed = {
                'name': row.get('제품명', '').strip(),
                'partno': row.get('제품번호', '').strip(),
                'typeof': item_type,
                'WHD': [width, height, depth],
                'weight': weight,
                'level': level,
                'loadbear': loadbear,
                'updown': updown,
                'color': color,
                # 원본 데이터 보존
                'original': {
                    '분류': category,
                    '규격': row.get('규격', ''),
                    '적재패턴': row.get('적재패턴', ''),
                    '박스단위': row.get('박스단위', ''),
                    '파렛트단위': row.get('파렛트단위', ''),
                    '포장': packaging,
                    '적재방향제한': direction_restriction,
                    '파손취약성': fragility
                }
            }
            
            return processed
            
        except Exception as e:
            print(f"데이터 처리 오류 (제품번호: {row.get('제품번호', 'N/A')}): {e}")
            return None
    
    def process_all_items(self, csv_path: str = None) -> List[Dict]:
        """모든 아이템 처리"""
        if csv_path or not self.raw_data:
            self.read_csv(csv_path)
        
        processed = []
        for row in self.raw_data:
            item = self.process_item(row)
            if item:
                processed.append(item)
        
        self.processed_items = processed
        return processed
    
    def to_py3dbp_json(self, output_path: str = None) -> Dict:
        """py3dbp JSON 형식으로 변환"""
        if not self.processed_items:
            self.process_all_items()
        
        # JSON 형식 구성
        json_data = {
            'box': [],  # 박스 정보는 별도로 추가 필요
            'item': []
        }
        
        for item in self.processed_items:
            json_item = {
                'name': item['name'],
                'WHD': item['WHD'],
                'count': 1,  # 기본값, 필요시 수정
                'updown': 1 if item['updown'] else 0,
                'type': 2 if item['typeof'] == 'cylinder' else 1,
                'level': item['level'],
                'loadbear': item['loadbear'],
                'weight': item['weight'],
                'color': self._color_to_number(item['color'])
            }
            json_data['item'].append(json_item)
        
        if output_path:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, indent=2, ensure_ascii=False)
        
        return json_data
    
    def _color_to_number(self, color: str) -> int:
        """색상 이름을 숫자로 변환"""
        color_map = {
            'red': 1,
            'yellow': 2,
            'blue': 3,
            'green': 4,
            'purple': 5,
            'brown': 6,
            'orange': 7
        }
        # HEX 색상도 처리
        if color.startswith('#'):
            # HEX 색상은 기본값으로 처리
            return 1
        return color_map.get(color, 1)
    
    def filter_by_category(self, categories: List[str]) -> List[Dict]:
        """카테고리별 필터링"""
        if not self.processed_items:
            self.process_all_items()
        
        return [
            item for item in self.processed_items
            if item['original']['분류'] in categories
        ]
    
    def filter_by_name(self, name_keywords: List[str]) -> List[Dict]:
        """제품명 키워드로 필터링"""
        if not self.processed_items:
            self.process_all_items()
        
        filtered = []
        for item in self.processed_items:
            name = item['name']
            if any(keyword in name for keyword in name_keywords):
                filtered.append(item)
        
        return filtered
    
    def get_statistics(self) -> Dict:
        """데이터 통계 정보"""
        if not self.processed_items:
            self.process_all_items()
        
        stats = {
            'total_items': len(self.processed_items),
            'by_category': {},
            'by_packaging': {},
            'by_fragility': {},
            'total_volume': 0,
            'total_weight': 0
        }
        
        for item in self.processed_items:
            # 카테고리별
            cat = item['original']['분류']
            stats['by_category'][cat] = stats['by_category'].get(cat, 0) + 1
            
            # 포장별
            pkg = item['original']['포장']
            stats['by_packaging'][pkg] = stats['by_packaging'].get(pkg, 0) + 1
            
            # 취약성별
            frag = item['original']['파손취약성']
            stats['by_fragility'][frag] = stats['by_fragility'].get(frag, 0) + 1
            
            # 부피 및 무게
            volume = item['WHD'][0] * item['WHD'][1] * item['WHD'][2]
            stats['total_volume'] += volume
            stats['total_weight'] += item['weight']
        
        return stats

