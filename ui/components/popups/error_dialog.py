from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QTextEdit
from PyQt6.QtCore import Qt

class ErrorDialog(QDialog):
    def __init__(self, title: str, message: str, details: str = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(450)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # 에러 메시지
        message_label = QLabel(message)
        message_label.setWordWrap(True)
        layout.addWidget(message_label)
        
        # 상세 정보가 있는 경우
        if details:
            details_edit = QTextEdit()
            details_edit.setPlainText(details)
            details_edit.setReadOnly(True)
            details_edit.setMaximumHeight(100)
            layout.addWidget(details_edit)
        
        # 확인 버튼
        ok_button = QPushButton("확인")
        ok_button.setFixedSize(100, 32)
        ok_button.clicked.connect(self.accept)
        layout.addWidget(ok_button, alignment=Qt.AlignmentFlag.AlignRight)
        
        self.setLayout(layout)
