from config.system.log_config import setup_logging
from PyQt6.QtWidgets import QGroupBox, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QSizePolicy, QDialog
from PyQt6.QtCore import pyqtSignal, QTimer, QDateTime
from ui.components.settings_dialog import SettingsDialog
from network.connection_manager import ConnectionManager
from config.server.server_config import server_config
from managers.dell_server_manager import DellServerManager
from ui.components.update_dialog import UpdateDialog
from ui.components.popups.help_dialog import HelpDialog
from utils.server_utils import convert_to_dict
from version import __version__
from updater import check_for_updates
import requests
import time

class ServerSection(QGroupBox):
    server_connection_changed = pyqtSignal(dict)
    def __init__(self, parent=None):
        super().__init__(parent)
        self.logger = None
        self.current_server_info = None
        self.connection_manager = None
        self.connection_timer = QTimer()
        self.connection_timer.timeout.connect(self.check_connection_health)
        self.connection_retry_count = 0
        self.last_response_time = None
        self.last_log_check_time = 0
        self.log_check_interval = 30
        self.last_log_count = 0
        self.use_event_subscription = False
        
        # 기본 UI 설정
        self.setup_ui()
        
        # 나머지 초기화는 비동기로 수행
        QTimer.singleShot(0, self.delayed_init)

    def delayed_init(self):
        """지연된 초기화 수행"""
        self.logger = setup_logging()
        self.connection_manager = ConnectionManager()
        # 연결 타이머는 실제 서버 선택 후에 시작

    def start_connection_timer(self):
        """서버가 선택되었을 때만 타이머 시작"""
        if not self.connection_timer.isActive():
            self.connection_timer.start(5000)

    def stop_connection_timer(self):
        """서버 연결이 해제되었을 때 타이머 중지"""
        if self.connection_timer.isActive():
            self.connection_timer.stop()

    def setup_ui(self):
        """UI 초기화"""
        layout = QVBoxLayout(self)
        
        # 현재 서버 표시
        self.current_server_label = QLabel("현재 서버: 서버를 선택해 주세요")
        layout.addWidget(self.current_server_label)
        
        # 도구 버튼 그룹
        tools_group = QGroupBox("도구")
        tools_layout = QHBoxLayout()
        
        self.tools_buttons = {}
        button_configs = [
            ("⚙️ 설정", self.show_settings),
            ("🔌 연결", self.check_server_connection),
            ("🔔 0", None),
            ("❓ 도움말", self.show_help),
            ("v" + __version__, self.show_version_info),
        ]
        
        for text, callback in button_configs:
            button = QPushButton(text)
            button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            if callback:
                button.clicked.connect(callback)
            tools_layout.addWidget(button)
            self.tools_buttons[text] = button
        
        tools_group.setLayout(tools_layout)
        layout.addWidget(tools_group)

    def show_version_info(self):
        try:
            from version import __version__
            latest_release = check_for_updates(__version__)
            
            version_info = {
                'current': __version__,
                'latest': latest_release['tag_name'].replace('v', '') if latest_release else __version__
            }
            
            dialog = UpdateDialog(
                self,
                version_info,
                is_update=(latest_release is not None)
            )
            
            result = dialog.exec()
            
            if result == QDialog.DialogCode.Accepted and latest_release:
                main_window = self.window()
                if hasattr(main_window, 'apply_update'):
                    main_window.apply_update(latest_release)
                    
        except Exception as e:
            self.logger.error(f"버전 확인 중 오류 발생: {e}")
            error_dialog = UpdateDialog(
                self,
                {'current': str(e)},
                is_update=False
            )
            error_dialog.exec()

    def show_help(self):
        help_dialog = HelpDialog(self)
        help_dialog.exec()

    def show_settings(self):
        dialog = SettingsDialog(self)
        dialog.exec()

    def on_server_connected(self, server_info):
        """서버 연결 시그널 처리"""
        self.current_server_info = server_info
        self.update_current_server_label(server_info)
        
        # DellServerManager 인스턴스 생성
        self.server_manager = DellServerManager(
            ip=server_info['IP'],
            port=server_info.get('PORT', '443'),
            auth=(server_info['USERNAME'], server_info['PASSWORD'])
        )

        self.check_event_subscription()  # 이벤트 구독 상태 확인

        # SEL 로그 버튼 이벤트 핸들러 연결
        from ui.components.monitor_section import show_sel_log_popup
        bell_button = self.tools_buttons["🔔 0"]
        bell_button.clicked.disconnect() if bell_button.receivers(bell_button.clicked) > 0 else None
        bell_button.clicked.connect(lambda: show_sel_log_popup(self))
        
        # 연결 상태 초기화
        self.connection_retry_count = 0
        self.last_response_time = None
        
        # 상태 업데이트 및 버튼 활성화
        self.update_connection_status("연결됨", "✅")
        self.enable_all_buttons()
        
        # 로그 카운트 업데이트
        self.update_log_count()
        
        # 연결 상태 모니터링 시작
        self.start_connection_timer()
        
        # 시스템 정보 업데이트 시그널 발생
        self.server_connection_changed.emit(server_info)
        
        # 메인 윈도우의 다른 섹션 업데이트
        main_window = self.window()
        if hasattr(main_window, 'hardware_section'):
            main_window.hardware_section.update_system_info()
        if hasattr(main_window, 'monitor_section'):
            main_window.monitor_section.update_all_status()

    def update_current_server_label(self, server_info):
        """현재 서버 표시 레이블 업데이트"""
        display_text = f"{server_info.get('NAME')} ({server_info.get('IP')})"
        self.current_server_label.setText(f"현재 서버: {display_text}")
        logger.debug(f"현재 서버 표시 업데이트: {display_text}")

    def check_server_connection(self):
        """연결 버튼 클릭 이벤트 처리"""
        if hasattr(self, 'server_manager'):
            self.disconnect_server()
            return

        current_server = self.current_server_label.text()
        if "서버를 선택해 주세요" in current_server:
            return
            
        server_name = current_server.replace("현재 서버: ", "").split('(')[0].strip()
        server_info = server_config.get_server(server_name)
        if server_info:
            self.connect_server(server_info)

    def disconnect_server(self):
        """서버 연결 해제 및 상태 초기화"""
        self.stop_connection_timer()
        self.server_manager = None
        self.current_server_info = None
        self.connection_retry_count = 0
        self.last_response_time = None
        
        # UI 상태 초기화
        self.update_connection_status("연결 해제됨", "🔌")
        self.current_server_label.setText("현재 서버: 서버를 선택해 주세요")
        self.tools_buttons["🔔 0"].setText("🔔 0")
        
        # 이벤트 핸들러 제거
        bell_button = self.tools_buttons["🔔 0"]
        if bell_button.receivers(bell_button.clicked) > 0:
            bell_button.clicked.disconnect()
        
        # 버튼 상태 초기화
        self.disable_all_buttons()
        
        # 설정, 연결, 도움말 버튼은 다시 활성화
        self.tools_buttons["⚙️ 설정"].setEnabled(True)
        self.tools_buttons["🔌 연결"].setEnabled(True)
        self.tools_buttons["❓ 도움말"].setEnabled(True)

    def connect_server(self, server_info):
        """서버 연결 및 상태 모니터링 시작"""
        try:
            self.update_connection_status("연결 중...", "🔄")
            
            # 서버 정보를 딕셔너리로 변환
            if hasattr(server_info, 'NAME'):  # IDRACConfig 인스턴스인 경우
                server_dict = {
                    'NAME': server_info.NAME,
                    'IP': server_info.IP,
                    'PORT': server_info.PORT,
                    'USERNAME': server_info.USERNAME,
                    'PASSWORD': server_info.PASSWORD
                }
            else:  # 이미 딕셔너리인 경우
                server_dict = server_info
            
            # 연결 시도
            response_time = self.connection_manager.check_connection_with_timeout(server_dict)
            if response_time:
                self.current_server_info = server_dict
                self.server_manager = DellServerManager(
                    ip=server_dict['IP'],
                    port=server_dict['PORT'],
                    auth=(server_dict['USERNAME'], server_dict['PASSWORD'])
                )
                
                # 이벤트 구독 상태 확인
                self.check_event_subscription()

                # SEL 로그 버튼 이벤트 핸들러 연결
                from ui.components.monitor_section import show_sel_log_popup
                bell_button = self.tools_buttons["🔔 0"]
                bell_button.clicked.disconnect() if bell_button.receivers(bell_button.clicked) > 0 else None
                bell_button.clicked.connect(lambda: show_sel_log_popup(self))
                
                self.update_connection_status(f"연결됨 ({response_time}ms)", "✅")
                self.connection_retry_count = 0
                self.last_response_time = response_time
                
                # 상태 업데이트 및 버튼 활성화
                self.enable_all_buttons()
                self.update_log_count()
                
                # 현재 서버 레이블 업데이트
                self.update_current_server_label(server_dict)
                
                # 연결 상태 모니터링 시작
                self.start_connection_timer()
                
                # 시스템 정보 업데이트 시그널 발생
                self.server_connection_changed.emit(server_dict)
                
                # 메인 윈도우의 다른 섹션 업데이트
                main_window = self.window()
                if hasattr(main_window, 'hardware_section'):
                    main_window.hardware_section.update_system_info()
                if hasattr(main_window, 'monitor_section'):
                    main_window.monitor_section.update_all_status()
            else:
                self.update_connection_status("연결 실패", "❌")
                
        except Exception as e:
            logger.error(f"서버 연결 실패: {str(e)}")
            self.update_connection_status("연결 오류", "❌")

    def check_event_subscription(self):
        """Redfish 이벤트 구독 상태 확인"""
        if not hasattr(self, 'server_manager'):
            logger.debug("서버 매니저가 초기화되지 않음")
            self.use_event_subscription = False
            return
            
        try:
            base_url = f"https://{self.current_server_info['IP']}:{self.current_server_info['PORT']}"
            logger.debug("Redfish 이벤트 서비스 상태 확인 시작")
            
            service_response = requests.get(
                f"{base_url}/redfish/v1/EventService",
                auth=self.server_manager.auth,
                verify=False
            )
            
            if service_response.status_code == 200:
                service_data = service_response.json()
                
                if service_data.get('Status', {}).get('State') == 'Enabled':
                    # 구독 상태 확인
                    subscription_response = requests.get(
                        f"{base_url}/redfish/v1/EventService/Subscriptions",
                        auth=self.server_manager.auth,
                        verify=False
                    )
                    
                    if subscription_response.status_code == 200:
                        subscriptions = subscription_response.json().get('Members', [])
                        self.use_event_subscription = len(subscriptions) > 0
                        logger.info(f"Redfish 이벤트 구독 상태: {'활성화' if self.use_event_subscription else '비활성화'}")
                        
                        if not self.use_event_subscription:
                            logger.info("구독이 비활성화되어 있어 폴링 방식으로 전환")
                            self.last_log_check_time = time.time()
                    else:
                        logger.warning("구독 상태 확인 실패 - 폴링 방식으로 전환")
                        self.use_event_subscription = False
                else:
                    logger.warning("이벤트 서비스 비활성화 상태 - 폴링 방식으로 전환")
                    self.use_event_subscription = False
                    
        except Exception as e:
            logger.error(f"이벤트 서비스 확인 실패: {str(e)}")
            self.use_event_subscription = False
            logger.info("이벤트 서비스 확인 실패로 폴링 방식으로 전환")

    def check_connection_health(self):
        """주기적인 연결 상태 확인"""
        if not self.current_server_info:
            try:
                response = requests.get(f"http://{self.current_server_label.text().split('(')[1].strip(')')}", timeout=2)
                if response.status_code != 200:
                    self.update_connection_status("서버 응답 없음", "⚠️")
                    self.disable_all_buttons()
            except:
                self.update_connection_status("연결 끊김", "❌")
                self.disable_all_buttons()
            return

        try:
            response_time = self.connection_manager.check_connection_with_timeout(self.current_server_info, timeout=2)
            current_time = time.time()
            
            if response_time:
                if self.last_response_time is None or abs(response_time - self.last_response_time) > 50:
                    logger.info(f"서버 연결 상태 변경: {self.current_server_info['IP']} (응답시간: {response_time}ms)")
                
                if response_time > 100:
                    self.update_connection_status(f"응답 지연 ({response_time}ms)", "⚠️")
                else:
                    self.update_connection_status(f"연결됨 ({response_time}ms)", "✅")
                    
                # 이벤트 구독이 비활성화된 경우에만 주기적 로그 체크
                if not hasattr(self, 'use_event_subscription') or not self.use_event_subscription:
                    if current_time - self.last_log_check_time >= self.log_check_interval:
                        logger.debug("폴링 방식으로 SEL 로그 조회")
                        self.update_log_count()
                        self.last_log_check_time = current_time
                
                self.last_response_time = response_time
                self.connection_retry_count = 0
                self.enable_all_buttons()
            else:
                self.connection_retry_count += 1
                if self.connection_retry_count > 2:
                    self.update_connection_status("연결 끊김", "❌")
                    self.disable_all_buttons()
                else:
                    self.update_connection_status(f"재연결 시도 중... ({self.connection_retry_count}/3)", "🔄")
        except Exception as e:
            logger.error(f"연결 상태 확인 실패: {str(e)}")
            self.update_connection_status("연결 오류", "⚠️")
            self.disable_all_buttons()

    def disable_all_buttons(self):
        """모든 기능 버튼 비활성화"""
        for name, button in self.tools_buttons.items():
            if name not in ["⚙️ 설정", "🔌 연결", "❓ 도움말", "v" + __version__]:  # 설정, 연결, 버전, 도움말 버튼은 제외
                button.setEnabled(False)
        
        # 상태 표시 업데이트
        self.current_server_label.setStyleSheet("color: #FF6B6B;")  # 빨간색으로 변경

    def enable_all_buttons(self):
        """모든 기능 버튼 활성화"""
        for button in self.tools_buttons.values():
            button.setEnabled(True)
        
        # 상태 표시 복구
        self.current_server_label.setStyleSheet("")  # 기본 색상으로 복구

    def update_connection_status(self, status, icon="🔌"):
        """연결 상태에 따른 UI 업데이트"""
        connect_button = self.tools_buttons["🔌 연결"]
        connect_button.setText(f"{icon} {status}")
        logger.debug(f"연결 상태 업데이트: {status}")

    def update_log_count(self):
        if not hasattr(self, 'server_manager'):
            return
            
        try:
            sel_entries = self.server_manager.fetch_log_entries('sel')
            entries = sel_entries.get('Members', [])
            count = len(entries)
            
            bell_button = self.tools_buttons["🔔 0"]
            current_count = int(bell_button.text().split()[1])
            
            # 단순히 현재 로그 수를 반영
            if count != current_count:
                bell_button.setText(f"🔔 {count}")
                logger.debug(f"SEL 로그 카운트 변경: {current_count} → {count}")
                
                # 툴팁 업데이트
                current_time = QDateTime.currentDateTime().toString("yyyy-MM-dd hh:mm:ss")
                bell_button.setToolTip(f"마지막 업데이트: {current_time}")
                
        except Exception as e:
            logger.error(f"SEL 로그 카운트 업데이트 실패: {str(e)}")
            
def create_server_section():
    return ServerSection()
