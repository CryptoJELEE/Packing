"""
설정 테스트
"""
import pytest
import os
from config.settings import (
    Config,
    DevelopmentConfig,
    ProductionConfig,
    TestingConfig,
    get_config
)


class TestConfig:
    """설정 클래스 테스트"""

    def test_development_config(self):
        """개발 환경 설정"""
        config = DevelopmentConfig()
        assert config.DEBUG is True
        assert config.TESTING is False
        assert config.LOG_LEVEL == 'DEBUG'

    def test_production_config(self):
        """프로덕션 환경 설정"""
        config = ProductionConfig()
        assert config.DEBUG is False
        assert config.TESTING is False
        assert config.LOG_LEVEL == 'WARNING'

    def test_testing_config(self):
        """테스트 환경 설정"""
        config = TestingConfig()
        assert config.DEBUG is True
        assert config.TESTING is True
        assert config.SECRET_KEY is not None

    def test_get_config_default(self):
        """기본 설정 가져오기"""
        config = get_config()
        assert config is not None

    def test_get_config_by_name(self):
        """이름으로 설정 가져오기"""
        config = get_config('testing')
        assert config == TestingConfig

        config = get_config('production')
        assert config == ProductionConfig

        config = get_config('development')
        assert config == DevelopmentConfig
