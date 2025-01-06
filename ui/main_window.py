from config.system.app_config import ResourceManager
from config.system.log_config import setup_logging
from datetime import datetime
from PyQt6.QtCore import Qt, QUrl, QCoreApplication, pyqtSignal, QEvent
from PyQt6.QtGui import QGuiApplication, QCloseEvent, QDesktopServices
from PyQt6.QtWidgets import QDialog, QFormLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem, QMainWindow, QMenu, QMessageBox, QPushButton, QVBoxLayout, QWidget
from typing import Optional
from ui.components.hardware_section import create_hardware_section
from ui.components.monitor_section import create_monitor_section
from ui.components.server_section import create_server_section
from version import __version__
from config.server.server_config import server_config
from utils.server_utils import convert_to_idrac_config

logger = setup_logging()

class ServerSettingsDialog(QDialog):
    server_status_changed = pyqtSignal(str, bool)  # 딕셔너리 대신 개별 값으로 변경
    def __init__(self, parent=None, server_section=None):
        super().__init__(parent)
        self.original_server_name = None
        self.server_section = server_section
        if self.server_section:
            self.server_section.server_connection_changed.connect(self.on_connection_changed)
        
        self.setWindowTitle("서버 설정")
        self.setMinimumWidth(200)
        self.setMinimumHeight(300)
        self.setup_ui()
        self.load_servers()

    def on_connection_changed(self, server_name):
        """서버 연결 상태 변경 시그널 처리"""
        self.on_server_connection_changed(server_name, True)

    def setup_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setSpacing(2)
        main_layout.setContentsMargins(2, 2, 2, 2)
        self.setLayout(main_layout)

        # 서버 목록
        self.server_list = QListWidget()
        self.server_list.installEventFilter(self)  # 이벤트 필터 설치
        main_layout.addWidget(self.server_list)

        # 버튼 레이아웃
        button_layout = QHBoxLayout()
        connect_btn = QPushButton("연결")
        quick_connect_btn = QPushButton("빠른 연결로 설정")
        remove_btn = QPushButton("삭제")
        
        button_layout.addStretch()
        button_layout.addWidget(connect_btn)
        button_layout.addWidget(quick_connect_btn)
        button_layout.addWidget(remove_btn)
        button_layout.addStretch()

        connect_btn.clicked.connect(self.on_server_selected)
        quick_connect_btn.clicked.connect(self.set_quick_connect_server)
        remove_btn.clicked.connect(self.remove_server)
        self.server_list.itemClicked.connect(self.on_server_clicked)
        self.server_list.itemDoubleClicked.connect(self.on_server_selected)

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
        add_btn = QPushButton("추가")
        close_btn = QPushButton("닫기")
        
        bottom_layout.addStretch()
        bottom_layout.addWidget(add_btn)
        bottom_layout.addWidget(close_btn)

        add_btn.clicked.connect(self.add_server)
        close_btn.clicked.connect(self.reject)

        main_layout.addLayout(bottom_layout)

        # 시그널 연결
        self.server_status_changed.connect(self.update_server_status)

    def eventFilter(self, obj, event):
        """이벤트 필터를 통해 컨텍스트 메뉴 이벤트 제어"""
        if obj == self.server_list and event.type() == QEvent.Type.ContextMenu:
            # 마우스 우클릭 이벤트 처리
            self.show_context_menu(self.server_list.mapFromGlobal(event.globalPos()))
            return True  # 이벤트 소비
        return super().eventFilter(obj, event)

    def show_context_menu(self, position):
        """서버 목록에서 우클릭 시 컨텍스트 메뉴 생성"""
        menu = QMenu()
        current_item = self.server_list.itemAt(position)
        
        # 선택된 서버가 없을 때도 동일한 기본 액션들 추가
        connect_action = menu.addAction("서버 연결")
        quick_connect_action = menu.addAction("빠른 연결로 설정")
        menu.addSeparator()
        edit_action = menu.addAction("서버 정보 수정")
        clone_action = menu.addAction("서버 복제")
        menu.addSeparator()
        
        delete_action = menu.addAction("서버 삭제")
        
        if current_item:
            server_name = current_item.data(Qt.ItemDataRole.UserRole)
            server = server_config.servers.get(server_name)
            
            menu.addSeparator()
            
            # 서버 관리 액션
            if server and server.CONNECTED:
                disconnect_action = menu.addAction("서버 연결 해제")
                disconnect_action.triggered.connect(lambda: self.on_server_disconnected(server_name))
            else:
                connect_action.triggered.connect(lambda: self.on_server_selected())
        
        # 액션 실행
        action = menu.exec(self.server_list.mapToGlobal(position))
        
        # 액션 처리
        if action == add_server_action:
            self.show_server_add_dialog()
        elif action == connect_action:
            self.on_server_selected()
        elif action == quick_connect_action:
            self.set_quick_connect_server()
        elif action == edit_action and current_item:
            self.edit_server(current_item.data(Qt.ItemDataRole.UserRole))
        elif action == clone_action and current_item:
            self.clone_server(current_item.data(Qt.ItemDataRole.UserRole))
        elif action == delete_action and current_item:
            self.remove_server()

    def show_server_add_dialog(self):
        """서버 추가 다이얼로그 표시"""
        # 입력 필드 초기화
        self.name_edit.clear()
        self.ip_edit.clear()
        self.port_edit.clear()
        self.username_edit.clear()
        self.password_edit.clear()
        
        # 다이얼로그 실행
        if self.exec():
            # 서버 추가 로직은 add_server 메서드에서 처리됨
            pass

    def on_server_disconnected(self, server_name):
        """서버 연결 해제 메서드"""
        try:
            # 서버 섹션을 통해 서버 연결 해제
            self.server_section.disconnect_server(server_name)
            
            # 서버 목록 새로고침
            self.load_servers()
        except Exception as e:
            QMessageBox.critical(self, "서버 연결 해제 오류", f"서버 연결 해제 중 오류가 발생했습니다: {str(e)}")

    def clone_server(self, server_name):
        """서버 설정 복제"""
        try:
            original_server = server_config.servers[server_name]
            new_name = f"{server_name}_복사본"
            counter = 1
            
            # 중복 이름 처리
            while new_name in server_config.servers:
                new_name = f"{server_name}_복사본_{counter}"
                counter += 1
                
            server_info = {
                'NAME': new_name,
                'IP': original_server.IP,
                'PORT': getattr(original_server, 'PORT', '443'),
                'USERNAME': original_server.USERNAME,
                'PASSWORD': original_server.PASSWORD
            }
            
            server_config.servers[new_name] = convert_to_idrac_config(server_info)
            server_config.save_servers()
            self.load_servers()
            
            QMessageBox.information(
                self,
                "서버 복제",
                f"서버 '{server_name}'이(가) '{new_name}'(으)로 복제되었습니다."
            )
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "복제 오류",
                f"서버 복제 중 오류가 발생했습니다: {str(e)}"
            )

    def load_servers(self):
        self.server_list.clear()
        servers = server_config.servers
        quick_connect_server = server_config.quick_connect_server
        
        for server_name, server_info in servers.items():
            is_connected = getattr(server_info, 'CONNECTED', False)
            status_icon = "✅" if is_connected else "❌"
            display_text = f"{status_icon} {server_name} ({server_info.IP})"
            
            if quick_connect_server and server_name == quick_connect_server:
                display_text = f"⚡ {display_text}"
                
            # 툴팁에 상세 정보 추가
            tooltip = f"서버: {server_name}\n"
            tooltip += f"IP: {server_info.IP}\n"
            tooltip += f"포트: {getattr(server_info, 'PORT', '443')}\n"
            if server_info.LAST_CONNECTED:
                tooltip += f"마지막 연결: {server_info.LAST_CONNECTED.strftime('%Y-%m-%d %H:%M')}"
            else:
                tooltip += "마지막 연결: 없음"
                
            item = QListWidgetItem(display_text)
            item.setToolTip(tooltip)
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
        name = self.name_edit.text().strip()
        ip = self.ip_edit.text().strip()
        port = self.port_edit.text().strip()
        username = self.username_edit.text().strip()
        password = self.password_edit.text().strip()
        
        # IP 주소 형식 검사
        import re
        ip_pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
        if not re.match(ip_pattern, ip):
            QMessageBox.warning(self, "경고", "올바른 IP 주소 형식이 아닙니다.")
            return
        
        # 포트 번호 검사
        if port and not port.isdigit():
            QMessageBox.warning(self, "경고", "포트는 숫자만 입력 가능합니다.")
            return

        if name in server_config.servers:
            reply = QMessageBox.question(
                self, 
                '서버 중복', 
                f'"{name}" 서버가 이미 존재합니다. 덮어쓰시겠습니까?',
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.No:
                return

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

                self.name_edit.clear()
                self.ip_edit.clear()
                self.username_edit.clear()
                self.password_edit.clear()

    def on_connection_changed(self, server_name, connected=True):
        """서버 연결 상태 변경 시그널 처리"""
        try:
            if server_name in server_config.servers:
                server = server_config.servers[server_name]
                server.CONNECTED = connected
                server.LAST_CONNECTED = datetime.now() if connected else None
                self.load_servers()
                
                # 상태 업데이트를 위한 시그널 발생 (딕셔너리 대신 개별 값 전달)
                self.server_status_changed.emit(server_name, connected)
        except Exception as e:
            logger.error(f"서버 상태 업데이트 중 오류: {e}")

    def on_server_selected(self, item=None):
        """서버 연결 시도 및 처리"""
        try:
            # 현재 선택된 서버 확인
            current_item = self.server_list.currentItem()
            if not current_item:
                QMessageBox.warning(self, "선택 오류", "연결할 서버를 선택해주세요.")
                return

            # 서버 이름 추출
            server_name = current_item.data(Qt.ItemDataRole.UserRole)
            logger.info(f"서버 연결 시도: {server_name}")

            # 서버 정보 조회
            server = server_config.servers.get(server_name)
            if not server:
                QMessageBox.critical(self, "서버 오류", f"서버 '{server_name}'의 정보를 찾을 수 없습니다.")
                return

            # 서버 연결 정보 준비
            server_info = {
                'NAME': server_name,
                'IP': server.IP,
                'PORT': getattr(server, 'PORT', '443'),
                'USERNAME': server.USERNAME,
                'PASSWORD': server.PASSWORD
            }

            # 서버 연결 시도
            if self.server_section:
                # 이미 연결된 경우 건너뛰기
                if self.server_section.session_manager.is_connected(server_name):
                    logger.info(f"서버 '{server_name}'은 이미 연결되어 있습니다.")
                    return

                connection_result = self.server_section.connect_server(server_info)
                
                if connection_result:
                    # UI 갱신
                    self.load_servers()
                    
                    # 다이얼로그 닫기
                    self.accept()
                else:
                    # 연결 실패 시 메시지 박스는 이미 ServerSection에서 처리됨
                    pass
            else:
                # 서버 섹션 초기화 실패
                QMessageBox.critical(self, "시스템 오류", "서버 섹션을 초기화할 수 없습니다.")

        except Exception as e:
            # 예상치 못한 예외 처리
            logger.error(f"서버 연결 중 예외 발생: {e}", exc_info=True)
            # 예외 메시지 박스도 ServerSection에서 처리됨

    def update_server_status(self, server_name, connected):
        """서버 상태 업데이트"""
        try:
            # 서버 정보 다시 로드 제거
            server = server_config.servers.get(server_name)
            if server is not None:
                # 이미 상태가 같다면 업데이트 건너뛰기
                if server.CONNECTED == connected:
                    return
                
                server.CONNECTED = connected
                if connected:
                    server.LAST_CONNECTED = datetime.now()
                
                # UI 갱신
                self.load_servers()
                
                logger.info(f"서버 상태 업데이트: {server_name}, 연결 상태: {connected}")
            else:
                logger.warning(f"상태 업데이트 실패: 서버 '{server_name}'을 찾을 수 없음")
        except Exception as e:
            logger.error(f"서버 상태 업데이트 중 오류: {e}", exc_info=True)

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

    def edit_server(self, server_name):
        """서버 정보 수정"""
        # 서버 목록에서 해당 서버 항목 찾기
        for i in range(self.server_list.count()):
            item = self.server_list.item(i)
            if item.data(Qt.ItemDataRole.UserRole) == server_name:
                self.server_list.setCurrentItem(item)
                break
                
        server_info = server_config.servers.get(server_name)
        if not server_info:
            QMessageBox.warning(self, "오류", f"서버 '{server_name}'을 찾을 수 없습니다.")
            return
            
        # 기존 서버 정보로 입력 필드 설정
        self.name_edit.setText(server_name)
        self.ip_edit.setText(server_info.IP)
        self.port_edit.setText(getattr(server_info, 'PORT', '443'))
        self.username_edit.setText(server_info.USERNAME)
        self.password_edit.setText(server_info.PASSWORD)
        
        # 기존 서버 이름 저장
        self.original_server_name = server_name
        
        # IP 주소 형식 검사 함수
        def validate_ip(ip):
            import re
            ip_pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
            return re.match(ip_pattern, ip) is not None
        
        # 다이얼로그 실행
        if self.exec():
            # 수정된 정보 검증
            new_server_name = self.name_edit.text().strip()
            new_ip = self.ip_edit.text().strip()
            new_port = self.port_edit.text().strip()
            new_username = self.username_edit.text().strip()
            new_password = self.password_edit.text().strip()
            
            # 입력 필드 검증
            if not all([new_server_name, new_ip, new_username, new_password]):
                QMessageBox.warning(self, "경고", "모든 필드를 입력해주세요.")
                return
            
            # IP 주소 형식 검증
            if not validate_ip(new_ip):
                QMessageBox.warning(self, "경고", "올바른 IP 주소 형식이 아닙니다.")
                return
            
            # 포트 번호 검증 (숫자만 허용)
            if new_port and not new_port.isdigit():
                QMessageBox.warning(self, "경고", "포트는 숫자만 입력 가능합니다.")
                return
            
            # 서버 이름 중복 확인
            if (new_server_name != self.original_server_name and 
                new_server_name in server_config.servers):
                QMessageBox.warning(self, "경고", f"'{new_server_name}' 서버가 이미 존재합니다.")
                return
            
            # 새로운 서버 정보 생성
            new_server_info = {
                'NAME': new_server_name,
                'IP': new_ip,
                'PORT': new_port,
                'USERNAME': new_username,
                'PASSWORD': new_password
            }
            
            # 기존 서버 삭제 후 새로운 정보로 저장
            del server_config.servers[self.original_server_name]
            server_config.servers[new_server_name] = convert_to_idrac_config(new_server_info)
            server_config.save_servers()
            
            # 빠른 연결 서버였다면 새 이름으로 업데이트
            if server_config.quick_connect_server == self.original_server_name:
                server_config.save_quick_connect_server(new_server_name)
            
            # 서버 목록 새로고침
            self.load_servers()

class DellIDRACMonitor(QMainWindow):
    def __init__(self):
        super().__init__()
        self._is_closing = False
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, False)
        self.setWindowTitle(f"Dell iDRAC Monitor")
        self.resize(500, 400)
        
        self.last_update_check = datetime.now()
        self.server_section = create_server_section()  # 먼저 서버 섹션 생성
        self.settings_dialog = ServerSettingsDialog(self, self.server_section)
        
        self.init_ui()
        self.show()

    def init_ui(self):
        # 메뉴바 생성
        menubar = self.menuBar()
        
        # 파일 메뉴
        file_menu = menubar.addMenu('파일')
        export_action = file_menu.addAction('서버 설정 내보내기')
        import_action = file_menu.addAction('서버 설정 가져오기')
        file_menu.addSeparator()
        exit_action = file_menu.addAction('종료')
        
        # 보기 메뉴
        view_menu = menubar.addMenu('보기')
        log_view_action = view_menu.addAction('로그 보기')
        system_info_action = view_menu.addAction('시스템 정보')
        
        # 도구 메뉴
        tools_menu = menubar.addMenu('도구')
        quick_connect_action = tools_menu.addAction('빠른 연결로 설정')
        refresh_action = tools_menu.addAction('새로 고침')
        
        # 도움말 메뉴
        help_menu = menubar.addMenu('도움말')
        check_update_action = help_menu.addAction('업데이트 확인')
        open_log_action = help_menu.addAction('로그 폴더 열기')
        about_action = help_menu.addAction('정보')
        
        # 액션 연결
        exit_action.triggered.connect(self.close)
        check_update_action.triggered.connect(self.check_updates)
        open_log_action.triggered.connect(self.open_log_folder)
        refresh_action.triggered.connect(self.refresh_server_list)
        quick_connect_action.triggered.connect(self.settings_dialog.set_quick_connect_server)
        
        self.center()
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 전체 레이아웃을 수평 분할
        main_layout = QHBoxLayout(central_widget)
        main_layout.setSpacing(2)
        main_layout.setContentsMargins(2, 2, 2, 2)
        
        # 왼쪽 영역 (서버 목록)
        left_layout = QVBoxLayout()
        left_layout.setSpacing(2)
        
        # 서버 목록 그룹 추가
        server_group = QGroupBox("서버 목록")
        server_layout = QVBoxLayout(server_group)
        server_layout.setSpacing(2)
        
        # settings_dialog의 server_list 사용
        self.server_list = self.settings_dialog.server_list
        self.server_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.server_list.customContextMenuRequested.connect(self.settings_dialog.show_context_menu)
        
        # 서버 목록 위젯에 마우스 이벤트 핸들러 연결
        self.server_list.mousePressEvent = self.server_list_mouse_press_event
        
        server_layout.addWidget(self.server_list)
        
        # 서버 관련 버튼
        button_layout = QHBoxLayout()
        button_layout.setSpacing(2)
        
        add_server_btn = QPushButton("+ 서버 추가")
        quick_connect_btn = QPushButton("빠른 연결 지정")
        add_server_btn.clicked.connect(self.show_settings_dialog)
        quick_connect_btn.clicked.connect(self.settings_dialog.set_quick_connect_server)
        
        button_layout.addStretch()
        button_layout.addWidget(add_server_btn)
        button_layout.addWidget(quick_connect_btn)
        button_layout.addStretch()
        
        server_layout.addLayout(button_layout)
        left_layout.addWidget(server_group)
        
        # 오른쪽 영역 (기존 컴포넌트들)
        right_layout = QVBoxLayout()
        right_layout.setSpacing(2)
        
        # 서버 연결 섹션
        self.hardware_section = create_hardware_section(self)
        
        self.server_section.server_connection_changed.connect(
            self.hardware_section.on_server_connected
        )
        
        right_layout.addWidget(self.server_section)
        right_layout.addWidget(create_monitor_section())
        right_layout.addWidget(self.hardware_section)

        # 메인 레이아웃에 좌우 레이아웃 추가
        main_layout.addLayout(left_layout, 1)  # 1은 stretch factor
        main_layout.addLayout(right_layout, 3)  # 3은 stretch factor (오른쪽이 더 넓게)        

    def refresh_server_list(self):
        """서버 목록을 새로고침"""
        try:
            # 서버 설정 다시 로드
            server_config.load_servers()
            
            # 서버 목록 업데이트
            self.settings_dialog.load_servers()
            
            # 현재 연결된 서버 정보 갱신
            if hasattr(self, 'server_section'):
                self.server_section.update_server_info()
                
            logger.debug("서버 목록 새로고침 완료")
        except Exception as e:
            logger.error(f"서버 목록 새로고침 중 오류 발생: {e}")

    def showEvent(self, event):
        """윈도우가 실제로 화면에 표시된 후 호출되는 이벤트"""
        super().showEvent(event)
        if not hasattr(self, '_initialized'):
            self._initialized = True
            self.check_server_settings()

    def check_server_settings(self):
        """서버 설정 확인"""
        from config.server.server_config import server_config
        if not server_config.servers:
            self.show_settings_dialog()

    def closeEvent(self, a0: Optional[QCloseEvent]) -> None:
        """창 닫기 이벤트 처리"""
        if not self._is_closing and a0 is not None:
            self._is_closing = True
            logger.info("애플리케이션 종료 프로세스 시작")
            self.cleanup()
        if a0 is not None:
            super().closeEvent(a0)

    def cleanup(self):
        """모든 리소스 정리"""
        try:
            logger.debug("서버 연결 해제 중...")
            # hardware_section 정리
            if hasattr(self, 'hardware_section'):
                if hasattr(self.hardware_section, 'server_manager') and self.hardware_section.server_manager:
                    try:
                        self.hardware_section.server_manager = None
                    except Exception as e:
                        logger.error(f"서버 매니저 정리 중 오류: {e}")
                self.hardware_section.deleteLater()
                self.hardware_section = None
            
            # server_section 정리
            if hasattr(self, 'server_section'):
                self.server_section.cleanup()
                self.server_section.deleteLater()
                self.server_section = None
                
            # 타이머 정리
            if hasattr(self, 'update_timer'):
                self.update_timer.stop()
                self.update_timer.deleteLater()
                self.update_timer = None
                
            # 서버 목록 정리
            if hasattr(self, 'server_list'):
                self.server_list.clear()
                self.server_list.deleteLater()
                self.server_list = None
                
            logger.debug("모든 리소스 정리 완료")
            logger.info("애플리케이션 종료 완료")
                
            # Qt 애플리케이션 종료 - 마지막에 실행
            app = QCoreApplication.instance()
            if app:
                app.quit()
                
        except Exception as e:
            logger.error(f"종료 중 오류 발생: {e}")
        finally:
            self.setParent(None)
            self.deleteLater()
        
    def show_settings_dialog(self):
        """설정 창을 표시합니다."""
        if self.settings_dialog.exec():
            self.load_servers()

    def check_updates(self):
        from updater import check_for_updates
        check_for_updates(__version__)

    def check_server_settings(self):
        """서버 설정 확인"""
        try:
            from config.server.server_config import server_config
            if not server_config.servers:
                self.show_settings_dialog()
        except Exception as e:
            logger.error(f"서버 설정 확인 중 오류 발생: {e}")

    def open_log_folder(self):
        """로그 폴더를 Finder에서 엽니다."""
        log_dir = ResourceManager.get_log_dir()
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(log_dir)))

    def center(self):
        """윈도우를 화면 중앙에 배치합니다."""
        qr = self.frameGeometry()
        screen = QGuiApplication.primaryScreen()
        if screen is not None:
            cp = screen.availableGeometry().center()
            qr.moveCenter(cp)
            self.move(qr.topLeft())

    def server_list_mouse_press_event(self, event):
        """서버 목록 위젯의 마우스 좌클릭 이벤트 처리"""
        # 원래의 마우스 이벤트 처리
        super(QListWidget, self.server_list).mousePressEvent(event)
        
        # 마우스 좌클릭 이벤트 확인
        if event.button() == Qt.MouseButton.LeftButton:
            # 클릭된 아이템이 없다면 선택 해제
            if not self.server_list.itemAt(event.pos()):
                self.server_list.clearSelection()