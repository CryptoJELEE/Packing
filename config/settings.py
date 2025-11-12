"""
애플리케이션 설정
"""
import os
import secrets
from pathlib import Path

# 기본 경로
BASE_DIR = Path(__file__).parent.parent


class Config:
    """기본 애플리케이션 설정 클래스"""

    # Flask 설정
    SECRET_KEY = os.environ.get('SECRET_KEY')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
    JSON_SORT_KEYS = False

    # 디렉토리 설정
    UPLOAD_FOLDER = BASE_DIR / 'uploads'
    OUTPUT_FOLDER = BASE_DIR / 'output'
    DATA_FOLDER = BASE_DIR / 'data'
    LOG_FOLDER = BASE_DIR / 'logs'

    # Supabase 설정
    SUPABASE_URL = os.environ.get('SUPABASE_URL')
    SUPABASE_KEY = os.environ.get('SUPABASE_KEY')

    # Flask 디버그 모드
    DEBUG = False
    TESTING = False

    # 로깅 설정
    LOG_LEVEL = 'INFO'
    LOG_FILE = None

    # 보안 설정
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'

    # Rate Limiting
    RATELIMIT_ENABLED = True
    RATELIMIT_STORAGE_URL = "memory://"

    @classmethod
    def init_app(cls, app):
        """앱 초기화 시 디렉토리 생성 및 검증"""
        # 필요한 디렉토리 생성
        cls.UPLOAD_FOLDER.mkdir(exist_ok=True)
        cls.OUTPUT_FOLDER.mkdir(exist_ok=True)
        cls.DATA_FOLDER.mkdir(exist_ok=True)
        cls.LOG_FOLDER.mkdir(exist_ok=True)
        (cls.OUTPUT_FOLDER / 'images').mkdir(exist_ok=True)
        (cls.OUTPUT_FOLDER / 'reports').mkdir(exist_ok=True)

        # SECRET_KEY 검증
        if not app.config.get('SECRET_KEY'):
            if cls.__name__ == 'DevelopmentConfig':
                # 개발 환경에서는 자동 생성
                app.config['SECRET_KEY'] = secrets.token_hex(32)
                print("⚠️  WARNING: SECRET_KEY가 설정되지 않아 임시 키를 생성했습니다.")
            else:
                # 프로덕션에서는 필수
                raise ValueError(
                    "SECRET_KEY 환경 변수가 필수입니다. "
                    "다음 명령어로 생성하세요: python -c 'import secrets; print(secrets.token_hex(32))'"
                )


class DevelopmentConfig(Config):
    """개발 환경 설정"""
    DEBUG = True
    LOG_LEVEL = 'DEBUG'
    LOG_FILE = str(Config.LOG_FOLDER / 'development.log')
    SESSION_COOKIE_SECURE = False  # HTTP에서도 작동


class ProductionConfig(Config):
    """프로덕션 환경 설정"""
    DEBUG = False
    LOG_LEVEL = 'WARNING'
    LOG_FILE = str(Config.LOG_FOLDER / 'production.log')

    @classmethod
    def init_app(cls, app):
        Config.init_app(app)

        # 프로덕션 전용 검증
        if not os.environ.get('SECRET_KEY'):
            raise ValueError("프로덕션 환경에서 SECRET_KEY는 필수입니다")


class TestingConfig(Config):
    """테스트 환경 설정"""
    TESTING = True
    DEBUG = True
    SECRET_KEY = 'test-secret-key-do-not-use-in-production'
    LOG_LEVEL = 'DEBUG'
    RATELIMIT_ENABLED = False


# 환경 설정 매핑
config_by_name = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}


def get_config(env: str = None) -> Config:
    """
    환경에 맞는 설정 가져오기

    Args:
        env: 환경 이름 (development, production, testing)

    Returns:
        설정 클래스
    """
    if env is None:
        env = os.environ.get('FLASK_ENV', 'development')

    return config_by_name.get(env, DevelopmentConfig)

