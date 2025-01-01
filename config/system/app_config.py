from dataclasses import dataclass
import os
import sys
from pathlib import Path
import logging

@dataclass
class IDRACConfig:
    NAME: str = ""
    IP: str = ""
    PORT: str = ""
    USERNAME: str = ""
    PASSWORD: str = ""

    def update(self, ip="", username="", password="", name="", port=""):
        self.NAME = name
        self.IP = ip
        self.PORT = port
        self.USERNAME = username
        self.PASSWORD = password

    def __str__(self):
        return f"{self.NAME}: {self.IP}"

class ResourceManager:
    @staticmethod
    def get_resource_dir():
        if getattr(sys, 'frozen', False):
            if sys.platform == 'darwin':  # macOS
                resource_dir = Path.home() / 'Library' / 'Application Support' / 'DellIDRACMonitor'
            else:
                resource_dir = Path.home() / '.dell_idrac_monitor'
        else:
            resource_dir = Path.cwd() / 'resources'
        
        resource_dir.mkdir(parents=True, exist_ok=True)
        return resource_dir

    @staticmethod
    def get_log_dir():
        if getattr(sys, 'frozen', False):
            if sys.platform == 'darwin':  # macOS
                log_dir = Path.home() / 'Library' / 'Logs' / 'DellIDRACMonitor'
            elif sys.platform == 'win32':  # Windows
                log_dir = Path(os.getenv('APPDATA')) / 'DellIDRACMonitor' / 'Logs'
            else:  # Linux 등 기타 OS
                log_dir = Path.home() / '.dell_idrac_monitor' / 'logs'
        else:
            log_dir = ResourceManager.get_resource_dir() / 'logs'
        
        log_dir.mkdir(parents=True, exist_ok=True)
        return log_dir

    @staticmethod
    def setup_directories():
        resource_dir = ResourceManager.get_resource_dir()
        directories = {
            'config': ['server', 'data'],
            'logs': [],
            'cache': [],
            'translations': ['PyQt6/Qt6/translations'],
            'temp': []
        }

        for dir_name, subdirs in directories.items():
            dir_path = resource_dir / dir_name
            dir_path.mkdir(parents=True, exist_ok=True)
            for subdir in subdirs:
                (dir_path / subdir).mkdir(parents=True, exist_ok=True)
