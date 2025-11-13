#!/bin/bash

# API 엔드포인트 테스트 스크립트

BASE_URL="http://localhost:5050"

echo "========================================"
echo "API 엔드포인트 테스트"
echo "========================================"

# 서버가 실행 중인지 확인
echo -e "\n1. 서버 상태 확인..."
if curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/" | grep -q "200\|302\|404"; then
    echo "✓ 서버 실행 중"
else
    echo "❌ 서버가 실행되지 않았습니다. python api.py를 먼저 실행하세요."
    exit 1
fi

# RL 상태 조회
echo -e "\n2. RL 모델 상태 조회 (GET /api/rl/status)..."
curl -s "$BASE_URL/api/rl/status" | python3 -m json.tool

# RL 예측 테스트
echo -e "\n3. RL 예측 테스트 (POST /api/rl/pack)..."
curl -s -X POST "$BASE_URL/api/rl/pack" \
  -H "Content-Type: application/json" \
  -d '{
    "container": {
      "dimensions": [400, 200, 200],
      "max_weight": 1000
    },
    "items": [
      {"name": "Box1", "width": 50, "height": 50, "depth": 50, "weight": 10, "level": 1, "loadbear": 100, "updown": true},
      {"name": "Box2", "width": 40, "height": 40, "depth": 40, "weight": 8, "level": 1, "loadbear": 100, "updown": true}
    ],
    "mode": "hybrid"
  }' | python3 -m json.tool

# 기존 API에 RL 모드 테스트
echo -e "\n4. 기존 API에 RL 모드 (POST /api/calPacking?mode=hybrid)..."
curl -s -X POST "$BASE_URL/api/calPacking?mode=hybrid" \
  -H "Content-Type: application/json" \
  -d '{
    "box": {"WHD": [400, 200, 200], "weight": 1000},
    "item": [
      {"name": "Box1", "WHD": [50, 50, 50], "weight": 10, "level": 1, "loadbear": 100, "updown": true}
    ],
    "binding": []
  }' | python3 -m json.tool

# 피드백 저장 테스트
echo -e "\n5. 휴먼 피드백 저장 (POST /api/rl/feedback)..."
curl -s -X POST "$BASE_URL/api/rl/feedback" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "test_session_001",
    "algorithm": "hybrid",
    "scores": {
      "overall": 4,
      "stability": 5,
      "workability": 4,
      "efficiency": 3
    },
    "comments": "Good packing result",
    "worker_id": "worker_test"
  }' | python3 -m json.tool

# 통계 조회
echo -e "\n6. RL 통계 조회 (GET /api/rl/stats)..."
curl -s "$BASE_URL/api/rl/stats" | python3 -m json.tool

echo -e "\n========================================"
echo "✅ 모든 API 테스트 완료"
echo "========================================"
