import socket
import logging
from typing import Tuple

logger = logging.getLogger(__name__)

def check_internet_connection(timeout: int = 3) -> Tuple[bool, str]:
    """
    인터넷 연결 상태를 확인합니다.
    
    Args:
        timeout (int): 연결 시도 제한 시간 (초)
        
    Returns:
        Tuple[bool, str]: (연결 성공 여부, 메시지)
    """
    try:
        # Google DNS 서버로 연결 시도
        socket.setdefaulttimeout(timeout)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect(("8.8.8.8", 53))
        return True, "인터넷 연결이 정상입니다."
    except (socket.timeout, socket.error) as ex:
        logger.warning(f"인터넷 연결 확인 실패: {str(ex)}")
        return False, "인터넷 연결을 확인할 수 없습니다."
