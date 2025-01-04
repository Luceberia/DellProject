from config.system.log_config import setup_logging
from config.data.models import IDRACConfig
from utils.server_utils import convert_to_idrac_config, convert_to_dict
from utils.config_utils import ConfigManager
from typing import Dict, Optional

# logger 객체 생성
logger = setup_logging()

class ServerConfig:
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ServerConfig, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self.config_manager = ConfigManager()
            self.servers: Dict[str, IDRACConfig] = {}
            self.observers = []
            self.quick_connect_server = None
            self._initialized = True
            self.initialize()
    
    def initialize(self):
        """서버 설정 초기화"""
        self.quick_connect_server = self.load_quick_connect_server()
        self.load_servers()

    def load_servers(self) -> Dict[str, IDRACConfig]:
        """서버 정보 로드"""
        try:
            config = self.config_manager.load_config()
            self.servers = {}
            
            for name, server_info in config.items():
                if name != 'quick_connect_server':  # 빠른 연결 서버 설정은 제외
                    try:
                        if isinstance(server_info, dict):  # 딕셔너리인지 확인
                            required_keys = ['NAME', 'IP', 'USERNAME', 'PASSWORD']
                            if all(key in server_info for key in required_keys):  # 필수 키가 모두 있는지 확인
                                self.servers[name] = convert_to_idrac_config(server_info)
                            else:
                                logger.error(f"서버 정보에 필수 키가 없습니다: {name}")
                        else:
                            logger.error(f"서버 정보가 딕셔너리가 아닙니다: {name}")
                    except Exception as e:
                        logger.error(f"서버 정보 변환 실패 ({name}): {str(e)}")
            
            # 빠른 연결 서버 설정 로드
            self.quick_connect_server = self.load_quick_connect_server()
            server_names = list(self.servers.keys())
            logger.debug(f"서버 정보 로드 완료: {len(server_names)}개의 서버")
            if self.quick_connect_server:
                logger.info(f"빠른 연결 서버 설정: {self.quick_connect_server}")
            
            return self.servers
        except Exception as e:
            logger.error(f"서버 정보 로드 실패: {str(e)}")
            return {}

    def save_servers(self):
        """서버 정보 저장"""
        try:
            # 서버 정보를 딕셔너리로 변환
            config = {}
            for name, server in self.servers.items():
                try:
                    if isinstance(server, IDRACConfig):
                        server_dict = {
                            'NAME': server.NAME,
                            'IP': server.IP,
                            'PORT': server.PORT,
                            'USERNAME': server.USERNAME,
                            'PASSWORD': server.PASSWORD
                        }
                        config[name] = server_dict
                    else:
                        logger.error(f"서버 객체가 IDRACConfig 인스턴스가 아닙니다: {name}")
                except Exception as e:
                    logger.error(f"서버 정보 변환 실패 ({name}): {str(e)}")

            # 빠른 연결 서버 설정 저장
            if self.quick_connect_server:
                config['quick_connect_server'] = self.quick_connect_server

            # 설정 파일에 저장
            server_names = list(self.servers.keys())
            logger.debug(f"서버 정보 저장 완료: {len(server_names)}개의 서버")
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

    def load_quick_connect_server(self) -> Optional[str]:
        """빠른 연결 서버 설정 로드"""
        config = self.config_manager.load_config()
        return config.get('quick_connect_server')

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
