"""
애플리케이션 설정
"""
import os
from pathlib import Path

# 기본 경로
BASE_DIR = Path(__file__).parent.parent

class Config:
    """애플리케이션 설정 클래스"""
    
    # Flask 설정
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
    
    # 디렉토리 설정
    UPLOAD_FOLDER = BASE_DIR / 'uploads'
    OUTPUT_FOLDER = BASE_DIR / 'output'
    DATA_FOLDER = BASE_DIR / 'data'
    
    # Supabase 설정
    SUPABASE_URL = os.environ.get('SUPABASE_URL')
    SUPABASE_KEY = os.environ.get('SUPABASE_KEY')
    
    # Flask 디버그 모드
    FLASK_DEBUG = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    
    @staticmethod
    def init_app(app):
        """앱 초기화 시 디렉토리 생성"""
        # 필요한 디렉토리 생성
        Config.UPLOAD_FOLDER.mkdir(exist_ok=True)
        Config.OUTPUT_FOLDER.mkdir(exist_ok=True)
        Config.DATA_FOLDER.mkdir(exist_ok=True)
        (Config.OUTPUT_FOLDER / 'images').mkdir(exist_ok=True)
        (Config.OUTPUT_FOLDER / 'reports').mkdir(exist_ok=True)

