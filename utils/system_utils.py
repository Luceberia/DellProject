import platform
from PyQt6.QtGui import QFont
import matplotlib.pyplot as plt

def get_system_monospace_font(size=10):
    """
    운영 체제에 맞는 기본 등폭 폰트를 반환합니다.
    
    Args:
        size (int): 폰트 크기 (기본값: 10)
    
    Returns:
        QFont: 시스템에 맞는 등폭 폰트
    """
    os_name = platform.system().lower()
    
    font_map = {
        'darwin': ('Menlo', 10),   # macOS
        'windows': ('Consolas', 10),  # Windows
        'linux': ('DejaVu Sans Mono', 10)  # Linux (Ubuntu 등)
    }
    
    font_name, default_size = font_map.get(os_name, ('Monospace', 10))
    
    # 사용자가 지정한 크기가 있으면 그 크기 사용, 없으면 기본 크기 사용
    font_size = size if size else default_size
    
    return QFont(font_name, font_size)

def get_system_matplotlib_font():
    """
    운영 체제에 맞는 matplotlib 한글 폰트를 설정합니다.
    
    Returns:
        str: 시스템에 맞는 한글 폰트 이름
    """
    os_name = platform.system().lower()
    
    # 한글 폰트 맵핑
    hangul_font_map = {
        'darwin': 'AppleGothic',   # macOS
        'windows': 'Malgun Gothic',  # Windows
        'linux': 'NanumGothic'  # Linux
    }
    
    # 선택된 폰트 이름
    font_name = hangul_font_map.get(os_name, 'sans-serif')
    
    # matplotlib 한글 폰트 설정
    plt.rcParams['font.family'] = font_name
    plt.rcParams['axes.unicode_minus'] = False
    
    return font_name
