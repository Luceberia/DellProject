from config.system.log_config import setup_logging
from config.data.models import IDRACConfig
from utils.server_utils import convert_to_idrac_config
from utils.config_utils import ConfigManager
from typing import Dict, Optional, Any
from datetime import datetime, timedelta

# logger 객체 생성
logger = setup_logging()

class ServerConfig:
    _instance = None
    _RELOAD_INTERVAL = timedelta(minutes=5)  # 설정 파일 재로드 간격
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ServerConfig, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self.config_manager = ConfigManager()
            self.servers: Dict[str, IDRACConfig] = {}
            self.observers = []
            self.quick_connect_server = None
            self._last_load_time = None  # 마지막 로드 시간 추적
            self._initialized = True
            self._load_servers()  # 초기화 시 서버 로드 복원
    
    def _validate_server_config(self, server_info: Dict[str, Any]) -> bool:
        """서버 설정 유효성 검사 메서드"""
        required_keys = ['NAME', 'IP', 'USERNAME', 'PASSWORD']
        return (
            isinstance(server_info, dict) and 
            all(key in server_info for key in required_keys)
        )
    
    def _convert_server_to_dict(self, server: IDRACConfig) -> Dict[str, Any]:
        """서버 객체를 딕셔너리로 변환하는 공통 메서드"""
        return {
            'NAME': server.NAME,
            'IP': server.IP,
            'PORT': server.PORT,
            'USERNAME': server.USERNAME,
            'PASSWORD': server.PASSWORD
        }
    
    def load_servers(self) -> Dict[str, IDRACConfig]:
        """외부에서 호출 가능한 서버 정보 로드 메서드"""
        current_time = datetime.now()
        
        # 캐시된 데이터 재사용 또는 강제 새로고침
        if (not self.servers or 
            not self._last_load_time or 
            current_time - self._last_load_time > self._RELOAD_INTERVAL):
            return self._load_servers()
        
        return self.servers
    
    def _load_servers(self) -> Dict[str, IDRACConfig]:
        """서버 정보 로드 (내부 메서드)"""
        try:
            config = self.config_manager.load_config()
            
            # 서버 정보 로드
            self.servers.clear()  # 기존 서버 정보 초기화
            for name, server_info in config.items():
                if name != 'quick_connect_server':
                    try:
                        if self._validate_server_config(server_info):
                            self.servers[name] = convert_to_idrac_config(server_info)
                        else:
                            logger.warning(f"잘못된 서버 설정 형식: {name}")
                    except Exception as e:
                        logger.error(f"서버 정보 변환 실패 ({name}): {str(e)}")
            
            # 빠른 연결 서버 설정 로드
            self.quick_connect_server = config.get('quick_connect_server')
            
            # 로드 시간 업데이트
            self._last_load_time = datetime.now()
            
            logger.debug(f"서버 정보 로드 완료: {len(self.servers)}개의 서버")
            if self.quick_connect_server:
                logger.info(f"빠른 연결 서버 설정: {self.quick_connect_server}")
            
            return self.servers
        except Exception as e:
            logger.error(f"서버 정보 로드 실패: {str(e)}")
            return {}
    
    def save_servers(self):
        """서버 정보 저장"""
        try:
            # 서버 정보를 딕셔너리로 변환 (공통 메서드 사용)
            config = {
                name: self._convert_server_to_dict(server) 
                for name, server in self.servers.items() 
                if isinstance(server, IDRACConfig)
            }

            # 빠른 연결 서버 설정 저장
            if self.quick_connect_server:
                config['quick_connect_server'] = self.quick_connect_server

            # 설정 파일에 저장
            logger.debug(f"서버 정보 저장 완료: {len(self.servers)}개의 서버")
            if self.quick_connect_server:
                logger.info(f"빠른 연결 서버 설정: {self.quick_connect_server}")
            
            self.config_manager.save_config(config)
            self._notify_observers()
        except Exception as e:
            logger.error(f"서버 정보 저장 실패: {str(e)}")

    def add_server(self, name: str, ip: str, username: str, password: str, port: str):
        server_info = {
            'NAME': name,
            'IP': ip,
            'PORT': port,
            'USERNAME': username,
            'PASSWORD': password
        }
        self.servers[name] = convert_to_idrac_config(server_info)
        self.save_servers()

    def remove_server(self, name: str):
        if name in self.servers:
            del self.servers[name]
            self.save_servers()

    def get_server(self, name: str) -> Optional[IDRACConfig]:
        return self.servers.get(name)

    def get_all_servers(self) -> Dict[str, IDRACConfig]:
        return self.servers

    def add_observer(self, observer):
        self.observers.append(observer)

    def _notify_observers(self):
        for observer in self.observers:
            observer()

    def set_quick_connect_server(self, name: str):
        """빠른 연결 서버 설정"""
        if name in self.servers:
            self.quick_connect_server = name
            self.save_servers()
            logger.info(f"빠른 연결 서버 설정: {name}")

    def get_quick_connect_server(self) -> Optional[IDRACConfig]:
        """빠른 연결 서버 정보 반환"""
        try:
            if self.quick_connect_server:
                server = self.servers.get(self.quick_connect_server)
                if server and isinstance(server, IDRACConfig):
                    return server
                else:
                    logger.error(f"빠른 연결 서버를 찾을 수 없거나 잘못된 형식입니다: {self.quick_connect_server}")
            return None
        except Exception as e:
            logger.error(f"빠른 연결 서버 정보 조회 실패: {str(e)}")
            return None

    def save_quick_connect_server(self, server_name: str):
        """빠른 연결 서버 설정 저장"""
        try:
            config = self.config_manager.load_config()
            config['quick_connect_server'] = server_name
            self.config_manager.save_config(config)
            self.quick_connect_server = server_name
            logger.info(f"빠른 연결 서버 설정 저장: {server_name}")
        except Exception as e:
            logger.error(f"빠른 연결 서버 설정 저장 실패: {str(e)}")

server_config = ServerConfig()
