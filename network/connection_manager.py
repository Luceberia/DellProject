import requests
import asyncio
import time
from config.system.log_config import setup_logging

logger = setup_logging()

class ConnectionManager:
    def __init__(self):
        self.session = requests.Session()
        self.current_server = None
        self.is_connected = False
        self.connection_status_callback = None

    def set_status_callback(self, callback):
        """UI 업데이트 콜백 설정"""
        self.connection_status_callback = callback

    def check_connection(self, server_info):
        """서버 연결 상태 확인"""
        try:
            url = f"https://{server_info['IP']}:{server_info['PORT']}"
            logger.debug(f"서버 연결 확인 시도: {url}")
            
            response = self.session.get(url, timeout=5, verify=False)
            if response.status_code == 200:
                self.is_connected = True
                self.current_server = server_info
                logger.info(f"서버 연결 성공: {server_info['IP']}:{server_info['PORT']}")
                
                # UI 업데이트 콜백 호출
                if self.connection_status_callback:
                    self.connection_status_callback("연결됨")
                return True
            else:
                if self.connection_status_callback:
                    self.connection_status_callback("연결 실패")
                return False
                
        except requests.RequestException as e:
            self.is_connected = False
            logger.error(f"서버 연결 오류: {str(e)}")
            if self.connection_status_callback:
                self.connection_status_callback("재시도")
            return False

    def check_connection_with_timeout(self, server_info, timeout=5):
        """서버 연결 상태 및 응답 시간 확인"""
        try:
            url = f"https://{server_info['IP']}:{server_info['PORT']}/redfish/v1/Systems/System.Embedded.1"
            start_time = time.time()
            
            response = self.session.get(
                url,
                auth=(server_info['USERNAME'], server_info['PASSWORD']),
                verify=False,
                timeout=timeout
            )
            
            end_time = time.time()
            response_time = int((end_time - start_time) * 1000)  # ms 단위로 변환
            
            if response.status_code == 200:
                self.is_connected = True
                self.current_server = server_info
                
                if self.connection_status_callback:
                    self.connection_status_callback("연결됨")
                    
                return response_time
            else:
                if self.connection_status_callback:
                    self.connection_status_callback("연결 실패")
                return None
                
        except requests.exceptions.Timeout:
            if self.connection_status_callback:
                self.connection_status_callback("연결 시간 초과")
            return None
        except requests.exceptions.ConnectionError:
            logger.error("서버 연결 거부됨")
            return None
        except Exception as e:
            logger.error(f"서버 연결 오류: {str(e)}")
            return None

    async def disconnect(self):
        """서버 연결 해제"""
        if self.current_server:
            logger.info(f"서버 연결 해제: {self.current_server['IP']}")
            self.current_server = None
            self.is_connected = False
