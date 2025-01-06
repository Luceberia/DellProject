import os
import platform
import psutil
import socket
import uuid

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, 
                             QLabel, QGroupBox, QPushButton, QScrollArea, 
                             QWidget, QApplication)
from PyQt6.QtGui import QFont, QPalette, QColor
from PyQt6.QtCore import Qt

from config.system.log_config import setup_logging
from version import __version__

logger = setup_logging()

class SystemInfoDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("시스템 정보")
        self.setMinimumSize(600, 500)
        
        # 스타일시트
        self.setStyleSheet("")
        
        # 메인 레이아웃
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)
        
        # 스크롤 영역
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        main_layout.addWidget(scroll_area)
        
        # 스크롤 위젯
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_area.setWidget(scroll_content)
        
        # 시스템 정보 그룹
        system_group = self.create_info_group("시스템 정보", [
            ("컴퓨터 이름", socket.gethostname()),
            ("운영 체제", platform.platform()),
            ("OS 버전", platform.version()),
            ("OS 릴리즈", platform.release())
        ])
        scroll_layout.addWidget(system_group)
        
        # 하드웨어 그룹
        hardware_group = self.create_info_group("하드웨어 정보", [
            ("프로세서", platform.processor()),
            ("물리적 코어 수", str(psutil.cpu_count(logical=False))),
            ("논리적 코어 수", str(psutil.cpu_count(logical=True))),
            ("총 메모리", f"{psutil.virtual_memory().total / (1024**3):.2f} GB"),
            ("사용 가능 메모리", f"{psutil.virtual_memory().available / (1024**3):.2f} GB"),
            ("MAC 주소", ':'.join(['{:02x}'.format((uuid.getnode() >> elements) & 0xff) for elements in range(0,2*6,2)][::-1]))
        ])
        scroll_layout.addWidget(hardware_group)
        
        # 디스크 그룹
        disk_group = self.create_info_group("디스크 정보", [
            ("디스크 총 공간", f"{psutil.disk_usage('/').total / (1024**3):.2f} GB"),
            ("디스크 사용 공간", f"{psutil.disk_usage('/').used / (1024**3):.2f} GB"),
            ("디스크 여유 공간", f"{psutil.disk_usage('/').free / (1024**3):.2f} GB")
        ])
        scroll_layout.addWidget(disk_group)
        
        # 애플리케이션 그룹
        app_group = self.create_info_group("애플리케이션 정보", [
            ("애플리케이션 버전", __version__),
            ("Python 버전", platform.python_version())
        ])
        scroll_layout.addWidget(app_group)
        
        # 여백 추가
        scroll_layout.addStretch(1)
        
        # 닫기 버튼
        close_btn = QPushButton("닫기")
        close_btn.clicked.connect(self.close)
        main_layout.addWidget(close_btn)
    
    def create_info_group(self, title, info_list):
        """정보 그룹 생성"""
        group = QGroupBox(title)
        group_layout = QVBoxLayout()
        group.setLayout(group_layout)
        
        for key, value in info_list:
            info_layout = QHBoxLayout()
            
            key_label = QLabel(f"{key}:")
            key_label.setStyleSheet("")
            key_label.setFixedWidth(150)
            
            value_label = QLabel(str(value))
            value_label.setStyleSheet("")
            
            info_layout.addWidget(key_label)
            info_layout.addWidget(value_label)
            info_layout.addStretch(1)
            
            group_layout.addLayout(info_layout)
        
        return group
