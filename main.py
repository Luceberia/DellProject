import os
import sys

# 프로젝트 루트 디렉토리를 Python 경로에 추가
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

import time
from PyQt6.QtWidgets import QApplication, QProgressDialog, QMessageBox
from PyQt6.QtCore import Qt

from config.system.app_config import ResourceManager
from config.system.log_config import setup_logging
from ui.main_window import DellIDRACMonitor

def main():
    # PyQt 애플리케이션 초기화
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    # 리소스 디렉토리 초기화
    ResourceManager.setup_directories()
    
    # 로깅 설정
    logger = setup_logging()
    
    progress = QProgressDialog()
    progress.setWindowTitle("DellIDRACMonitor")
    progress.setLabelText("데이터베이스 연결 중...")
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
