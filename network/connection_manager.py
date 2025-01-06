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
        self.redfish_client = None

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
                    self.connection_status_callback(True)
                return True
            return False
        except Exception as e:
            logger.error(f"서버 연결 확인 실패: {str(e)}")
            return False

    def disconnect_server(self, server_name):
        """서버 연결 해제 메서드"""
        from config.server.server_config import server_config

        try:
            # 서버가 존재하고 연결된 상태인지 확인
            if server_name in server_config.servers and server_config.servers[server_name].CONNECTED:
                logger.debug(f"서버 연결 해제 시작: {server_name}")
                
                # Redfish 세션 종료
                if self.redfish_client:
                    try:
                        self.redfish_client.logout()
                        logger.debug(f"Redfish 세션 로그아웃: {server_name}")
                    except Exception as e:
                        logger.error(f"Redfish 세션 로그아웃 실패: {str(e)}")
                
                # 연결 상태 업데이트
                server_config.servers[server_name].set_connected(False)
                
                # 연결 관련 리소스 초기화
                self.redfish_client = None
                self.current_server = None
                self.is_connected = False
                
                # 세션 초기화
                self.session = requests.Session()
                self.session.verify = False
                
                logger.info(f"서버 연결 해제 완료: {server_name}")
                
                # UI 콜백 호출
                if self.connection_status_callback:
                    self.connection_status_callback(False)
                
                return True
            else:
                logger.warning(f"연결 해제할 서버를 찾을 수 없거나 이미 연결 해제됨: {server_name}")
                return False
        
        except Exception as e:
            logger.error(f"서버 연결 해제 중 오류 발생: {str(e)}")
            return False

    def check_connection_with_timeout(self, server_info, timeout=5):
        """서버 연결 상태 및 응답 시간 확인"""
        try:
            start_time = time.time()
            url = f"https://{server_info['IP']}:{server_info['PORT']}"
            
            response = self.session.get(url, timeout=timeout, verify=False)
            
            if response.status_code == 200:
                response_time = int((time.time() - start_time) * 1000)  # 밀리초 단위
                self.is_connected = True
                self.current_server = server_info
                
                logger.debug(f"서버 연결 성공: {server_info['IP']}:{server_info['PORT']} (응답 시간: {response_time}ms)")
                
                # UI 업데이트 콜백 호출
                if self.connection_status_callback:
                    self.connection_status_callback(True)
                
                return response_time
            return None
        
        except requests.exceptions.RequestException as e:
            logger.error(f"서버 연결 확인 실패: {str(e)}")
            return None

    async def disconnect(self):
        """서버 연결 해제"""
        if self.current_server:
            logger.info(f"서버 연결 해제: {self.current_server['IP']}")
            self.current_server = None
            self.is_connected = False
