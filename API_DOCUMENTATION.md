# API 문서

## 개요

3D Bin Packing 시뮬레이션 REST API

**Base URL**: `http://localhost:5050`

**응답 형식**: JSON

---

## 인증

현재 버전에서는 인증이 필요하지 않습니다.

---

## 표준 응답 형식

### 성공 응답
```json
{
  "Success": true,
  "message": "작업 완료",
  "data": { ... }
}
```

### 오류 응답
```json
{
  "Success": false,
  "Reason": "오류 메시지",
  "error_code": "ERROR_CODE",
  "details": { ... }
}
```

---

## 엔드포인트

### 1. 마스터 데이터 관리

#### 1.1 마스터 CSV 업로드
```
POST /api/uploadMaster
```

**요청**:
- Content-Type: `multipart/form-data`
- Body: `file` (CSV 파일)

**응답**:
```json
{
  "Success": true,
  "message": "마스터 데이터 100개 항목이 저장되었습니다.",
  "stats": {
    "total_items": 100,
    "categories": {...}
  },
  "total_items": 100
}
```

**오류 코드**:
- `400`: 파일 형식 오류, 파일 크기 초과
- `500`: 서버 내부 오류

---

#### 1.2 마스터 상태 조회
```
GET /api/getMasterStatus
```

**응답**:
```json
{
  "Success": true,
  "has_master": true,
  "stats": {
    "total_items": 100,
    "categories": {
      "과일음료": 20,
      "비타민음료": 30
    }
  }
}
```

---

### 2. 주문 처리

#### 2.1 주문 CSV 업로드
```
POST /api/uploadOrder
```

**요청**:
- Content-Type: `multipart/form-data`
- Body: `file` (CSV 파일)

**응답**:
```json
{
  "Success": true,
  "message": "주문서 처리 완료",
  "session_id": "uuid-string",
  "matched_count": 50,
  "unmatched_count": 2,
  "total_quantity": 100,
  "matched_items": [...],
  "unmatched_items": [...]
}
```

**오류 코드**:
- `400`: 마스터 데이터 없음, 파일 오류
- `500`: 서버 내부 오류

---

#### 2.2 주문 아이템 조회
```
GET /api/getOrderItems?session_id={session_id}
```

**파라미터**:
- `session_id` (required): 세션 ID

**응답**:
```json
{
  "Success": true,
  "items": [...],
  "unmatched_items": [...]
}
```

---

### 3. 패킹 시뮬레이션

#### 3.1 시각화 생성
```
POST /api/visualize
```

**요청 본문**:
```json
{
  "session_id": "uuid-string",
  "box": {
    "name": "Container1",
    "WHD": [589.8, 243.8, 259.1],
    "weight": 28080,
    "coner": 0,
    "openTop": [1],
    "is_pallet": false
  },
  "simulation_params": {
    "bigger_first": true,
    "distribute_items": true,
    "fix_point": true,
    "check_stable": true,
    "support_surface_ratio": 0.75,
    "use_advanced_strategy": false
  }
}
```

**응답**:
```json
{
  "Success": true,
  "images": ["Container1.png"],
  "result": {
    "elapsed_time": 1.23,
    "bins": [...],
    "unfit_items": 5
  },
  "report_id": "uuid-string",
  "detailed_report": {...}
}
```

---

#### 3.2 패킹 계산
```
POST /api/calPacking
```

**요청 본문**:
```json
{
  "session_id": "uuid-string",
  "box": {...},
  "item_counts": {
    "제품1": 10,
    "제품2": 20
  },
  "simulation_params": {...}
}
```

**응답**:
```json
{
  "Success": true,
  "data": {
    "box": [...],
    "fitItem": [...],
    "unfitItem": [...]
  }
}
```

---

### 4. 리포트

#### 4.1 JSON 리포트 다운로드
```
GET /api/report/{session_id}
```

**응답**: JSON 파일 다운로드

---

#### 4.2 HTML 리포트 조회
```
GET /api/reportHTML/{session_id}/{bin_name}
```

**응답**: HTML 페이지

---

#### 4.3 작업 지시서 조회
```
GET /api/workInstruction/{session_id}/{bin_name}
```

**응답**: HTML 작업 지시서

---

#### 4.4 상세 리포트 목록
```
GET /api/getDetailedReport/{session_id}
```

**응답**:
```json
{
  "Success": true,
  "reports": [
    {
      "bin_name": "Container1",
      "html_file": "Container1_report.html",
      "url": "/api/reportHTML/session-id/Container1"
    }
  ]
}
```

---

#### 4.5 이미지 조회
```
GET /api/image/{filename}
```

**파라미터**:
- `filename`: 이미지 파일명 (URL 인코딩 필요)

**응답**: PNG 이미지 파일

---

## Rate Limiting

- **일일 제한**: 200 요청/일
- **시간당 제한**: 50 요청/시간

제한 초과 시 `429 Too Many Requests` 반환

---

## 오류 코드

| 코드 | 의미 |
|------|------|
| 400 | 잘못된 요청 |
| 404 | 리소스를 찾을 수 없음 |
| 405 | 허용되지 않은 HTTP 메서드 |
| 413 | 파일 크기 초과 |
| 422 | 유효성 검증 실패 |
| 429 | Rate Limit 초과 |
| 500 | 서버 내부 오류 |

---

## 예제

### Python 예제
```python
import requests

# 마스터 업로드
with open('master.csv', 'rb') as f:
    files = {'file': f}
    response = requests.post(
        'http://localhost:5050/api/uploadMaster',
        files=files
    )
    print(response.json())

# 주문 업로드
with open('order.csv', 'rb') as f:
    files = {'file': f}
    response = requests.post(
        'http://localhost:5050/api/uploadOrder',
        files=files
    )
    data = response.json()
    session_id = data['session_id']

# 시각화 생성
payload = {
    "session_id": session_id,
    "box": {
        "name": "Container1",
        "WHD": [589.8, 243.8, 259.1],
        "weight": 28080
    }
}
response = requests.post(
    'http://localhost:5050/api/visualize',
    json=payload
)
print(response.json())
```

### cURL 예제
```bash
# 마스터 업로드
curl -X POST http://localhost:5050/api/uploadMaster \
  -F "file=@master.csv"

# 마스터 상태 조회
curl http://localhost:5050/api/getMasterStatus
```

---

## 변경 로그

### v2.0.0 (2025-01-XX)
- ✅ 보안 강화 (eval() 제거, CSV injection 방어)
- ✅ 로깅 시스템 추가
- ✅ Rate Limiting 추가
- ✅ 표준화된 API 응답 형식
- ✅ 파일 검증 강화
- ✅ 보안 헤더 추가
