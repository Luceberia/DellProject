import platform
from PyQt6.QtGui import QFont

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
