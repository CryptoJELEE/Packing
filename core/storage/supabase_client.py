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
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SupabaseClient, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not self._initialized:
            self._initialized = True
            url = os.getenv("SUPABASE_URL")
            key = os.getenv("SUPABASE_KEY")

            if not url or not key:
                print("Supabase 환경변수가 설정되지 않았습니다. 로컬 모드로 동작합니다.")
                self._client = None
                return

            try:
                self._client = create_client(url, key)
            except Exception as e:
                print(f"Supabase 연결 실패: {e}. 로컬 모드로 동작합니다.")
                self._client = None
    
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

