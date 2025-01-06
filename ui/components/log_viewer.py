import os
import sys
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QTextEdit, QHBoxLayout, 
                             QPushButton, QFileDialog, QLabel, QComboBox, QLineEdit)
from PyQt6.QtGui import QTextCursor, QFont
from PyQt6.QtCore import Qt

from config.system.app_config import ResourceManager
from config.system.log_config import setup_logging
from utils.system_utils import get_system_monospace_font

logger = setup_logging()

class LogViewerDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("로그 뷰어")
        self.setMinimumSize(800, 600)
        
        # 메인 레이아웃
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)
        
        # 로그 파일 선택 레이아웃
        file_layout = QHBoxLayout()
        main_layout.addLayout(file_layout)
        
        # 로그 파일 선택 라벨
        file_label = QLabel("로그 파일:")
        file_layout.addWidget(file_label)
        
        # 로그 파일 선택 콤보박스
        self.log_file_combo = QComboBox()
        file_layout.addWidget(self.log_file_combo)
        
        # 로그 파일 찾기 버튼
        find_log_btn = QPushButton("파일 찾기")
        find_log_btn.clicked.connect(self.open_log_file)
        file_layout.addWidget(find_log_btn)
        
        # 검색 레이아웃
        search_layout = QHBoxLayout()
        main_layout.addLayout(search_layout)
        
        # 검색 라벨
        search_label = QLabel("검색:")
        search_layout.addWidget(search_label)
        
        # 검색 입력 필드
        self.search_input = QLineEdit()
        self.search_input.textChanged.connect(self.search_logs)
        search_layout.addWidget(self.search_input)
        
        # 이전/다음 검색 버튼
        prev_btn = QPushButton("이전")
        next_btn = QPushButton("다음")
        prev_btn.clicked.connect(self.search_previous)
        next_btn.clicked.connect(self.search_next)
        search_layout.addWidget(prev_btn)
        search_layout.addWidget(next_btn)
        
        # 시스템에 맞는 등폭 폰트 사용
        system_font = get_system_monospace_font()
        
        # 텍스트 에디터
        self.text_edit = QTextEdit()
        self.text_edit.setReadOnly(True)
        self.text_edit.setFont(system_font)
        main_layout.addWidget(self.text_edit)
        
        # 하단 버튼 레이아웃
        button_layout = QHBoxLayout()
        main_layout.addLayout(button_layout)
        
        # 맨 아래로 스크롤 버튼
        scroll_bottom_btn = QPushButton("맨 아래로")
        scroll_bottom_btn.clicked.connect(self.scroll_to_bottom)
        button_layout.addWidget(scroll_bottom_btn)
        
        # 닫기 버튼
        close_btn = QPushButton("닫기")
        close_btn.clicked.connect(self.close)
        button_layout.addWidget(close_btn)
        
        # 검색 관련 변수
        self.search_matches = []
        self.current_match_index = -1
        
        # 로그 파일 목록 초기화
        self.init_log_files()
        
        # 초기 로그 파일 로드
        if self.log_file_combo.count() > 0:
            self.load_log_file(self.log_file_combo.currentText())
        
        # 로그 파일 선택 이벤트 연결
        self.log_file_combo.currentTextChanged.connect(self.load_log_file)
    
    def init_log_files(self):
        """로그 파일 목록 초기화"""
        try:
            log_dir = ResourceManager.get_log_dir()
            log_files = [f for f in os.listdir(log_dir) if f.endswith('.log')]
            
            self.log_file_combo.clear()
            self.log_file_combo.addItems(log_files)
        except Exception as e:
            logger.error(f"로그 파일 목록 초기화 중 오류: {e}")
    
    def open_log_file(self):
        """외부 로그 파일 열기"""
        try:
            file_path, _ = QFileDialog.getOpenFileName(
                self, 
                "로그 파일 선택", 
                "", 
                "로그 파일 (*.log);;모든 파일 (*)"
            )
            
            if file_path:
                # 파일 이름만 추출
                file_name = os.path.basename(file_path)
                
                # 콤보박스에 파일 추가 (중복 방지)
                if self.log_file_combo.findText(file_name) == -1:
                    self.log_file_combo.addItem(file_name)
                
                # 추가된 파일 선택
                self.log_file_combo.setCurrentText(file_name)
                
                # 로그 파일 로드
                self.load_log_file(file_name, file_path)
        except Exception as e:
            logger.error(f"로그 파일 열기 중 오류: {e}")
    
    def load_log_file(self, file_name, custom_path=None):
        """로그 파일 로드"""
        try:
            if custom_path:
                file_path = custom_path
            else:
                log_dir = ResourceManager.get_log_dir()
                file_path = os.path.join(log_dir, file_name)
            
            with open(file_path, 'r', encoding='utf-8') as f:
                log_content = f.read()
            
            # 텍스트 에디터에 로그 내용 표시
            self.text_edit.setPlainText(log_content)
            
            # 맨 아래로 스크롤
            self.scroll_to_bottom()
        except Exception as e:
            logger.error(f"로그 파일 로드 중 오류: {e}")
            self.text_edit.setPlainText(f"로그 파일을 읽을 수 없습니다: {e}")
    
    def scroll_to_bottom(self):
        """텍스트 에디터 맨 아래로 스크롤"""
        cursor = self.text_edit.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.text_edit.setTextCursor(cursor)
        self.text_edit.ensureCursorVisible()
    
    def search_logs(self):
        """로그 검색"""
        search_text = self.search_input.text()
        if not search_text:
            self.search_matches = []
            self.current_match_index = -1
            return
        
        log_content = self.text_edit.toPlainText()
        self.search_matches = [i for i in range(len(log_content)) if log_content.startswith(search_text, i)]
        self.current_match_index = -1
    
    def search_previous(self):
        """이전 검색 결과로 이동"""
        if not self.search_matches:
            return
        
        if self.current_match_index == -1:
            self.current_match_index = len(self.search_matches) - 1
        else:
            self.current_match_index = (self.current_match_index - 1) % len(self.search_matches)
        
        self.highlight_match()
    
    def search_next(self):
        """다음 검색 결과로 이동"""
        if not self.search_matches:
            return
        
        if self.current_match_index == -1:
            self.current_match_index = 0
        else:
            self.current_match_index = (self.current_match_index + 1) % len(self.search_matches)
        
        self.highlight_match()
    
    def highlight_match(self):
        """검색 결과 강조"""
        if self.current_match_index == -1:
            return
        
        log_content = self.text_edit.toPlainText()
        match_index = self.search_matches[self.current_match_index]
        match_text = log_content[match_index:match_index + len(self.search_input.text())]
        
        cursor = self.text_edit.textCursor()
        cursor.setPosition(match_index)
        cursor.setPosition(match_index + len(match_text), QTextCursor.MoveMode.KeepAnchor)
        self.text_edit.setTextCursor(cursor)
        self.text_edit.ensureCursorVisible()
