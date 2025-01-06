from datetime import datetime
import logging
from logging.handlers import RotatingFileHandler
import os
from .app_config import ResourceManager
import traceback

# 상수 정의
LOG_FILE_MAX_SIZE = 1 * 1024 * 1024  # 1MB
LOG_FILE_BACKUP_COUNT = 5
LOG_FORMAT = '%(asctime)s - [%(process)d] - %(name)s - %(levelname)s - %(message)s'
LOG_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'
LOGGER_NAME = 'dell_idrac_monitor'

class TimestampRotatingFileHandler(RotatingFileHandler):
    def rotation_filename(self, default_name):
        dir_name = os.path.dirname(default_name)
        base_name = os.path.basename(default_name)
        timestamp = datetime.now().strftime('%Y%m%d')
        return os.path.join(dir_name, f'{timestamp}-{base_name}')

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

def setup_logging():
    logger = logging.getLogger(LOGGER_NAME)
    if logger.handlers:
        return logger
        
    logger.setLevel(logging.DEBUG)
    
    log_dir = ResourceManager.get_log_dir()
    log_file = log_dir / 'app.log'
    
    file_handler = TimestampRotatingFileHandler(
        str(log_file),
        maxBytes=LOG_FILE_MAX_SIZE,
        backupCount=LOG_FILE_BACKUP_COUNT,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    
    formatter = logging.Formatter(LOG_FORMAT, LOG_DATE_FORMAT)
    file_handler.setFormatter(formatter)
    
    connection_filter = ConnectionLogFilter()
    file_handler.addFilter(connection_filter)
    
    logger.addHandler(file_handler)
    
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    return logger

def log_connection_status(status):
    logger = logging.getLogger(LOGGER_NAME)
    if status.is_connected:
        logger.info(f"서버 {status.server_name}({status.server_ip})에 연결되었습니다.")
    else:
        logger.info(f"서버 {status.server_name}({status.server_ip})와의 연결이 끊어졌습니다.")

def log_server_update(server):
    logger = logging.getLogger(LOGGER_NAME)
    logger.debug(f"서버 정보 업데이트: {server.name}({server.ip})")
    logger.debug(f"CPU 상태: {server.cpu_status}")
    logger.debug(f"메모리 상태: {server.memory_status}")
    logger.debug(f"전원 상태: {server.power_status}")
    logger.debug(f"팬 상태: {server.fan_status}")
