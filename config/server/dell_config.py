from config.system.log_config import setup_logging
from dataclasses import dataclass
from typing import Optional
import threading
from endpoints.redfish_endpoints import RedfishEndpoints

logger = setup_logging()

class DellConfig:
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance.initialize()
        return cls._instance
    
    def initialize(self):
        self._name: Optional[str] = None
        self._ip: Optional[str] = None
        self._username: Optional[str] = None
        self._password: Optional[str] = None
        self._endpoints: Optional[RedfishEndpoints] = None
    
    def update_config(self, server_info: dict):
        if not server_info:
            return
            
        self._name = server_info['NAME']
        self._ip = server_info['IP']
        self._username = server_info['USERNAME']
        self._password = server_info['PASSWORD']
        self._endpoints = RedfishEndpoints(self.base_url)
        logger.debug(f"Updated DellConfig with new server: {self._name}: {self._ip}")
    
    @property
    def is_connected(self) -> bool:
        return self._name is not None and self._ip is not None
    
    @property
    def base_url(self) -> str:
        if not self._ip:
            raise ValueError("IP not initialized")
        return f"https://{self._ip}"
    
    @property
    def endpoints(self) -> RedfishEndpoints:
        if not self._endpoints:
            raise ValueError("Endpoints not initialized")
        return self._endpoints
    
    @property
    def username(self) -> str:
        if not self._username:
            raise ValueError("Username not initialized")
        return self._username
    
    @property
    def password(self) -> str:
        if not self._password:
            raise ValueError("Password not initialized")
        return self._password
    
    @property
    def name(self) -> str:
        if not self._name:
            raise ValueError("Server name not initialized")
        return self._name
    
    @property
    def ip(self) -> str:
        if not self._ip:
            raise ValueError("IP not initialized")
        return self._ip

# DellConfig 인스턴스 생성
dell_config = DellConfig()
