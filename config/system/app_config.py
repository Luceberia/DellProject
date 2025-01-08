from dataclasses import dataclass
import os
import sys
from pathlib import Path
import logging
import shutil

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
    @classmethod
    def get_resource_dir(cls):
        if getattr(sys, 'frozen', False):
            if sys.platform == 'darwin':  # macOS
                resource_dir = Path.home() / 'Library' / 'Application Support' / 'DellIDRACMonitor'
            else:
                resource_dir = Path.home() / '.dell_idrac_monitor'
        else:
            resource_dir = Path.cwd() / 'resources'
        
        resource_dir.mkdir(parents=True, exist_ok=True)
        return resource_dir

    @classmethod
    def get_log_dir(cls):
        if getattr(sys, 'frozen', False):
            if sys.platform == 'darwin':  # macOS
                log_dir = Path.home() / 'Library' / 'Logs' / 'DellIDRACMonitor'
            elif sys.platform == 'win32':  # Windows
                log_dir = Path(os.getenv('APPDATA')) / 'DellIDRACMonitor' / 'Logs'
            else:  # Linux 등 기타 OS
                log_dir = Path.home() / '.dell_idrac_monitor' / 'logs'
        else:
            log_dir = cls.get_resource_dir() / 'logs'
        
        log_dir.mkdir(parents=True, exist_ok=True)
        return log_dir

    @classmethod
    def get_cache_dir(cls):
        cache_dir = cls.get_resource_dir() / 'cache'
        cache_dir.mkdir(parents=True, exist_ok=True)
        return cache_dir

    @classmethod
    def get_lib_dir(cls):
        """라이브러리 디렉토리 경로 반환"""
        lib_dir = cls.get_resource_dir() / 'lib'
        lib_dir.mkdir(parents=True, exist_ok=True)
        return lib_dir

    @classmethod
    def preload_resources(cls):
        """자주 사용되는 리소스를 메모리에 미리 로드"""
        try:
            # 핵심 라이브러리 추출
            cls.extract_core_libraries()
            
            # 자주 사용되는 아이콘 파일 미리 로드
            icon_dir = cls.get_resource_dir() / 'icon'
            if icon_dir.exists():
                for icon in icon_dir.glob('*.png'):
                    try:
                        with open(icon, 'rb') as f:
                            f.read()
                    except Exception as e:
                        logging.error(f"아이콘 프리로드 실패 ({icon.name}): {e}")
                        
        except Exception as e:
            logging.error(f"리소스 프리로드 실패: {e}", exc_info=True)

    @classmethod
    def extract_core_libraries(cls):
        """핵심 라이브러리를 라이브러리 디렉토리로 추출하고 경로 설정"""
        if not getattr(sys, 'frozen', False):
            return
        
        lib_dir = cls.get_lib_dir()
        base_path = sys._MEIPASS
        
        try:
            # 라이브러리 디렉토리를 Python 경로에 추가
            if str(lib_dir) not in sys.path:
                sys.path.insert(0, str(lib_dir))
            
            core_libs = {
                'PyQt6': ['QtCore', 'QtGui', 'QtWidgets'],
                'cryptography': ['fernet'],
                'numpy': ['core', 'lib'],
                'pandas': ['core']
            }
            
            for lib, modules in core_libs.items():
                lib_path = os.path.join(base_path, lib)
                if os.path.exists(lib_path):
                    dst_path = lib_dir / lib
                    if not dst_path.exists():
                        shutil.copytree(lib_path, dst_path)
                        print(f"라이브러리 추출 완료: {lib}")
                        
                    # 라이브러리별 경로 설정
                    lib_specific_path = str(dst_path)
                    if lib_specific_path not in sys.path:
                        sys.path.insert(0, lib_specific_path)
                        
        except Exception as e:
            logging.error(f"라이브러리 추출 실패: {e}", exc_info=True)

    @classmethod
    def extract_package_resources(cls):
        """패키지 리소스를 라이브러리 디렉토리로 추출"""
        if not getattr(sys, 'frozen', False):
            return
            
        resource_dir = cls.get_resource_dir()
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
                        try:
                            if not dst.exists() and os.path.exists(src):
                                shutil.copy2(src, dst)
                                print(f"번역 파일 복사 완료: {file}")
                        except Exception as e:
                            print(f"번역 파일 복사 실패 ({file}): {e}")
            
            # 아이콘 파일 복사
            icon_files = [
                'boot_icon.png', 'cpu_icon.png', 'device_icon.png',
                'idrac_icon.png', 'misc_icon.png', 'network_icon.png',
                'nic_icon.png', 'power_icon.png', 'profile_icon.png',
                'system_icon.png'
            ]
            icon_dir = resource_dir / 'icon'
            icon_dir.mkdir(parents=True, exist_ok=True)
            for icon in icon_files:
                src = os.path.join(base_path, 'icon', icon)
                dst = icon_dir / icon
                try:
                    if not dst.exists() and os.path.exists(src):
                        shutil.copy2(src, dst)
                        print(f"아이콘 파일 복사 완료: {icon}")
                except Exception as e:
                    print(f"아이콘 파일 복사 실패 ({icon}): {e}")
            
            # 설정 파일 복사
            config_files = {
                'server': ['server_config.json'],
                'data': ['data_config.json']
            }
            
            config_dir = resource_dir / 'config'
            for subdir, files in config_files.items():
                subdir_path = config_dir / subdir
                subdir_path.mkdir(parents=True, exist_ok=True)
                for file in files:
                    src = os.path.join(base_path, 'config', subdir, file)
                    dst = subdir_path / file
                    try:
                        if not dst.exists() and os.path.exists(src):
                            shutil.copy2(src, dst)
                            print(f"설정 파일 복사 완료: {file}")
                    except Exception as e:
                        print(f"설정 파일 복사 실패 ({file}): {e}")
                        
        except Exception as e:
            print(f"리소스 추출 중 오류 발생: {e}")
            logging.error(f"리소스 추출 중 오류 발생: {e}", exc_info=True)

    @classmethod
    def setup_directories(cls):
        """
        모든 필요한 디렉토리를 초기화하고 생성합니다.
        애플리케이션에 필요한 기본 디렉토리 구조를 설정합니다.
        """
        try:
            # 주요 디렉토리 생성
            resource_dir = cls.get_resource_dir()
            log_dir = cls.get_log_dir()
            cache_dir = cls.get_cache_dir()
            lib_dir = cls.get_lib_dir()

            # 추가 디렉토리 생성
            icon_dir = resource_dir / 'icon'
            config_dir = resource_dir / 'config'
            temp_dir = resource_dir / 'temp'

            # 모든 디렉토리 생성
            for directory in [
                resource_dir, log_dir, cache_dir, lib_dir, 
                icon_dir, config_dir, temp_dir
            ]:
                directory.mkdir(parents=True, exist_ok=True)

            # 리소스 사전 로드
            cls.preload_resources()

            logging.info("애플리케이션 디렉토리 초기화 완료")
            return True

        except Exception as e:
            logging.error(f"디렉토리 초기화 중 오류 발생: {e}", exc_info=True)
            return False