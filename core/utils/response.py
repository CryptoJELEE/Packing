"""
API 응답 표준화 및 에러 핸들링
"""
import traceback
from typing import Any, Optional, Dict
from flask import jsonify, Response
from .logger import get_logger

logger = get_logger(__name__)


class APIResponse:
    """표준 API 응답 생성"""

    @staticmethod
    def success(
        data: Any = None,
        message: str = "Success",
        status_code: int = 200,
        **kwargs
    ) -> tuple[Response, int]:
        """
        성공 응답 생성

        Args:
            data: 응답 데이터
            message: 메시지
            status_code: HTTP 상태 코드
            **kwargs: 추가 필드

        Returns:
            (Flask Response, 상태 코드)
        """
        response = {
            "Success": True,
            "message": message
        }

        if data is not None:
            response["data"] = data

        response.update(kwargs)

        return jsonify(response), status_code

    @staticmethod
    def error(
        reason: str,
        status_code: int = 400,
        error_code: Optional[str] = None,
        details: Optional[Dict] = None
    ) -> tuple[Response, int]:
        """
        에러 응답 생성

        Args:
            reason: 에러 이유
            status_code: HTTP 상태 코드
            error_code: 에러 코드
            details: 에러 상세 정보

        Returns:
            (Flask Response, 상태 코드)
        """
        response = {
            "Success": False,
            "Reason": reason
        }

        if error_code:
            response["error_code"] = error_code

        if details:
            response["details"] = details

        logger.error(f"API Error ({status_code}): {reason}")

        return jsonify(response), status_code

    @staticmethod
    def not_found(resource: str = "리소스") -> tuple[Response, int]:
        """404 응답"""
        return APIResponse.error(
            f"{resource}를 찾을 수 없습니다",
            status_code=404,
            error_code="NOT_FOUND"
        )

    @staticmethod
    def validation_error(errors: Dict[str, str]) -> tuple[Response, int]:
        """유효성 검증 에러 응답"""
        return APIResponse.error(
            "입력 데이터 유효성 검증 실패",
            status_code=422,
            error_code="VALIDATION_ERROR",
            details=errors
        )

    @staticmethod
    def internal_error(
        message: str = "내부 서버 오류",
        exception: Optional[Exception] = None
    ) -> tuple[Response, int]:
        """500 응답"""
        if exception:
            logger.error(f"Internal Error: {message}", exc_info=True)
            # 프로덕션에서는 스택 트레이스 노출 안 함
            return APIResponse.error(
                message,
                status_code=500,
                error_code="INTERNAL_ERROR"
            )
        else:
            return APIResponse.error(
                message,
                status_code=500,
                error_code="INTERNAL_ERROR"
            )


class ErrorHandler:
    """Flask 에러 핸들러"""

    @staticmethod
    def register_handlers(app):
        """
        Flask 앱에 에러 핸들러 등록

        Args:
            app: Flask 앱 인스턴스
        """

        @app.errorhandler(400)
        def bad_request(e):
            return APIResponse.error("잘못된 요청", status_code=400)

        @app.errorhandler(404)
        def not_found(e):
            return APIResponse.not_found()

        @app.errorhandler(405)
        def method_not_allowed(e):
            return APIResponse.error(
                "허용되지 않은 HTTP 메서드",
                status_code=405,
                error_code="METHOD_NOT_ALLOWED"
            )

        @app.errorhandler(413)
        def request_entity_too_large(e):
            return APIResponse.error(
                "파일 크기가 너무 큽니다",
                status_code=413,
                error_code="FILE_TOO_LARGE"
            )

        @app.errorhandler(500)
        def internal_error(e):
            logger.error(f"Internal Server Error: {e}", exc_info=True)
            return APIResponse.internal_error()

        logger.info("에러 핸들러 등록 완료")
