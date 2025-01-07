import os
from datetime import datetime
from collections import Counter
import re
import html

import openpyxl
from openpyxl.styles import Font, Alignment, Border, Side

import matplotlib
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from utils.system_utils import get_system_matplotlib_font

# 시스템 한글 폰트 설정
get_system_matplotlib_font()
plt.rcParams['font.family'] = 'AppleGothic'
plt.rcParams['axes.unicode_minus'] = False

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTextEdit, 
                             QPushButton, QFileDialog, QLabel, QComboBox, 
                             QLineEdit, QCheckBox, QTabWidget, QWidget, 
                             QApplication, QScrollArea, QGroupBox, QGridLayout)
from PyQt6.QtGui import QTextCursor
from PyQt6.QtCore import Qt, QTimer

from config.system.app_config import ResourceManager
from config.system.log_config import setup_logging
from utils.system_utils import get_system_monospace_font, get_system_matplotlib_font
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
        
        # 서버 필터 콤보박스
        self.server_filter_combo = QComboBox()
        self.server_filter_combo.addItem("모든 서버")
        self.server_filter_combo.currentTextChanged.connect(self.filter_logs)
        filter_layout.addWidget(QLabel("서버:"))
        filter_layout.addWidget(self.server_filter_combo)
        
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
        
        # 로그 통계 레이아웃
        log_stats_layout = QHBoxLayout()
        
        # 로그 레벨 차트 레이아웃
        self.log_level_chart_layout = QVBoxLayout()
        log_stats_layout.addLayout(self.log_level_chart_layout)
        
        # 메인 레이아웃에 통계 레이아웃 추가
        log_viewer_layout.addLayout(log_stats_layout)

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
        self.last_log_file_position = 0  # 마지막으로 읽은 로그 파일 위치
        self.populate_log_files()
        
        # 실시간 업데이트 체크박스 연결
        self.auto_update_check.stateChanged.connect(self.toggle_auto_update)
        
        # 창 닫기 버튼 활성화
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowCloseButtonHint)

    def setup_log_analysis_tab(self):
        """로그 분석 탭 설정"""
        log_analysis_layout = QVBoxLayout(self.log_analysis_tab)

        # 로그 파일 경로 라벨
        self.log_file_path_label = QLabel("현재 로그 파일: 없음")
        self.log_file_path_label.setStyleSheet("font-style: italic; color: gray;")
        log_analysis_layout.addWidget(self.log_file_path_label)

        # 서버 및 로그 레벨 필터링 레이아웃
        filter_layout = QHBoxLayout()
        
        # 서버 필터 콤보박스
        server_filter_label = QLabel("서버:")
        self.analysis_server_filter = QComboBox()
        self.analysis_server_filter.addItem("모든 서버")
        self.analysis_server_filter.currentTextChanged.connect(self.update_log_stats)
        
        # 로그 레벨 필터 콤보박스
        level_filter_label = QLabel("로그 레벨:")
        self.analysis_level_filter = QComboBox()
        self.analysis_level_filter.addItems(["모든 로그", "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])
        self.analysis_level_filter.currentTextChanged.connect(self.update_log_stats)
        
        # 필터 레이아웃에 추가
        filter_layout.addWidget(server_filter_label)
        filter_layout.addWidget(self.analysis_server_filter)
        filter_layout.addWidget(level_filter_label)
        filter_layout.addWidget(self.analysis_level_filter)
        filter_layout.addStretch()
        
        # 로그 통계 레이아웃
        log_stats_layout = QHBoxLayout()
        
        # 통계 텍스트 라벨
        self.log_stats_label = QLabel("로그 통계")
        log_stats_layout.addWidget(self.log_stats_label)
        
        # 로그 레벨 차트 레이아웃
        self.log_level_chart_layout = QVBoxLayout()
        log_stats_layout.addLayout(self.log_level_chart_layout)
        
        # 메인 레이아웃에 추가
        log_analysis_layout.addLayout(filter_layout)
        log_analysis_layout.addLayout(log_stats_layout)
        log_analysis_layout.addStretch()

    def populate_log_files(self):
        """로그 파일 목록 채우기"""
        try:
            log_dir = str(ResourceManager.get_log_dir())
            # 모든 로그 파일 패턴 포함 (app.log와 20*-app.log.*)
            log_files = [f for f in os.listdir(log_dir) if f.startswith('app.log') or f.startswith('20')]
            log_files.sort(key=lambda f: os.path.getctime(os.path.join(log_dir, f)), reverse=True)
            
            self.log_file_combo.clear()
            self.log_file_combo.addItems(log_files)
            
            # 가장 최근 로그 파일 선택
            if log_files:
                # 현재 선택된 파일이 없거나 목록에 없는 경우에만 최근 파일 선택
                current_text = self.log_file_combo.currentText()
                if not current_text or current_text not in log_files:
                    self.log_file_combo.setCurrentText(log_files[0])
                    # 자동으로 최근 로그 파일 로드
                    self.load_log_file(log_files[0])
        except Exception as e:
            logger.error(f"로그 파일 목록 로드 중 오류: {e}")
            # 오류 발생 시 빈 목록으로 초기화
            self.log_file_combo.clear()
            self.log_file_combo.addItem("로그 파일 없음")

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
            # 파일명이 지정되지 않은 경우 콤보박스에서 선택
            if file_name is None:
                file_name = self.log_file_combo.currentText()
            
            # 로그 파일 경로 설정 (개발 모드와 배포 모드 모두 고려)
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            possible_log_dirs = [
                os.path.join(base_dir, 'resources', 'logs'),  # 개발 모드
                os.path.join(base_dir, 'logs'),  # 배포 모드
                str(ResourceManager.get_log_dir())  # 기존 리소스 매니저 로직
            ]
            
            # 실제 존재하는 로그 디렉토리 찾기
            log_dir = None
            for dir_path in possible_log_dirs:
                if os.path.exists(dir_path):
                    log_dir = dir_path
                    break
            
            if not log_dir:
                raise FileNotFoundError("로그 디렉토리를 찾을 수 없습니다.")
            
            full_path = os.path.join(log_dir, file_name)
            
            # 로그 파일 읽기
            with open(full_path, 'r', encoding='utf-8') as f:
                self.all_log_entries = f.readlines()
            
            # 서버 필터 콤보박스 초기화
            self.server_filter_combo.clear()
            self.server_filter_combo.addItem("모든 서버")
            
            # 서버 필터 분석 탭 콤보박스 초기화
            if hasattr(self, 'analysis_server_filter'):
                self.analysis_server_filter.clear()
                self.analysis_server_filter.addItem("모든 서버")

            # 서버 목록 추출
            server_list = set()
            for log_entry in self.all_log_entries:
                try:
                    # 서버 이름 추출 (대괄호 안의 서버 이름)
                    server_match = log_entry.split('[서버: ')
                    if len(server_match) > 1:
                        server_name = server_match[1].split(']')[0].strip()
                        server_list.add(server_name)
                except Exception:
                    pass
            
            # 서버 목록 추가
            for server in sorted(server_list):
                self.server_filter_combo.addItem(server)
                
                # 분석 탭 콤보박스에도 추가
                if hasattr(self, 'analysis_server_filter'):
                    self.analysis_server_filter.addItem(server)
            
            # 로그 텍스트 업데이트
            self.populate_log_text(self.all_log_entries)
            
            # 로그 파일 경로 라벨 업데이트
            self.log_file_path_label.setText(f"현재 로그 파일: {full_path}")
            
            # 로그 통계 업데이트
            self.update_log_stats()
        
            # 로그 파일 경로 저장
            self.current_log_file = full_path
            self.last_log_file_position = 0  # 마지막으로 읽은 로그 파일 위치 초기화
        
        except Exception as e:
            # 오류 다이얼로그 대신 로그 파일 경로 라벨에 오류 메시지 표시
            self.log_file_path_label.setText(f"로그 파일 로드 오류: {str(e)}")
            logger.error(f"로그 파일 로드 중 오류: {e}")

    def populate_log_text(self, log_entries):
        """로그 텍스트 채우기"""
        try:
            # 기존 텍스트 지우기
            self.log_text.clear()
            
            # HTML 형식으로 로그 항목 추가 (가독성 개선)
            html_log_entries = []
            for log_entry in log_entries:
                # 로그 레벨에 따른 색상 지정
                if 'ERROR' in log_entry:
                    color = 'red'
                elif 'WARNING' in log_entry:
                    color = 'orange'
                elif 'INFO' in log_entry:
                    color = 'green'
                elif 'DEBUG' in log_entry:
                    color = 'blue'
                else:
                    color = 'black'
                
                # HTML 형식으로 로그 항목 포맷팅
                html_entry = f'<font color="{color}">{html.escape(log_entry)}</font>'
                html_log_entries.append(html_entry)
            
            # HTML 형식으로 전체 로그 텍스트 설정
            full_html_log = '<br>'.join(html_log_entries)
            self.log_text.setHtml(full_html_log)
            
            # 커서를 맨 끝으로 이동
            cursor = self.log_text.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.End)
            self.log_text.setTextCursor(cursor)
            
            # 스크롤을 맨 하단으로 이동
            scrollbar = self.log_text.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())
        except Exception as e:
            logger.error(f"로그 텍스트 채우기 중 오류: {e}")

    def toggle_auto_update(self, state):
        """실시간 업데이트 토글"""
        try:
            # 체크박스의 실제 상태 확인
            is_checked = self.auto_update_check.isChecked()
            
            # Qt.CheckState.Checked는 2입니다
            if is_checked:
                # 현재 선택된 로그 파일 확인
                current_file = self.log_file_combo.currentText()
                if current_file:
                    # 즉시 로그 파일 로드
                    self.load_log_file(current_file)
                    # 현재 필터 상태 유지
                    self.filter_logs()
                    # 실시간으로 1초마다 자동 업데이트 활성화
                    self.update_timer.start(1000)
            else:
                # 자동 업데이트 비활성화
                self.update_timer.stop()
        except Exception as e:
            logger.error(f"실시간 업데이트 토글 중 오류: {e}")
            # 체크박스 상태 초기화
            self.auto_update_check.setChecked(False)
            self.update_timer.stop()

    def filter_logs(self, server_filter=None, level_filter=None):
        """로그 필터링"""
        try:
            # 필터링된 로그 저장할 리스트
            filtered_logs = []
            
            # 필터링 조건에 맞는 로그 선택
            for log_entry in self.all_log_entries:
                # 서버 필터 적용
                if server_filter and server_filter.lower() not in log_entry.lower():
                    continue
                
                # 로그 레벨 필터 적용
                if level_filter and level_filter.lower() not in log_entry.lower():
                    continue
                
                filtered_logs.append(log_entry)
            
            # 필터링된 로그 표시
            self.populate_log_text(filtered_logs)
        
        except Exception as e:
            logger.error(f"로그 필터링 중 오류: {e}")
            # 오류 발생 시 모든 로그 다시 표시
            self.populate_log_text(self.all_log_entries)

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
        # 한글 폰트 설정
        get_system_matplotlib_font()
        
        # 로그 레벨별 통계
        log_level_counts = {}
        total_logs = len(log_entries)
        
        # 로그 레벨 카운트
        for entry in log_entries:
            try:
                # 로그 레벨 추출 (로그 형식: 2025-01-07 23:43:47 - [87281] - dell_idrac_monitor - INFO - [서버: SYSTEM] - 빠른 연결 서버 설정: web1)
                log_level_parts = entry.split(' - ')
                
                if len(log_level_parts) >= 4:
                    log_level = log_level_parts[3].strip()
                    log_level_counts[log_level] = log_level_counts.get(log_level, 0) + 1
            except Exception as e:
                print(f"로그 레벨 추출 중 오류: {e}")
        
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
        
        # 통계 라벨 업데이트
        self.total_logs_label.setText(f"전체 로그: {total_logs}")
        self.info_logs_label.setText(f"INFO 로그: {log_level_counts.get('INFO', 0)}")
        self.warning_logs_label.setText(f"WARNING 로그: {log_level_counts.get('WARNING', 0)}")
        self.error_logs_label.setText(f"ERROR 로그: {log_level_counts.get('ERROR', 0)}")
        self.debug_logs_label.setText(f"DEBUG 로그: {log_level_counts.get('DEBUG', 0)}")

    def analyze_timeline_statistics(self, log_entries):
        """시간대별 로그 통계 분석"""
        try:
            # 한글 폰트 설정
            get_system_matplotlib_font()
            
            # 로그 항목 파싱
            parsed_logs = []
            for log_entry in log_entries:
                try:
                    # 로그 형식: 2025-01-06 13:49:40 - [90528] - dell_idrac_monitor - DEBUG - 메시지
                    parts = log_entry.split(' - ', 4)
                    if len(parts) >= 4:
                        timestamp, pid, module, level, message = parts
                        parsed_logs.append({
                            'timestamp': timestamp,
                            'level': level.strip(),  # 공백 제거
                            'message': message
                        })
                except Exception:
                    pass
            
            # 시간대별 통계 계산
            timeline_stats = self.calculate_timeline_stats(parsed_logs)
            
            # 그래프 그리기 (matplotlib)
            plt.clf()  # 이전 그래프 초기화
            fig, ax = plt.subplots(figsize=(10, 5))
            
            # 시간대별 로그 레벨 분포
            levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR']
            colors = ['blue', 'green', 'orange', 'red']
            
            bottom = [0] * len(timeline_stats)
            for level, color in zip(levels, colors):
                counts = [stats.get(level, 0) for stats in timeline_stats]
                ax.bar(range(len(timeline_stats)), counts, bottom=bottom, label=level, color=color, alpha=0.7)
                bottom = [b + c for b, c in zip(bottom, counts)]
            
            ax.set_title('시간대별 로그 레벨 분포')
            ax.set_xlabel('시간대')
            ax.set_ylabel('로그 수')
            ax.set_xticks(range(len(timeline_stats)))
            ax.set_xticklabels([stat['hour'] for stat in timeline_stats], rotation=45)
            ax.legend()
            
            # 기존 위젯 제거
            for i in reversed(range(self.timeline_chart.layout().count())): 
                self.timeline_chart.layout().itemAt(i).widget().setParent(None)
            
            # 새 캔버스 추가
            canvas = FigureCanvas(fig)
            self.timeline_chart.layout().addWidget(canvas)
            
        except Exception as e:
            logger.error(f"시간대별 로그 통계 분석 중 오류: {e}")

    def update_log_stats(self, log_entries=None):
        """로그 통계 업데이트"""
        # 재귀 호출 방지 플래그
        if hasattr(self, '_updating_log_stats'):
            return
        
        try:
            # 업데이트 중임을 표시
            self._updating_log_stats = True

            # 모든 로그 엔트리 사용
            if log_entries is None:
                log_entries = self.all_log_entries

            # 서버 필터 초기화
            if not hasattr(self, 'analysis_server_filter'):
                return

            server_filter = self.analysis_server_filter.currentText()
            level_filter = self.analysis_level_filter.currentText()

            # 서버 목록 추출 및 콤보박스 채우기
            server_list = set()
            for log_entry in self.all_log_entries:
                try:
                    server_name_parts = log_entry.split('[서버: ')
                    if len(server_name_parts) > 1:
                        server_name = server_name_parts[1].split(']')[0].strip()
                        server_list.add(server_name)
                except Exception:
                    pass
            
            # 서버 필터 콤보박스 업데이트
            current_server = self.analysis_server_filter.currentText()
            self.analysis_server_filter.clear()
            self.analysis_server_filter.addItem("모든 서버")
            for server in sorted(server_list):
                self.analysis_server_filter.addItem(server)
            
            # 이전 선택 유지 (가능한 경우)
            index = self.analysis_server_filter.findText(current_server)
            if index > -1:
                self.analysis_server_filter.setCurrentIndex(index)

            # 필터링된 로그 선택
            filtered_logs = []
            log_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
            
            for log_entry in self.all_log_entries:  # 전체 로그 사용
                # 서버 필터링
                try:
                    server_name_parts = log_entry.split('[서버: ')
                    server_name = 'SYSTEM'  # 기본값
                    if len(server_name_parts) > 1:
                        server_name = server_name_parts[1].split(']')[0].strip()
                    
                    if server_filter != "모든 서버" and server_name != server_filter:
                        continue
                    
                    # 로그 레벨 필터링 (더 안전한 방식)
                    log_level_match = None
                    for level in log_levels:
                        if f" - {level} - " in log_entry:
                            log_level_match = level
                            break
                    
                    # 로그 레벨 필터링 적용
                    if level_filter != "모든 로그" and log_level_match != level_filter:
                        continue
                    
                    filtered_logs.append(log_entry)
                except Exception as e:
                    logger.error(f"로그 필터링 중 오류: {e}")

            # 로그 레벨별 카운트
            log_level_counts = {
                'DEBUG': 0,
                'INFO': 0,
                'WARNING': 0,
                'ERROR': 0,
                'CRITICAL': 0
            }

            # 로그 레벨 카운트
            for entry in filtered_logs:
                for level in log_level_counts.keys():
                    if f" - {level} - " in entry:
                        log_level_counts[level] += 1
                        break

            # 로그 통계 텍스트 업데이트
            stats_text = "로그 통계:\n"
            total_logs = sum(log_level_counts.values())
            
            # 로그가 없을 경우 처리
            if total_logs == 0:
                self.log_stats_label.setText("로그 없음")
                # 기존 차트 제거
                for i in reversed(range(self.log_level_chart_layout.count())): 
                    widget = self.log_level_chart_layout.itemAt(i).widget()
                    if widget:
                        widget.setParent(None)
                        widget.deleteLater()
                return

            for level, count in log_level_counts.items():
                percentage = (count / total_logs * 100)
                stats_text += f"{level}: {count} ({percentage:.1f}%)\n"
            
            # 통계 라벨 업데이트
            self.log_stats_label.setText(stats_text)

            # 막대 그래프 생성
            self.create_log_level_chart(log_level_counts)

        except Exception as e:
            logger.error(f"로그 통계 업데이트 중 오류: {e}")
        
        finally:
            # 업데이트 플래그 제거
            if hasattr(self, '_updating_log_stats'):
                delattr(self, '_updating_log_stats')

    def create_log_level_chart(self, log_level_counts):
        # 기존 레이아웃의 모든 위젯 제거
        for i in reversed(range(self.log_level_chart_layout.count())): 
            widget = self.log_level_chart_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)
                widget.deleteLater()

        # 데이터 개수에 따라 동적으로 그래프 높이 조정
        graph_height = max(3, min(len(log_level_counts) * 0.5, 6))
        if len(log_level_counts) <= 2:
            graph_height = 2.5  # 로그 개수가 적을 때 더 작은 높이

        plt.close('all')  # 기존 플롯 닫기
        
        # 데이터 준비
        levels = list(log_level_counts.keys())
        counts = list(log_level_counts.values())
        percentages = [(count / sum(log_level_counts.values()) * 100) for count in counts]
        
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
        fig, ax = plt.subplots(figsize=(8, graph_height))
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

    def calculate_timeline_stats(self, log_entries):
        """로그의 시간대별 통계 계산"""
        # 시간대별 통계를 저장할 딕셔너리 리스트
        timeline_stats = []
        
        # 24시간을 2시간 단위로 분할
        for hour in range(0, 24, 2):
            # 각 시간대의 통계 초기화
            hour_stats = {
                'hour': f'{hour:02d}:00-{hour+2:02d}:00',
                'DEBUG': 0,
                'INFO': 0,
                'WARNING': 0,
                'ERROR': 0
            }
            
            # 해당 시간대의 로그 필터링
            for log in log_entries:
                try:
                    # 로그 항목에서 타임스탬프 추출
                    timestamp = log.get('timestamp', '')
                    log_time = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
                    
                    # 로그 시간이 현재 시간대에 속하는지 확인
                    if hour <= log_time.hour < hour + 2:
                        # 로그 레벨 카운트
                        log_level = log.get('level', '')
                        if log_level in hour_stats:
                            hour_stats[log_level] += 1
                except Exception as e:
                    logger.warning(f"시간대 통계 계산 중 오류: {e}")
            
            timeline_stats.append(hour_stats)
        
        return timeline_stats

    def periodic_log_update(self):
        """주기적인 로그 업데이트"""
        try:
            # 현재 로그 파일 경로 확인
            if not hasattr(self, 'current_log_file') or not self.current_log_file:
                return

            # 실시간 업데이트 체크박스가 체크되어 있는지 확인
            if not self.auto_update_check.isChecked():
                return

            # 로그 파일 다시 로드
            with open(self.current_log_file, 'r', encoding='utf-8') as f:
                # 마지막으로 읽은 위치부터 새로운 로그 읽기
                f.seek(self.last_log_file_position)
                new_log_entries = f.readlines()
                
                # 마지막 읽은 위치 업데이트
                self.last_log_file_position = f.tell()
            
            # 새로운 로그 항목이 있는 경우에만 처리
            if new_log_entries:
                # 기존 로그 항목에 새 로그 추가 (최대 1000개로 제한)
                self.all_log_entries.extend(new_log_entries)
                if len(self.all_log_entries) > 1000:
                    self.all_log_entries = self.all_log_entries[-1000:]
                
                # 현재 필터 상태 유지하며 로그 업데이트 (최적화된 필터링)
                current_server_filter = self.server_filter_combo.currentText()
                current_level_filter = self.log_level_combo.currentText()
                
                # 필터링된 로그 다시 표시 (최적화)
                filtered_logs = []
                for log_entry in self.all_log_entries:
                    # 서버 필터
                    if current_server_filter != "모든 서버":
                        server_parts = log_entry.split('[서버: ')
                        if len(server_parts) > 1:
                            server_name = server_parts[1].split(']')[0].strip()
                            if server_name != current_server_filter:
                                continue
                    
                    # 로그 레벨 필터
                    if current_level_filter != "모든 로그":
                        log_level_parts = log_entry.split(' - ')
                        if len(log_level_parts) >= 3:
                            log_level = log_level_parts[2].strip()
                            if log_level != current_level_filter:
                                continue
                    
                    filtered_logs.append(log_entry)
                
                # 최근 1000개 로그만 표시
                filtered_logs = filtered_logs[-1000:]
                
                # 로그 텍스트 업데이트 (최적화)
                self.populate_log_text(filtered_logs)
                
                # 로그 통계 업데이트 (최적화)
                self.update_log_stats(filtered_logs)
        
        except Exception as e:
            logger.error(f"주기적 로그 업데이트 중 오류: {e}")
            # 타이머 중지
            if hasattr(self, 'update_timer'):
                self.update_timer.stop()
