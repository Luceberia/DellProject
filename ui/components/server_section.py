from collections import OrderedDict
from datetime import datetime

import requests
import time

from config.server.server_config import server_config
from config.system.log_config import setup_logging
from managers.dell_server_manager import DellServerManager
from network.connection_manager import ConnectionManager
from PyQt6.QtCore import Qt, QDateTime, QTimer, pyqtSignal
from PyQt6.QtWidgets import (
    QGroupBox, QHBoxLayout, QLabel, QMessageBox, 
    QPushButton, QProgressDialog, QSizePolicy, QVBoxLayout
)
from ui.components.popups.help_dialog import HelpDialog
from version import __version__

logger = setup_logging()

class ServerUIManager:
    def __init__(self, parent):
        self.parent = parent
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self.parent)
        self.parent.current_server_label = QLabel("현재 서버: 서버를 선택해 주세요")
        layout.addWidget(self.parent.current_server_label)
        self.setup_tools_group(layout)

    def setup_tools_group(self, layout):
        tools_group = QGroupBox("도구")
        tools_layout = QHBoxLayout()
        self.parent.tools_buttons = {}
        button_configs = [
            ("🔌 연결", self.parent.toggle_server_connection),
            ("🔔 0", None),
            ("❓ 도움말", self.parent.show_help),
            (f"v{__version__}", self.parent.show_version_info),
        ]
        for text, callback in button_configs:
            button = QPushButton(text)
            button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            if callback:
                button.clicked.connect(callback)
            tools_layout.addWidget(button)
            self.parent.tools_buttons[text] = button
        tools_group.setLayout(tools_layout)
        layout.addWidget(tools_group)

class ServerSessionManager:
    def __init__(self):
        self.sessions = {}

    def get_session(self, server_name):
        return self.sessions.get(server_name)

    def create_session(self, server_name, server_info):
        session = {
            'server_name': server_name,
            'info': server_info,
            'connected': True,
            'last_connected': datetime.now()
        }
        self.sessions[server_name] = session
        return session

    def is_connected(self, server_name):
        session = self.get_session(server_name)
        return session and session['connected']

class CacheManager:
    def __init__(self, max_size=100, ttl=300):  # 300초(5분) TTL
        self.cache = OrderedDict()
        self.max_size = max_size
        self.ttl = ttl

    def get(self, key):
        if key in self.cache:
            value, timestamp = self.cache[key]
            if time.time() - timestamp <= self.ttl:
                return value
            del self.cache[key]
        return None

    def set(self, key, value):
        if len(self.cache) >= self.max_size:
            self.cache.popitem(last=False)
        self.cache[key] = (value, time.time())

class ServerSection(QGroupBox):
    # 상수 정의
    RETRY_MAX_COUNT = 3
    RETRY_INTERVAL = 5
    MIN_POLLING_INTERVAL = 5000
    MAX_POLLING_INTERVAL = 60000
    LOG_CHECK_INTERVAL = 30
    RESPONSE_TIME_THRESHOLD = 300
    RESPONSE_TIME_CRITICAL = 1000

    server_connection_changed = pyqtSignal(str, bool)  # 서버 이름과 연결 상태만 전달

    def __init__(self, parent=None):
        super().__init__(parent)
        self.logger = logger
        self.current_server_info = None
        self.connection_manager = ConnectionManager()
        self.cache_manager = CacheManager()
        self.session_manager = ServerSessionManager()
        self.ui_manager = ServerUIManager(self)
        self.setup_timers()
        self.cached_data = {}
        self.setup_status_checker()

    def setup_timers(self):
        self.connection_timer = QTimer()
        self.connection_timer.timeout.connect(self.check_connection_health)
        self.connection_retry_count = 0
        self.last_response_time = None
        self.last_log_check_time = 0
        self.use_event_subscription = False
        self.current_polling_interval = self.MIN_POLLING_INTERVAL

    def show_version_info(self):
        from updater import check_for_updates
        check_for_updates(__version__)

    def show_help(self):
        HelpDialog(self).exec()

    def toggle_server_connection(self):
        if hasattr(self, 'server_manager'):
            self.disconnect_server()
        else:
            current_server = self.current_server_label.text()
            if "서버를 선택해 주세요" in current_server:
                self.logger.warning("서버가 선택되지 않았습니다.")
                return
            server_name = current_server.replace("현재 서버: ", "").split('(')[0].strip()
            server_info = server_config.get_server(server_name)
            if server_info:
                self.connect_server(server_info)
            else:
                self.logger.error(f"서버 정보를 찾을 수 없습니다: {server_name}")

    def connect_server(self, server_info):
        try:
            server_name = server_info['NAME']
            session = self.session_manager.get_session(server_name)

            if session and session['connected']:
                # 기존 세션 재사용 시 UI 업데이트 추가
                self.logger.info(f"기존 세션 재사용: {server_name}")
                self.current_server_info = server_info
                self.update_ui_status("connected", {"response_time": "재사용"})
                # 현재 서버 정보 업데이트
                self.setup_successful_connection(server_info, "재사용")
                return True

            # 새로운 연결 시도
            progress = QProgressDialog(f"{server_name} 연결 시도 중...", None, 0, 0, self)
            progress.setWindowModality(Qt.WindowModality.WindowModal)
            progress.setMinimumDuration(0)
            progress.setCancelButton(None)
            progress.show()

            self.update_ui_status("connecting")
            response_time = self.connection_manager.check_connection_with_timeout(server_info)

            # response_time이 None이 아니면 연결 성공으로 간주
            if response_time is not None:
                session = self.session_manager.create_session(server_name, server_info)
                self.setup_successful_connection(server_info, response_time)
                progress.close()
                return True
            else:
                self.update_ui_status("disconnected", "연결 실패")
                progress.close()
                QMessageBox.warning(self, "연결 실패", f"서버 '{server_name}'에 연결할 수 없습니다. 설정을 확인해주세요.")
                return False

        except Exception as e:
            self.logger.error(f"서버 연결 실패: {str(e)}")
            self.update_ui_status("disconnected", "연결 오류")
            QMessageBox.critical(self, "심각한 오류", f"서버 연결 중 심각한 오류가 발생했습니다: {str(e)}")
            return False

    def setup_status_checker(self):
        self.status_checker = QTimer()
        self.status_checker.timeout.connect(self.check_all_connections)
        self.status_checker.start(5000)  # 5초마다 확인

    def check_all_connections(self):
        try:
            # 연결 해제된 서버를 추적하기 위한 리스트
            disconnected_servers = []

            # 세션 매니저의 세션 복사본 생성
            current_sessions = list(self.session_manager.sessions.items())

            for server_name, session in current_sessions:
                try:
                    is_alive = self.connection_manager.check_connection_with_timeout(session['info'])
                    if not is_alive:
                        # 세션 상태 업데이트
                        session['connected'] = False
                        self.update_ui_status("disconnected", "연결 끊김")
                        
                        # 상태 변경 시그널 발생
                        self.server_connection_changed.emit(server_name, False)
                        
                        # 연결 해제된 서버 추적
                        disconnected_servers.append(server_name)
                except Exception as e:
                    self.logger.error(f"서버 연결 확인 실패: {str(e)}")
                    disconnected_servers.append(server_name)

            # 완전히 연결 해제된 서버 세션 제거
            for server_name in disconnected_servers:
                if server_name in self.session_manager.sessions:
                    del self.session_manager.sessions[server_name]

        except Exception as e:
            self.logger.error(f"서버 연결 확인 전체 프로세스 실패: {str(e)}")

    def clear_system_info(self):
        """시스템 정보 초기화"""
        try:
            # 시스템 정보 초기화
            self.current_server_info = None
            self.server_manager = None
            # UI 상태 업데이트
            self.update_ui_status("disconnected", "연결 끊김")
        except Exception as e:
            self.logger.error(f"시스템 정보 초기화 중 오류: {str(e)}")

    def setup_successful_connection(self, server_dict, response_time):
        self.current_server_info = server_dict
        self.server_manager = DellServerManager(
            ip=server_dict['IP'],
            port=server_dict.get('PORT', '443'),
            auth=(server_dict['USERNAME'], server_dict['PASSWORD'])
        )
        
        self.update_log_count()
        self.check_event_subscription()
        self.setup_sel_log_button()
        self.update_ui_status("connected", {"response_time": response_time})
        self.reset_connection_state()
        
        # 서버 연결 상태 업데이트 (중복 방지)
        server = server_config.servers.get(server_dict['NAME'])
        if server and not server.CONNECTED:
            server.CONNECTED = True
            server.LAST_CONNECTED = datetime.now()
            
            # 상태 변경 시그널 발생 (중복 방지)
            self.server_connection_changed.emit(server_dict['NAME'], True)
        
        self.update_ui_on_connection()

    def disconnect_server(self, server_name=None):
        """서버 연결 해제 메서드"""
        try:
            # 현재 서버 이름 결정
            if server_name is None:
                current_server = self.current_server_label.text()
                if "서버를 선택해 주세요" in current_server:
                    self.logger.warning("연결 해제할 서버가 선택되지 않았습니다.")
                    return False
                server_name = current_server.replace("현재 서버: ", "").split('(')[0].strip()

            # 연결 관리자를 통해 서버 연결 해제
            if hasattr(self, 'connection_manager'):
                result = self.connection_manager.disconnect_server(server_name)
                
                if result:
                    # UI 상태 업데이트
                    self.update_ui_disconnected()
                    
                    # 세션 관리자에서 세션 제거
                    if server_name in self.session_manager.sessions:
                        del self.session_manager.sessions[server_name]
                    
                    # 현재 서버 정보 초기화
                    self.current_server_info = None
                    
                    # 연결 상태 시그널 발생
                    self.server_connection_changed.emit(server_name, False)
                    
                    return True
                else:
                    self.logger.warning(f"서버 연결 해제 실패: {server_name}")
                    return False
            else:
                self.logger.error("연결 관리자가 초기화되지 않았습니다.")
                return False
        
        except Exception as e:
            self.logger.error(f"서버 연결 해제 중 오류 발생: {str(e)}")
            QMessageBox.critical(self, "연결 해제 오류", f"서버 연결 해제 중 오류가 발생했습니다: {str(e)}")
            return False

    def update_ui_disconnected(self, message="연결 해제됨"):
        """UI를 연결 해제 상태로 업데이트"""
        # 현재 서버 레이블 초기화
        self.current_server_label.setText("현재 서버: 서버를 선택해 주세요")
        
        # 연결 상태 관련 UI 요소 업데이트
        if hasattr(self, 'tools_buttons') and '🔌 연결' in self.tools_buttons:
            self.tools_buttons['🔌 연결'].setText('🔌 연결')
        
        # 필요한 경우 추가 UI 업데이트 로직 구현

    def check_connection_health(self):
        if not self.current_server_info:
            return

        cached_health = self.cache_manager.get('connection_health')
        if cached_health:
            return cached_health

        try:
            start_time = time.time()
            if not self.server_manager.check_connection():
                self.handle_connection_failure()
                return

            response_time = int((time.time() - start_time) * 1000)
            self.cache_manager.set('connection_health', response_time)
            self.process_successful_health_check(response_time)
        except Exception as e:
            self.logger.error(f"서버 연결 확인 중 오류 발생: {str(e)}")
            self.handle_connection_failure()

    def process_successful_health_check(self, response_time):
        self.last_response_time = response_time
        self.connection_retry_count = 0
        self.update_ui_status("connected", {"response_time": response_time})
        self.adjust_polling_interval(response_time)
        self.check_sel_logs_if_needed()

    def handle_connection_failure(self):
        self.connection_retry_count += 1
        self.update_ui_status("connecting", f"재연결 시도 중... (시도 횟수: {self.connection_retry_count})")
        if self.connection_retry_count >= self.RETRY_MAX_COUNT:
            self.logger.warning(f"연결 재시도 계속 진행 중... (현재 시도 횟수: {self.connection_retry_count})")
            self.adjust_polling_interval(None)

    def adjust_polling_interval(self, response_time):
        if response_time is None or response_time >= self.RESPONSE_TIME_CRITICAL:
            new_interval = min(self.connection_timer.interval() + 5000, self.MAX_POLLING_INTERVAL)
            self.connection_timer.setInterval(new_interval)
            self.logger.warning(f"폴링 간격 조정: {new_interval}ms")
        elif response_time < self.RESPONSE_TIME_THRESHOLD:
            self.connection_timer.setInterval(self.MIN_POLLING_INTERVAL)

    def check_sel_logs_if_needed(self):
        current_time = time.time()
        if current_time - self.last_log_check_time >= self.LOG_CHECK_INTERVAL:
            self.check_sel_logs()
            self.last_log_check_time = current_time

    def check_sel_logs(self):
        try:
            previous_count = int(self.tools_buttons["🔔 0"].text().split()[1])
            self.update_log_count()
            new_count = int(self.tools_buttons["🔔 0"].text().split()[1])
            if new_count != previous_count:
                self.logger.info(f"SEL 로그 카운트 변경: {previous_count} → {new_count}")
        except Exception as e:
            self.logger.error(f"SEL 로그 확인 실패: {str(e)}")

    def update_log_count(self):
        if not hasattr(self, 'server_manager'):
            return
        try:
            sel_entries = self.server_manager.fetch_sel_entries()
            count = len(sel_entries.get('Members', []))
            self.update_log_ui(count)
            self.logger.debug(f"SEL 로그 카운트 업데이트: {count}")
        except Exception as e:
            self.logger.error(f"SEL 로그 카운트 업데이트 실패: {str(e)}")
            self.update_log_ui(0)

    def update_log_ui(self, count):
        bell_button = self.tools_buttons["🔔 0"]
        bell_button.setText(f"🔔 {count}")
        current_time = QDateTime.currentDateTime().toString("yyyy-MM-dd hh:mm:ss")
        tooltip = f"마지막 업데이트: {current_time}\nSEL 로그: {count}개"
        try:
            sel_service = self.server_manager.fetch_sel_service()
            if sel_service:
                service_status = sel_service.get('Status', {}).get('State', 'Unknown')
                tooltip += f"\n서비스 상태: {service_status}"
        except Exception as e:
            self.logger.debug(f"SEL 서비스 정보 조회 실패: {str(e)}")
        bell_button.setToolTip(tooltip)

    def check_event_subscription(self):
        if not hasattr(self, 'server_manager'):
            self.use_event_subscription = False
            return
        try:
            base_url = f"https://{self.current_server_info['IP']}:{self.current_server_info['PORT']}"
            self.logger.debug("Redfish 이벤트 서비스 상태 확인 시작")
            service_response = requests.get(
                f"{base_url}/redfish/v1/EventService",
                auth=self.server_manager.auth,
                verify=False
            )
            if service_response.status_code == 200:
                self.process_event_service_response(service_response, base_url)
            else:
                self.logger.warning("이벤트 서비스 비활성화 상태 - 폴링 방식으로 전환")
                self.use_event_subscription = False
        except Exception as e:
            self.logger.error(f"이벤트 서비스 확인 실패: {str(e)}")
            self.use_event_subscription = False
            self.logger.info("이벤트 서비스 확인 실패로 폴링 방식으로 전환")

    def process_event_service_response(self, service_response, base_url):
        service_data = service_response.json()
        if service_data.get('Status', {}).get('State') == 'Enabled':
            self.check_subscription_status(base_url)
        else:
            self.logger.warning("이벤트 서비스 비활성화 상태 - 폴링 방식으로 전환")
            self.use_event_subscription = False

    def check_subscription_status(self, base_url):
        subscription_response = requests.get(
            f"{base_url}/redfish/v1/EventService/Subscriptions",
            auth=self.server_manager.auth,
            verify=False
        )
        if subscription_response.status_code == 200:
            subscriptions = subscription_response.json().get('Members', [])
            self.use_event_subscription = len(subscriptions) > 0
            self.logger.info(f"Redfish 이벤트 구독 상태: {'활성화' if self.use_event_subscription else '비활성화'}")
            if not self.use_event_subscription:
                self.logger.info("구독이 비활성화되어 있어 폴링 방식으로 전환")
                self.last_log_check_time = time.time()
        else:
            self.logger.warning("구독 상태 확인 실패 - 폴링 방식으로 전환")
            self.use_event_subscription = False

    def update_ui_status(self, status_type, data=None):
        if status_type == "connected":
            self.update_ui_connected(data)
        elif status_type == "connecting":
            self.update_ui_connecting(data)
        elif status_type == "disconnected":
            self.update_ui_disconnected(data)

    def update_ui_connected(self, data):
        server_name = self.current_server_info.get('NAME', 'Unknown')
        server_ip = self.current_server_info.get('IP', '')
        response_time = data.get('response_time') if data else None
        self.current_server_label.setText(f"현재 서버: {server_name} ({server_ip})")
        status_text = f"✅ 연결됨 ({response_time}ms)" if response_time else "✅ 연결됨"
        self.tools_buttons["🔌 연결"].setText(status_text)

    def update_ui_connecting(self, message="연결 중..."):
        self.current_server_label.setText("현재 서버: 연결 시도 중...")
        self.tools_buttons["🔌 연결"].setText(f"🔄 {message}")

    def update_ui_disconnected(self, message="연결 해제됨"):
        self.current_server_label.setText("현재 서버: 서버를 선택해 주세요")
        self.tools_buttons["🔌 연결"].setText(f"🔌 {message}")
        self.tools_buttons["🔔 0"].setText("🔔 0")

    def setup_sel_log_button(self):
        from ui.components.monitor_section import show_sel_log_popup
        bell_button = self.tools_buttons["🔔 0"]
        bell_button.clicked.disconnect() if bell_button.receivers(bell_button.clicked) > 0 else None
        bell_button.clicked.connect(lambda: show_sel_log_popup(self))

    def reset_connection_state(self):
        self.connection_retry_count = 0
        self.last_response_time = None
        self.connection_timer.start(self.MIN_POLLING_INTERVAL)

    def update_ui_on_connection(self):
        main_window = self.window()
        if hasattr(main_window, 'hardware_section'):
            main_window.hardware_section.update_system_info()
        if hasattr(main_window, 'monitor_section'):
            main_window.monitor_section.update_all_status()

    @staticmethod
    def convert_server_info(server_info):
        if hasattr(server_info, 'NAME'):
            return {
                'NAME': server_info.NAME,
                'IP': server_info.IP,
                'PORT': server_info.PORT,
                'USERNAME': server_info.USERNAME,
                'PASSWORD': server_info.PASSWORD
            }
        return server_info

    def cleanup(self):
        """서버 섹션 정리 작업 수행"""
        try:
            # 타이머 정리
            if hasattr(self, 'connection_timer'):
                self.connection_timer.stop()
                self.connection_timer.deleteLater()
                
            # 서버 매니저 정리
            if hasattr(self, 'server_manager'):
                self.server_manager = None
                
            # 캐시 데이터 정리
            if hasattr(self, 'cached_data'):
                self.cached_data.clear()
                
            # UI 상태 초기화
            self.update_ui_status("disconnected")
            
            logger.debug("서버 섹션 정리 완료")
        except Exception as e:
            logger.error(f"서버 섹션 정리 중 오류 발생: {str(e)}")

def create_server_section():
    return ServerSection()
