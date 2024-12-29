from datetime import datetime
from pathlib import Path
import logging
from logging.handlers import RotatingFileHandler
from typing import Optional
import os
import sys
import time

# 상수 정의
LOG_FILE_MAX_SIZE = 1 * 1024 * 1024  # 1MB
LOG_FILE_BACKUP_COUNT = 5
LOG_FORMAT = '%(asctime)s - [%(process)d] - %(name)s - %(levelname)s - %(message)s'
LOG_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'
FILE_LOG_LEVEL = logging.DEBUG
CONSOLE_LOG_LEVEL = logging.INFO
LOGGER_NAME = 'dell_idrac_monitor'

class TimestampRotatingFileHandler(RotatingFileHandler):
    def rotation_filename(self, default_name):
        """로그 로테이션 시 timestamp를 포함한 파일명 생성"""
        dir_name = os.path.dirname(default_name)
        base_name = os.path.basename(default_name)
        timestamp = datetime.now().strftime('%Y%m%d-%H:%M:%S')
        return os.path.join(dir_name, f'{timestamp}-{base_name}')

    def rotate(self, source, dest):
        """기존 로그 파일을 timestamp 포함된 이름으로 변경"""
        if os.path.exists(source):
            os.rename(source, dest)
            
    def compress_file(self, file_path):
        compressed_file = file_path + '.gz'
        with open(file_path, 'rb') as f_in:
            with gzip.open(compressed_file, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
        os.remove(file_path)

def get_app_dir():
    """애플리케이션 디렉토리를 찾습니다."""
    if getattr(sys, 'frozen', False):
        # PyInstaller로 패키징된 경우
        return Path(sys._MEIPASS)
    else:
        # 일반 Python 스크립트로 실행되는 경우
        current_dir = Path(__file__).resolve().parent
        while current_dir.name != 'app' and current_dir != current_dir.parent:
            current_dir = current_dir.parent
        return current_dir

def get_log_dir():
    """로그 디렉토리를 결정합니다."""
    if getattr(sys, 'frozen', False):
        # 배포 모드 (PyInstaller로 패키징된 경우)
        if sys.platform == 'darwin':  # macOS
            log_dir = Path.home() / 'Library' / 'Logs' / 'DellIDRACMonitor' # ~/Library/Logs/DellIDRACMonitor/
        elif sys.platform == 'win32':  # Windows
            log_dir = Path(os.getenv('APPDATA')) / 'DellIDRACMonitor' / 'Logs'
        else:  # Linux 등 기타 OS
            log_dir = Path.home() / '.dell_idrac_monitor' / 'logs'
    else:
        # 개발 모드
        log_dir = get_app_dir() / 'dell_logging'
    
    # 디렉토리가 없으면 생성
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir

class ConnectionLogFilter(logging.Filter):
    """연결 상태 로그 필터"""
    def __init__(self):
        super().__init__()
        self.last_status = None
        self.is_connected = False

    def filter(self, record):
        # 연결 상태 관련 메시지 필터링
        if "연결 상태 업데이트" in record.msg or "서버 연결 성공" in record.msg:
            if ("연결 끊김" in record.msg or "서버 연결 거부됨" in record.msg) and self.is_connected:
                self.is_connected = False
                return True
            elif ("연결됨" in record.msg or "서버 연결 성공" in record.msg) and not self.is_connected:
                self.is_connected = True
                return True
            elif "응답 없음" in record.msg or "연결 실패" in record.msg or "응답 지연" in record.msg:
                return True
            return False
            
        # API 요청 로그는 DEBUG 레벨로만 기록
        if "Redfish API 요청" in record.msg:
            return record.levelno == logging.DEBUG
            
        # 시스템 상태나 정보 업데이트는 변경이 있을 때만 기록
        if "시스템 상태" in record.msg or "정보 업데이트" in record.msg:
            current_status = record.msg
            if current_status != self.last_status:
                self.last_status = current_status
                return True
            return False
            
        # 애플리케이션 시작/종료 관련 로그는 항상 기록
        if any(msg in record.msg for msg in ["애플리케이션 시작", "애플리케이션 종료", "리소스 정리"]):
            return True
            
        return True

def setup_logging():
    """로깅 설정"""
    logger = logging.getLogger(LOGGER_NAME)
    if logger.handlers:  # 이미 핸들러가 설정되어 있으면 리턴
        return logger
        
    logger.setLevel(logging.DEBUG)  # DEBUG 레벨로 변경하여 더 상세한 로그 기록
    
    # 로그 파일 경로 설정
    log_dir = get_log_dir()  # 새로운 함수 사용
    log_file = log_dir / 'app.log'
    
    # 파일 핸들러 설정
    file_handler = TimestampRotatingFileHandler(
        str(log_file),
        maxBytes=LOG_FILE_MAX_SIZE,
        backupCount=LOG_FILE_BACKUP_COUNT,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)  # 파일에는 DEBUG 레벨까지 기록
    
    # 포매터 설정
    formatter = logging.Formatter(
        LOG_FORMAT,
        LOG_DATE_FORMAT
    )
    file_handler.setFormatter(formatter)
    
    # 연결 상태 관련 로그 필터
    connection_filter = ConnectionLogFilter()
    file_handler.addFilter(connection_filter)
    
    logger.addHandler(file_handler)
    
    # 콘솔 핸들러 설정 - 콘솔에는 중요한 메시지만 출력
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter(LOG_FORMAT, LOG_DATE_FORMAT)
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    return logger

# 전역 logger 객체 생성
logger = setup_logging()

def log_connection_status(status):
    """연결 상태 로깅
    
    Args:
        status: 연결 상태 객체
    """
    if status.is_connected:
        logger.info(f"서버 {status.server_name}({status.server_ip})에 연결되었습니다.")
    else:
        logger.info(f"서버 {status.server_name}({status.server_ip})와의 연결이 끊어졌습니다.")

def log_server_update(server):
    """서버 정보 업데이트 로깅
    
    Args:
        server: 서버 정보 객체
    """
    logger.debug(f"서버 정보 업데이트: {server.name}({server.ip})")
    logger.debug(f"CPU 상태: {server.cpu_status}")
    logger.debug(f"메모리 상태: {server.memory_status}")
    logger.debug(f"전원 상태: {server.power_status}")
    logger.debug(f"팬 상태: {server.fan_status}")
