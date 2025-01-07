from datetime import datetime
import logging
from logging.handlers import RotatingFileHandler
import os
from .app_config import ResourceManager

# 상수 정의
LOG_FILE_MAX_SIZE = 1 * 1024 * 1024  # 1MB
LOG_FILE_BACKUP_COUNT = 5
LOG_FORMAT = '%(asctime)s - [%(process)d] - %(name)s - %(levelname)s - [서버: %(server)s] - %(message)s'
LOG_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'
LOGGER_NAME = 'dell_idrac_monitor'

class TimestampRotatingFileHandler(RotatingFileHandler):
    def rotation_filename(self, default_name):
        # 개발 모드와 배포 모드 모두에서 동일한 로그 파일 이름 생성
        dir_name = os.path.dirname(default_name)
        base_name = os.path.basename(default_name)
        timestamp = datetime.now().strftime('%Y%m%d')
        return os.path.join(dir_name, f'{timestamp}-{base_name}.1')

    def rotate(self, source, dest):
        if os.path.exists(source):
            os.rename(source, dest)

class ConnectionLogFilter(logging.Filter):
    def __init__(self):
        super().__init__()
        self.last_status = None
        self.is_connected = False

    def filter(self, record):
        try:
            if "연결 상태 업데이트" in str(record.msg) or "서버 연결 성공" in str(record.msg):
                if ("연결 끊김" in str(record.msg) or "서버 연결 거부됨" in str(record.msg)) and self.is_connected:
                    self.is_connected = False
                    return True
                elif ("연결됨" in str(record.msg) or "서버 연결 성공" in str(record.msg)) and not self.is_connected:
                    self.is_connected = True
                    return True
                elif "응답 없음" in str(record.msg) or "연결 실패" in str(record.msg) or "응답 지연" in str(record.msg):
                    return True
                return False
                
            if "Redfish API 요청" in str(record.msg):
                # SEL 및 LC 로그 엔트리 조회는 로깅하지 않음
                if "로그 엔트리 조회" in str(record.msg):
                    return False
                
                # 현재 활성 서버 상태 유지
                record.server = _current_active_server
                
                return record.levelno == logging.DEBUG
                
            if "시스템 상태" in str(record.msg) or "정보 업데이트" in str(record.msg):
                current_status = str(record.msg)
                if current_status != self.last_status:
                    self.last_status = current_status
                    return True
                return False
                
            if any(msg in str(record.msg) for msg in ["애플리케이션 시작", "애플리케이션 종료", "리소스 정리"]):
                return True
                
            return True
        except Exception as e:
            # 예외 발생 시 기본적으로 로그를 허용
            return True

class DefaultServerFilter(logging.Filter):
    def filter(self, record):
        if not hasattr(record, 'server'):
            record.server = 'SYSTEM'
        return True

_current_active_server = 'SYSTEM'

def set_current_server(server_name):
    """
    현재 활성 서버를 설정하는 함수
    모든 로그에 이 서버 이름을 적용
    """
    global _current_active_server
    _current_active_server = server_name

def get_logger(name=LOGGER_NAME, server=None):
    """
    서버 정보를 포함한 로거를 반환하는 함수
    server 파라미터가 없으면 전역 활성 서버 사용
    """
    logger = logging.getLogger(name)
    
    # 모든 로거에 DefaultServerFilter 추가 (중복 추가 방지)
    has_server_filter = any(isinstance(f, DefaultServerFilter) for f in logger.filters)
    if not has_server_filter:
        logger.addFilter(DefaultServerFilter())
    
    class ServerLoggerAdapter(logging.LoggerAdapter):
        def process(self, msg, kwargs):
            # 서버 정보 설정 우선순위: 
            # 1. 직접 전달된 서버 
            # 2. 전역 활성 서버
            # 3. 기본값 'SYSTEM'
            server_name = server or _current_active_server or 'SYSTEM'
            kwargs.setdefault('extra', {})['server'] = server_name
            return msg, kwargs
    
    return ServerLoggerAdapter(logger, {})

def setup_logging():
    logger = get_logger(LOGGER_NAME)
    if logger.logger.handlers:
        return logger
        
    logger.logger.setLevel(logging.DEBUG)
    
    log_dir = ResourceManager.get_log_dir()
    log_file = log_dir / 'app.log'
    
    file_handler = TimestampRotatingFileHandler(
        str(log_file),
        maxBytes=LOG_FILE_MAX_SIZE,
        backupCount=LOG_FILE_BACKUP_COUNT,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    
    # 기본 서버 정보를 제공하는 필터 추가
    default_server_filter = DefaultServerFilter()
    file_handler.addFilter(default_server_filter)
    logger.logger.addFilter(default_server_filter)
    
    formatter = logging.Formatter(LOG_FORMAT, LOG_DATE_FORMAT)
    file_handler.setFormatter(formatter)
    
    connection_filter = ConnectionLogFilter()
    file_handler.addFilter(connection_filter)
    logger.logger.addFilter(connection_filter)
    
    logger.logger.addHandler(file_handler)
    
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    console_handler.addFilter(default_server_filter)
    logger.logger.addHandler(console_handler)
    
    return logger

# 기존 로깅 함수들 수정
def log_connection_status(status):
    logger = get_logger(LOGGER_NAME)
    logger.info(f"서버 연결 상태 업데이트: {status}")

def log_server_update(server):
    logger = get_logger(LOGGER_NAME)
    logger.info(f"서버 정보 업데이트: {server}")
