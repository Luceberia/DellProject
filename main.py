import os
import sys
import time
from typing import Optional

# 프로젝트 루트 디렉토리를 Python 경로에 추가
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from PyQt6.QtWidgets import QApplication, QProgressDialog, QMessageBox
from PyQt6.QtCore import Qt, QTimer
from config.system.log_config import setup_logging
from ui.main_window import DellIDRACMonitor
from utils.network_utils import check_internet_connection
from updater import check_for_updates
from version import __version__
from config.system.app_config import ResourceManager

class ApplicationInitializer:
    def __init__(self, app: QApplication):
        self.app = app
        self.logger = setup_logging()
        self.progress_dialog: Optional[QProgressDialog] = None
        self.initialization_steps = [
            ("시스템 리소스 초기화", self.initialize_resources),
            ("로깅 시스템 설정", self.setup_logging),
            ("네트워크 연결 확인", self.check_network),
            ("UI 구성 요소 준비", self.prepare_ui_components)
        ]

    def create_progress_dialog(self) -> QProgressDialog:
        """진행 상태 다이얼로그 생성"""
        progress = QProgressDialog()
        progress.setWindowTitle("DellIDRACMonitor")
        progress.setWindowModality(Qt.WindowModality.ApplicationModal)
        progress.setWindowFlags(
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.CustomizeWindowHint
        )
        progress.setCancelButton(None)
        progress.setMinimumDuration(0)
        progress.setMinimumWidth(300)
        progress.setMinimumHeight(100)
        progress.setStyleSheet("""
            QProgressDialog {
                background-color: #2b2b2b;
                border: none;
                border-radius: 12px;
            }
            QLabel {
                color: #ffffff;
                font-size: 14px;
                font-weight: 500;
                padding: 20px;
                qproperty-alignment: AlignCenter;
            }
            QProgressBar {
                height: 0px;
                max-height: 0px;
                border: none;
            }
        """)

        # 화면 중앙에 배치
        screen = self.app.primaryScreen().geometry()
        x = (screen.width() - progress.width()) // 2
        y = (screen.height() - progress.height()) // 2
        progress.move(x, y)

        return progress

    def update_progress(self, progress: QProgressDialog, current_step: int, total_steps: int):
        """진행 상태 업데이트"""
        try:
            step_name, _ = self.initialization_steps[current_step]
            progress.setLabelText(f"{step_name} 중...")
            progress.setValue(int((current_step + 1) / total_steps * 100))
            self.app.processEvents()
        except Exception as e:
            self.logger.error(f"진행 상태 업데이트 중 오류: {e}")

    def initialize_resources(self):
        """리소스 및 디렉토리 초기화"""
        try:
            from utils.ssh_utils import setup_ssh_config
            
            # SSH 설정 초기화
            setup_ssh_config()
            
            # 리소스 디렉토리 초기화
            result = ResourceManager.setup_directories()
            if not result:
                raise Exception("리소스 디렉토리 초기화 실패")
        except Exception as e:
            self.logger.error(f"리소스 초기화 실패: {e}")
            raise

    def setup_logging(self):
        """로깅 시스템 설정"""
        try:
            # 로깅 설정은 이미 main.py에서 setup_logging()으로 처리됨
            self.logger.info("로깅 시스템 초기화 완료")
        except Exception as e:
            self.logger.error(f"로깅 시스템 설정 실패: {e}")
            raise

    def check_network(self):
        """네트워크 연결 상태를 확인합니다."""
        is_connected, message = check_internet_connection()
        self.logger.info(message)
        
        if not is_connected:
            QMessageBox.warning(
                None,
                "네트워크 알림",
                "인터넷 연결이 감지되지 않았습니다.\n버전 업데이트를 하려면 인터넷을 연결 해 주세요.\n또는 현재 버전을 클릭하면 조회가 가능합니다.",
                QMessageBox.StandardButton.Ok
            )
        else:
            # 인터넷이 연결되어 있으면 버전 업데이트 확인
            check_for_updates(__version__)

    def prepare_ui_components(self):
        """UI 구성 요소 준비"""
        try:
            # 필요한 UI 구성 요소 사전 로드 또는 초기화 작업
            # 예: 아이콘, 테마, 폰트 등
            pass
        except Exception as e:
            self.logger.error(f"UI 구성 요소 준비 실패: {e}")
            raise

    def run(self):
        """애플리케이션 초기화 및 실행"""
        try:
            # 진행 상태 다이얼로그 생성
            self.progress_dialog = self.create_progress_dialog()
            self.progress_dialog.show()

            # 초기화 단계 순차 실행
            total_steps = len(self.initialization_steps)
            for step_index, (_, step_func) in enumerate(self.initialization_steps):
                self.update_progress(self.progress_dialog, step_index, total_steps)
                step_func()

            # 진행 상태 다이얼로그 닫기
            self.progress_dialog.close()

            # 메인 윈도우 생성 및 표시
            window = DellIDRACMonitor()
            window.show()

            # 애플리케이션 실행
            return self.app.exec()

        except Exception as e:
            # 오류 로깅 및 사용자에게 알림
            error_message = f"애플리케이션 초기화 중 오류가 발생했습니다: {str(e)}"
            self.logger.error(error_message)
            
            if self.progress_dialog:
                self.progress_dialog.close()
            
            QMessageBox.critical(None, "오류", error_message)
            return -1

def main():
    # PyQt 애플리케이션 초기화
    app = QApplication(sys.argv)
    
    # macOS 네이티브 스타일 유지
    app.setStyle('macos')  # 'macintosh' 대신 'macos' 사용
    
    # 고해상도 지원 설정 (PyQt6용)
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    
    # 애플리케이션 초기화 및 실행
    initializer = ApplicationInitializer(app)
    
    # 애플리케이션 종료 핸들러 설정
    def on_last_window_closed():
        initializer.logger.info("마지막 윈도우 닫힘. 애플리케이션 종료 준비")
        app.quit()
    
    app.lastWindowClosed.connect(on_last_window_closed)
    
    # 메인 이벤트 루프 실행
    result = initializer.run()
    sys.exit(result)

if __name__ == "__main__":
    main()
