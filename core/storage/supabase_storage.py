"""
Supabase Storage 관리 모듈
"""
import os
from typing import Optional, BinaryIO
from core.storage.supabase_client import supabase_client

class SupabaseStorage:
    """Supabase Storage 관리 클래스"""
    
    def __init__(self):
        self.storage = supabase_client.get_storage()
    
    def upload_file(self, bucket: str, file_path: str, file_data: bytes, 
                   content_type: str = "application/octet-stream") -> Optional[str]:
        """파일 업로드"""
        try:
            # 경로에서 파일명 추출
            file_name = os.path.basename(file_path)
            
            # 업로드
            response = self.storage.from_(bucket).upload(
                path=file_path,
                file=file_data,
                file_options={"content-type": content_type}
            )
            
            if response:
                # 공개 URL 생성
                public_url = self.storage.from_(bucket).get_public_url(file_path)
                return public_url
            return None
        except Exception as e:
            print(f"파일 업로드 오류: {str(e)}")
            return None
    
    def download_file(self, bucket: str, file_path: str) -> Optional[bytes]:
        """파일 다운로드"""
        try:
            response = self.storage.from_(bucket).download(file_path)
            return response
        except Exception as e:
            print(f"파일 다운로드 오류: {str(e)}")
            return None
    
    def delete_file(self, bucket: str, file_path: str) -> bool:
        """파일 삭제"""
        try:
            self.storage.from_(bucket).remove([file_path])
            return True
        except Exception as e:
            print(f"파일 삭제 오류: {str(e)}")
            return False
    
    def get_public_url(self, bucket: str, file_path: str) -> str:
        """공개 URL 가져오기"""
        return self.storage.from_(bucket).get_public_url(file_path)
    
    def list_files(self, bucket: str, folder: str = "") -> list:
        """폴더 내 파일 목록"""
        try:
            response = self.storage.from_(bucket).list(folder)
            return response if response else []
        except Exception as e:
            print(f"파일 목록 조회 오류: {str(e)}")
            return []

# 전역 인스턴스
supabase_storage = SupabaseStorage()

