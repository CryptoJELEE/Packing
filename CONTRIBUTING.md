# 개발 가이드

## 개발 환경 설정

### 1. 저장소 클론
```bash
git clone <repository-url>
cd Packing
```

### 2. 가상 환경 생성
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

### 3. 의존성 설치
```bash
# 프로덕션 의존성
pip install -r requirements.txt

# 개발 의존성 (테스트, 린팅 등)
pip install -r requirements-dev.txt
```

### 4. 환경 변수 설정
```bash
cp .env.example .env
# .env 파일 수정
```

필수 환경 변수:
- `SECRET_KEY`: Flask 시크릿 키
- `SUPABASE_URL`: Supabase 프로젝트 URL (선택)
- `SUPABASE_KEY`: Supabase API 키 (선택)
- `FLASK_ENV`: development / production

---

## 코드 스타일

### Python 스타일 가이드
- **PEP 8** 준수
- **Black** 포맷터 사용
- 최대 줄 길이: 100자

### 포맷팅
```bash
# Black으로 자동 포맷팅
black .

# Flake8으로 린팅
flake8 .

# MyPy로 타입 체크
mypy api.py core/
```

---

## 테스트

### 테스트 실행
```bash
# 전체 테스트
pytest

# 특정 파일
pytest tests/test_api.py

# 커버리지 포함
pytest --cov=core --cov=api

# 상세 출력
pytest -v
```

### 테스트 작성 가이드
1. `tests/` 디렉토리에 작성
2. 파일명: `test_*.py`
3. 클래스명: `Test*`
4. 함수명: `test_*`

예제:
```python
def test_example():
    """테스트 설명"""
    assert 1 + 1 == 2
```

---

## Git 워크플로우

### 브랜치 전략
- `main`: 프로덕션 코드
- `develop`: 개발 브랜치
- `feature/*`: 기능 개발
- `bugfix/*`: 버그 수정
- `hotfix/*`: 긴급 수정

### 커밋 메시지 규칙
```
<타입>: <제목>

<본문>

<푸터>
```

타입:
- `feat`: 새로운 기능
- `fix`: 버그 수정
- `docs`: 문서 수정
- `style`: 코드 포맷팅
- `refactor`: 리팩토링
- `test`: 테스트 추가/수정
- `chore`: 빌드, 설정 등

예제:
```
feat: CSV 파일 검증 기능 추가

- MIME 타입 검증
- 파일 크기 제한
- CSV injection 방어

Closes #123
```

---

## 개발 서버 실행

### 로컬 개발
```bash
# Flask 개발 서버
python api.py

# 또는
flask run --debug
```

### 프로덕션 (Gunicorn)
```bash
gunicorn api:app --bind 0.0.0.0:5050 --workers 2
```

---

## 디렉토리 구조

```
Packing/
├── api.py              # Flask 앱 메인 파일
├── config/             # 설정
│   └── settings.py
├── core/               # 핵심 비즈니스 로직
│   ├── data/          # 데이터 처리
│   ├── packing/       # 패킹 알고리즘
│   ├── storage/       # 저장소
│   └── utils/         # 유틸리티
├── py3dbp/            # 3D 패킹 라이브러리
├── templates/         # HTML 템플릿
├── static/            # 정적 파일
├── tests/             # 테스트
├── logs/              # 로그 파일
├── uploads/           # 업로드 파일
└── output/            # 출력 파일
```

---

## 보안 체크리스트

개발 시 확인 사항:
- [ ] 사용자 입력 검증
- [ ] SQL Injection 방지
- [ ] XSS 방지
- [ ] CSRF 방지
- [ ] 민감 정보 로깅 금지
- [ ] 환경 변수 사용 (하드코딩 금지)
- [ ] HTTPS 사용 (프로덕션)
- [ ] Rate Limiting 설정

---

## 디버깅

### 로그 확인
```bash
# 개발 환경 로그
tail -f logs/development.log

# 프로덕션 로그
tail -f logs/production.log
```

### 디버거 사용
```python
import pdb; pdb.set_trace()
```

---

## 배포

### 프로덕션 체크리스트
- [ ] `FLASK_ENV=production` 설정
- [ ] `SECRET_KEY` 설정 확인
- [ ] `DEBUG=False` 확인
- [ ] 모든 테스트 통과
- [ ] 보안 헤더 확인
- [ ] HTTPS 설정
- [ ] 데이터베이스 백업

### Heroku 배포
```bash
git push heroku main
```

### Render 배포
1. GitHub 연동
2. 환경 변수 설정
3. 자동 배포

---

## 도움말

- 이슈 등록: GitHub Issues
- 질문: Discussions
- 보안 취약점: security@example.com (비공개)

---

## 라이선스

MIT License
