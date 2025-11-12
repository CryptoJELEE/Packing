"""
Validator 테스트
"""
import pytest
from io import BytesIO
from werkzeug.datastructures import FileStorage
from core.utils.validators import FileValidator, CSVSanitizer


class TestFileValidator:
    """FileValidator 테스트 클래스"""

    def test_validate_csv_file_success(self):
        """정상 CSV 파일 검증"""
        file_content = b"col1,col2\nval1,val2"
        file = FileStorage(
            stream=BytesIO(file_content),
            filename="test.csv",
            content_type="text/csv"
        )

        is_valid, error = FileValidator.validate_csv_file(file)
        assert is_valid is True
        assert error is None

    def test_validate_csv_file_no_filename(self):
        """파일명 없는 경우"""
        file = FileStorage(stream=BytesIO(b""), filename="")

        is_valid, error = FileValidator.validate_csv_file(file)
        assert is_valid is False
        assert "선택되지 않았습니다" in error

    def test_validate_csv_file_wrong_extension(self):
        """잘못된 확장자"""
        file = FileStorage(
            stream=BytesIO(b"test"),
            filename="test.txt"
        )

        is_valid, error = FileValidator.validate_csv_file(file)
        assert is_valid is False
        assert "CSV 파일만" in error

    def test_validate_csv_file_too_large(self):
        """파일 크기 초과"""
        # 17MB 파일
        large_content = b"x" * (17 * 1024 * 1024)
        file = FileStorage(
            stream=BytesIO(large_content),
            filename="test.csv"
        )

        is_valid, error = FileValidator.validate_csv_file(file)
        assert is_valid is False
        assert "너무 큽니다" in error

    def test_validate_csv_file_empty(self):
        """빈 파일"""
        file = FileStorage(
            stream=BytesIO(b""),
            filename="test.csv"
        )

        is_valid, error = FileValidator.validate_csv_file(file)
        assert is_valid is False
        assert "빈 파일" in error


class TestCSVSanitizer:
    """CSVSanitizer 테스트 클래스"""

    def test_sanitize_cell_with_equals(self):
        """= 로 시작하는 셀 sanitize"""
        result = CSVSanitizer.sanitize_cell("=SUM(A1:A10)")
        assert result == "'=SUM(A1:A10)"

    def test_sanitize_cell_with_plus(self):
        """+ 로 시작하는 셀 sanitize"""
        result = CSVSanitizer.sanitize_cell("+1234")
        assert result == "'+1234"

    def test_sanitize_cell_normal(self):
        """정상 셀"""
        result = CSVSanitizer.sanitize_cell("normal text")
        assert result == "normal text"

    def test_sanitize_row(self):
        """행 sanitize"""
        row = {
            "col1": "=DANGEROUS",
            "col2": "safe",
            "col3": "+suspicious"
        }
        result = CSVSanitizer.sanitize_row(row)

        assert result["col1"] == "'=DANGEROUS"
        assert result["col2"] == "safe"
        assert result["col3"] == "'+suspicious"
