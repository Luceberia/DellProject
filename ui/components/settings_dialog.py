from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                           QLineEdit, QPushButton, QMessageBox, QListWidget,
                           QListWidgetItem, QGroupBox, QFormLayout)
from PyQt6.QtCore import Qt
from config.server.server_config import server_config
from utils.server_utils import convert_to_idrac_config

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("서버 설정")
        self.setMinimumWidth(200)  # 최소 너비 설정
        self.setMinimumHeight(300)  # 최소 높이 설정
        self.setup_ui()
        self.load_servers()

    def setup_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setSpacing(2)
        main_layout.setContentsMargins(2, 2, 2, 2)
        self.setLayout(main_layout)
        
        # 서버 목록
        self.server_list = QListWidget()
        self.server_list.itemClicked.connect(self.on_server_clicked)
        self.server_list.itemDoubleClicked.connect(self.on_server_selected)
        main_layout.addWidget(self.server_list)
        
        # 버튼 레이아웃
        button_layout = QHBoxLayout()
        button_layout.setSpacing(2)
        
        connect_button = QPushButton("연결")
        connect_button.clicked.connect(self.on_server_selected)
        
        quick_connect_button = QPushButton("빠른 연결로 설정")
        quick_connect_button.clicked.connect(self.set_quick_connect_server)
        
        remove_button = QPushButton("삭제")
        remove_button.clicked.connect(self.remove_server)
        
        button_layout.addStretch()
        button_layout.addWidget(connect_button)
        button_layout.addWidget(quick_connect_button)
        button_layout.addWidget(remove_button)
        button_layout.addStretch()
        main_layout.addLayout(button_layout)
        
        # 구분선
        line = QLabel()
        line.setFrameStyle(QLabel.Shape.HLine | QLabel.Shadow.Sunken)
        main_layout.addWidget(line)
        
        # 서버 정보 입력 폼
        form_layout = QFormLayout()
        form_layout.setSpacing(2)
        form_layout.setContentsMargins(2, 2, 2, 2)
        
        self.name_edit = QLineEdit()
        self.ip_edit = QLineEdit()
        self.port_edit = QLineEdit()
        self.username_edit = QLineEdit()
        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        
        form_layout.addRow("이름:", self.name_edit)
        form_layout.addRow("IP:", self.ip_edit)
        form_layout.addRow("포트:", self.port_edit)
        form_layout.addRow("계정:", self.username_edit)
        form_layout.addRow("암호:", self.password_edit)
        
        main_layout.addLayout(form_layout)
        
        # 하단 버튼
        bottom_layout = QHBoxLayout()
        
        add_button = QPushButton("추가")
        add_button.clicked.connect(self.add_server)
        close_button = QPushButton("닫기")
        close_button.clicked.connect(self.reject)
        
        bottom_layout.addStretch()
        bottom_layout.addWidget(add_button)
        bottom_layout.addWidget(close_button)
        main_layout.addLayout(bottom_layout)

    def load_servers(self):
        """서버 목록을 로드하고 표시"""
        self.server_list.clear()
        
        # servers 속성을 직접 사용
        servers = server_config.servers
        quick_connect_server = server_config.quick_connect_server
        
        for server_name, server_info in servers.items():
            display_text = server_name
            if hasattr(server_info, 'IP'):
                display_text = f"{server_name} ({server_info.IP})"
            
            # 빠른 연결 서버인 경우 표시 추가
            if quick_connect_server and server_name == quick_connect_server:
                display_text = f"⚡ {display_text}"
            
            item = QListWidgetItem(display_text)
            item.setData(Qt.ItemDataRole.UserRole, server_name)
            self.server_list.addItem(item)

    def on_server_clicked(self, item):
        """서버 클릭 시 폼에 정보 표시"""
        name = item.data(Qt.ItemDataRole.UserRole)
        server = server_config.servers[name]
        if server:
            self.name_edit.setText(name)
            self.ip_edit.setText(server.IP)
            self.port_edit.setText(server.PORT)
            self.username_edit.setText(server.USERNAME)
            self.password_edit.setText(server.PASSWORD)

    def add_server(self):
        name = self.name_edit.text()
        ip = self.ip_edit.text()
        port = self.port_edit.text()
        username = self.username_edit.text()
        password = self.password_edit.text()
        
        if not all([name, ip, username, password]):
            QMessageBox.warning(self, "경고", "모든 필드를 입력해주세요.")
            return
            
        server_info = {
            'NAME': name,
            'IP': ip,
            'PORT': port,
            'USERNAME': username,
            'PASSWORD': password
        }
        server_config.servers[name] = convert_to_idrac_config(server_info)
        server_config.save_servers()
        self.load_servers()
        
        # 입력 필드 초기화
        self.name_edit.clear()
        self.ip_edit.clear()
        self.port_edit.clear()
        self.username_edit.clear()
        self.password_edit.clear()

    def remove_server(self):
        """선택된 서버 삭제"""
        current_item = self.server_list.currentItem()
        if current_item:
            name = current_item.data(Qt.ItemDataRole.UserRole)
            reply = QMessageBox.question(self, '서버 삭제', 
                                    '선택한 서버를 삭제하시겠습니까?',
                                    QMessageBox.StandardButton.Yes | 
                                    QMessageBox.StandardButton.No)
            
            if reply == QMessageBox.StandardButton.Yes:
                del server_config.servers[name]
                server_config.save_servers()
                self.load_servers()
                
                # 입력 필드 초기화
                self.name_edit.clear()
                self.ip_edit.clear()
                self.username_edit.clear()
                self.password_edit.clear()

    def on_server_selected(self, item=None):
        """서버 선택 시 호출되는 메서드"""
        current_item = self.server_list.currentItem()
        if current_item:
            name = current_item.data(Qt.ItemDataRole.UserRole)
            server = server_config.servers[name]
            if server:
                server_info = {
                    'NAME': name,
                    'IP': server.IP,
                    'PORT': getattr(server, 'PORT', '443'),
                    'USERNAME': server.USERNAME,
                    'PASSWORD': server.PASSWORD
                }
                self.parent().on_server_connected(server_info)
                self.accept()

    def set_quick_connect_server(self):
        """선택된 서버를 빠른 연결 서버로 설정"""
        current_item = self.server_list.currentItem()
        if not current_item:
            return
            
        server_name = current_item.data(Qt.ItemDataRole.UserRole)
        server_config.save_quick_connect_server(server_name)
        
        # 서버 목록 새로고침하여 빠른 연결 표시 업데이트
        self.load_servers()
        
        QMessageBox.information(
            self,
            "빠른 연결 서버 설정",
            f"{server_name}가 빠른 연결 서버로 설정되었습니다."
        )
