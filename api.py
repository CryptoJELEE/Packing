
import flask
import json
import random
import os
import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict
from werkzeug.utils import secure_filename
from py3dbp import Packer, Bin, Item
from flask_cors import cross_origin
from flask import render_template, send_from_directory, request

# 새로운 모듈 구조 import
from core.data.csv_processor import CSVDataProcessor
from core.packing.pipeline import PackingPipeline
from core.packing.helpers import PackingSerializer, ColorGenerator
from core.data.master_manager import MasterDataManager
from core.data.order_processor import OrderProcessor
from config.settings import get_config
from core.utils import (
    setup_logger,
    get_logger,
    FileValidator,
    CSVSanitizer,
    APIResponse,
    ErrorHandler,
    SecurityHeaders,
    setup_rate_limiting
)

# 환경 설정 로드
config_class = get_config()

# Supabase 및 세션 관리
try:
    from core.storage.supabase_client import supabase_client
    from core.storage.session_manager import SessionManager
    USE_SUPABASE_SESSION = True
except ImportError:
    from core.storage.session_manager import SessionManager
    supabase_client = None
    USE_SUPABASE_SESSION = False

# init flask
app = flask.Flask(__name__)
app.config.from_object(config_class)
config_class.init_app(app)

# 로거 설정
logger = setup_logger(
    name='packing',
    log_file=app.config.get('LOG_FILE'),
    level=app.config.get('LOG_LEVEL', 'INFO')
)
logger.info(f"애플리케이션 시작 - 환경: {app.config.get('ENV', 'development')}")

if not USE_SUPABASE_SESSION:
    logger.warning("Supabase 클라이언트를 사용할 수 없습니다. 인메모리 세션을 사용합니다.")

# 에러 핸들러 등록
ErrorHandler.register_handlers(app)

# 보안 헤더 설정
SecurityHeaders.init_app(app)

# Rate Limiting 설정 (선택적)
limiter = setup_rate_limiting(app)

# RL API 라우트 등록
try:
    from core.api.rl_routes import register_rl_routes
    register_rl_routes(app)
    logger.info("RL API 라우트 등록 완료")
except ImportError as e:
    logger.warning(f"RL API 라우트를 등록할 수 없습니다: {e}")

# load data
try:
    with open('widadvance.json', encoding='utf-8') as f:
        alldata = json.load(f)
    logger.info("widadvance.json 파일 로드 성공")
except (FileNotFoundError, json.JSONDecodeError) as e:
    logger.warning(f"widadvance.json 로드 실패: {e}")
    alldata = {"box": [], "item": []}

# 세션 매니저 초기화
session_manager = SessionManager(
    use_supabase=USE_SUPABASE_SESSION,
    supabase_client=supabase_client if USE_SUPABASE_SESSION else None
)

# 전역 마스터 매니저
master_manager = MasterDataManager()


# 세션 관리 래퍼 함수 (하위 호환성)
def save_session(session_id: str, session_type: str, data: dict) -> bool:
    """세션 저장 (SessionManager 래퍼)"""
    return session_manager.save(session_id, session_type, data)


def get_session(session_id: str) -> Optional[Dict]:
    """세션 조회 (SessionManager 래퍼)"""
    return session_manager.get(session_id)

# 웹 인터페이스
@app.route('/')
@cross_origin()
def index():
    return render_template('index.html')


# get all item and box information
@app.route("/getAllData", methods=["POST","GET"])
@cross_origin()
def getAllItemAndBoxAPI():
    ''' get all item and box information '''
    if flask.request.method == "POST":
        alldata["Success"] = True
        return flask.jsonify(alldata)
    else :
        return {"Success": False,"Reason":"can't use GET"}


# cal packing 
@app.route("/calPacking", methods=["POST"])
@cross_origin()
def mkResultAPI():
    '''
    '''
    res = {"Success": False}
    if flask.request.method == "POST":
        try:
            q = flask.request.get_json()
            if q is None:
                q = json.loads(flask.request.data.decode('utf-8'))
        except (json.JSONDecodeError, ValueError) as e:
            res["Reason"] = f"Invalid JSON: {str(e)}"
            return flask.jsonify(res)
        if 'box' in q.keys() and 'item' in q.keys() and 'binding' in q.keys():
            try:
                packer, box, binding = getBoxAndItem(q)
            except (KeyError, ValueError, TypeError) as e:
                res["Reason"] = f"Input data error: {str(e)}"
                return flask.jsonify(res)
            try :
                # calculate packing
                packer.pack(bigger_first=True,distribute_items=False,fix_point=True,binding=binding,
                number_of_decimals=0)
                box = packer.bins[0]
                # make box dict
                box_r = makeDictBox(box)
                # make item dict
                fitItem,unfitItem = [],[]
                for item in box.items:
                    fitItem.append(makeDictItem(item))
                
                for item in box.unfitted_items:
                    unfitItem.append(makeDictItem(item))

                # for unfitem in box
                # make response
                res["Success"] = True
                res["data"] = {
                    "box" : box_r,
                    "fitItem" : fitItem,
                    "unfitItem": unfitItem
                }
                # print(len(res["data"]["unfitItem"]))
                return res
            except Exception as e:
                res['Reason'] = 'cal packing err'
                return res
        else :
            res['Reason'] = 'box or item not in input data'
            return res
    else :
        res['Reason'] = 'method not POST'
        return res


def makeDictBox(box: Bin) -> list:
    """
    박스를 딕셔너리로 변환

    Args:
        box: py3dbp Bin 객체

    Returns:
        박스 정보 딕셔너리 리스트
    """
    return [PackingSerializer.serialize_box(box)]


def makeDictItem(item: Item) -> Dict:
    """
    아이템을 딕셔너리로 변환

    Args:
        item: py3dbp Item 객체

    Returns:
        아이템 정보 딕셔너리
    """
    return PackingSerializer.serialize_item(item)


def getBoxAndItem(data: Dict) -> tuple[Packer, Bin, list]:
    """
    입력 데이터에서 Packer, Bin, binding 생성

    Args:
        data: 박스와 아이템 정보를 담은 딕셔너리

    Returns:
        (packer, box, binding) 튜플

    Raises:
        KeyError: 필수 키가 없을 때
        ValueError: 데이터 형식이 잘못되었을 때
    """
    # init packer
    packer = Packer()

    # get bin data
    box_data = data["box"][0]
    box = Bin(
        partno=box_data['name'],
        WHD=box_data['WHD'],
        max_weight=box_data['weight'],
        corner=box_data['coner'],
        put_type=box_data['openTop'][0]
    )
    packer.addBin(box)

    # get item data
    item_data = data["item"]
    for item_info in item_data:
        count = item_info['count']
        for j in range(count):
            packer.addItem(Item(
                partno=f"{item_info['name']}-{j+1}",
                name=item_info['name'],
                typeof='cylinder' if item_info['type'] == 2 else 'cube',
                WHD=item_info['WHD'],
                weight=item_info['weight'],
                level=1 if item_info['level'] == 1 else 2,
                loadbear=item_info['loadbear'],
                updown=bool(item_info['updown']),
                color=randColor(item_info['color'])
            ))

    # get binding data
    binding_data = data['binding']
    binding = [tuple(b) for b in binding_data] if binding_data else []

    return packer, box, binding


def randColor(seed: int) -> str:
    """
    시드값으로 랜덤 색상 생성

    Args:
        seed: 색상 시드값

    Returns:
        HEX 색상 코드
    """
    return ColorGenerator.generate_color(seed)


# 마스터 데이터 업로드
@app.route('/api/uploadMaster', methods=['POST'])
@cross_origin()
def upload_master():
    """자재마스터 CSV 업로드 및 저장"""
    if 'file' not in request.files:
        return APIResponse.error("파일이 없습니다", status_code=400)

    file = request.files['file']

    # 파일 검증
    is_valid, error_msg = FileValidator.validate_csv_file(file)
    if not is_valid:
        return APIResponse.error(error_msg, status_code=400)

    try:
        # 파일 저장
        filename = secure_filename(file.filename)
        filepath = os.path.join(str(config_class.UPLOAD_FOLDER), f"master_{filename}")
        config_class.UPLOAD_FOLDER.mkdir(exist_ok=True)
        file.save(filepath)
        logger.info(f"마스터 CSV 파일 저장: {filepath}")

        # CSV 내용 검증
        is_valid, error_msg = CSVSanitizer.validate_csv_content(filepath)
        if not is_valid:
            os.remove(filepath)  # 잘못된 파일 삭제
            return APIResponse.error(error_msg, status_code=400)

        # CSV 처리
        processor = CSVDataProcessor(filepath)
        items = processor.process_all_items()

        # 마스터 데이터에 추가
        master_manager.add_master_items(items)
        stats = master_manager.get_master_stats()

        logger.info(f"마스터 데이터 {len(items)}개 항목 저장 완료")

        return APIResponse.success(
            message=f"마스터 데이터 {len(items)}개 항목이 저장되었습니다.",
            stats=stats,
            total_items=len(items)
        )
    except Exception as e:
        logger.error(f"마스터 데이터 업로드 오류: {e}", exc_info=True)
        return APIResponse.internal_error("파일 처리 중 오류가 발생했습니다", exception=e)

# 마스터 상태 확인
@app.route('/api/getMasterStatus', methods=['GET'])
@cross_origin()
def get_master_status():
    """마스터 데이터 로드 여부 확인"""
    return flask.jsonify({
        "Success": True,
        "has_master": master_manager.has_master_data(),
        "stats": master_manager.get_master_stats()
    })

# 주문서 CSV 업로드
@app.route('/api/uploadOrder', methods=['POST'])
@cross_origin()
def upload_order():
    """주문서 CSV 업로드 및 처리"""
    if not master_manager.has_master_data():
        return APIResponse.error("먼저 자재마스터를 업로드해주세요.", status_code=400)

    if 'file' not in request.files:
        return APIResponse.error("파일이 없습니다", status_code=400)

    file = request.files['file']

    # 파일 검증
    is_valid, error_msg = FileValidator.validate_csv_file(file)
    if not is_valid:
        return APIResponse.error(error_msg, status_code=400)

    try:
        # 파일 저장
        filename = secure_filename(file.filename)
        filepath = os.path.join(str(config_class.UPLOAD_FOLDER), f"order_{filename}")
        config_class.UPLOAD_FOLDER.mkdir(exist_ok=True)
        file.save(filepath)
        logger.info(f"주문 CSV 파일 저장: {filepath}")

        # CSV 내용 검증
        is_valid, error_msg = CSVSanitizer.validate_csv_content(filepath)
        if not is_valid:
            os.remove(filepath)
            return APIResponse.error(error_msg, status_code=400)

        # 주문서 처리
        order_processor = OrderProcessor(master_manager)
        orders = order_processor.read_order_csv(filepath)
        result = order_processor.process_orders_with_master()

        # 세션 ID 생성
        session_id = str(uuid.uuid4())
        save_session(session_id, 'order', {
            'orders': orders,
            'matched_items': result['matched_items'],
            'unmatched_items': result['unmatched_items'],
            'filepath': filepath
        })

        logger.info(f"주문서 처리 완료 - 세션ID: {session_id}, 매칭: {len(result['matched_items'])}, 미매칭: {len(result['unmatched_items'])}")

        return APIResponse.success(
            message="주문서 처리 완료",
            session_id=session_id,
            matched_count=len(result['matched_items']),
            unmatched_count=len(result['unmatched_items']),
            total_quantity=result['total_quantity'],
            matched_items=result['matched_items'][:50],  # 미리보기
            unmatched_items=result['unmatched_items']
        )
    except Exception as e:
        logger.error(f"주문서 업로드 오류: {e}", exc_info=True)
        return APIResponse.internal_error("주문서 처리 중 오류가 발생했습니다", exception=e)

# 주문서 아이템 조회
@app.route('/api/getOrderItems', methods=['GET'])
@cross_origin()
def get_order_items():
    """주문서 아이템 조회"""
    res = {"Success": False}
    
    session_id = request.args.get('session_id')
    session_info = get_session(session_id)
    if not session_id or not session_info:
        res["Reason"] = "유효하지 않은 세션 ID"
        return flask.jsonify(res)
    
    if session_info.get('type') != 'order':
        res["Reason"] = "주문서 세션이 아닙니다"
        return flask.jsonify(res)
    
    res["Success"] = True
    res["items"] = session_info['matched_items']
    res["unmatched_items"] = session_info['unmatched_items']
    
    return flask.jsonify(res)

# CSV 파일 업로드 및 처리 (기존 - 호환성 유지)
@app.route('/api/uploadCSV', methods=['POST'])
@cross_origin()
def upload_csv():
    """CSV 파일 업로드 및 처리"""
    res = {"Success": False}
    
    if 'file' not in request.files:
        res["Reason"] = "파일이 없습니다"
        return flask.jsonify(res)
    
    file = request.files['file']
    if file.filename == '':
        res["Reason"] = "파일이 선택되지 않았습니다"
        return flask.jsonify(res)
    
    if not file.filename.endswith('.csv'):
        res["Reason"] = "CSV 파일만 업로드 가능합니다"
        return flask.jsonify(res)
    
    try:
        # 파일 저장
        filename = secure_filename(file.filename)
        filepath = os.path.join(str(Config.UPLOAD_FOLDER), filename)
        Config.UPLOAD_FOLDER.mkdir(exist_ok=True)
        file.save(filepath)
        
        # CSV 처리
        processor = CSVDataProcessor(filepath)
        items = processor.process_all_items()
        stats = processor.get_statistics()
        
        # 세션 ID 생성
        session_id = str(uuid.uuid4())
        save_session(session_id, 'csv', {
            'processor_path': filepath,  # 파일 경로만 저장
            'items': items,
            'stats': stats,
            'filepath': filepath
        })
        
        res["Success"] = True
        res["session_id"] = session_id
        res["stats"] = stats
        res["total_items"] = len(items)
        res["items"] = items[:50]  # 처음 50개만 반환 (미리보기)
        
        return flask.jsonify(res)
    except Exception as e:
        res["Reason"] = f"파일 처리 오류: {str(e)}"
        return flask.jsonify(res)

# CSV 아이템 목록 조회
@app.route('/api/getCSVItems', methods=['GET'])
@cross_origin()
def get_csv_items():
    """처리된 CSV 아이템 목록 조회"""
    res = {"Success": False}
    
    session_id = request.args.get('session_id')
    categories = request.args.getlist('categories')
    
    session_info = get_session(session_id)
    if not session_id or not session_info:
        res["Reason"] = "유효하지 않은 세션 ID"
        return flask.jsonify(res)
    
    try:
        data = session_info
        
        if categories:
            # 카테고리 필터링을 위해 processor 재생성
            processor = CSVDataProcessor(data['filepath'])
            processor.process_all_items()
            items = processor.filter_by_category(categories)
        else:
            items = data['items']
        
        res["Success"] = True
        res["items"] = items
        res["total"] = len(items)
        
        return flask.jsonify(res)
    except Exception as e:
        res["Reason"] = f"데이터 조회 오류: {str(e)}"
        return flask.jsonify(res)

# 시각화 이미지 생성
@app.route('/api/visualize', methods=['POST'])
@cross_origin()
def visualize():
    """시각화 이미지 생성"""
    res = {"Success": False}
    
    try:
        data = request.get_json()
        session_id = data.get('session_id')
        
        session_info = get_session(session_id)
        if not session_id or not session_info:
            res["Reason"] = "유효하지 않은 세션 ID"
            return flask.jsonify(res)
        
        # 패킹 파이프라인 생성
        pipeline = PackingPipeline()
        
        # 박스 추가
        box_data = data.get('box', {})
        pipeline.add_box(
            partno=box_data.get('name', 'Box1'),
            WHD=tuple(box_data.get('WHD', [589.8, 243.8, 259.1])),
            max_weight=box_data.get('weight', 28080),
            corner=box_data.get('coner', 0),
            put_type=box_data.get('openTop', [1])[0] if isinstance(box_data.get('openTop'), list) else 1,
            is_pallet=box_data.get('is_pallet', False)
        )
        
        # 아이템 추가
        # session_info는 이미 위에서 가져옴
        
        # 주문서인 경우
        if session_info.get('type') == 'order':
            items = session_info['matched_items']
            # 주문 수량을 count로 사용
            item_counts = {item['name']: item.get('order_quantity', 1) 
                          for item in items}
            pipeline.add_items_from_data(items, item_counts)
        else:
            # 기존 방식 (직접 선택)
            items = session_info['items']
            item_counts = data.get('item_counts', {})
            pipeline.add_items_from_data(items, item_counts)
        
        # 시뮬레이션 실행
        sim_params = data.get('simulation_params', {})
        result = pipeline.run_simulation(
            bigger_first=sim_params.get('bigger_first', True),
            distribute_items=sim_params.get('distribute_items', True),
            fix_point=sim_params.get('fix_point', True),
            check_stable=sim_params.get('check_stable', True),
            support_surface_ratio=sim_params.get('support_surface_ratio', 0.75),
            number_of_decimals=0,
            use_advanced_strategy=sim_params.get('use_advanced_strategy', False),
            try_multiple_strategies=sim_params.get('try_multiple_strategies', False)
        )
        
        # 시각화 생성
        images_dir = Config.OUTPUT_FOLDER / 'images'
        images_dir.mkdir(parents=True, exist_ok=True)  # 디렉토리 생성 보장
        image_paths = pipeline.visualize_results(save_path=str(images_dir), alpha=0.2)
        
        # 이미지 파일 생성 확인
        for img in image_paths:
            img_path = images_dir / img
            if img_path.exists():
                print(f"✅ 이미지 생성 완료: {img_path}")
            else:
                print(f"❌ 이미지 생성 실패: {img_path}")
        
        # 기본 리포트 생성
        report_dir = Config.OUTPUT_FOLDER / 'reports'
        report_dir.mkdir(exist_ok=True)
        report_filename = f"{session_id}.json"
        report_path = report_dir / report_filename
        report = pipeline.generate_report(str(report_path))
        
        # 상세 보고서 생성 (레이어별 정보)
        detailed_report_dir = report_dir / session_id
        detailed_report = pipeline.generate_detailed_report(
            output_dir=str(detailed_report_dir),
            include_layer_diagrams=True
        )
        
        res["Success"] = True
        res["images"] = image_paths
        res["result"] = result
        res["report_id"] = session_id
        res["detailed_report"] = detailed_report
        
        return flask.jsonify(res)
    except Exception as e:
        res["Reason"] = f"시각화 생성 오류: {str(e)}"
        import traceback
        traceback.print_exc()
        return flask.jsonify(res)

# 리포트 다운로드
@app.route('/api/report/<session_id>', methods=['GET'])
@cross_origin()
def get_report(session_id):
    """리포트 다운로드"""
    try:
        report_path = Config.OUTPUT_FOLDER / 'reports' / f"{session_id}.json"
        if report_path.exists():
            return send_from_directory(
                str(Config.OUTPUT_FOLDER / 'reports'),
                f"{session_id}.json",
                as_attachment=True,
                download_name=f"packing_report_{session_id}.json"
            )
        else:
            return flask.jsonify({"Success": False, "Reason": "리포트를 찾을 수 없습니다"}), 404
    except Exception as e:
        return flask.jsonify({"Success": False, "Reason": str(e)}), 500

# 상세 HTML 보고서 조회
@app.route('/api/reportHTML/<session_id>/<bin_name>', methods=['GET'])
@cross_origin()
def get_html_report(session_id, bin_name):
    """HTML 보고서 조회"""
    try:
        report_dir = Config.OUTPUT_FOLDER / 'reports' / session_id
        html_file = f"{bin_name}_report.html"
        html_path = report_dir / html_file
        
        if html_path.exists():
            return send_from_directory(str(report_dir), html_file)
        else:
            return flask.jsonify({"Success": False, "Reason": "HTML 보고서를 찾을 수 없습니다"}), 404
    except Exception as e:
        return flask.jsonify({"Success": False, "Reason": str(e)}), 500

# 작업 지시서 조회
@app.route('/api/workInstruction/<session_id>/<bin_name>', methods=['GET'])
@cross_origin()
def get_work_instruction(session_id, bin_name):
    """작업 지시서 형태의 보고서 조회"""
    try:
        report_dir = Config.OUTPUT_FOLDER / 'reports' / session_id
        work_file = f"{bin_name}_work_instruction.html"
        work_path = report_dir / work_file
        
        if work_path.exists():
            return send_from_directory(str(report_dir), work_file)
        else:
            return flask.jsonify({"Success": False, "Reason": "작업 지시서를 찾을 수 없습니다"}), 404
    except Exception as e:
        return flask.jsonify({"Success": False, "Reason": str(e)}), 500

# 상세 보고서 데이터 조회
@app.route('/api/getDetailedReport/<session_id>', methods=['GET'])
@cross_origin()
def get_detailed_report(session_id):
    """상세 보고서 데이터 조회"""
    try:
        report_dir = Config.OUTPUT_FOLDER / 'reports' / session_id
        
        if not report_dir.exists():
            return flask.jsonify({"Success": False, "Reason": "보고서를 찾을 수 없습니다"}), 404
        
        # 리포트 파일들 찾기
        reports = []
        for file in os.listdir(report_dir):
            if file.endswith('_report.html'):
                bin_name = file.replace('_report.html', '')
                reports.append({
                    'bin_name': bin_name,
                    'html_file': file,
                    'url': f'/api/reportHTML/{session_id}/{bin_name}'
                })
        
        return flask.jsonify({
            "Success": True,
            "reports": reports
        })
    except Exception as e:
        return flask.jsonify({"Success": False, "Reason": str(e)}), 500

# 이미지 조회
@app.route('/api/image/<path:filename>', methods=['GET'])
@cross_origin()
def get_image(filename):
    """생성된 이미지 조회"""
    try:
        # 파일명 디코딩
        from urllib.parse import unquote
        filename = unquote(filename)
        
        image_path = Config.OUTPUT_FOLDER / 'images' / filename
        
        if image_path.exists():
            return send_from_directory(
                str(Config.OUTPUT_FOLDER / 'images'),
                filename
            )
        else:
            # 파일이 없으면 404 반환
            print(f"⚠️ 이미지 파일을 찾을 수 없습니다: {image_path}")
            return flask.jsonify({
                "Success": False, 
                "Reason": f"이미지 파일을 찾을 수 없습니다: {filename}"
            }), 404
    except Exception as e:
        print(f"❌ 이미지 조회 오류: {str(e)}")
        return flask.jsonify({
            "Success": False, 
            "Reason": str(e)
        }), 404

# 기존 calPacking 엔드포인트 개선 (CSV 데이터도 지원)
@app.route('/api/calPacking', methods=['POST'])
@cross_origin()
def cal_packing():
    """패킹 계산 (기존 + CSV 지원 + RL 모드)"""
    res = {"Success": False}

    if request.method == "POST":
        try:
            # JSON 데이터 받기
            if request.is_json:
                q = request.get_json()
            else:
                try:
                    q = json.loads(request.data.decode('utf-8'))
                except (json.JSONDecodeError, ValueError) as e:
                    res["Reason"] = f"Invalid JSON: {str(e)}"
                    return flask.jsonify(res)

            # RL 모드 체크 (mode 파라미터 또는 쿼리 스트링)
            mode = q.get('mode') or request.args.get('mode', 'baseline')

            # RL 모드 사용 (mode=rl 또는 mode=hybrid)
            if mode in ['rl', 'hybrid']:
                try:
                    from core.rl.model_server import get_model_server

                    # 박스 데이터 추출
                    box_data = q.get("box", [{}])[0] if isinstance(q.get("box"), list) else q.get("box", {})
                    container_dims = tuple(box_data.get('WHD', [589.8, 243.8, 259.1]))
                    max_weight = box_data.get('weight', 28080)

                    # 아이템 데이터 추출
                    items = []
                    if 'item' in q:
                        # 기존 JSON 방식
                        for item_data in q['item']:
                            items.append({
                                'name': item_data.get('name', 'Unknown'),
                                'width': item_data['WHD'][0],
                                'height': item_data['WHD'][1],
                                'depth': item_data['WHD'][2],
                                'weight': item_data.get('weight', 1),
                                'level': item_data.get('level', 1),
                                'loadbear': item_data.get('loadbear', 100),
                                'updown': item_data.get('updown', True)
                            })
                    elif 'session_id' in q and q['session_id'] in session_data:
                        # CSV 세션 방식
                        session_info = session_data[q['session_id']]
                        for item_data in session_info['items']:
                            items.append({
                                'name': item_data.get('name', 'Unknown'),
                                'width': item_data.get('width', 0),
                                'height': item_data.get('height', 0),
                                'depth': item_data.get('depth', 0),
                                'weight': item_data.get('weight', 1),
                                'level': item_data.get('level', 1),
                                'loadbear': item_data.get('loadbear', 100),
                                'updown': item_data.get('updown', True)
                            })

                    # RL 모델 서버 사용
                    server = get_model_server(mode='hybrid')
                    force_mode = 'rl' if mode == 'rl' else None

                    rl_result = server.predict(
                        container_dims=container_dims,
                        items=items,
                        max_weight=max_weight,
                        force_mode=force_mode
                    )

                    # 결과 변환 (RL 형식 → 기존 형식)
                    res["Success"] = True
                    res["mode"] = mode
                    res["algorithm"] = rl_result.get('algorithm', 'rl')
                    res["data"] = {
                        "box": [{
                            "name": "Container",
                            "WHD": list(container_dims),
                            "weight": max_weight
                        }],
                        "fitItem": [
                            {
                                "name": item['name'],
                                "WHD": item['dimensions'],
                                "position": item['position'],
                                "rotationType": item['rotation_type'],
                                "color": item.get('color', 'red')
                            }
                            for item in rl_result['packed_items']
                        ],
                        "unfitItem": [
                            {
                                "name": item['name'],
                                "WHD": item['dimensions']
                            }
                            for item in rl_result['unpacked_items']
                        ],
                        "metrics": rl_result['metrics']
                    }
                    logger.info(f"RL mode used: {mode}, packed: {rl_result['metrics']['num_packed']}/{len(items)}")
                    return flask.jsonify(res)

                except ImportError:
                    logger.warning("RL model server not available, falling back to baseline")
                    # RL 사용 불가시 기존 방식으로 fallback
                except Exception as e:
                    logger.error(f"RL mode failed: {e}, falling back to baseline")
                    # 에러 발생시 기존 방식으로 fallback
            
            # CSV 세션에서 가져오기
            session_id = q.get('session_id')
            if session_id and session_id in session_data:
                # CSV 데이터 사용
                session_info = session_data[session_id]
                items = session_info['items']
                item_counts = q.get('item_counts', {})
                
                # 패킹 파이프라인 사용
                pipeline = PackingPipeline()
                
                # 박스 추가
                box_data = q.get("box", [{}])[0] if isinstance(q.get("box"), list) else q.get("box", {})
                pipeline.add_box(
                    partno=box_data.get('name', 'Box1'),
                    WHD=tuple(box_data.get('WHD', [589.8, 243.8, 259.1])),
                    max_weight=box_data.get('weight', 28080),
                    corner=box_data.get('coner', 0),
                    put_type=box_data.get('openTop', [1])[0] if isinstance(box_data.get('openTop'), list) else 1,
                    is_pallet=box_data.get('is_pallet', False)
                )
                
                # 아이템 추가
                pipeline.add_items_from_data(items, item_counts)
                
                # 시뮬레이션 실행
                sim_params = q.get('simulation_params', {})
                result = pipeline.run_simulation(
                    bigger_first=sim_params.get('bigger_first', True),
                    distribute_items=sim_params.get('distribute_items', False),
                    fix_point=sim_params.get('fix_point', True),
                    check_stable=sim_params.get('check_stable', True),
                    support_surface_ratio=sim_params.get('support_surface_ratio', 0.75),
                    binding=q.get('binding', []),
                    number_of_decimals=0
                )
                
                # 결과 변환
                box_r = []
                fitItem = []
                unfitItem = []
                
                for bin in pipeline.packer.bins:
                    box_r.append(makeDictBox(bin)[0])
                    for item in bin.items:
                        fitItem.append(makeDictItem(item))
                    for item in bin.unfitted_items:
                        unfitItem.append(makeDictItem(item))
                
                res["Success"] = True
                res["data"] = {
                    "box": box_r,
                    "fitItem": fitItem,
                    "unfitItem": unfitItem
                }
                return flask.jsonify(res)
            else:
                # 기존 방식 (JSON 직접 입력)
                if 'box' in q.keys() and 'item' in q.keys() and 'binding' in q.keys():
                    try:
                        packer, box, binding = getBoxAndItem(q)
                    except (KeyError, ValueError, TypeError) as e:
                        res["Reason"] = f"Input data error: {str(e)}"
                        return flask.jsonify(res)
                    try:
                        # calculate packing
                        packer.pack(bigger_first=True, distribute_items=False, fix_point=True, binding=binding,
                                   number_of_decimals=0)
                        box = packer.bins[0]
                        # make box dict
                        box_r = makeDictBox(box)
                        # make item dict
                        fitItem, unfitItem = [], []
                        for item in box.items:
                            fitItem.append(makeDictItem(item))
                        
                        for item in box.unfitted_items:
                            unfitItem.append(makeDictItem(item))
                        
                        res["Success"] = True
                        res["data"] = {
                            "box": box_r,
                            "fitItem": fitItem,
                            "unfitItem": unfitItem
                        }
                        return flask.jsonify(res)
                    except Exception as e:
                        res['Reason'] = f'cal packing err: {str(e)}'
                        return flask.jsonify(res)
                else:
                    res['Reason'] = 'box or item not in input data'
                    return flask.jsonify(res)
        except Exception as e:
            res['Reason'] = f'request processing error: {str(e)}'
            return flask.jsonify(res)
    else:
        res['Reason'] = 'method not POST'
        return flask.jsonify(res)

if __name__ == "__main__":
    '''
    1. get all item
    2. return choose item
    3. return result
    '''

    # start the web server
    # 프로덕션 환경에서는 PORT 환경 변수 사용, 로컬에서는 5050
    port = int(os.environ.get('PORT', 5050))
    debug_mode = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    print("* Starting web service...")
    app.run(host='0.0.0.0', port=port, debug=debug_mode)