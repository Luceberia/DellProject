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
    def extract_package_resources():
        """패키지 리소스를 라이브러리 디렉토리로 추출"""
        if not getattr(sys, 'frozen', False):
            return
            
        resource_dir = ResourceManager.get_resource_dir()
        base_path = sys._MEIPASS
        
        try:
            # PyQt6 번역 파일 복사
            translations_dir = resource_dir / 'translations' / 'PyQt6' / 'Qt6' / 'translations'
            translations_dir.mkdir(parents=True, exist_ok=True)
            qt_translations = os.path.join(base_path, 'PyQt6', 'Qt6', 'translations')
            if os.path.exists(qt_translations):
                for file in os.listdir(qt_translations):
                    if file.endswith('.qm'):
                        src = os.path.join(qt_translations, file)
                        dst = translations_dir / file
                        if not dst.exists():
                            shutil.copy2(src, dst)
            
            # 설정 파일 복사
            config_dir = resource_dir / 'config'
            for subdir in ['server', 'data']:
                (config_dir / subdir).mkdir(parents=True, exist_ok=True)
                
            # 기타 필요한 파일들 복사
            for dirname in ['cache', 'temp']:
                dir_path = resource_dir / dirname
                dir_path.mkdir(parents=True, exist_ok=True)
                        
        except Exception as e:
            print(f"리소스 추출 중 오류 발생: {e}")

    @staticmethod
    def setup_directories():
        """디렉토리 구조 생성 및 리소스 추출"""
        resource_dir = ResourceManager.get_resource_dir()
        directories = {
            'config': ['server', 'data'],
            'logs': [],
            'cache': [],
            'translations': ['PyQt6/Qt6/translations'],
            'temp': []
        }

        # 디렉토리 구조 생성
        for dir_name, subdirs in directories.items():
            dir_path = resource_dir / dir_name
            dir_path.mkdir(parents=True, exist_ok=True)
            for subdir in subdirs:
                (dir_path / subdir).mkdir(parents=True, exist_ok=True)
        
        # 리소스 파일 추출
        ResourceManager.extract_package_resources()