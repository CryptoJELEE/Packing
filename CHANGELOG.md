# 변경 로그

모든 주목할 만한 변경 사항이 이 파일에 문서화됩니다.

## [2.0.0] - 2025-01-XX

### 🔒 보안 개선
- **[CRITICAL]** eval() 함수 제거 및 json.loads() 사용으로 코드 인젝션 방지
- **[CRITICAL]** SECRET_KEY 필수화 및 환경별 검증 강화
- CSV Injection 방어 메커니즘 추가
- 파일 업로드 검증 강화 (MIME 타입, 파일 크기, 내용 검증)
- 보안 헤더 추가 (CSP, X-Frame-Options, HSTS 등)
- Rate Limiting 추가 (200/day, 50/hour)

### ✨ 새로운 기능
- 체계적인 로깅 시스템 (파일 + 콘솔 로깅)
- 표준화된 API 응답 형식
- 환경별 설정 분리 (Development, Production, Testing)
- 전역 에러 핸들러
- 파일 검증 유틸리티 (FileValidator, CSVSanitizer)

### 🏗️ 구조 개선
- 유틸리티 모듈 추가 (core/utils/)
  - logger.py: 로깅 설정
  - validators.py: 파일 및 데이터 검증
  - response.py: API 응답 표준화
  - security.py: 보안 헤더 및 Rate Limiting
- 환경별 설정 클래스 (DevelopmentConfig, ProductionConfig, TestingConfig)

### 🧪 테스트
- pytest 기반 테스트 프레임워크 추가
- 단위 테스트 작성 (validators, config, API)
- pytest.ini, .flake8 설정 파일 추가

### 📝 문서화
- API 문서 작성 (API_DOCUMENTATION.md)
- 변경 로그 추가 (CHANGELOG.md)
- 개발 가이드 추가 (CONTRIBUTING.md)
- requirements-dev.txt 분리

### 🔧 의존성
- flask-limiter 추가 (Rate Limiting)
- 버전 범위 명시 (상한선 지정)
- 개발 의존성 분리 (pytest, black, flake8, mypy)

### 🐛 버그 수정
- Bare except 제거 및 구체적 예외 처리
- API 응답 불일치 문제 해결
- 파일 경로 처리 개선

### ⚠️ Breaking Changes
- API 응답 형식 변경 (일부 엔드포인트)
- SECRET_KEY 환경 변수 필수화 (프로덕션)
- Config 클래스 구조 변경

### 🔄 마이그레이션 가이드

#### 환경 변수 설정
```bash
# .env 파일에 추가
SECRET_KEY=your-secret-key-here
FLASK_ENV=development  # or production
```

#### SECRET_KEY 생성
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

#### 의존성 업데이트
```bash
pip install -r requirements.txt
# 개발 환경
pip install -r requirements-dev.txt
```

---

## [1.0.0] - 이전 버전

### 기본 기능
- 3D Bin Packing 알고리즘
- CSV 파일 업로드 및 처리
- 시각화 생성
- 리포트 생성
- Supabase 통합
