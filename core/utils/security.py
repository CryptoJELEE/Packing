"""
보안 헤더 및 Rate Limiting 설정
"""
from flask import Flask
from functools import wraps
from typing import Callable


class SecurityHeaders:
    """보안 헤더 미들웨어"""

    @staticmethod
    def init_app(app: Flask):
        """Flask 앱에 보안 헤더 추가"""

        @app.after_request
        def add_security_headers(response):
            """모든 응답에 보안 헤더 추가"""
            # XSS 보호
            response.headers['X-Content-Type-Options'] = 'nosniff'
            response.headers['X-Frame-Options'] = 'SAMEORIGIN'
            response.headers['X-XSS-Protection'] = '1; mode=block'

            # Content Security Policy (CSP)
            # 현재 설정은 느슨함 - 필요에 따라 강화 필요
            csp = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data:; "
                "font-src 'self' data:;"
            )
            response.headers['Content-Security-Policy'] = csp

            # HSTS (HTTPS 전용 - 프로덕션에서만)
            if app.config.get('ENV') == 'production':
                response.headers['Strict-Transport-Security'] = (
                    'max-age=31536000; includeSubDomains'
                )

            # Referrer Policy
            response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'

            # Permissions Policy
            response.headers['Permissions-Policy'] = (
                'geolocation=(), microphone=(), camera=()'
            )

            return response


def rate_limit_handler(e):
    """Rate limit 초과 시 커스텀 응답"""
    from .response import APIResponse
    return APIResponse.error(
        "요청 횟수 제한을 초과했습니다. 잠시 후 다시 시도해주세요.",
        status_code=429,
        error_code="RATE_LIMIT_EXCEEDED"
    )


def setup_rate_limiting(app: Flask):
    """Rate Limiting 설정"""
    try:
        from flask_limiter import Limiter
        from flask_limiter.util import get_remote_address

        limiter = Limiter(
            app=app,
            key_func=get_remote_address,
            default_limits=["200 per day", "50 per hour"],
            storage_uri=app.config.get('RATELIMIT_STORAGE_URL', 'memory://'),
            strategy="fixed-window"
        )

        # Rate limit 에러 핸들러
        app.register_error_handler(429, rate_limit_handler)

        return limiter

    except ImportError:
        app.logger.warning(
            "flask-limiter가 설치되지 않았습니다. "
            "Rate limiting을 사용하려면 'pip install flask-limiter'를 실행하세요."
        )
        return None
