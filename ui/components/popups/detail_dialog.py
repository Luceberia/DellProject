from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QTreeWidget, QTreeWidgetItem, QPushButton, QScrollArea, QWidget
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from config.system.log_config import setup_logging

logger = setup_logging()

class DetailDialog(QDialog):
    def __init__(self, title, component_info, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"{title} 상세 정보")
        self.setMinimumWidth(500)
        self.setMinimumHeight(400)
        self.setup_ui(component_info)
        
    def setup_ui(self, component_info):
        layout = QVBoxLayout(self)
        tree_widget = QTreeWidget()
        tree_widget.setHeaderLabels(["항목", "상태", "값"])
        tree_widget.setColumnWidth(0, 200)
        tree_widget.setColumnWidth(1, 100)
        
        # 메모리 정렬 함수
        def sort_memory_slots(items):
            def get_slot_order(slot_id):
                # DIMM.Socket.X 형식에서 X 추출
                socket = slot_id.split('.')[-1]
                # 알파벳과 숫자 분리 (예: A1 -> ('A', 1))
                letter = socket[0]
                number = int(socket[1:]) if socket[1:].isdigit() else 0
                return (letter, number)
            
            return sorted(items, key=lambda x: get_slot_order(x[0]))
        
        # 정렬된 컴포넌트 리스트 생성
        if any('DIMM.Socket' in key for key in component_info.keys()):
            sorted_components = sort_memory_slots(component_info.items())
        else:
            sorted_components = sorted(component_info.items())
        
        # 컴포넌트별 트리 아이템 생성 및 상태에 따른 표시
        has_issues = False
        for component_name, info in sorted_components:
            component_item = QTreeWidgetItem(tree_widget, [component_name])
            component_status = 'OK'
            
            # 정보 표시 로직
            for key, value in info.items():
                item = QTreeWidgetItem(component_item)
                item.setText(0, key)
                item.setText(2, str(value))
                
                if '상태' in key.lower():
                    if value in ['OK', '활성화', 'Online']:
                        item.setText(1, "✅")
                        item.setForeground(2, QColor('green'))
                    elif value in ['None', 'Offline', 'Critical']:
                        item.setText(1, "❌")
                        item.setForeground(2, QColor('red'))
                        component_status = 'Error'
                        has_issues = True
                    else:
                        item.setText(1, "⚠️")
                        item.setForeground(2, QColor('orange'))
                        component_status = 'Warning'
                        has_issues = True
            
            # 문제가 있는 항목만 펼치기
            component_item.setExpanded(component_status != 'OK')
        
        # 문제가 있는 항목이 없으면 첫 번째 항목 펼치기
        if not has_issues and tree_widget.topLevelItemCount() > 0:
            tree_widget.topLevelItem(0).setExpanded(True)
        
        layout.addWidget(tree_widget)
        
        # 버튼 추가
        button_layout = QHBoxLayout()
        expand_btn = QPushButton("전체 펼치기")
        close_btn = QPushButton("닫기")
        
        expand_btn.clicked.connect(lambda: self.toggle_tree(tree_widget, expand_btn))
        close_btn.clicked.connect(self.close)
        
        button_layout.addWidget(expand_btn)
        button_layout.addWidget(close_btn)
        layout.addLayout(button_layout)

    def toggle_tree(self, tree_widget, button):
        if button.text() == "전체 펼치기":
            tree_widget.expandAll()
            button.setText("전체 접기")
        else:
            # 문제가 있는 항목만 펼치고 나머지는 접기
            for i in range(tree_widget.topLevelItemCount()):
                item = tree_widget.topLevelItem(i)
                status = 'OK'
                for j in range(item.childCount()):
                    if '상태' in item.child(j).text(0).lower():
                        if item.child(j).text(1) != "✅":
                            status = 'Error'
                item.setExpanded(status != 'OK')
            button.setText("전체 펼치기")
