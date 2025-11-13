# 합성 데이터 기반 RL 학습 가이드

## 개요

실제 적재 데이터가 없는 초기 단계에서 강화학습 모델을 학습시키기 위한 합성 데이터 생성 시스템입니다.

## 시스템 구조

```
합성 데이터 생성
    ↓
기존 알고리즘으로 시뮬레이션
    ↓
RL 형식으로 변환 (State-Action-Reward)
    ↓
Imitation Learning (모방 학습)
    ↓
RL Fine-tuning
    ↓
실제 환경 적용 + 휴먼 피드백
```

## 주요 모듈

### 1. `core/rl/data_generator.py`

다양한 적재 케이스를 자동으로 생성하고 시뮬레이션합니다.

**주요 클래스:**
- `PackingCaseGenerator`: 합성 케이스 생성
  - 다양한 컨테이너 타입 (20ft, 40ft, 등)
  - 다양한 박스 크기 프로필 (small, medium, large, mixed)
  - 난이도 조절 (easy, medium, hard)

- `SyntheticDataGenerator`: 시뮬레이션 실행
  - py3dbp 알고리즘 사용
  - 적재 결과 수집
  - 성능 메트릭 계산

- `ExperienceReplayBuffer`: 경험 저장
  - State-Action-Reward 저장
  - 랜덤 샘플링
  - 파일 저장/로드

### 2. `core/rl/data_converter.py`

시뮬레이션 결과를 RL 학습 데이터로 변환합니다.

**주요 클래스:**
- `SimulationToRLConverter`: 데이터 변환
  - 월드 좌표 → 그리드 좌표
  - 적재 순서 → Action sequence
  - 성능 → Reward 계산

- `ImitationLearningDataset`: 학습 데이터셋
  - State-Action 쌍 관리
  - 성공 에피소드 필터링
  - 통계 계산
  - 저장/로드

### 3. `examples/train_with_synthetic_data.py`

전체 학습 파이프라인 통합 스크립트

**4단계 프로세스:**
1. 합성 데이터 생성
2. RL 형식 변환
3. Imitation Learning
4. 평가 및 비교

## 사용 방법

### 빠른 테스트 (의존성 최소)

```bash
# py3dbp만 있으면 실행 가능
python examples/quick_test_synthetic_data.py
```

이 스크립트는:
- ✅ 케이스 생성 테스트
- ✅ 시뮬레이션 테스트
- ✅ 데이터 변환 테스트
- ✅ 전체 파이프라인 검증

### 전체 학습 파이프라인

```bash
# 1. RL 의존성 설치 (필요시)
pip install gymnasium stable-baselines3 torch scipy

# 2. 학습 실행
python examples/train_with_synthetic_data.py \
    --num-cases 100 \
    --num-epochs 10 \
    --eval-episodes 10 \
    --seed 42

# 3. 기존 데이터로 학습 (재실행시)
python examples/train_with_synthetic_data.py \
    --skip-generation \
    --num-epochs 20
```

**파라미터:**
- `--num-cases`: 생성할 합성 케이스 개수 (기본: 100)
- `--num-epochs`: 학습 에폭 수 (기본: 10)
- `--eval-episodes`: 평가 에피소드 수 (기본: 10)
- `--seed`: 랜덤 시드 (기본: 42)
- `--skip-generation`: 데이터 생성 건너뛰기

## 생성 데이터 예시

### 케이스 타입

1. **Easy (쉬움)**
   - 아이템: 5-15개
   - 공간 활용: 30-50%
   - 목적: 기본 학습

2. **Medium (중간)**
   - 아이템: 15-30개
   - 공간 활용: 60-80%
   - 목적: 실전 수준 학습

3. **Hard (어려움)**
   - 아이템: 30-50개
   - 공간 활용: 80-100%+
   - 목적: 최적화 능력 향상

### 컨테이너 타입

```python
CONTAINER_TYPES = {
    'standard_20ft': (589.8, 243.8, 259.1),
    'standard_40ft': (1203.2, 243.8, 259.1),
    'high_cube_40ft': (1203.2, 243.8, 289.6),
    'small': (400.0, 200.0, 200.0),
    'medium': (800.0, 300.0, 250.0),
}
```

### 박스 프로필

```python
BOX_SIZE_PROFILES = {
    'small_boxes': (20-50cm, 1-10kg),
    'medium_boxes': (40-100cm, 10-50kg),
    'large_boxes': (80-150cm, 50-150kg),
    'mixed': (20-150cm, 1-150kg)  # 혼합
}
```

## 데이터 출력 구조

### 1. 시뮬레이션 결과 (JSON)

```json
{
  "case_id": "case_20250112_143022_123456",
  "metadata": {
    "box_profile": "mixed",
    "complexity": "medium",
    "num_items": 25
  },
  "packed_items": [
    {
      "name": "Item_001",
      "position": [10.0, 10.0, 0.0],
      "rotation_type": 0,
      "dimensions": [50.0, 50.0, 50.0],
      "weight": 10.0
    }
  ],
  "metrics": {
    "space_utilization": 0.65,
    "packing_rate": 0.92,
    "num_packed": 23,
    "num_unpacked": 2
  }
}
```

### 2. RL 데이터셋 (Pickle)

```python
{
    'states': np.ndarray,        # (N, grid_w, grid_h, grid_d)
    'actions': List[Dict],       # [{'item_index': 0, 'position': [...], 'rotation': 0}, ...]
    'rewards': np.ndarray,       # (N,)
    'next_states': np.ndarray,   # (N, grid_w, grid_h, grid_d)
    'dones': np.ndarray,         # (N,) bool
    'infos': List[Dict],         # Additional info
    'metadata': {
        'num_episodes': 100,
        'num_transitions': 2341,
        'avg_reward': 15.6
    }
}
```

## 학습 전략

### Phase 1: Imitation Learning (모방 학습)

기존 py3dbp 알고리즘의 행동을 모방합니다.

**목표:**
- 기본적인 적재 패턴 학습
- 물리적 제약 조건 이해
- 초기 정책 형성

**방법:**
- Behavioral Cloning
- Supervised Learning
- Expert demonstrations

### Phase 2: RL Fine-tuning

Imitation으로 학습한 모델을 RL로 개선합니다.

**목표:**
- 기존 알고리즘보다 나은 성능
- 복잡한 케이스 최적화
- 보상 함수 최적화

**방법:**
- PPO (Proximal Policy Optimization)
- 보상 셰이핑 (Reward Shaping)
- 커리큘럼 학습 (Curriculum Learning)

### Phase 3: Human Feedback Integration

실제 현장 피드백을 반영합니다.

**목표:**
- 작업자 선호도 반영
- 실제 환경 적응
- 지속적 개선

**방법:**
- RLHF (Reinforcement Learning from Human Feedback)
- Preference Learning
- A/B Testing

## 성능 메트릭

### 학습 중 추적 메트릭

1. **공간 활용률** (Space Utilization)
   ```python
   packed_volume / total_volume
   ```

2. **적재율** (Packing Rate)
   ```python
   packed_items / total_items
   ```

3. **안정성** (Stability)
   ```python
   - 무게 중심 위치
   - 지지면 비율
   - 높이 분포
   ```

4. **효율성** (Efficiency)
   ```python
   - 배치 시간
   - 불필요한 회전 횟수
   ```

### 평가 메트릭

```python
{
    'mean_reward': float,
    'mean_space_utilization': float,
    'mean_stability': float,
    'success_rate': float,
    'avg_packed_items': float
}
```

## 파일 구조

```
data/
├── synthetic/                    # 합성 데이터
│   ├── training_cases_*.json     # 시뮬레이션 결과
│   └── summary_*.json            # 통계 요약
│
├── rl_dataset/                   # RL 학습 데이터
│   └── imitation_dataset.pkl     # 변환된 데이터셋
│
models/
├── imitation/                    # Imitation Learning 모델
│   ├── best_model.zip            # 최적 모델
│   ├── checkpoints/              # 체크포인트
│   └── training_history.json    # 학습 기록
│
└── rl/                          # RL Fine-tuned 모델
    └── ...
```

## 예상 결과

### 초기 Imitation Learning

- **공간 활용률**: 55-65% (기존 알고리즘 수준)
- **학습 시간**: 10-30분 (100 케이스 기준)
- **성공률**: 80-90%

### RL Fine-tuning 후

- **공간 활용률**: 60-70% (+5-10% 개선)
- **학습 시간**: 1-3시간
- **성공률**: 85-95%

### Human Feedback 후

- **공간 활용률**: 65-75%
- **작업성 점수**: 4.0+/5.0
- **안정성 점수**: 4.5+/5.0

## 문제 해결

### 1. 메모리 부족

```python
# 배치 크기 줄이기
--num-cases 50  # 기본 100에서 줄임

# 그리드 해상도 낮추기
grid_resolution=8  # 기본 10에서 줄임
```

### 2. 학습이 느림

```python
# GPU 사용 (PyTorch)
device = 'cuda' if torch.cuda.is_available() else 'cpu'

# 병렬 환경
n_envs = 4  # 4개 환경 동시 실행
```

### 3. 수렴하지 않음

```python
# 학습률 조정
learning_rate = 1e-4  # 기본 3e-4에서 낮춤

# 커리큘럼 학습
# Easy → Medium → Hard 순으로 학습
```

## 다음 단계

1. **데이터 생성 확장**
   - 더 많은 케이스 생성 (1000+)
   - 실제 고객 데이터 프로필 반영
   - 특수 케이스 추가 (깨지기 쉬운 물품 등)

2. **학습 개선**
   - Curriculum Learning 구현
   - Multi-task Learning (다양한 컨테이너)
   - Transfer Learning (20ft → 40ft)

3. **실전 배포**
   - A/B 테스트 프레임워크
   - 점진적 롤아웃 (10% → 50% → 100%)
   - 모니터링 대시보드

4. **휴먼 피드백**
   - 피드백 UI 구현
   - 피드백 수집 자동화
   - 선호도 학습 통합

## 참고 자료

- **RL 환경**: `docs/RL_ARCHITECTURE.md`
- **기본 예제**: `examples/rl_basic_example.py`
- **API 문서**: `docs/API_DOCUMENTATION.md`
- **변경 로그**: `CHANGELOG.md`
