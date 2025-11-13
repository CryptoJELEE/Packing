"""
API 엔드포인트 테스트
"""
import pytest
import json
from io import BytesIO


class TestAPIEndpoints:
    """API 엔드포인트 테스트"""

    def test_index_route(self, client):
        """메인 페이지 테스트"""
        response = client.get('/')
        assert response.status_code == 200

    def test_get_master_status_initial(self, client):
        """초기 마스터 상태 조회"""
        response = client.get('/api/getMasterStatus')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["Success"] is True
        assert "has_master" in data

    def test_upload_master_no_file(self, client):
        """파일 없이 업로드"""
        response = client.post('/api/uploadMaster')
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data["Success"] is False
        assert "파일이 없습니다" in data["Reason"]

    def test_upload_master_wrong_extension(self, client):
        """잘못된 확장자 업로드"""
        data = {
            'file': (BytesIO(b"test"), 'test.txt')
        }
        response = client.post(
            '/api/uploadMaster',
            data=data,
            content_type='multipart/form-data'
        )
        assert response.status_code == 400
        response_data = json.loads(response.data)
        assert response_data["Success"] is False

    def test_upload_order_without_master(self, client):
        """마스터 없이 주문 업로드"""
        data = {
            'file': (BytesIO(b"test,data"), 'order.csv')
        }
        response = client.post(
            '/api/uploadOrder',
            data=data,
            content_type='multipart/form-data'
        )
        assert response.status_code == 400
        response_data = json.loads(response.data)
        assert "마스터" in response_data["Reason"]


class TestAPIResponse:
    """API 응답 형식 테스트"""

    def test_success_response_format(self, client):
        """성공 응답 형식 확인"""
        response = client.get('/api/getMasterStatus')
        data = json.loads(response.data)

        assert "Success" in data
        assert data["Success"] is True
        assert isinstance(data, dict)

    def test_error_response_format(self, client):
        """에러 응답 형식 확인"""
        response = client.post('/api/uploadMaster')
        data = json.loads(response.data)

        assert "Success" in data
        assert data["Success"] is False
        assert "Reason" in data
        assert isinstance(data["Reason"], str)
