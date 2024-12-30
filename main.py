import sys
import os
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QScreen

if getattr(sys, 'frozen', False):
    # PyInstaller로 패키징된 경우
    application_path = sys._MEIPASS
else:
    # 일반적인 Python 실행의 경우
    application_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

sys.path.append(application_path)

from app.config.system.log_config import setup_logging
from app.ui.main_window import DellIDRACMonitor

logger = setup_logging()

def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    window = DellIDRACMonitor()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()