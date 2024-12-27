from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QTabWidget, 
                           QWidget, QTextEdit, QPushButton, QHBoxLayout)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

class HelpDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Dell Server Management Help")
        self.setMinimumSize(600, 400)
        
        # 메인 레이아웃
        layout = QVBoxLayout()
        
        # 탭 위젯 생성
        tab_widget = QTabWidget()
        
        # 기본 사용법 탭
        basic_tab = QWidget()
        basic_layout = QVBoxLayout()
        basic_text = QTextEdit()
        basic_text.setReadOnly(True)
        basic_text.setHtml(self._get_basic_usage_text())
        basic_layout.addWidget(basic_text)
        basic_tab.setLayout(basic_layout)
        
        # 상세 기능 탭
        features_tab = QWidget()
        features_layout = QVBoxLayout()
        features_text = QTextEdit()
        features_text.setReadOnly(True)
        features_text.setHtml(self._get_features_text())
        features_layout.addWidget(features_text)
        features_tab.setLayout(features_layout)
        
        # 문제 해결 탭
        troubleshoot_tab = QWidget()
        troubleshoot_layout = QVBoxLayout()
        troubleshoot_text = QTextEdit()
        troubleshoot_text.setReadOnly(True)
        troubleshoot_text.setHtml(self._get_troubleshooting_text())
        troubleshoot_layout.addWidget(troubleshoot_text)
        troubleshoot_tab.setLayout(troubleshoot_layout)
        
        # 탭 추가
        tab_widget.addTab(basic_tab, "기본 사용법")
        tab_widget.addTab(features_tab, "상세 기능")
        tab_widget.addTab(troubleshoot_tab, "문제 해결")
        
        # 닫기 버튼
        button_layout = QHBoxLayout()
        close_button = QPushButton("닫기")
        close_button.clicked.connect(self.accept)
        button_layout.addStretch()
        button_layout.addWidget(close_button)
        
        # 레이아웃에 위젯 추가
        layout.addWidget(tab_widget)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)

    def _get_basic_usage_text(self):
        return """
        <h2>Dell Server Management 기본 사용법</h2>
        <p><b>1. 서버 연결</b></p>
        <ul>
            <li>설정 버튼을 클릭하여 서버 정보를 입력합니다.</li>
            <li>서버 IP, 사용자 이름, 비밀번호를 입력합니다.</li>
            <li>연결 버튼을 클릭하여 서버에 연결합니다.</li>
            <li>연결 서버를 유지하려면 서버 저장을 클릭하여 설정 파일에 저장합니다.</li>
        </ul>
        
        <p><b>2. 기본 기능</b></p>
        <ul>
            <li>서버 상태 모니터링</li>
            <li>하드웨어 정보 확인</li>
            <li>시스템 이벤트 로그 확인</li>
            <li>LifeCycle 로그 확인</li>
        </ul>
        """

    def _get_features_text(self):
        return """
        <h2>상세 기능 설명</h2>
        <p><b>하드웨어 모니터링</b></p>
        <ul>
            <li>CPU 상태 및 사용률 모니터링</li>
            <li>메모리 상태 확인</li>
            <li>스토리지 디바이스 정보</li>
            <li>네트워크 인터페이스 상태</li>
            <li>iDRAC MAC 주소 정보</li>
            <li>각 장치별 펌웨어 정보</li>
        </ul>
        
        <p><b>시스템 관리</b></p>
        <ul>
            <li>전원 관리 (켜기/끄기/재시작)</li>
            <li>시스템 이벤트 로그 관리</li>
            <li>하드웨어 인벤토리 관리</li>
        </ul>
        
        """

    def _get_troubleshooting_text(self):
        return """
        <h2>문제 해결 가이드</h2>
        <p><b>연결 문제</b></p>
        <ul>
            <li>서버 IP 주소가 올바른지 확인</li>
            <li>사용자 이름과 비밀번호가 정확한지 확인</li>
            <li>네트워크 연결 상태 확인</li>
            <li>방화벽 설정 확인</li>
        </ul>
        
        <p><b>일반적인 문제</b></p>
        <ul>
            <li>데이터 업데이트가 되지 않을 경우 새로고침 버튼 클릭</li>
            <li>응답이 없을 경우 서버 연결 상태 확인</li>
            <li>오류 메시지 발생 시 로그 확인</li>
        </ul>
        """