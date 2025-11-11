"""
matplotlib 한글 폰트 설정 유틸리티
"""
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import platform
import os

def setup_korean_font():
    """한글 폰트 설정"""
    system = platform.system()
    
    # 폰트 설정
    if system == 'Darwin':  # macOS
        font_list = [
            'AppleGothic',
            'Apple SD Gothic Neo',
            'NanumGothic',
            'NanumBarunGothic',
        ]
    elif system == 'Windows':  # Windows
        font_list = [
            'Malgun Gothic',
            'NanumGothic',
            'Gulim',
            'Batang',
        ]
    else:  # Linux
        font_list = [
            'NanumGothic',
            'NanumBarunGothic',
            'DejaVu Sans',
            'Noto Sans CJK KR',
        ]
    
    # 사용 가능한 폰트 찾기
    available_fonts = [f.name for f in fm.fontManager.ttflist]
    
    selected_font = None
    for font_name in font_list:
        if font_name in available_fonts:
            selected_font = font_name
            break
    
    if selected_font:
        plt.rcParams['font.family'] = selected_font
        plt.rcParams['axes.unicode_minus'] = False  # 마이너스 기호 깨짐 방지
        matplotlib.rcParams['font.family'] = selected_font
        matplotlib.rcParams['axes.unicode_minus'] = False
        return selected_font
    else:
        # 폰트를 찾지 못한 경우 기본 설정
        plt.rcParams['font.family'] = 'DejaVu Sans'
        plt.rcParams['axes.unicode_minus'] = False
        matplotlib.rcParams['font.family'] = 'DejaVu Sans'
        matplotlib.rcParams['axes.unicode_minus'] = False
        return None

def get_korean_font_path():
    """한글 폰트 파일 경로 찾기"""
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

