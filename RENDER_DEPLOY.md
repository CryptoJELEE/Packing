# Render.com 배포 가이드

## 배포 전 준비사항

### 1. GitHub에 코드 푸시
```bash
git add .
git commit -m "Prepare for Render deployment"
git push origin main
```

### 2. Render.com 가입 및 로그인
- https://render.com 에서 가입
- GitHub 계정으로 연동

## 배포 단계

### 1. 새 Web Service 생성
1. Render 대시보드에서 **New +** 클릭
2. **Web Service** 선택
3. GitHub 저장소 연결 및 선택

### 2. 서비스 설정

#### 기본 설정
- **Name**: `3d-bin-packing` (원하는 이름)
- **Region**: `Singapore` (가장 가까운 지역 선택)
- **Branch**: `main` (또는 배포할 브랜치)
- **Root Directory**: `.` (루트 디렉토리)

#### Build & Deploy 설정
- **Environment**: `Python 3`
- **Build Command**: 
  ```bash
  pip install -r requirements.txt
  ```
- **Start Command**: 
  ```bash
  gunicorn api:app --bind 0.0.0.0:$PORT --workers 2 --timeout 120
  ```
  (또는 Procfile이 자동으로 인식됨)

### 3. 환경 변수 설정

**Environment Variables** 섹션에서 다음 변수들을 추가:

| Key | Value |
|-----|-------|
| `SUPABASE_URL` | `https://cwmrqvsqcmhifzvuoifc.supabase.co` |
| `SUPABASE_KEY` | `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImN3bXJxdnNxY21oaWZ6dnVvaWZjIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjI4MTgxMTUsImV4cCI6MjA3ODM5NDExNX0.6E7wP3PSffPC_gUtg3jO5ZJWYJQMOPvVTzKBjJ6c6iA` |
| `FLASK_DEBUG` | `False` |
| `PORT` | (자동 설정됨, 추가 불필요) |

### 4. 고급 설정 (선택사항)

#### Health Check
- **Health Check Path**: `/` (또는 `/api/getMasterStatus`)

#### Auto-Deploy
- **Auto-Deploy**: `Yes` (GitHub 푸시 시 자동 배포)

### 5. 배포 시작
- **Create Web Service** 클릭
- 빌드 및 배포 진행 (약 5-10분 소요)

## 배포 후 확인

1. **서비스 URL 확인**
   - Render 대시보드에서 제공되는 URL (예: `https://3d-bin-packing.onrender.com`)

2. **서비스 테스트**
   - 브라우저에서 URL 접속
   - API 엔드포인트 테스트: `https://your-app.onrender.com/api/getMasterStatus`

3. **로그 확인**
   - Render 대시보드의 **Logs** 탭에서 실시간 로그 확인

## 문제 해결

### 빌드 실패
- **requirements.txt 확인**: 모든 패키지가 올바른지 확인
- **Python 버전**: runtime.txt의 버전이 Render에서 지원하는지 확인
- **로그 확인**: 빌드 로그에서 오류 메시지 확인

### 서비스 시작 실패
- **Procfile 확인**: Start Command가 올바른지 확인
- **포트 확인**: `$PORT` 환경 변수 사용 확인
- **의존성 확인**: 모든 Python 패키지가 설치되었는지 확인

### Supabase 연결 실패
- **환경 변수 확인**: SUPABASE_URL과 SUPABASE_KEY가 올바르게 설정되었는지 확인
- **Supabase 대시보드**: 테이블이 생성되었는지 확인
- **네트워크**: Render에서 Supabase로의 네트워크 연결 확인

## 무료 플랜 제한사항

- **서비스 중지**: 15분 동안 요청이 없으면 서비스가 자동으로 중지됨
- **첫 요청 지연**: 중지된 서비스는 첫 요청 시 약 30초 정도 지연될 수 있음
- **월 사용량**: 무료 플랜은 월 750시간 제한

## 업데이트 배포

코드를 수정한 후:
```bash
git add .
git commit -m "Update code"
git push origin main
```

Render는 자동으로 감지하고 재배포합니다 (Auto-Deploy가 활성화된 경우).

## 참고사항

- **파일 저장**: `uploads/`, `output/` 폴더는 임시이므로 Supabase Storage 사용 권장
- **데이터베이스**: Supabase PostgreSQL 사용 중
- **세션**: Supabase sessions 테이블에 저장됨
- **마스터 데이터**: Supabase master_items 테이블에 저장됨

