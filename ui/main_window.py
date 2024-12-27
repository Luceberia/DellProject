from config.system.log_config import setup_logging
from PyQt6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QMessageBox, QProgressDialog
from PyQt6.QtGui import QGuiApplication, QCloseEvent, QDesktopServices
from PyQt6.QtCore import QCoreApplication, QTimer, Qt, QProcess
from typing import Optional
from ui.components.server_section import create_server_section
from ui.components.monitor_section import create_monitor_section
from ui.components.hardware_section import create_hardware_section
from ui.components.settings_dialog import SettingsDialog
from version import __version__
from updater import update_application

logger = setup_logging()

class DellIDRACMonitor(QMainWindow):
    def __init__(self):
        super().__init__()
        self._is_closing = False
        self.setWindowTitle(f"Dell iDRAC Monitor {__version__}")
        self.resize(500, 400)

        # 업데이트 체크 타이머 설정
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(lambda: update_application(self))
        self.update_timer.start(3600000)  # 1시간마다 체크

        self.center()
        
        # 중앙 위젯 생성
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # 설정 다이얼로그 초기화
        self.settings_dialog = SettingsDialog(self)
        
        # 서버 섹션 초기화
        self.server_section = create_server_section()
        
        # 하드웨어 섹션 초기화 (연결 전 상태)
        self.hardware_section = create_hardware_section(self)
        
        # 서버 섹션 시그널 연결
        self.server_section.server_connection_changed.connect(
            self.hardware_section.on_server_connected
        )

        # 각 섹션 추가
        main_layout.addWidget(self.server_section)
        main_layout.addWidget(create_monitor_section())
        main_layout.addWidget(self.hardware_section)

        # 종료 시그널 연결
        self._is_closing = False
        
        # 저장된 서버가 없으면 설정 창 자동으로 표시
        from config.server.server_config import server_config
        if not server_config.get_all_servers():
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
        """종료 전 정리 작업 수행"""
        try:
            logger.debug("서버 연결 해제 중...")
            # hardware_section 존재 여부 확인
            if hasattr(self, 'hardware_section') and self.hardware_section and hasattr(self.hardware_section, 'server_manager'):
                self.hardware_section.server_manager = None
            logger.debug("서버 연결 해제 완료")
            
            logger.debug("리소스 정리 중...")
            app = QCoreApplication.instance()
            if app:
                app.quit()
            logger.debug("리소스 정리 완료")

            # 업데이트 타이머 정지
            logger.debug("업데이트 타이머 정리 중...")
            if hasattr(self, 'update_timer'):
                self.update_timer.stop()
            logger.debug("업데이트 타이머 정리 완료")

        except Exception as e:
            logger.error(f"종료 중 오류 발생: {e}")
        finally:
            logger.info("애플리케이션 종료 완료")
        
    def show_settings_dialog(self):
        """설정 창을 표시합니다."""
        self.settings_dialog.exec()

    def center(self):
        """윈도우를 화면 중앙에 배치합니다."""
        qr = self.frameGeometry()
        screen = QGuiApplication.primaryScreen()
        if screen is not None:
            cp = screen.availableGeometry().center()
            qr.moveCenter(cp)
            self.move(qr.topLeft())