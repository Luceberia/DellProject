from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime

@dataclass
class IDRACConfig:
    NAME: str = ""
    IP: str = ""
    PORT: str = ""
    USERNAME: str = ""
    PASSWORD: str = ""
    CONNECTED: bool = False
    LAST_CONNECTED: Optional[datetime] = None
    LAST_DISCONNECTED: Optional[datetime] = None

    def __init__(self, NAME: str = "", IP: str = "", PORT: str = "", USERNAME: str = "", PASSWORD: str = ""):
        self.NAME = NAME
        self.IP = IP
        self.PORT = PORT
        self.USERNAME = USERNAME
        self.PASSWORD = PASSWORD
        self.CONNECTED = False  
        self.LAST_CONNECTED = None  
        self.LAST_DISCONNECTED = None  

    def update(self, IP="", USERNAME="", PASSWORD="", NAME="", PORT=""):
        self.NAME = NAME
        self.IP = IP
        self.PORT = PORT
        self.USERNAME = USERNAME
        self.PASSWORD = PASSWORD

    def set_connected(self, is_connected: bool):
        """서버 연결 상태 업데이트"""
        from datetime import datetime
        self.CONNECTED = is_connected
        if is_connected:
            self.LAST_CONNECTED = datetime.now()
        else:
            self.LAST_DISCONNECTED = datetime.now()

    def to_dict(self):
        """서버 정보를 딕셔너리로 변환"""
        return {
            'NAME': self.NAME,
            'IP': self.IP,
            'PORT': self.PORT,
            'USERNAME': self.USERNAME,
            'PASSWORD': self.PASSWORD,
            'CONNECTED': self.CONNECTED,
            'LAST_CONNECTED': self.LAST_CONNECTED,
            'LAST_DISCONNECTED': self.LAST_DISCONNECTED
        }

    def __str__(self):
        return f"{self.NAME}: {self.IP}"