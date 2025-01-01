import sys
import os
import time
from PyQt6.QtWidgets import QApplication, QProgressDialog, QMessageBox
from PyQt6.QtCore import Qt

from config.system.app_config import ResourceManager
from config.system.log_config import setup_logging
from ui.main_window import DellIDRACMonitor

def main():
    # 리소스 디렉토리 초기화
    ResourceManager.setup_directories()
    
    # 로깅 설정
    logger = setup_logging()
    
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    progress = QProgressDialog()
    progress.setWindowTitle("DellIDRACMonitor")
    progress.setLabelText("애플리케이션 초기화 중...")
    progress.setWindowModality(Qt.WindowModality.ApplicationModal)
    progress.setWindowFlags(
        Qt.WindowType.WindowStaysOnTopHint |
        Qt.WindowType.FramelessWindowHint |
        Qt.WindowType.CustomizeWindowHint
    )
    progress.setCancelButton(None)
    progress.setMinimumDuration(0)
    progress.setMinimumWidth(400)
    progress.setStyleSheet("""
        QProgressDialog {
            background-color: transparent;
            border: none;
        }
        QLabel {
            color: #000000;
            font-size: 13px;
        }
        QProgressBar {
            border: none;
            background-color: #f0f0f0;
            height: 6px;
        }
        QProgressBar::chunk {
            background-color: #0064FF;
        }
    """)

    screen = QApplication.primaryScreen().geometry()
    x = (screen.width() - progress.width()) // 2
    y = (screen.height() - progress.height()) // 2
    progress.move(x, y)
    progress.show()
    app.processEvents()

    try:
        for i in range(101):
            if i < 30:
                progress.setLabelText("시스템 리소스 초기화 중...")
            elif i < 60:
                progress.setLabelText("데이터베이스 연결 중...")
            elif i < 90:
                progress.setLabelText("UI 구성 요소 로딩 중...")
            else:
                progress.setLabelText("초기화 완료 중...")
            progress.setValue(i)
            app.processEvents()
            time.sleep(0.02)

        window = DellIDRACMonitor()
        window.show()
        progress.close()
    except Exception as e:
        progress.close()
        logger.error(f"초기화 중 오류 발생: {str(e)}")
        QMessageBox.critical(None, "오류", f"애플리케이션 초기화 중 오류가 발생했습니다: {str(e)}")
        return

    sys.exit(app.exec())

if __name__ == "__main__":
    main()
