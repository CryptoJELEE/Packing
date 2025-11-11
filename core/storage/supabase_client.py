"""
Supabase 클라이언트 초기화 모듈
"""
import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

class SupabaseClient:
    """Supabase 클라이언트 싱글톤"""
    _instance = None
    _client = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SupabaseClient, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._client is None:
            url = os.getenv("SUPABASE_URL")
            key = os.getenv("SUPABASE_KEY")
            
            if not url or not key:
                raise ValueError("SUPABASE_URL과 SUPABASE_KEY 환경 변수가 필요합니다.")
            
            self._client = create_client(url, key)
    
    @property
    def client(self) -> Client:
        """Supabase 클라이언트 반환"""
        return self._client
    
    def get_table(self, table_name: str):
        """테이블 참조 반환"""
        return self._client.table(table_name)
    
    def get_storage(self):
        """Storage 클라이언트 반환"""
        return self._client.storage

# 전역 인스턴스
supabase_client = SupabaseClient()

