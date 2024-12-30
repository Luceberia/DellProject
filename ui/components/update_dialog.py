from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton
from PyQt6.QtCore import Qt

class UpdateDialog(QDialog):
    def __init__(self, parent=None, version_info=None, is_update=True):
        super().__init__(parent)
        self.setWindowTitle("업데이트 확인")
        
        layout = QVBoxLayout()
        
        if is_update:
            message = (f"새로운 버전이 있습니다!\n\n"
                      f"현재 버전: {version_info['current']}\n"
                      f"최신 버전: {version_info['latest']}\n\n"
                      "업데이트를 진행하시겠습니까?")
            
            buttons = QHBoxLayout()
            yes_btn = QPushButton("예")
            no_btn = QPushButton("아니오")
            yes_btn.clicked.connect(self.accept)
            no_btn.clicked.connect(self.reject)
            buttons.addWidget(yes_btn)
            buttons.addWidget(no_btn)
        else:
            message = (f"현재 최신 버전을 사용 중입니다.\n\n"
                      f"현재 버전: {version_info['current']}")
            
            buttons = QHBoxLayout()
            ok_btn = QPushButton("확인")
            ok_btn.clicked.connect(self.accept)
            buttons.addWidget(ok_btn)
            
        label = QLabel(message)
        layout.addWidget(label)
        layout.addLayout(buttons)
        self.setLayout(layout)