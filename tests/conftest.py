"""
Pytest 설정 및 Fixture
"""
import pytest
import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


@pytest.fixture
def app():
    """Flask 앱 fixture"""
    from api import app as flask_app
    from config.settings import TestingConfig

    flask_app.config.from_object(TestingConfig)
    TestingConfig.init_app(flask_app)

    yield flask_app


@pytest.fixture
def client(app):
    """Flask 테스트 클라이언트"""
    return app.test_client()


@pytest.fixture
def sample_csv_data():
    """샘플 CSV 데이터"""
    return """분류,제품번호,제품명,규격,적재패턴,박스단위,파렛트단위,포장,가로,세로,높이,박스무게,적재방향제한,파손취약성
과일음료,P001,오렌지주스,1L,기본,10,100,박스,100,100,200,5,변경 불가,보통
비타민음료,P002,비타민워터,500ml,기본,20,200,박스,80,80,150,3,변경 불가,보통"""


@pytest.fixture
def sample_order_data():
    """샘플 주문 데이터"""
    return """제품번호,수량
P001,10
P002,20"""
