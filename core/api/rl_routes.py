"""
RL 관련 API 라우트

강화학습 모델 예측, 피드백 수집, 성능 비교 등의 엔드포인트를 제공합니다.
"""

import json
from flask import Blueprint, request, jsonify
from typing import Optional

from core.rl.model_server import get_model_server
from core.utils import APIResponse, get_logger

# RL 전용 Blueprint
rl_bp = Blueprint('rl', __name__, url_prefix='/api/rl')

# 로거
logger = get_logger('rl_api')

# 모델 서버 (지연 초기화)
_model_server = None


def get_server():
    """모델 서버 인스턴스 가져오기"""
    global _model_server
    if _model_server is None:
        _model_server = get_model_server(mode='hybrid')
    return _model_server


@rl_bp.route('/status', methods=['GET'])
def rl_status():
    """
    RL 모델 상태 조회

    GET /api/rl/status

    Returns:
        {
            "Success": true,
            "data": {
                "model_loaded": bool,
                "model_path": str,
                "available_modes": list,
                "performance_stats": dict
            }
        }
    """
    try:
        server = get_server()
        status = server.get_status()

        # 하이브리드 서버면 성능 통계 추가
        if hasattr(server, 'get_performance_stats'):
            status['performance_stats'] = server.get_performance_stats()

        logger.info("RL status queried")
        return APIResponse.success(data=status)

    except Exception as e:
        logger.error(f"Failed to get RL status: {e}")
        return APIResponse.error(f"Status query failed: {str(e)}", status_code=500)


@rl_bp.route('/pack', methods=['POST'])
def rl_pack():
    """
    RL 기반 적재 예측

    POST /api/rl/pack

    Request Body:
        {
            "container": {
                "dimensions": [width, height, depth],
                "max_weight": float
            },
            "items": [
                {
                    "name": str,
                    "width": float,
                    "height": float,
                    "depth": float,
                    "weight": float,
                    "level": int,
                    "loadbear": float,
                    "updown": bool
                }
            ],
            "mode": "auto" | "rl" | "baseline" | "hybrid",  // optional
            "options": {  // optional
                "bigger_first": bool,
                "distribute_items": bool,
                "check_stable": bool
            }
        }

    Returns:
        {
            "Success": true,
            "data": {
                "algorithm": str,
                "mode": str,
                "packed_items": [...],
                "unpacked_items": [...],
                "metrics": {...}
            }
        }
    """
    try:
        data = request.get_json()

        if not data:
            return APIResponse.error("No data provided", status_code=400)

        # 필수 필드 검증
        if 'container' not in data or 'items' not in data:
            return APIResponse.error("Missing required fields: container, items", status_code=400)

        container = data['container']
        items = data['items']

        # 컨테이너 정보
        container_dims = tuple(container.get('dimensions', [589.8, 243.8, 259.1]))
        max_weight = container.get('max_weight', 50000)

        # 모드 설정
        mode = data.get('mode', 'auto')
        force_mode = None

        if mode == 'rl':
            force_mode = 'rl'
        elif mode == 'baseline':
            force_mode = 'baseline'
        # 'auto' 또는 'hybrid'면 하이브리드 모드 사용

        # 옵션
        options = data.get('options', {})

        # 예측 실행
        server = get_server()

        if hasattr(server, 'predict') and 'force_mode' in server.predict.__code__.co_varnames:
            # HybridModelServer
            result = server.predict(
                container_dims=container_dims,
                items=items,
                max_weight=max_weight,
                force_mode=force_mode,
                **options
            )
        else:
            # RLModelServer
            result = server.predict(
                container_dims=container_dims,
                items=items,
                max_weight=max_weight,
                **options
            )

        logger.info(f"RL pack completed: {result['metrics']['num_packed']}/{len(items)} items packed")
        return APIResponse.success(data=result)

    except Exception as e:
        logger.error(f"RL pack failed: {e}")
        return APIResponse.error(f"Packing failed: {str(e)}", status_code=500)


@rl_bp.route('/compare', methods=['POST'])
def rl_compare():
    """
    RL vs 기존 알고리즘 비교

    POST /api/rl/compare

    Request Body: (rl_pack과 동일)

    Returns:
        {
            "Success": true,
            "data": {
                "baseline": {...},
                "rl": {...},
                "comparison": {
                    "space_utilization_diff": float,
                    "winner": "rl" | "baseline",
                    "improvement_pct": float
                }
            }
        }
    """
    try:
        data = request.get_json()

        if not data:
            return APIResponse.error("No data provided", status_code=400)

        if 'container' not in data or 'items' not in data:
            return APIResponse.error("Missing required fields: container, items", status_code=400)

        container = data['container']
        items = data['items']

        container_dims = tuple(container.get('dimensions', [589.8, 243.8, 259.1]))
        max_weight = container.get('max_weight', 50000)
        options = data.get('options', {})

        # 비교 실행
        server = get_server()
        comparison = server.compare_algorithms(
            container_dims=container_dims,
            items=items,
            max_weight=max_weight,
            **options
        )

        logger.info("RL comparison completed")
        return APIResponse.success(data=comparison)

    except Exception as e:
        logger.error(f"RL comparison failed: {e}")
        return APIResponse.error(f"Comparison failed: {str(e)}", status_code=500)


@rl_bp.route('/feedback', methods=['POST'])
def rl_feedback():
    """
    휴먼 피드백 수집

    POST /api/rl/feedback

    Request Body:
        {
            "session_id": str,
            "worker_id": str,  // optional
            "algorithm": "rl" | "baseline",
            "scores": {
                "overall": int,  // 1-5
                "stability": int,
                "workability": int,
                "efficiency": int
            },
            "comments": str,  // optional
            "packed_items": [...],  // optional
            "metadata": {...}  // optional
        }

    Returns:
        {
            "Success": true,
            "data": {
                "feedback_id": str,
                "saved": true
            }
        }
    """
    try:
        data = request.get_json()

        if not data:
            return APIResponse.error("No data provided", status_code=400)

        # 필수 필드 검증
        required_fields = ['session_id', 'algorithm', 'scores']
        missing_fields = [f for f in required_fields if f not in data]

        if missing_fields:
            return APIResponse.error(
                f"Missing required fields: {', '.join(missing_fields)}",
                status_code=400
            )

        # 피드백 데이터 저장
        # TODO: Supabase 또는 로컬 DB에 저장
        import uuid
        from datetime import datetime

        feedback_id = str(uuid.uuid4())
        feedback_data = {
            'feedback_id': feedback_id,
            'session_id': data['session_id'],
            'worker_id': data.get('worker_id'),
            'algorithm': data['algorithm'],
            'scores': data['scores'],
            'comments': data.get('comments'),
            'packed_items': data.get('packed_items'),
            'metadata': data.get('metadata', {}),
            'created_at': datetime.now().isoformat()
        }

        # 로컬 파일로 임시 저장
        import os
        feedback_dir = 'data/feedback'
        os.makedirs(feedback_dir, exist_ok=True)

        feedback_file = os.path.join(feedback_dir, f'feedback_{feedback_id}.json')
        with open(feedback_file, 'w', encoding='utf-8') as f:
            json.dump(feedback_data, f, indent=2, ensure_ascii=False)

        logger.info(f"Feedback saved: {feedback_id}")

        return APIResponse.success(data={
            'feedback_id': feedback_id,
            'saved': True,
            'message': 'Feedback received successfully'
        })

    except Exception as e:
        logger.error(f"Feedback save failed: {e}")
        return APIResponse.error(f"Failed to save feedback: {str(e)}", status_code=500)


@rl_bp.route('/feedback/<feedback_id>', methods=['GET'])
def get_feedback(feedback_id: str):
    """
    피드백 조회

    GET /api/rl/feedback/<feedback_id>
    """
    try:
        import os

        feedback_file = f'data/feedback/feedback_{feedback_id}.json'

        if not os.path.exists(feedback_file):
            return APIResponse.error("Feedback not found", status_code=404)

        with open(feedback_file, 'r', encoding='utf-8') as f:
            feedback_data = json.load(f)

        return APIResponse.success(data=feedback_data)

    except Exception as e:
        logger.error(f"Feedback retrieval failed: {e}")
        return APIResponse.error(f"Failed to retrieve feedback: {str(e)}", status_code=500)


@rl_bp.route('/feedback/list', methods=['GET'])
def list_feedback():
    """
    피드백 목록 조회

    GET /api/rl/feedback/list?algorithm=rl&limit=10&offset=0
    """
    try:
        import os
        from pathlib import Path

        algorithm = request.args.get('algorithm')
        limit = int(request.args.get('limit', 10))
        offset = int(request.args.get('offset', 0))

        feedback_dir = Path('data/feedback')

        if not feedback_dir.exists():
            return APIResponse.success(data={'feedbacks': [], 'total': 0})

        # 모든 피드백 파일 로드
        feedbacks = []
        for feedback_file in feedback_dir.glob('feedback_*.json'):
            with open(feedback_file, 'r', encoding='utf-8') as f:
                feedback = json.load(f)

                # 알고리즘 필터
                if algorithm and feedback.get('algorithm') != algorithm:
                    continue

                feedbacks.append(feedback)

        # 최신순 정렬
        feedbacks.sort(key=lambda x: x.get('created_at', ''), reverse=True)

        # 페이지네이션
        total = len(feedbacks)
        feedbacks = feedbacks[offset:offset + limit]

        return APIResponse.success(data={
            'feedbacks': feedbacks,
            'total': total,
            'limit': limit,
            'offset': offset
        })

    except Exception as e:
        logger.error(f"Feedback list retrieval failed: {e}")
        return APIResponse.error(f"Failed to retrieve feedback list: {str(e)}", status_code=500)


@rl_bp.route('/stats', methods=['GET'])
def rl_stats():
    """
    RL 시스템 통계

    GET /api/rl/stats

    Returns:
        {
            "Success": true,
            "data": {
                "total_predictions": int,
                "rl_usage_rate": float,
                "avg_space_utilization": dict,
                "feedback_stats": dict
            }
        }
    """
    try:
        server = get_server()

        stats = {
            'model_status': server.get_status()
        }

        # 하이브리드 서버 성능 통계
        if hasattr(server, 'get_performance_stats'):
            stats['performance'] = server.get_performance_stats()

        # 피드백 통계
        import os
        from pathlib import Path

        feedback_dir = Path('data/feedback')
        if feedback_dir.exists():
            feedback_files = list(feedback_dir.glob('feedback_*.json'))

            feedback_scores = {'rl': [], 'baseline': []}
            for feedback_file in feedback_files:
                with open(feedback_file, 'r', encoding='utf-8') as f:
                    feedback = json.load(f)
                    algorithm = feedback.get('algorithm', 'baseline')
                    overall_score = feedback.get('scores', {}).get('overall')

                    if overall_score and algorithm in feedback_scores:
                        feedback_scores[algorithm].append(overall_score)

            stats['feedback'] = {
                'total_count': len(feedback_files),
                'rl_avg_score': sum(feedback_scores['rl']) / len(feedback_scores['rl']) if feedback_scores['rl'] else 0,
                'baseline_avg_score': sum(feedback_scores['baseline']) / len(feedback_scores['baseline']) if feedback_scores['baseline'] else 0,
                'rl_count': len(feedback_scores['rl']),
                'baseline_count': len(feedback_scores['baseline'])
            }
        else:
            stats['feedback'] = {'total_count': 0}

        logger.info("RL stats retrieved")
        return APIResponse.success(data=stats)

    except Exception as e:
        logger.error(f"Stats retrieval failed: {e}")
        return APIResponse.error(f"Failed to retrieve stats: {str(e)}", status_code=500)


def register_rl_routes(app):
    """
    Flask app에 RL 라우트 등록

    Args:
        app: Flask application instance
    """
    app.register_blueprint(rl_bp)
    logger.info("RL routes registered")
