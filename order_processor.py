"""
주문서 CSV 처리 모듈
형식: 제품번호, 제품명, 수량
"""
import csv
from typing import List, Dict
from master_data_manager import MasterDataManager

class OrderProcessor:
    """주문서 처리 클래스"""
    
    def __init__(self, master_manager: MasterDataManager):
        self.master_manager = master_manager
        self.orders = []
    
    def read_order_csv(self, csv_path: str) -> List[Dict]:
        """주문서 CSV 읽기"""
        orders = []
        
        with open(csv_path, 'r', encoding='utf-8') as f:
            # 첫 줄을 읽어서 컬럼 확인
            first_line = f.readline().strip()
            f.seek(0)  # 파일 포인터 리셋
            
            # CSV 읽기
            reader = csv.DictReader(f)
            
            for row in reader:
                # 컬럼명이 다양할 수 있으므로 유연하게 처리
                partno = (row.get('제품번호') or row.get('product_code') or 
                         row.get('코드') or row.get('partno') or 
                         row.get('PARTNO') or row.get('제품코드'))
                
                name = (row.get('제품명') or row.get('product_name') or 
                       row.get('품명') or row.get('name') or 
                       row.get('NAME') or row.get('상품명'))
                
                quantity = (row.get('수량') or row.get('quantity') or 
                           row.get('qty') or row.get('QTY') or 
                           row.get('QUANTITY') or row.get('개수'))
                
                if partno:
                    partno = str(partno).strip()
                    try:
                        qty = int(float(quantity)) if quantity else 1
                        orders.append({
                            'partno': partno,
                            'name': name.strip() if name else '',
                            'quantity': qty
                        })
                    except (ValueError, TypeError):
                        # 수량이 없거나 잘못된 경우 기본값 1
                        orders.append({
                            'partno': partno,
                            'name': name.strip() if name else '',
                            'quantity': 1
                        })
        
        self.orders = orders
        return orders
    
    def process_orders_with_master(self) -> Dict:
        """주문서를 마스터 데이터와 매칭하여 처리"""
        result = {
            'matched_items': [],
            'unmatched_items': [],
            'total_orders': len(self.orders),
            'total_quantity': 0
        }
        
        for order in self.orders:
            partno = order['partno']
            quantity = order['quantity']
            
            # 마스터에서 아이템 정보 조회
            master_item = self.master_manager.get_item_by_partno(partno)
            
            if master_item:
                # 마스터 정보와 주문 수량 결합
                item_with_order = master_item.copy()
                item_with_order['order_quantity'] = quantity
                item_with_order['order_name'] = order.get('name', '')
                result['matched_items'].append(item_with_order)
                result['total_quantity'] += quantity
            else:
                # 매칭되지 않은 아이템
                result['unmatched_items'].append({
                    'partno': partno,
                    'name': order.get('name', ''),
                    'quantity': quantity,
                    'reason': '마스터 데이터에 없음'
                })
        
        return result


