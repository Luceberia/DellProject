from config.system.log_config import setup_logging
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QTableWidget, QTableWidgetItem, QHeaderView, QPushButton, QHBoxLayout, QLabel
from PyQt6.QtGui import QColor
from PyQt6.QtCore import Qt

logger = setup_logging()

class SystemEventPopup(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("시스템 이벤트 로그")
        self.setMinimumSize(800, 600)
        self.total_events = []  # 전체 이벤트 저장
        self.page_size = 50  # 페이지당 표시할 항목 수
        self.current_page = 0  # 현재 페이지
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # 테이블 위젯 설정
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels([
            "발생 시간", "심각도", "구성요소", "메시지"
        ])

        # 헤더 설정 (타입 체크 추가)
        header = self.table.horizontalHeader()
        if header is not None:  # None 체크 추가
            # 발생 시간 - 내용에 맞게 자동 조정
            header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
            # 심각도 - 고정 크기
            header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
            header.resizeSection(1, 80)  # 80픽셀로 고정
            # 구성요소 - 내용에 맞게 자동 조정
            header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
            # 메시지 - 남은 공간 채우기
            header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        
        # 페이지네이션 컨트롤
        pagination_layout = QHBoxLayout()
        
        self.prev_button = QPushButton("이전")
        self.prev_button.clicked.connect(self.prev_page)
        
        self.page_label = QLabel()
        
        self.next_button = QPushButton("다음")
        self.next_button.clicked.connect(self.next_page)
        
        pagination_layout.addStretch()
        pagination_layout.addWidget(self.prev_button)
        pagination_layout.addWidget(self.page_label)
        pagination_layout.addWidget(self.next_button)
        pagination_layout.addStretch()
        
        layout.addWidget(self.table)
        layout.addLayout(pagination_layout)
    
    def update_events(self, events):
        try:
            if isinstance(events, dict):
                self.total_events = events.get('Members', [])
            elif isinstance(events, list):
                self.total_events = events
            else:
                raise ValueError(f"지원하지 않는 이벤트 데이터 형식: {type(events)}")
            
            self.current_page = 0
            logger.debug(f"전체 이벤트 업데이트: {len(self.total_events)}개")
            
            # 데이터 정렬 (최신 순)
            self.total_events.sort(key=lambda x: x.get('Created', ''), reverse=True)
            
            self.update_page()
        except Exception as e:
            logger.error(f"이벤트 데이터 업데이트 실패: {str(e)}")
            logger.exception(e)
    
    def update_page(self):
        try:
            # 현재 페이지 데이터 계산
            start_idx = self.current_page * self.page_size
            end_idx = min(start_idx + self.page_size, len(self.total_events))
            current_data = self.total_events[start_idx:end_idx]
            
            logger.debug(f"페이지 업데이트 - 시작: {start_idx}, 끝: {end_idx}, 전체: {len(self.total_events)}")
            
            # 테이블 초기화
            self.table.clearContents()
            self.table.setRowCount(len(current_data))
            
            # 데이터 채우기
            for row, event in enumerate(current_data):
                for col, value in enumerate([
                    event.get('Created', ''),
                    event.get('Severity', ''),
                    event.get('Oem', {}).get('Dell', {}).get('Category', ''),
                    event.get('Message', '')
                ]):
                    item = QTableWidgetItem(str(value))
                    self.table.setItem(row, col, item)
            
            # 페이지 버튼 상태 업데이트
            total_pages = (len(self.total_events) - 1) // self.page_size + 1
            self.prev_button.setEnabled(self.current_page > 0)
            self.next_button.setEnabled(self.current_page < total_pages - 1)
            self.page_label.setText(f"{self.current_page + 1} / {total_pages}")
            
        except Exception as e:
            logger.error(f"페이지 업데이트 실패: {str(e)}")
            logger.exception(e)


    def prev_page(self):
        """이전 페이지로 이동"""
        if self.current_page > 0:
            self.current_page -= 1
            self.update_page()
    
    def next_page(self):
        """다음 페이지로 이동"""
        total_pages = (len(self.total_events) - 1) // self.page_size + 1
        if self.current_page < total_pages - 1:
            self.current_page += 1
            self.update_page()