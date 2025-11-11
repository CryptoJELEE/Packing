"""
matplotlib 한글 폰트 설정 유틸리티
"""
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from pathlib import Path
import platform
import os

# 프로젝트 내 폰트 디렉토리
FONT_DIR = Path(__file__).parent.parent.parent / 'fonts'

def download_font_if_needed():
    """필요시 폰트 다운로드"""
    font_path = FONT_DIR / 'NanumGothic.ttf'
    
    if font_path.exists():
        return str(font_path)
    
    # 폰트 디렉토리 생성
    FONT_DIR.mkdir(exist_ok=True)
    
    # 온라인에서 폰트 다운로드 시도
    try:
        import urllib.request
        # 여러 URL 시도
        font_urls = [
            'https://fonts.gstatic.com/ea/nanumgothic/v5/NanumGothic-Regular.ttf',
            'https://github.com/naver/nanumfont/raw/master/Desktop/NanumGothic.ttf',
            'https://raw.githubusercontent.com/naver/nanumfont/master/Desktop/NanumGothic.ttf',
        ]
        
        for font_url in font_urls:
            try:
                print(f"폰트 다운로드 시도: {font_url}")
                urllib.request.urlretrieve(font_url, font_path)
                if font_path.exists() and os.path.getsize(font_path) > 1000:
                    print(f"폰트 다운로드 완료: {font_path}")
                    return str(font_path)
            except Exception as e:
                print(f"다운로드 실패: {e}")
                continue
        
        return None
    except Exception as e:
        print(f"폰트 다운로드 실패: {e}")
        return None

def setup_korean_font():
    """한글 폰트 설정 (개선 버전)"""
    # 1. 프로젝트 내 폰트 파일 시도
    font_path = download_font_if_needed()
    
    if font_path and os.path.exists(font_path):
        try:
            # 폰트 파일 직접 로드
            font_prop = fm.FontProperties(fname=font_path)
            font_name = font_prop.get_name()
            
            # matplotlib 설정
            plt.rcParams['font.family'] = font_name
            matplotlib.rcParams['font.family'] = font_name
            plt.rcParams['axes.unicode_minus'] = False
            matplotlib.rcParams['axes.unicode_minus'] = False
            
            # 폰트 캐시에 추가
            try:
                # 폰트 매니저에 폰트 추가
                fm.fontManager.addfont(font_path)
            except:
                pass
            
            print(f"폰트 설정 완료 (파일): {font_name}")
            return font_name
        except Exception as e:
            print(f"폰트 파일 로드 실패: {e}")
    
    # 2. 시스템 폰트 시도
    system = platform.system()
    
    if system == 'Darwin':  # macOS
        font_list = ['AppleGothic', 'Apple SD Gothic Neo', 'NanumGothic', 'NanumBarunGothic']
    elif system == 'Windows':  # Windows
        font_list = ['Malgun Gothic', 'NanumGothic', 'Gulim', 'Batang']
    else:  # Linux
        font_list = ['NanumGothic', 'NanumBarunGothic', 'Noto Sans CJK KR', 'DejaVu Sans']
    
    available_fonts = [f.name for f in fm.fontManager.ttflist]
    
    for font_name in font_list:
        if font_name in available_fonts:
            plt.rcParams['font.family'] = font_name
            matplotlib.rcParams['font.family'] = font_name
            plt.rcParams['axes.unicode_minus'] = False
            matplotlib.rcParams['axes.unicode_minus'] = False
            print(f"시스템 폰트 사용: {font_name}")
            return font_name
    
    # 3. 폴백: DejaVu Sans
    plt.rcParams['font.family'] = 'DejaVu Sans'
    matplotlib.rcParams['font.family'] = 'DejaVu Sans'
    plt.rcParams['axes.unicode_minus'] = False
    matplotlib.rcParams['axes.unicode_minus'] = False
    print("경고: 한글 폰트를 찾을 수 없습니다. DejaVu Sans 사용 (한글 표시 불가)")
    return None

def get_korean_font_path():
    """한글 폰트 파일 경로 찾기"""
    # 프로젝트 내 폰트 우선
    font_path = FONT_DIR / 'NanumGothic.ttf'
    if font_path.exists():
        return str(font_path)
    
    # 시스템 폰트 경로
    system = platform.system()
    
    if system == 'Darwin':  # macOS
        font_paths = [
            '/System/Library/Fonts/AppleGothic.ttf',
            '/Library/Fonts/NanumGothic.ttf',
            '/Library/Fonts/NanumBarunGothic.ttf',
            os.path.expanduser('~/Library/Fonts/NanumGothic.ttf'),
        ]
    elif system == 'Windows':
        font_paths = [
            'C:/Windows/Fonts/malgun.ttf',
            'C:/Windows/Fonts/gulim.ttc',
            'C:/Windows/Fonts/batang.ttc',
        ]
    else:  # Linux
        font_paths = [
            '/usr/share/fonts/truetype/nanum/NanumGothic.ttf',
            '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
        ]
    
    for path in font_paths:
        if os.path.exists(path):
            return path
    
    return None

# 모듈 로드 시 자동으로 폰트 설정
_configured_font = setup_korean_font()
