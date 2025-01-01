from config.system.app_config import ResourceManager
from config.system.log_config import setup_logging
from PyQt6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QDialog, QProgressDialog, QMessageBox, QApplication
from PyQt6.QtGui import QGuiApplication, QCloseEvent, QDesktopServices
from PyQt6.QtCore import Qt, QUrl, QCoreApplication, QDateTime
from typing import Optional
from ui.components.server_section import create_server_section
from ui.components.monitor_section import create_monitor_section
from ui.components.hardware_section import create_hardware_section
from ui.components.settings_dialog import SettingsDialog
from datetime import datetime
from version import __version__
from updater import show_update_dialog, download_and_apply_update


logger = setup_logging()

class DellIDRACMonitor(QMainWindow):
    def __init__(self):
        super().__init__()
        self._is_closing = False
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, False)
        self.setWindowTitle(f"Dell iDRAC Monitor")
        self.resize(500, 400)
        
        # 마지막 업데이트 확인 시간 저장
        self.last_update_check = datetime.now()
        
        self.init_ui()
        self.show()

    def init_ui(self):
        menubar = self.menuBar()
        help_menu = menubar.addMenu('도움말')
        
        # 업데이트 확인 메뉴 추가
        check_update_action = help_menu.addAction('업데이트 확인')
        check_update_action.triggered.connect(self.check_updates)
        
        open_log_action = help_menu.addAction('로그 폴더 열기')
        open_log_action.triggered.connect(self.open_log_folder)
        
        self.center()
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        self.settings_dialog = SettingsDialog(self)
        self.server_section = create_server_section()
        self.hardware_section = create_hardware_section(self)
        
        self.server_section.server_connection_changed.connect(
            self.hardware_section.on_server_connected
        )
        
        main_layout.addWidget(self.server_section)
        main_layout.addWidget(create_monitor_section())
        main_layout.addWidget(self.hardware_section)

    def showEvent(self, event):
        """윈도우가 실제로 화면에 표시된 후 호출되는 이벤트"""
        super().showEvent(event)
        from config.server.server_config import server_config
        server_config.initialize()  # 서버 설정 초기화
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

    def check_updates(self):
        result, latest_release = show_update_dialog(self, __version__)
        if result == QDialog.DialogCode.Accepted and latest_release:
            self.apply_update(latest_release)
            self.last_update_check = QDateTime.currentDateTime()

    def apply_update(self, latest_release):
        download_url = latest_release['assets'][0]['browser_download_url']
        progress_dialog = QProgressDialog("업데이트 다운로드 중...", "취소", 0, 100, self)
        progress_dialog.setWindowModality(Qt.WindowModal)
        progress_dialog.setMinimumDuration(0)
        
        if download_and_apply_update(download_url, progress_dialog):
            QMessageBox.information(self, "업데이트 완료", "업데이트가 성공적으로 완료되었습니다. 프로그램을 재시작합니다.")
            self.close()
            QApplication.quit()
        else:
            QMessageBox.warning(self, "업데이트 실패", "업데이트 적용에 실패했습니다. 수동으로 최신 버전을 다운로드해 주세요.")

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