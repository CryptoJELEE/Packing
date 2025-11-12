# 강화학습 기반 적재 최적화 시스템 아키텍처

## 개요

기존 규칙 기반 3D Bin Packing 알고리즘을 강화학습(RL)과 휴먼 피드백(RLHF)을 통해 고도화하는 시스템 설계 문서.

---

## 시스템 구조

```
┌─────────────────────────────────────────────────────────────┐
│                    Frontend / UI Layer                       │
│  - 작업자 피드백 인터페이스                                   │
│  - 적재 결과 시각화 및 평가                                   │
└─────────────────────────────────────────────────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    API / Service Layer                       │
│  - /api/rl/predict      : RL 모델 추론                       │
│  - /api/rl/feedback     : 휴먼 피드백 수집                   │
│  - /api/rl/compare      : 알고리즘 비교 (Rule vs RL)         │
└─────────────────────────────────────────────────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    RL Agent Layer                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  PPO Agent   │  │  DQN Agent   │  │  A3C Agent   │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│  - Policy Network (적재 순서/위치 결정)                      │
│  - Value Network (상태 가치 평가)                            │
└─────────────────────────────────────────────────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Environment Layer                         │
│  - PackingEnvironment (Gym Interface)                        │
│  - State: 컨테이너 상태, 남은 아이템, 무게 분포              │
│  - Action: 아이템 선택, 위치, 회전                           │
│  - Reward: 공간활용률, 안정성, 작업시간, 휴먼피드백          │
└─────────────────────────────────────────────────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Core Packing Engine                       │
│  - py3dbp (기존 알고리즘)                                     │
│  - AdvancedPackingStrategy                                   │
│  - 물리 엔진 (중력, 안정성 체크)                              │
└─────────────────────────────────────────────────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Data & Learning Layer                     │
│  - Experience Replay Buffer                                  │
│  - Human Feedback Database                                   │
│  - Training Pipeline                                         │
│  - Model Versioning (MLflow)                                 │
└─────────────────────────────────────────────────────────────┘
```

---

## 핵심 컴포넌트

### 1. PackingEnvironment (Gym 환경)

**State (상태 공간)**:
```python
{
    # 컨테이너 상태
    'container_occupancy': np.array([W, H, D]),  # 3D 점유 그리드
    'current_height_map': np.array([W, D]),      # 높이 맵
    'weight_distribution': np.array([W, D]),     # 무게 분포

    # 아이템 정보
    'remaining_items': List[Item],               # 남은 아이템
    'placed_items_count': int,                   # 배치된 아이템 수
    'item_features': np.array([N, F]),          # 아이템 특징 벡터

    # 물리적 제약
    'total_weight': float,                       # 현재 총 무게
    'center_of_gravity': np.array([3]),         # 무게 중심
    'stability_score': float,                    # 안정성 점수

    # 메타 정보
    'step_count': int,                          # 현재 스텝
    'time_elapsed': float                        # 경과 시간
}
```

**Action (행동 공간)**:
```python
{
    'item_index': int,              # 배치할 아이템 선택 (0 ~ N-1)
    'position': (x, y, z),          # 배치 위치
    'rotation': int,                # 회전 타입 (0-5)
    'placement_strategy': int       # 배치 전략 (바닥우선, 벽붙임 등)
}
```

**Reward (보상 함수)**:
```python
reward = (
    α * space_utilization_reward      # 공간 활용률
    + β * stability_reward            # 안정성 (무게 중심, 지지율)
    + γ * packing_efficiency_reward   # 적재 효율성
    + δ * time_penalty                # 시간 페널티
    + ε * human_feedback_reward       # 휴먼 피드백 (RLHF)
    + ζ * constraint_violation_penalty # 제약 위반 페널티
)
```

---

### 2. RL Agent 아키텍처

#### A. PPO (Proximal Policy Optimization) - 추천
**장점**:
- 안정적인 학습
- 샘플 효율성
- 연속/이산 행동 공간 모두 지원

**네트워크 구조**:
```python
Actor Network (Policy):
  Input: State Features (embedding)
  Hidden: [512, 256, 128]
  Output: Action Probabilities

Value Network:
  Input: State Features
  Hidden: [512, 256, 128]
  Output: State Value
```

#### B. DQN (Deep Q-Network) - 대안
**장점**:
- 구현 단순
- 이산 행동 공간에 효과적

#### C. Multi-Agent System
```python
- Item Selector Agent: 어떤 아이템을 먼저 배치할지
- Position Agent: 어디에 배치할지
- Rotation Agent: 어떻게 회전할지
```

---

### 3. 휴먼 피드백 시스템 (RLHF)

#### A. 피드백 수집 인터페이스

**평가 기준**:
```yaml
작업자 피드백:
  - 전체 만족도: 1-5점
  - 세부 평가:
    - 안정성: 실제 작업 시 안전한가?
    - 작업성: 적재/언로딩이 쉬운가?
    - 공간활용: 공간을 잘 활용했는가?
    - 실용성: 실제 현장에서 실행 가능한가?
  - 개선 제안: 텍스트
```

**피드백 DB 스키마**:
```sql
CREATE TABLE human_feedback (
    id UUID PRIMARY KEY,
    session_id VARCHAR(255),
    packing_result_id VARCHAR(255),

    -- 알고리즘 정보
    algorithm_type VARCHAR(50),  -- 'rule_based', 'rl_model', 'hybrid'
    model_version VARCHAR(50),

    -- 평가 점수
    overall_score INT,           -- 1-5
    stability_score INT,
    workability_score INT,
    space_utilization_score INT,
    practicality_score INT,

    -- 비교 평가
    compared_with VARCHAR(255),  -- 비교 대상 결과 ID
    preference VARCHAR(50),      -- 'this', 'other', 'similar'

    -- 상세 피드백
    comments TEXT,
    improvement_suggestions TEXT,

    -- 작업자 정보
    worker_id VARCHAR(255),
    worker_experience_level VARCHAR(50),

    -- 메타데이터
    created_at TIMESTAMP,
    feedback_duration INT        -- 피드백 소요 시간(초)
);
```

#### B. 피드백 통합 방법

**1. Reward Shaping**:
```python
# 휴먼 피드백을 보상 함수에 반영
def compute_reward_with_feedback(state, action, next_state, feedback=None):
    base_reward = compute_base_reward(state, action, next_state)

    if feedback:
        # 정규화된 피드백 점수 (0-1)
        feedback_score = feedback['overall_score'] / 5.0

        # 가중치 적용
        human_reward = feedback_score * HUMAN_FEEDBACK_WEIGHT

        # 통합
        total_reward = base_reward + human_reward
    else:
        total_reward = base_reward

    return total_reward
```

**2. Preference Learning (Bradley-Terry Model)**:
```python
# 두 결과 비교 시
P(A > B) = σ(r_A - r_B)  # σ는 sigmoid 함수
```

**3. Inverse Reinforcement Learning (IRL)**:
```python
# 전문가(작업자)의 행동에서 보상 함수 학습
```

---

### 4. 학습 파이프라인

```python
┌─────────────┐
│ Data        │
│ Collection  │  → Experience Replay Buffer
└─────────────┘    - (state, action, reward, next_state, done)
                   - Human Feedback
       ↓
┌─────────────┐
│ Offline     │
│ Training    │  → 배치 학습 (야간 실행)
└─────────────┘    - PPO Update
                   - 피드백 통합
       ↓
┌─────────────┐
│ Model       │
│ Evaluation  │  → Validation Set
└─────────────┘    - 공간활용률
                   - 안정성 점수
                   - A/B 테스트
       ↓
┌─────────────┐
│ Model       │
│ Deployment  │  → Model Serving
└─────────────┘    - 버전 관리
                   - Rollback 가능
       ↓
┌─────────────┐
│ Online      │
│ Inference   │  → Production
└─────────────┘    - Real-time 추론
                   - Monitoring
```

---

### 5. 하이브리드 접근법 (추천)

**Phase 1: Rule-Based + RL Co-existence**
```python
def hybrid_packing(items, container):
    # 1. 규칙 기반으로 초기 배치
    rule_based_result = rule_based_packing(items, container)

    # 2. RL 에이전트로 개선
    rl_improved_result = rl_agent.improve(rule_based_result)

    # 3. 비교 및 선택
    if rl_improved_result.score > rule_based_result.score * 1.1:
        return rl_improved_result
    else:
        return rule_based_result
```

**Phase 2: RL-First with Rule Fallback**
```python
def rl_first_packing(items, container):
    try:
        result = rl_agent.pack(items, container)

        # 제약 조건 검증
        if validate_constraints(result):
            return result
        else:
            # 실패 시 규칙 기반으로 fallback
            return rule_based_packing(items, container)
    except Exception as e:
        logger.error(f"RL packing failed: {e}")
        return rule_based_packing(items, container)
```

---

### 6. 성능 메트릭

```python
metrics = {
    # 기본 메트릭
    'space_utilization': float,      # 공간 활용률 (%)
    'weight_utilization': float,     # 무게 활용률 (%)
    'item_fit_rate': float,          # 적재 성공률 (%)

    # 안정성 메트릭
    'stability_score': float,        # 안정성 점수 (0-1)
    'center_of_gravity_offset': float, # 무게중심 편차
    'support_ratio': float,          # 평균 지지율

    # 효율성 메트릭
    'packing_time': float,           # 계산 시간 (초)
    'steps_to_complete': int,        # 완료까지 스텝 수

    # 비즈니스 메트릭
    'container_count': int,          # 필요한 컨테이너 수
    'cost_savings': float,           # 비용 절감액
    'loading_time_estimate': float,  # 예상 작업 시간

    # RL 학습 메트릭
    'episode_reward': float,
    'policy_loss': float,
    'value_loss': float,
    'human_feedback_score': float
}
```

---

### 7. A/B 테스트 프레임워크

```python
class ABTestManager:
    """RL vs Rule-based 알고리즘 비교"""

    def run_ab_test(self, orders, duration_days=7):
        results = {
            'control': [],    # 규칙 기반
            'treatment': []   # RL 기반
        }

        for order in orders:
            # 50% 트래픽 분할
            if random.random() < 0.5:
                result = rule_based_pack(order)
                results['control'].append(result)
            else:
                result = rl_pack(order)
                results['treatment'].append(result)

        # 통계적 유의성 검정
        return self.statistical_test(results)
```

---

## 구현 로드맵

### Phase 0: 준비 (1-2주)
- [x] 아키텍처 설계
- [ ] 데이터 수집 파이프라인 구축
- [ ] 환경(Environment) 구현
- [ ] 보상 함수 설계

### Phase 1: 기본 RL (4-6주)
- [ ] PPO 에이전트 구현
- [ ] 오프라인 학습 파이프라인
- [ ] 기본 메트릭 수집
- [ ] 규칙 기반과 성능 비교

### Phase 2: 휴먼 피드백 (4-6주)
- [ ] 피드백 UI 개발
- [ ] 피드백 DB 구축
- [ ] RLHF 파이프라인 구현
- [ ] Preference Learning 적용

### Phase 3: 프로덕션 배포 (2-3주)
- [ ] 모델 서빙 API
- [ ] A/B 테스트 프레임워크
- [ ] 모니터링 대시보드
- [ ] 점진적 롤아웃

### Phase 4: 고도화 (지속)
- [ ] Multi-Agent 시스템
- [ ] Transfer Learning
- [ ] Meta-Learning
- [ ] AutoML for Hyperparameter Tuning

---

## 기술 스택

```yaml
RL Framework:
  - Stable-Baselines3 (PPO, DQN, A2C)
  - Ray RLlib (분산 학습)
  - PyTorch (모델 구현)

Environment:
  - Gymnasium (Gym interface)
  - NumPy (상태 표현)

데이터:
  - PostgreSQL (피드백 저장)
  - Redis (경험 버퍼)
  - S3 (모델 저장)

MLOps:
  - MLflow (실험 추적)
  - DVC (데이터 버전 관리)
  - Airflow (학습 파이프라인)

모니터링:
  - Prometheus + Grafana
  - TensorBoard
  - Weights & Biases

서빙:
  - FastAPI (추론 API)
  - ONNX Runtime (최적화된 추론)
  - Docker + Kubernetes
```

---

## 예상 효과

```yaml
정량적 효과:
  - 공간 활용률: 현재 대비 5-10% 향상
  - 컨테이너 절감: 월 10-15% 감소
  - 적재 시간: 20-30% 단축
  - 안정성 사고: 50% 이상 감소

정성적 효과:
  - 작업자 만족도 향상
  - 신규 제품/컨테이너 빠른 적응
  - 복잡한 제약조건 자동 학습
  - 지속적인 성능 개선
```

---

## 리스크 및 대응

| 리스크 | 확률 | 영향 | 대응 방안 |
|--------|------|------|-----------|
| 학습 불안정 | 중 | 고 | Baseline 대비 성능 보장, Fallback |
| 데이터 부족 | 고 | 중 | 시뮬레이션 데이터 생성, Data Augmentation |
| 컴퓨팅 비용 | 중 | 중 | 효율적인 모델, 배치 학습 |
| 휴먼 피드백 편향 | 중 | 중 | 다양한 작업자, 교차 검증 |
| 프로덕션 장애 | 저 | 고 | 점진적 배포, 모니터링 강화 |

---

## 참고 문헌

1. "Deep Reinforcement Learning for 3D Bin Packing" (2020)
2. "Learning to Pack: A Data-Driven Approach" (2021)
3. "RLHF: Reinforcement Learning from Human Feedback" (OpenAI, 2022)
4. "Proximal Policy Optimization Algorithms" (Schulman et al., 2017)
5. "Multi-Agent Reinforcement Learning for Container Loading" (2023)
