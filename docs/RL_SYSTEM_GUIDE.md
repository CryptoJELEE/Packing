# RL 시스템 가이드

## 개요

이 시스템은 강화학습(RL)과 기존 규칙 기반 알고리즘을 결합하여 3D 적재 최적화를 수행합니다.

## 시스템 구성

### 1. 알고리즘 모드

사용자는 3가지 알고리즘 모드 중 선택할 수 있습니다:

#### 📦 기존 알고리즘 (Baseline)
- **설명**: 검증된 규칙 기반 적재 알고리즘
- **장점**: 안정적이고 예측 가능한 결과
- **권장**: 프로덕션 환경, 중요한 작업

#### 🤖 AI 하이브리드 (Hybrid) - **권장**
- **설명**: 기존 알고리즘과 AI 모델을 확률적으로 혼합
- **동작**: 50% 확률로 RL, 50% 확률로 baseline 사용
- **장점**: 안정성 유지하면서 AI 성능 테스트
- **권장**: 대부분의 사용 케이스

#### 🚀 AI 전용 (RL)
- **설명**: 학습된 AI 모델만 사용
- **장점**: 최신 AI 기술 활용
- **주의**: 실험적, 모델이 없으면 baseline으로 fallback
- **권장**: 테스트 및 실험 목적

### 2. RL 모델

현재 사용 중인 모델: **Simple Packing Model**

- **프레임워크**: scikit-learn (RandomForest)
- **학습 방식**: Imitation Learning (기존 알고리즘 모방)
- **학습 데이터**: 50 케이스, 1,110 transitions
- **성능**:
  - 회전 예측 정확도: **100%**
  - 위치 예측 오차: **24.81cm** (평균)
  - R² Score: **0.77**

### 3. 아키텍처

```
┌─────────────────┐
│   Frontend UI   │
│  (알고리즘 선택)  │
└────────┬────────┘
         │
┌────────▼─────────────────────┐
│     Flask API Server         │
│  /api/visualize (mode param) │
└────────┬─────────────────────┘
         │
┌────────▼────────────────────┐
│   Model Server (Hybrid)     │
│  - RLModelServer            │
│  - HybridModelServer        │
└────┬────────────────┬───────┘
     │                │
┌────▼─────┐    ┌────▼─────┐
│   RL     │    │ Baseline │
│  Model   │    │Algorithm │
└──────────┘    └──────────┘
```

## 사용 방법

### 웹 UI 사용

1. Flask 서버 시작:
   ```bash
   python api.py
   ```

2. 브라우저에서 `http://localhost:5050` 접속

3. **시뮬레이션 설정** 섹션에서 알고리즘 선택:
   - 기존 알고리즘 (안정)
   - AI 하이브리드 (실험) 🤖 ← **권장**
   - AI 전용 (고급) 🚀

4. 시뮬레이션 실행

5. 결과 화면 상단에서 **사용된 알고리즘** 확인

### API 사용

#### 1. RL 모드로 시뮬레이션

```bash
curl -X POST "http://localhost:5050/api/visualize" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "test_001",
    "box": {"WHD": [400, 200, 200], "weight": 1000},
    "item_counts": {"Box1": 5, "Box2": 3},
    "simulation_params": {...},
    "mode": "hybrid"
  }'
```

#### 2. RL 상태 확인

```bash
curl http://localhost:5050/api/rl/status
```

응답:
```json
{
  "model_loaded": true,
  "available_modes": ["baseline", "rl"],
  "model_metadata": {
    "type": "simple_packing_model",
    "framework": "scikit-learn"
  }
}
```

#### 3. 통계 조회

```bash
curl http://localhost:5050/api/rl/stats
```

#### 4. 휴먼 피드백 저장

```bash
curl -X POST "http://localhost:5050/api/rl/feedback" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "test_001",
    "algorithm": "hybrid",
    "scores": {
      "overall": 4,
      "stability": 5,
      "workability": 4,
      "efficiency": 3
    },
    "comments": "Good result",
    "worker_id": "worker_001"
  }'
```

## 학습 및 개선

### 1. 학습 데이터 생성

기존 알고리즘으로 전문가(expert) 데이터를 생성합니다:

```bash
python scripts/generate_training_data.py \
  --cases 100 \
  --complexity mixed \
  --output core/rl/data/training_data.pkl
```

옵션:
- `--cases`: 생성할 케이스 수 (기본: 100)
- `--complexity`: simple/medium/hard/mixed
- `--seed`: 랜덤 시드

### 2. 모델 학습

생성된 데이터로 모델을 학습합니다:

```bash
python scripts/train_simple_model.py \
  --data core/rl/data/training_data.pkl \
  --output core/rl/models/simple_packing_model.pkl
```

학습 과정:
1. 데이터셋 로드 (transitions)
2. State에서 특징 추출
3. Position 예측 모델 학습 (회귀)
4. Rotation 예측 모델 학습 (분류)
5. 모델 저장

### 3. 모델 배포

학습된 모델은 Flask 서버 시작 시 자동으로 로드됩니다:

- 기본 경로: `core/rl/models/simple_packing_model.pkl`
- 환경 변수: `RL_MODEL_PATH`로 커스텀 경로 지정 가능

```bash
export RL_MODEL_PATH=/path/to/your/model.pkl
python api.py
```

## A/B 테스트

### 목적

- RL 모델 vs Baseline 알고리즘 성능 비교
- 실사용 환경에서 데이터 수집
- 모델 개선 방향 결정

### 테스트 설계

#### 1. 메트릭

**자동 수집 메트릭** (시스템 자동 계산):
- 공간 활용률 (Space Utilization)
- 무게 활용률 (Weight Utilization)
- 적재 성공률 (Packing Rate)
- 실행 시간

**휴먼 피드백 메트릭** (작업자 평가):
- 전체 만족도 (1-5점)
- 안정성 (1-5점)
- 작업 용이성 (1-5점)
- 효율성 (1-5점)

#### 2. 실험 그룹

- **Control Group**: Baseline 알고리즘만 사용
- **Treatment Group**: Hybrid 또는 RL 모드 사용

#### 3. 데이터 수집

모든 시뮬레이션 결과는 자동으로 저장됩니다:
- `/api/rl/stats`: 실시간 통계 확인
- 피드백 데이터: SQLite 또는 Supabase에 저장

#### 4. 분석

```bash
# 통계 조회
curl http://localhost:5050/api/rl/stats | python3 -m json.tool

# 피드백 리스트
curl http://localhost:5050/api/rl/feedback/list | python3 -m json.tool
```

결과 분석 항목:
- 평균 공간 활용률 차이
- 평균 휴먼 피드백 점수 차이
- 통계적 유의성 검정 (t-test)

### 테스트 실행 가이드

#### Phase 1: Baseline 수집 (1-2주)
```
- 모든 사용자 "기존 알고리즘" 사용
- 100+ 케이스 데이터 수집
- Baseline 성능 확립
```

#### Phase 2: Hybrid 테스트 (2-4주)
```
- 50% 사용자 "AI 하이브리드" 사용
- 데이터 비교 분석
- 문제점 파악 및 개선
```

#### Phase 3: RL 전용 테스트 (2-4주)
```
- 일부 사용자 "AI 전용" 사용
- 최종 성능 비교
- 프로덕션 배포 결정
```

## 모델 개선 로드맵

### 단기 (1-2개월)
- [x] 기본 RL 인프라 구축
- [x] Simple 모델 학습 및 배포
- [ ] 100+ 케이스 학습 데이터 생성
- [ ] 모델 정확도 85%+ 달성

### 중기 (3-6개월)
- [ ] PyTorch 기반 딥러닝 모델 도입
- [ ] 실시간 학습(online learning) 구현
- [ ] 피드백 기반 자동 재학습
- [ ] 다양한 컨테이너 타입 지원

### 장기 (6-12개월)
- [ ] 멀티모달 학습 (이미지 + 수치 데이터)
- [ ] 강화학습(PPO, DQN) 본격 적용
- [ ] 클라우드 기반 대규모 학습
- [ ] 실시간 추천 시스템

## 트러블슈팅

### 모델이 로드되지 않음

```bash
# 모델 파일 확인
ls -lh core/rl/models/

# 모델이 없으면 학습 실행
python scripts/train_simple_model.py
```

### RL 모드가 항상 baseline으로 동작

- Hybrid 모드는 확률적으로 동작합니다 (50% RL, 50% baseline)
- RL 전용 모드 사용: UI에서 "AI 전용" 선택

### 예측 오류 발생

- Fallback이 자동으로 작동하여 baseline 알고리즘 사용
- 로그에서 오류 확인: `tail -f /tmp/flask_server.log`

## 참고 자료

### 관련 파일
- `core/rl/simple_model.py`: ML 모델 구현
- `core/rl/model_server.py`: 모델 서빙
- `core/api/rl_routes.py`: RL API 엔드포인트
- `scripts/generate_training_data.py`: 데이터 생성
- `scripts/train_simple_model.py`: 모델 학습

### API 문서
- `/api/rl/status`: 모델 상태
- `/api/rl/pack`: RL 예측 (테스트용)
- `/api/rl/feedback`: 피드백 저장
- `/api/rl/stats`: 통계 조회
- `/api/visualize?mode=hybrid`: 시뮬레이션 실행

### 환경 변수
- `RL_MODEL_PATH`: 모델 파일 경로
- `RL_PROBABILITY`: Hybrid 모드 RL 확률 (기본: 0.5)
- `RL_THRESHOLD`: 성능 임계값 (기본: 0.6)

## 라이센스

이 프로젝트는 내부 연구 및 개발 목적으로 사용됩니다.
