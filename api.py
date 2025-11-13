
import flask
import json
import random
import os
import uuid
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict
from werkzeug.utils import secure_filename
from py3dbp import Packer, Bin, Item
from flask_cors import cross_origin
from flask import render_template, send_from_directory, request

# 새로운 모듈 구조 import
from core.data.csv_processor import CSVDataProcessor
from core.packing.pipeline import PackingPipeline
from core.data.master_manager import MasterDataManager
from core.data.order_processor import OrderProcessor
from config.settings import Config

# Supabase 사용 시도
try:
    from core.storage.supabase_client import supabase_client
    USE_SUPABASE_SESSION = True
except ImportError:
    USE_SUPABASE_SESSION = False
    print("Supabase 클라이언트를 사용할 수 없습니다. 인메모리 세션을 사용합니다.")

# init flask
app = flask.Flask(__name__)
app.config.from_object(Config)
Config.init_app(app)

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# load data
try:
    with open('widadvance.json',encoding='utf-8') as f:
        alldata = json.load(f)
except:
    alldata = {"box": [], "item": []}

# 세션 데이터 저장 (Supabase 우선, 실패 시 인메모리)
session_data = {}

# 전역 마스터 매니저
master_manager = MasterDataManager()

# Supabase 세션 관리 함수
def save_session(session_id: str, session_type: str, data: dict):
    """세션을 Supabase에 저장 (실패 시 인메모리)"""
    if USE_SUPABASE_SESSION:
        try:
            sessions_table = supabase_client.get_table('sessions')
            expires_at = (datetime.now() + timedelta(days=7)).isoformat()
            
            sessions_table.upsert({
                'session_id': session_id,
                'session_type': session_type,
                'data': data,
                'expires_at': expires_at
            }).execute()
            return True
        except Exception as e:
            print(f"Supabase 세션 저장 오류: {str(e)}, 인메모리로 저장")
    
    # 인메모리 저장
    session_data[session_id] = {
        'type': session_type,
        **data
    }
    return True

def get_session(session_id: str) -> Optional[Dict]:
    """Supabase에서 세션 조회 (실패 시 인메모리)"""
    if USE_SUPABASE_SESSION:
        try:
            sessions_table = supabase_client.get_table('sessions')
            response = sessions_table.select("*").eq('session_id', session_id).execute()
            
            if response.data and len(response.data) > 0:
                session = response.data[0]
                # 만료 확인
                expires_at = session.get('expires_at')
                if expires_at:
                    try:
                        exp_time = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
                        if exp_time < datetime.now(exp_time.tzinfo):
                            return None
                    except Exception as e:
                        logger.warning(f"세션 만료 시간 파싱 오류: {str(e)}")
                
                session_data_dict = session.get('data', {})
                session_data_dict['type'] = session.get('session_type', '')
                return session_data_dict
        except Exception as e:
            print(f"Supabase 세션 조회 오류: {str(e)}, 인메모리에서 조회")
    
    # 인메모리에서 조회
    return session_data.get(session_id)

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
        q = json.loads(flask.request.data.decode('utf-8'))
        if 'box' in q.keys() and 'item' in q.keys() and 'binding' in q.keys():
            try :
                packer,box,binding = getBoxAndItem(q)
            except :
                res["Reason"] = "input data err"
                return res
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


def makeDictBox(box):
    position = (int(box.width)/2,int(box.height)/2,int(box.depth)/2)
    r = {
            "partNumber" : box.partno,
            "position" : position,
            "WHD" : (int(box.width),int(box.height),int(box.depth)),
            "weight" : int(box.max_weight),
            "gravity" : box.gravity
        }
    return [r]


def makeDictItem(item):
    ''' '''

    if item.rotation_type == 0:
        pos = (int(item.position[0]) + int(item.width)//2,int(item.position[1])+ int(item.height)//2,int(item.position[2])+ int(item.depth)//2)
        whd = (int(item.width),int(item.height),int(item.depth))
    elif item.rotation_type == 1:
        pos = (int(item.position[0])+ int(item.height)//2,int(item.position[1]) + int(item.width)//2,int(item.position[2])+ int(item.depth)//2)
        whd = (int(item.height),int(item.width),int(item.depth))
    elif item.rotation_type == 2:
        pos = (int(item.position[0])+ int(item.height)//2,int(item.position[1])+ int(item.depth)//2,int(item.position[2]) + int(item.width)//2)
        whd = (int(item.height),int(item.depth),int(item.width))
    elif item.rotation_type == 3:
        pos = (int(item.position[0])+ int(item.depth)//2,int(item.position[1])+ int(item.height)//2,int(item.position[2]) + int(item.width)//2)
        whd = (int(item.depth),int(item.height),int(item.width))
    elif item.rotation_type == 4:
        pos = (int(item.position[0])+ int(item.depth)//2,int(item.position[1]) + int(item.width)//2,int(item.position[2])+ int(item.height)//2)
        whd = (int(item.depth),int(item.width),int(item.height))
    elif item.rotation_type == 5:
        pos = (int(item.position[0]) + int(item.width)//2,int(item.position[1])+ int(item.depth)//2,int(item.position[2])+ int(item.height)//2)
        whd = (int(item.width),int(item.depth),int(item.height))
    
    r = {
        "partNumber" : item.partno,
        "name" : item.name,
        "type" : item.typeof,
        "color" : item.color,
        "position" : pos,
        "rotationType" : item.rotation_type,
        "WHD" : whd,
        "weight" : int(item.weight)
    }

    return r


def getBoxAndItem(data):
    ''' '''
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
    # get item data  TODO
    item_data = data["item"]
    color_dict = {
        1:'red',
        2:'yellow',
        3:'blue',
        4:'green',
        5:'purple',
        6:'brown',
        7:'orange'
    }
    for i in item_data :
        for j in range(i['count']) :
            packer.addItem(Item(
            partno = i['name']+'-{}'.format(str(j+1)),
            name = i['name'],
            typeof = 'cylinder' if i['type'] == 2 else 'cube',
            WHD = i['WHD'], 
            weight = i['weight'],
            level = 1 if i['level'] == 1 else 2,
            loadbear = i['loadbear'],
            updown = bool(i['updown']),
            color = randColor(i['color']))
        )
    binding_data = data['binding']
    binding = []
    if len(binding_data) != 0:
        for i in binding_data :
            binding.append(tuple(i))

    return packer,box,binding


def randColor(s):
    ''' '''
    random.seed(s)
    color = "#"+''.join([random.choice('0123456789ABCDEF') for j in range(6)])

    return color


# 마스터 데이터 업로드
@app.route('/api/uploadMaster', methods=['POST'])
@cross_origin()
def upload_master():
    """자재마스터 CSV 업로드 및 저장"""
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
        filepath = os.path.join(str(Config.UPLOAD_FOLDER), f"master_{filename}")
        Config.UPLOAD_FOLDER.mkdir(exist_ok=True)
        file.save(filepath)
        
        # CSV 처리
        processor = CSVDataProcessor(filepath)
        items = processor.process_all_items()
        
        # 마스터 데이터에 추가
        master_manager.add_master_items(items)
        stats = master_manager.get_master_stats()
        
        res["Success"] = True
        res["message"] = f"마스터 데이터 {len(items)}개 항목이 저장되었습니다."
        res["stats"] = stats
        
        return flask.jsonify(res)
    except Exception as e:
        res["Reason"] = f"파일 처리 오류: {str(e)}"
        import traceback
        traceback.print_exc()
        return flask.jsonify(res)

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
    res = {"Success": False}
    
    if not master_manager.has_master_data():
        res["Reason"] = "먼저 자재마스터를 업로드해주세요."
        return flask.jsonify(res)
    
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
        filepath = os.path.join(str(Config.UPLOAD_FOLDER), f"order_{filename}")
        Config.UPLOAD_FOLDER.mkdir(exist_ok=True)
        file.save(filepath)
        
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
        
        res["Success"] = True
        res["session_id"] = session_id
        res["matched_count"] = len(result['matched_items'])
        res["unmatched_count"] = len(result['unmatched_items'])
        res["total_quantity"] = result['total_quantity']
        res["matched_items"] = result['matched_items'][:50]  # 미리보기
        res["unmatched_items"] = result['unmatched_items']
        
        return flask.jsonify(res)
    except Exception as e:
        res["Reason"] = f"주문서 처리 오류: {str(e)}"
        import traceback
        traceback.print_exc()
        return flask.jsonify(res)

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
    """패킹 계산 (기존 + CSV 지원)"""
    res = {"Success": False}
    
    if request.method == "POST":
        try:
            # JSON 데이터 받기
            if request.is_json:
                q = request.get_json()
            else:
                q = json.loads(request.data.decode('utf-8'))
            
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
                    except:
                        res["Reason"] = "input data err"
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