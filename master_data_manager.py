"""
자재마스터 데이터 관리 모듈 (Supabase 버전)
"""
import json
import os
from typing import Dict, Optional, List
from datetime import datetime

# Supabase 사용 시도, 실패 시 로컬 파일 사용
try:
    from supabase_client import supabase_client
    USE_SUPABASE = True
except ImportError:
    USE_SUPABASE = False
    print("Supabase 클라이언트를 사용할 수 없습니다. 로컬 파일 시스템을 사용합니다.")

class MasterDataManager:
    """마스터 데이터 관리 클래스 (Supabase 우선, 실패 시 로컬 파일)"""
    
    TABLE_NAME = 'master_items'
    MASTER_FILE = 'data/master_data.json'
    
    def __init__(self):
        self.use_supabase = USE_SUPABASE
        if self.use_supabase:
            try:
                self.table = supabase_client.get_table(self.TABLE_NAME)
                self._cache = {}
                self._load_cache()
            except Exception as e:
                print(f"Supabase 초기화 실패: {str(e)}, 로컬 파일 시스템 사용")
                self.use_supabase = False
                self.master_data = {}
                self.load_master_data()
        else:
            self.master_data = {}
            self.load_master_data()
    
    def _load_cache(self):
        """Supabase에서 캐시 로드"""
        try:
            response = self.table.select("*").execute()
            if response.data:
                for item in response.data:
                    partno = item.get('partno')
                    if partno:
                        # Supabase 데이터를 기존 형식으로 변환
                        self._cache[partno] = {
                            'partno': partno,
                            'name': item.get('name', ''),
                            'width': item.get('width', 0),
                            'height': item.get('height', 0),
                            'depth': item.get('depth', 0),
                            'weight': item.get('weight', 0),
                            'packaging': item.get('packaging', ''),
                            'original': item.get('original_data', {})
                        }
        except Exception as e:
            print(f"캐시 로드 오류: {str(e)}")
            self._cache = {}
    
    def load_master_data(self):
        """로컬 파일에서 마스터 데이터 로드"""
        if os.path.exists(self.MASTER_FILE):
            try:
                with open(self.MASTER_FILE, 'r', encoding='utf-8') as f:
                    self.master_data = json.load(f)
            except:
                self.master_data = {}
        else:
            os.makedirs(os.path.dirname(self.MASTER_FILE), exist_ok=True)
    
    def save_master_data(self):
        """로컬 파일에 마스터 데이터 저장"""
        os.makedirs(os.path.dirname(self.MASTER_FILE), exist_ok=True)
        with open(self.MASTER_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.master_data, f, indent=2, ensure_ascii=False)
    
    def add_master_items(self, items: List[Dict]):
        """마스터 아이템 추가/업데이트"""
        if self.use_supabase:
            try:
                for item in items:
                    partno = item.get('partno')
                    if not partno:
                        continue
                    
                    # 기존 데이터 확인
                    existing = self.get_item_by_partno(partno)
                    
                    item_data = {
                        'partno': partno,
                        'name': item.get('name', ''),
                        'width': item.get('width', 0),
                        'height': item.get('height', 0),
                        'depth': item.get('depth', 0),
                        'weight': item.get('weight', 0),
                        'packaging': item.get('packaging', ''),
                        'category': item.get('original', {}).get('분류', ''),
                        'original_data': item.get('original', {}),
                        'updated_at': datetime.now().isoformat()
                    }
                    
                    if existing:
                        # 업데이트
                        self.table.update(item_data).eq('partno', partno).execute()
                    else:
                        # 삽입
                        self.table.insert(item_data).execute()
                    
                    # 캐시 업데이트
                    self._cache[partno] = item
                
                return True
            except Exception as e:
                print(f"Supabase 마스터 데이터 추가 오류: {str(e)}, 로컬 파일로 저장")
                self.use_supabase = False
        
        # 로컬 파일 시스템 사용
        for item in items:
            partno = item.get('partno')
            if partno:
                self.master_data[partno] = item
        self.save_master_data()
        return True
    
    def get_item_by_partno(self, partno: str) -> Optional[Dict]:
        """제품번호로 아이템 조회"""
        if self.use_supabase:
            # 캐시에서 먼저 확인
            if partno in self._cache:
                return self._cache[partno]
            
            try:
                response = self.table.select("*").eq('partno', partno).execute()
                if response.data and len(response.data) > 0:
                    item = response.data[0]
                    # Supabase 데이터를 기존 형식으로 변환
                    converted_item = {
                        'partno': item.get('partno'),
                        'name': item.get('name', ''),
                        'width': item.get('width', 0),
                        'height': item.get('height', 0),
                        'depth': item.get('depth', 0),
                        'weight': item.get('weight', 0),
                        'packaging': item.get('packaging', ''),
                        'original': item.get('original_data', {})
                    }
                    self._cache[partno] = converted_item
                    return converted_item
            except Exception as e:
                print(f"Supabase 아이템 조회 오류: {str(e)}")
        
        # 로컬 파일 시스템 사용
        return self.master_data.get(partno)
    
    def get_items_by_partnos(self, partnos: List[str]) -> Dict[str, Dict]:
        """여러 제품번호로 아이템 조회"""
        if self.use_supabase:
            result = {}
            try:
                response = self.table.select("*").in_('partno', partnos).execute()
                if response.data:
                    for item in response.data:
                        partno = item.get('partno')
                        if partno:
                            converted_item = {
                                'partno': partno,
                                'name': item.get('name', ''),
                                'width': item.get('width', 0),
                                'height': item.get('height', 0),
                                'depth': item.get('depth', 0),
                                'weight': item.get('weight', 0),
                                'packaging': item.get('packaging', ''),
                                'original': item.get('original_data', {})
                            }
                            result[partno] = converted_item
                            self._cache[partno] = converted_item
            except Exception as e:
                print(f"Supabase 아이템 목록 조회 오류: {str(e)}")
            
            return result
        
        # 로컬 파일 시스템 사용
        return {partno: self.master_data.get(partno) 
                for partno in partnos if partno in self.master_data}
    
    def has_master_data(self) -> bool:
        """마스터 데이터 존재 여부"""
        if self.use_supabase:
            try:
                response = self.table.select("partno", count="exact").limit(1).execute()
                return response.count > 0 if hasattr(response, 'count') else len(self._cache) > 0
            except:
                return len(self._cache) > 0
        
        return len(self.master_data) > 0
    
    def get_master_stats(self) -> Dict:
        """마스터 데이터 통계"""
        if self.use_supabase:
            try:
                response = self.table.select("*").execute()
                total_items = len(response.data) if response.data else len(self._cache)
                
                categories = {}
                items = response.data if response.data else list(self._cache.values())
                for item in items:
                    original = item.get('original_data') if isinstance(item, dict) and 'original_data' in item else item.get('original', {})
                    cat = original.get('분류', '기타') if isinstance(original, dict) else '기타'
                    categories[cat] = categories.get(cat, 0) + 1
                
                return {
                    'total_items': total_items,
                    'categories': categories
                }
            except Exception as e:
                print(f"Supabase 통계 조회 오류: {str(e)}")
                return {
                    'total_items': len(self._cache),
                    'categories': {}
                }
        
        # 로컬 파일 시스템 사용
        categories = {}
        for item in self.master_data.values():
            cat = item.get('original', {}).get('분류', '기타')
            categories[cat] = categories.get(cat, 0) + 1
        
        return {
            'total_items': len(self.master_data),
            'categories': categories
        }
    
    def clear_master_data(self):
        """마스터 데이터 초기화"""
        if self.use_supabase:
            try:
                self.table.delete().neq('id', '00000000-0000-0000-0000-000000000000').execute()
                self._cache = {}
                return True
            except Exception as e:
                print(f"Supabase 데이터 초기화 오류: {str(e)}")
                return False
        
        self.master_data = {}
        if os.path.exists(self.MASTER_FILE):
            os.remove(self.MASTER_FILE)
        return True


