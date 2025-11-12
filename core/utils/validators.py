"""
파일 및 데이터 검증 유틸리티
"""
import mimetypes
import csv
import io
from pathlib import Path
from typing import List, Optional, Tuple
from werkzeug.datastructures import FileStorage
from .logger import get_logger

logger = get_logger(__name__)


class FileValidator:
    """파일 업로드 검증"""

    ALLOWED_CSV_MIMETYPES = [
        'text/csv',
        'application/csv',
        'text/plain',
        'application/vnd.ms-excel'
    ]

    MAX_FILE_SIZE = 16 * 1024 * 1024  # 16MB

    @staticmethod
    def validate_csv_file(file: FileStorage) -> Tuple[bool, Optional[str]]:
        """
        CSV 파일 검증

        Args:
            file: 업로드된 파일

        Returns:
            (성공 여부, 오류 메시지)
        """
        # 파일명 검증
        if not file or not file.filename:
            return False, "파일이 선택되지 않았습니다"

        # 확장자 검증
        if not file.filename.lower().endswith('.csv'):
            return False, "CSV 파일만 업로드 가능합니다"

        # MIME 타입 검증
        file.seek(0)
        mime_type, _ = mimetypes.guess_type(file.filename)

        # 파일 시그니처 검증 (첫 바이트 읽기)
        first_bytes = file.read(1024)
        file.seek(0)

        # CSV 파일인지 간단히 체크
        try:
            first_bytes.decode('utf-8')
        except UnicodeDecodeError:
            return False, "올바른 CSV 파일이 아닙니다 (인코딩 오류)"

        # 파일 크기 검증
        file.seek(0, 2)  # 파일 끝으로 이동
        file_size = file.tell()
        file.seek(0)  # 처음으로 되돌림

        if file_size > FileValidator.MAX_FILE_SIZE:
            return False, f"파일 크기가 너무 큽니다 (최대 {FileValidator.MAX_FILE_SIZE // 1024 // 1024}MB)"

        if file_size == 0:
            return False, "빈 파일입니다"

        logger.info(f"파일 검증 성공: {file.filename} ({file_size} bytes)")
        return True, None


class CSVSanitizer:
    """CSV Injection 방어"""

    DANGEROUS_PREFIXES = ['=', '+', '-', '@', '\t', '\r']

    @staticmethod
    def sanitize_cell(value: str) -> str:
        """
        CSV 셀 값 sanitize

        Args:
            value: 원본 값

        Returns:
            안전한 값
        """
        if not isinstance(value, str):
            return value

        value = value.strip()

        # 위험한 접두사로 시작하는 경우
        if value and value[0] in CSVSanitizer.DANGEROUS_PREFIXES:
            # 작은따옴표로 escape
            sanitized = "'" + value
            logger.warning(f"CSV Injection 방지: '{value}' -> '{sanitized}'")
            return sanitized

        return value

    @staticmethod
    def sanitize_row(row: dict) -> dict:
        """
        CSV 행 sanitize

        Args:
            row: 원본 행

        Returns:
            안전한 행
        """
        return {
            key: CSVSanitizer.sanitize_cell(value) if isinstance(value, str) else value
            for key, value in row.items()
        }

    @staticmethod
    def validate_csv_content(file_path: str, max_rows: int = 10000) -> Tuple[bool, Optional[str]]:
        """
        CSV 내용 검증

        Args:
            file_path: CSV 파일 경로
            max_rows: 최대 행 수

        Returns:
            (성공 여부, 오류 메시지)
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                # 행 개수 체크
                row_count = sum(1 for _ in f)

                if row_count > max_rows:
                    return False, f"CSV 파일의 행이 너무 많습니다 (최대 {max_rows}행)"

            return True, None

        except UnicodeDecodeError:
            return False, "CSV 파일 인코딩 오류 (UTF-8이 아닙니다)"
        except Exception as e:
            logger.error(f"CSV 내용 검증 오류: {e}")
            return False, f"CSV 파일 검증 중 오류: {str(e)}"
