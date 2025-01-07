import os
from datetime import datetime
from collections import Counter

import openpyxl
from openpyxl.styles import Font, Alignment, Border, Side

import matplotlib
matplotlib.use('qtagg')

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTextEdit, 
                             QPushButton, QFileDialog, QLabel, QComboBox, 
                             QLineEdit, QCheckBox, QTabWidget, QWidget, 
                             QApplication, QScrollArea)
from PyQt6.QtGui import QTextCursor
from PyQt6.QtCore import Qt, QTimer

from config.system.app_config import ResourceManager
from config.system.log_config import setup_logging
from utils.system_utils import get_system_monospace_font, get_system_matplotlib_font
from ui.components.popups.error_dialog import ErrorDialog
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas

logger = setup_logging()

class LogViewerDialog(QDialog):
    def __init__(self, parent=None):
        # 모덜리스 다이얼로그로 설정
        super().__init__(parent, Qt.WindowType.Window)
        self.setWindowTitle("로그 뷰어")
        self.setMinimumSize(1000, 700)
        
        # 모덜리스 다이얼로그 설정
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)  # 창 닫을 때 메모리에서 제거
        
        # 메인 레이아웃
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)
        
        # 탭 위젯 생성
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)
        
        # 로그 뷰어 탭
        log_viewer_tab = QWidget()
        log_viewer_layout = QVBoxLayout(log_viewer_tab)
        
        # 필터링 및 검색 레이아웃
        filter_layout = QHBoxLayout()
        log_viewer_layout.addLayout(filter_layout)
        
        # 로그 레벨 필터
        self.log_level_combo = QComboBox()
        self.log_level_combo.addItems(["모든 로그", "INFO", "WARNING", "ERROR", "DEBUG"])
        self.log_level_combo.currentTextChanged.connect(self.filter_logs)
        filter_layout.addWidget(QLabel("로그 레벨:"))
        filter_layout.addWidget(self.log_level_combo)
        
        # 검색 입력 필드
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("로그 검색...")
        self.search_input.textChanged.connect(self.filter_logs)
        filter_layout.addWidget(QLabel("검색:"))
        filter_layout.addWidget(self.search_input)
        
        # 실시간 업데이트 체크박스
        self.auto_update_check = QCheckBox("실시간 업데이트")
        filter_layout.addWidget(self.auto_update_check)

        # 로그 텍스트 에디터
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(get_system_monospace_font())
        log_viewer_layout.addWidget(self.log_text)

        # 로그 파일 선택 레이아웃
        log_file_layout = QHBoxLayout()
        log_viewer_layout.addLayout(log_file_layout)
        
        # 로그 파일 선택 라벨
        file_label = QLabel("로그 파일:")
        log_file_layout.addWidget(file_label)
        
        # 로그 파일 선택 콤보박스
        self.log_file_combo = QComboBox()
        self.log_file_combo.currentTextChanged.connect(self.load_log_file)
        log_file_layout.addWidget(self.log_file_combo)
        log_file_layout.addStretch()

        # 로그 컨트롤 버튼
        button_layout = QHBoxLayout()
        log_viewer_layout.addLayout(button_layout)

        # 파일 찾기 버튼
        find_log_btn = QPushButton("파일 찾기")
        find_log_btn.clicked.connect(self.open_log_file)
        button_layout.addWidget(find_log_btn)

        # 클립보드 복사 버튼
        copy_btn = QPushButton("로그 복사")
        copy_btn.clicked.connect(self.copy_logs_to_clipboard)
        button_layout.addWidget(copy_btn)
        
        # Excel 내보내기 버튼
        export_xlsx_btn = QPushButton("Excel 내보내기")
        export_xlsx_btn.clicked.connect(self.export_logs_to_xlsx)
        button_layout.addWidget(export_xlsx_btn)
        
        # 빈 공간 추가
        button_layout.addStretch()
        
        # 로그 분석 탭
        self.log_analysis_tab = QWidget()
        self.setup_log_analysis_tab()
        
        # 탭에 추가
        self.tab_widget.addTab(log_viewer_tab, "로그 뷰어")
        self.tab_widget.addTab(self.log_analysis_tab, "로그 분석")
        
        # 실시간 업데이트 타이머
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.periodic_log_update)
        
        # 초기화
        self.current_log_file = None
        self.all_log_entries = []
        self.populate_log_files()
        
        # 실시간 업데이트 체크박스 연결
        self.auto_update_check.stateChanged.connect(self.toggle_auto_update)
        
        # 창 닫기 버튼 활성화
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowCloseButtonHint)

    def setup_log_analysis_tab(self):
        """로그 분석 탭 UI 설정"""
        # matplotlib 한글 폰트 설정
        get_system_matplotlib_font()
        
        # 메인 레이아웃
        analysis_layout = QVBoxLayout()
        
        # 로그 레벨 통계 섹션
        log_level_stats_label = QLabel("로그 레벨 통계")
        log_level_stats_label.setStyleSheet("font-weight: bold; font-size: 16px;")
        analysis_layout.addWidget(log_level_stats_label)
        
        # 로그 레벨 차트를 위한 스크롤 영역
        log_level_scroll_area = QScrollArea()
        log_level_scroll_area.setWidgetResizable(True)
        self.log_level_chart = QWidget()
        self.log_level_chart_layout = QVBoxLayout(self.log_level_chart)
        log_level_scroll_area.setWidget(self.log_level_chart)
        analysis_layout.addWidget(log_level_scroll_area)
        
        # 타임라인 통계 섹션
        timeline_stats_label = QLabel("시간대별 로그 통계")
        timeline_stats_label.setStyleSheet("font-weight: bold; font-size: 16px;")
        analysis_layout.addWidget(timeline_stats_label)
        
        # 타임라인 차트를 위한 스크롤 영역
        timeline_scroll_area = QScrollArea()
        timeline_scroll_area.setWidgetResizable(True)
        self.timeline_chart = QWidget()
        self.timeline_chart_layout = QVBoxLayout(self.timeline_chart)
        timeline_scroll_area.setWidget(self.timeline_chart)
        analysis_layout.addWidget(timeline_scroll_area)
        
        # 로그 파일 경로 라벨
        self.log_file_path_label = QLabel("현재 로그 파일: 없음")
        self.log_file_path_label.setStyleSheet("font-style: italic; color: gray;")
        analysis_layout.addWidget(self.log_file_path_label)

        # 분석 탭에 레이아웃 설정
        self.log_analysis_tab.setLayout(analysis_layout)

    def populate_log_files(self):
        """로그 파일 목록 채우기"""
        log_dir = str(ResourceManager.get_log_dir())
        log_files = [f for f in os.listdir(log_dir) if f.endswith('.log')]
        self.log_file_combo.clear()
        self.log_file_combo.addItems(log_files)
        
        # 가장 최근 로그 파일 선택
        if log_files:
            latest_log = max(log_files, key=lambda f: os.path.getctime(os.path.join(log_dir, f)))
            self.log_file_combo.setCurrentText(latest_log)

    def open_log_file(self):
        """로그 파일 찾기"""
        log_dir = str(ResourceManager.get_log_dir())
        file_path, _ = QFileDialog.getOpenFileName(
            self, 
            "로그 파일 선택", 
            log_dir, 
            "로그 파일 (*.log)"
        )
        
        if file_path:
            # 콤보박스에 추가하고 선택
            log_filename = os.path.basename(file_path)
            if log_filename not in [self.log_file_combo.itemText(i) for i in range(self.log_file_combo.count())]:
                self.log_file_combo.addItem(log_filename)
            self.log_file_combo.setCurrentText(log_filename)

    def load_log_file(self, file_name=None):
        """로그 파일 로드"""
        try:
            # 파일명이 주어지지 않았다면 콤보박스에서 선택된 파일 사용
            if file_name is None:
                file_name = self.log_file_combo.currentText()
            
            # 로그 디렉토리 경로
            log_dir = str(ResourceManager.get_log_dir())
            full_path = os.path.join(log_dir, file_name)
            
            # 로그 파일 경로 라벨 업데이트
            self.log_file_path_label.setText(f"현재 로그 파일: {full_path}")
            
            # 로그 파일 읽기
            with open(full_path, 'r', encoding='utf-8') as f:
                self.all_log_entries = f.readlines()
            
            # 로그 텍스트 업데이트
            self.log_text.clear()
            self.log_text.setPlainText(''.join(self.all_log_entries))
            self.log_text.moveCursor(QTextCursor.MoveOperation.End)
            
            # 현재 로그 파일 설정
            self.current_log_file = full_path
            
            # 로그 통계 업데이트
            self.update_log_stats()
            
            # 실시간 업데이트 타이머 설정
            if self.auto_update_check.isChecked():
                self.update_timer.start(1000)
        
        except Exception as e:
            logger.error(f"로그 파일 로드 중 오류: {e}")
            error_dialog = ErrorDialog(self, "로그 파일 로드 오류", str(e))
            error_dialog.exec()

    def toggle_auto_update(self, state):
        """실시간 업데이트 토글"""
        # 체크박스의 실제 상태 확인
        is_checked = self.auto_update_check.isChecked()
        
        # Qt.CheckState.Checked는 2입니다
        if is_checked:
            # 즉시 로그 파일 로드
            current_file = self.log_file_combo.currentText()
            if current_file:
                self.load_log_file(current_file)
            # 실시간으로 1초마다 자동 업데이트 활성화
            self.update_timer.start(1000)
        else:
            # 자동 업데이트 비활성화
            self.update_timer.stop()

    def filter_logs(self):
        """로그 필터링"""
        level_filter = self.log_level_combo.currentText()
        search_text = self.search_input.text().lower()
        
        filtered_logs = []
        for log_entry in self.all_log_entries:
            # 로그 레벨 필터링
            if level_filter != "모든 로그" and level_filter not in log_entry:
                continue
            
            # 검색어 필터링
            if search_text and search_text not in log_entry.lower():
                continue
            
            filtered_logs.append(log_entry)
        
        # 로그 텍스트 업데이트
        self.log_text.clear()
        self.log_text.setPlainText(''.join(filtered_logs))
        self.log_text.moveCursor(QTextCursor.MoveOperation.End)

    def copy_logs_to_clipboard(self):
        """로그를 클립보드에 복사"""
        try:
            clipboard = QApplication.clipboard()
            clipboard.setText(self.log_text.toPlainText())
            logger.info("로그가 클립보드에 복사되었습니다.")
            
            # 성공 다이얼로그
            success_dialog = ErrorDialog(
                "클립보드 복사 성공", 
                "로그가 클립보드에 성공적으로 복사되었습니다."
            )
            success_dialog.exec()
        except Exception as e:
            logger.error(f"클립보드 복사 중 오류: {e}")
            error_dialog = ErrorDialog(
                "클립보드 복사 오류", 
                "로그를 클립보드에 복사하는 중 오류가 발생했습니다.", 
                str(e)
            )
            error_dialog.exec()

    def export_logs_to_xlsx(self):
        """로그를 Excel 파일로 내보내기"""
        log_dir = str(ResourceManager.get_log_dir())
        file_path, _ = QFileDialog.getSaveFileName(
            self, 
            "로그 파일 저장", 
            log_dir, 
            "Excel 파일 (*.xlsx)"
        )
        
        if file_path:
            try:
                # 새 워크북 생성
                wb = openpyxl.Workbook()
                ws = wb.active
                ws.title = "로그"
                
                # 헤더 설정
                headers = ["타임스탬프", "로그 레벨", "메시지"]
                ws.append(headers)
                
                # 헤더 스타일
                header_font = Font(bold=True)
                header_border = Border(
                    left=Side(style='thin'), 
                    right=Side(style='thin'), 
                    top=Side(style='thin'), 
                    bottom=Side(style='thin')
                )
                
                for cell in ws[1]:
                    cell.font = header_font
                    cell.border = header_border
                    cell.alignment = Alignment(horizontal='center')
                
                # 로그 데이터 추가
                for log_entry in self.log_text.toPlainText().split('\n'):
                    log_entry = log_entry.strip()
                    if not log_entry:
                        continue
                    
                    # 로그 형식 파싱
                    parts = log_entry.split(' - ', 4)
                    if len(parts) == 5:
                        timestamp, pid, module, level, message = parts
                        ws.append([timestamp, level, message])
                    else:
                        # 형식에 맞지 않는 경우 전체 로그 항목을 메시지로 처리
                        ws.append(["", "", log_entry])
                
                # 열 너비 자동 조정
                for col in ws.columns:
                    max_length = 0
                    column = col[0].column_letter
                    for cell in col:
                        try:
                            if len(str(cell.value)) > max_length:
                                max_length = len(cell.value)
                        except:
                            pass
                    adjusted_width = (max_length + 2)
                    ws.column_dimensions[column].width = adjusted_width
                
                # 파일 저장
                wb.save(file_path)
                
                logger.info(f"로그가 {file_path}에 저장되었습니다.")
                
                # 성공 다이얼로그
                success_dialog = ErrorDialog(
                    "Excel 내보내기 성공", 
                    f"로그가 {file_path}에 성공적으로 저장되었습니다."
                )
                success_dialog.exec()
            except Exception as e:
                logger.error(f"Excel 내보내기 중 오류: {e}")
                error_dialog = ErrorDialog(
                    "Excel 내보내기 오류", 
                    "로그를 Excel 파일로 내보내는 중 오류가 발생했습니다.", 
                    str(e)
                )
                error_dialog.exec()

    def analyze_log_statistics(self, log_entries):
        """로그 통계 분석"""
        # 로그 레벨별 통계
        log_level_counts = Counter(entry['level'] for entry in log_entries if 'level' in entry)
        total_logs = len(log_entries)
        
        # 기존 레이아웃 초기화
        for i in reversed(range(self.log_level_chart_layout.count())): 
            self.log_level_chart_layout.itemAt(i).widget().setParent(None)

        # 새 수평 막대 그래프 생성
        plt.close('all')  # 기존 플롯 닫기
        
        # 데이터 개수에 따라 동적으로 그래프 높이 조정
        graph_height = max(3, min(len(log_level_counts) * 0.5, 6))
        if len(log_level_counts) <= 2:
            graph_height = 2.5  # 로그 개수가 적을 때 더 작은 높이
        
        fig, ax = plt.subplots(figsize=(8, graph_height))
        
        # 데이터 준비
        levels = list(log_level_counts.keys())
        counts = list(log_level_counts.values())
        percentages = [(count / total_logs * 100) for count in counts]
        
        # 색상 매핑
        color_map = {
            'DEBUG': '#36A2EB',     # 밝은 파란색
            'INFO': '#4BC0C0',      # 청록색
            'WARNING': '#FFCE56',   # 노란색
            'ERROR': '#FF6384',     # 밝은 빨간색
            'CRITICAL': '#FF0000'   # 진한 빨간색
        }
        colors = [color_map.get(level, '#000000') for level in levels]
        
        # 수평 막대 그래프 생성
        bars = ax.barh(levels, percentages, color=colors, height=0.5)  # 막대 높이 더 작게
        
        # 각 막대에 로그 개수 표시
        for bar, count in zip(bars, counts):
            width = bar.get_width()
            ax.text(width, bar.get_y() + bar.get_height()/2, 
                    f'{count}', 
                    va='center', fontsize=8)
        
        plt.title('로그 레벨 분포', fontsize=10)
        plt.xlabel('비율 (%)', fontsize=9)
        plt.xticks(fontsize=8)
        plt.yticks(fontsize=8)
        plt.tight_layout()
        
        # Qt 캔버스에 추가
        canvas = FigureCanvas(fig)
        self.log_level_chart_layout.addWidget(canvas)

    def analyze_timeline_statistics(self, log_entries):
        """시간대별 로그 통계 분석"""
        # 기존 레이아웃 초기화
        for i in reversed(range(self.timeline_chart_layout.count())): 
            self.timeline_chart_layout.itemAt(i).widget().setParent(None)

        # 시간대별 통계 계산
        timeline_stats = self.calculate_timeline_stats(log_entries)
        total_entries = len(log_entries)
        
        # 새 막대 그래프 생성
        plt.close('all')  # 기존 플롯 닫기
        
        # 데이터 개수에 따라 동적으로 그래프 높이 조정
        graph_height = max(3, min(len(timeline_stats) * 0.5, 6))
        if len(timeline_stats) <= 2:
            graph_height = 2.5  # 로그 개수가 적을 때 더 작은 높이
        
        fig, ax = plt.subplots(figsize=(8, graph_height))
        
        # 데이터 준비
        time_periods = list(timeline_stats.keys())
        counts = list(timeline_stats.values())
        percentages = [(count / total_entries * 100) for count in counts]
        
        # 막대 그래프 생성
        bars = ax.barh(time_periods, counts, color='#4BC0C0', height=0.5)  # 막대 높이 더 작게
        
        # 각 막대에 로그 개수 표시
        for bar, count in zip(bars, counts):
            width = bar.get_width()
            ax.text(width, bar.get_y() + bar.get_height()/2, 
                    f'{count}', 
                    va='center', fontsize=8)
        
        plt.title('시간대별 로그 분포', fontsize=10)
        plt.xlabel('로그 수', fontsize=9)
        plt.xticks(fontsize=8)
        plt.yticks(fontsize=8)
        
        # 여백 조정으로 모든 정보 표시
        plt.subplots_adjust(left=0.2, bottom=0.15, right=0.95, top=0.9)
        
        # Qt 캔버스에 추가
        canvas = FigureCanvas(fig)
        self.timeline_chart_layout.addWidget(canvas)

    def update_log_stats(self):
        """로그 통계 업데이트"""
        try:
            log_entries = []
            for log_entry in self.all_log_entries:
                try:
                    # 로그 형식: 2025-01-06 13:49:40 - [90528] - dell_idrac_monitor - DEBUG - 메시지
                    parts = log_entry.split(' - ', 4)
                    if len(parts) >= 4:
                        timestamp, pid, module, level, message = parts
                        log_entries.append({
                            'timestamp': timestamp,
                            'level': level.strip(),  # 공백 제거
                            'message': message
                        })
                except Exception:
                    pass
            
            self.analyze_log_statistics(log_entries)
            self.analyze_timeline_statistics(log_entries)
        except Exception as e:
            logger.error(f"로그 통계 업데이트 중 오류: {e}")
            # 오류 발생 시 빈 통계 표시
            self.log_stats_table.setRowCount(0)
            self.timeline_stats_table.setRowCount(0)

    def periodic_log_update(self):
        """주기적인 로그 업데이트"""
        current_file = self.log_file_combo.currentText()
        if current_file:
            self.load_log_file(current_file)

    def calculate_timeline_stats(self, log_entries):
        """로그의 시간대별 통계 계산"""
        # 시간대별 로그 분포 (1시간 단위)
        timeline_counts = {}
        for entry in log_entries:
            try:
                entry_time = datetime.fromisoformat(entry.get('timestamp', '').replace('Z', '+00:00'))
                hour_key = entry_time.strftime("%Y/%m/%d %H시")
                timeline_counts[hour_key] = timeline_counts.get(hour_key, 0) + 1
            except:
                pass
        
        # 시간대 순서대로 정렬
        return dict(sorted(timeline_counts.items(), key=lambda x: x[0]))
