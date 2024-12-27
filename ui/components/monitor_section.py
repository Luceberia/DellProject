import pandas as pd
from PyQt6.QtGui import QColor, QIcon, QImage, QPixmap
from config.system.log_config import setup_logging
from PyQt6.QtWidgets import QDialog, QFileDialog, QGroupBox, QHBoxLayout, QMessageBox, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QPushButton, QProgressDialog, QApplication, QMainWindow, QLabel, QSpinBox, QProgressBar, QCheckBox, QDialogButtonBox, QLineEdit, QTreeView, QMenu
from PyQt6.QtCore import Qt, QTimer, QSettings
from typing import Optional, cast
from ui.components.popups.system_event_popup import SystemEventPopup
from ui.components.popups.error_dialog import ErrorDialog
from managers.dell_server_manager import DellServerManager
from common.cache.cache_manager import SystemInfoCache
from utils.utils import convert_capacity
import requests
import re
import base64
import os
from pathlib import Path
import time

logger = setup_logging()

def create_section(title, items, parent=None):
    group = QGroupBox(title)
    layout = QVBoxLayout(group)
    layout.setSpacing(10)
    layout.setContentsMargins(10, 15, 10, 15)
    
    # 섹션별 이모티콘 매핑
    icons = {
        # 모니터링 섹션
        "시스템 상태": "📊",
        "펌웨어 정보": "📦",
        # 관리 섹션
        "BIOS 설정": "🔧",
        "SSH 연결": "🔌",
        # 로그 섹션
        "SEL LOG": "📜",
        "LC LOG": "📋"
    }
    
    buttons = {}
    for item in items:
        # 해당 항목의 이모티콘 가져오기 (없으면 기본 화살표)
        icon = icons.get(item, "▸")
        btn = QPushButton(f"{icon} {item}")
        layout.addWidget(btn)
        buttons[item] = btn
        
        # 시스템 상태 버튼 클릭 이벤트 처리
        if item == "시스템 상태":
            btn.clicked.connect(lambda checked=False, p=parent: show_all_status(p))
        # 펌웨어 정보 버튼 클릭 이벤트 처리
        elif item == "펌웨어 정보":
            btn.clicked.connect(lambda checked=False, p=parent: show_firmware_info(p))
        # BIOS 설정 버튼 클릭 이벤트 처리
        elif item == "BIOS 설정":
            btn.clicked.connect(lambda checked=False, p=parent: show_system_info(p))
        # SSH 연결 버튼 클릭 이벤트 처리
        elif item == "SSH 연결":
            btn.clicked.connect(lambda checked=False, p=parent: open_ssh_connection(p))
        # SEL LOG와 LC LOG 버튼 클릭 이벤트 처리
        elif item == "SEL LOG":
            btn.clicked.connect(lambda checked=False, p=parent: show_sel_log_popup(p))
        elif item == "LC LOG":
            btn.clicked.connect(lambda checked=False, p=parent: show_lc_log_popup(p))
            
    return group, buttons

def get_main_window() -> Optional[QMainWindow]:
    """메인 윈도우 객체 가져오기"""
    app = cast(QApplication, QApplication.instance())
    if app is not None:
        window = app.activeWindow()
        if isinstance(window, QMainWindow):
            return window
    return None

def create_monitor_section(parent=None):
    monitor_group = QGroupBox()
    monitor_layout = QHBoxLayout(monitor_group)
    monitor_layout.setSpacing(5)
    
    sections = {
        "📊 모니터링": ["시스템 상태", "펌웨어 정보"],
        "⚙️ 관리": ["BIOS 설정", "SSH 연결"],
        "📋 로그": ["SEL LOG", "LC LOG"]
    }
    
    for title, items in sections.items():
        section_group, buttons = create_section(title, items, monitor_group)
        monitor_layout.addWidget(section_group)
    
    return monitor_group

def show_hostname_input_dialog(parent):
    dialog = QDialog(parent)
    dialog.setWindowTitle("호스트네임 변경")
    
    layout = QVBoxLayout()
    
    # 호스트네임 입력 필드
    hostname_label = QLabel("새로운 호스트네임:")
    hostname_input = QLineEdit()
    layout.addWidget(hostname_label)
    layout.addWidget(hostname_input)
    
    # 호스트네임 초기화 체크박스
    clear_hostname = QCheckBox("호스트네임 초기화 (빈 값으로 설정)")
    clear_hostname.toggled.connect(lambda checked: hostname_input.setEnabled(not checked))
    layout.addWidget(clear_hostname)
    
    # 확인/취소 버튼
    button_box = QDialogButtonBox(
        QDialogButtonBox.StandardButton.Ok | 
        QDialogButtonBox.StandardButton.Cancel
    )
    button_box.accepted.connect(dialog.accept)
    button_box.rejected.connect(dialog.reject)
    layout.addWidget(button_box)
    
    dialog.setLayout(layout)
    
    if dialog.exec() == QDialog.DialogCode.Accepted:
        if clear_hostname.isChecked():
            return ""  # 빈 문자열 반환
        return hostname_input.text()
    return None

def show_ssh_command_dialog(parent):
    dialog = QDialog(parent)
    dialog.setWindowTitle("SSH 명령어 선택")
    dialog.resize(400, 300)  # 대화상자 크기 조정
    
    # 레이아웃 설정
    layout = QVBoxLayout()
    
    # 명령어와 설명을 매핑하는 딕셔너리
    command_map = {
        "호스트네임 관리": {
            "호스트네임 조회": {
                "command": "racadm get system.serveros.hostname",
                "needs_input": False
            },
            "호스트네임 변경": {
                "command": "racadm set system.serveros.hostname '{hostname}'",
                "needs_input": True
            }
        },
        "시스템 로그 관리": {
            "SEL 로그 초기화": {
                "command": "racadm clrsel",
                "needs_input": False,
                "needs_confirm": True,
                "confirm_message": "SEL 로그를 초기화하시겠습니까?",
                "post_action": "refresh_sel"
            }
        }
    }
    
    # 설정 로드
    settings = QSettings('Dell', 'iDRAC Monitor')
    favorites = settings.value('ssh_favorites', [], type=list)
    
    # 즐겨찾기 섹션과 그룹박스를 클래스 변수로 저장
    dialog.favorites = favorites
    dialog.favorites_group = None
    
    def update_favorites_ui():
        # 기존 즐겨찾기 그룹박스가 있다면 제거
        if dialog.favorites_group:
            layout.removeWidget(dialog.favorites_group)
            dialog.favorites_group.deleteLater()
            dialog.favorites_group = None
        
        # 즐겨찾기가 있는 경우에만 그룹박스 생성
        if dialog.favorites:
            dialog.favorites_group = QGroupBox("즐겨찾기")
            favorites_layout = QVBoxLayout()
            for fav in dialog.favorites:
                btn = QPushButton(fav)
                btn.clicked.connect(lambda checked, cmd=fav: handle_favorite_click(dialog, command_map, cmd))
                favorites_layout.addWidget(btn)
            dialog.favorites_group.setLayout(favorites_layout)
            layout.insertWidget(0, dialog.favorites_group)  # 항상 최상단에 추가
    
    # 초기 즐겨찾기 UI 생성
    update_favorites_ui()
    
    # 트리 위젯 생성
    tree = QTreeWidget()
    tree.setHeaderLabels(["명령어"])
    tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
    
    def handle_context_menu(pos):
        item = tree.itemAt(pos)
        if not item:
            return
            
        command_info = item.data(0, Qt.ItemDataRole.UserRole)
        if not command_info:  # 카테고리인 경우
            return
            
        menu = QMenu()
        command_name = item.text(0)
        
        if command_name in dialog.favorites:
            action = menu.addAction("즐겨찾기 제거")
            action.triggered.connect(lambda: remove_from_favorites(command_name, dialog.favorites, settings, update_favorites_ui))
        else:
            action = menu.addAction("즐겨찾기 추가")
            action.triggered.connect(lambda: add_to_favorites(command_name, dialog.favorites, settings, update_favorites_ui))
        
        menu.exec(tree.viewport().mapToGlobal(pos))
    
    tree.customContextMenuRequested.connect(handle_context_menu)
    
    # 더블클릭 이벤트 추가
    tree.itemDoubleClicked.connect(lambda: dialog.accept())
    
    # 트리 아이템 추가
    for category, commands in command_map.items():
        category_item = QTreeWidgetItem([category])
        for cmd_name, cmd_info in commands.items():
            command_item = QTreeWidgetItem([cmd_name])
            command_item.setData(0, Qt.ItemDataRole.UserRole, cmd_info)
            category_item.addChild(command_item)
        tree.addTopLevelItem(category_item)
    
    tree.expandAll()
    layout.addWidget(tree)
    
    # 확인/취소 버튼
    button_box = QDialogButtonBox(
        QDialogButtonBox.StandardButton.Ok | 
        QDialogButtonBox.StandardButton.Cancel
    )
    button_box.accepted.connect(dialog.accept)
    button_box.rejected.connect(dialog.reject)
    layout.addWidget(button_box)
    
    dialog.setLayout(layout)
    
    # 대화상자 실행 및 결과 반환
    result = dialog.exec()
    
    # Cancel 버튼을 눌렀을 때
    if result == QDialog.DialogCode.Rejected:
        return False, None
    
    # OK 버튼을 눌렀을 때
    selected_items = tree.selectedItems()
    if not selected_items:
        return True, None
        
    selected_item = selected_items[0]
    command_info = selected_item.data(0, Qt.ItemDataRole.UserRole)
    
    if not command_info:  # 카테고리가 선택된 경우
        return True, None
        
    # 확인이 필요한 명령어인 경우
    if command_info.get('needs_confirm'):
        confirm = QMessageBox.question(
            dialog,
            "확인",
            command_info['confirm_message'],
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if confirm == QMessageBox.StandardButton.No:
            return False, None  # Cancel 버튼과 동일하게 처리
    
    # 입력이 필요한 명령어인 경우
    if command_info.get('needs_input'):
        hostname = show_hostname_input_dialog(dialog)
        if hostname is not None:
            return True, command_info['command'].format(hostname=hostname)
        return False, None  # Cancel 버튼과 동일하게 처리
    
    return True, command_info['command']

def show_context_menu(pos, tree, favorites, settings):
    item = tree.itemAt(pos)
    if not item:
        return
        
    command_info = item.data(0, Qt.ItemDataRole.UserRole)
    if not command_info:  # 카테고리인 경우
        return
        
    menu = QMenu()
    command_name = item.text(0)
    
    if command_name in favorites:
        action = menu.addAction("즐겨찾기 제거")
        action.triggered.connect(
            lambda: remove_from_favorites(command_name, favorites, settings)
        )
    else:
        action = menu.addAction("즐겨찾기 추가")
        action.triggered.connect(
            lambda: add_to_favorites(command_name, favorites, settings)
        )
    
    menu.exec(tree.viewport().mapToGlobal(pos))

def add_to_favorites(command_name, favorites, settings, update_callback):
    if command_name not in favorites:
        favorites.append(command_name)
        settings.setValue('ssh_favorites', favorites)
        update_callback()

def remove_from_favorites(command_name, favorites, settings, update_callback):
    if command_name in favorites:
        favorites.remove(command_name)
        settings.setValue('ssh_favorites', favorites)
        update_callback()

def open_ssh_connection(parent):
    try:
        main_window = parent.window()
        if not hasattr(main_window, 'server_section'):
            error_dialog = ErrorDialog(
                "서버 연결 오류",
                "서버가 연결되어 있지 않습니다.",
                "서버를 먼저 연결한 후 다시 시도해주세요.",
                parent
            )
            error_dialog.exec()
            return
            
        server_info = main_window.server_section.current_server_info
        if not server_info:
            error_dialog = ErrorDialog(
                "서버 연결 오류",
                "서버 정보를 찾을 수 없습니다.",
                "서버를 선택한 후 다시 시도해주세요.",
                parent
            )
            error_dialog.exec()
            return
        
        # SSH 명령어 선택 대화상자 표시
        proceed, selected_command = show_ssh_command_dialog(parent)
        
        # Cancel 버튼을 눌렀으면 종료
        if not proceed:
            return
            
        from utils.ssh_utils import open_ssh_terminal
        
        # SSH 연결 시도
        ssh_params = {
            "host": server_info['IP'],
            "username": 'root',
            "key_path": '~/.ssh/id_rsa',
            "password": server_info.get('PASSWORD')
        }
        
        if selected_command is not None:
            ssh_params["command"] = selected_command
            
        # SSH 명령어 실행
        open_ssh_terminal(**ssh_params)
        
        # SEL 로그 초기화 후 갱신
        if selected_command == "racadm clrsel":
            QTimer.singleShot(2000, lambda: refresh_sel_after_clear(main_window))
            
    except Exception as e:
        logger.error(f"SSH 연결 실패: {str(e)}")
        error_dialog = ErrorDialog(
            "SSH 연결 오류",
            "SSH 연결 중 오류가 발생했습니다.",
            str(e),
            parent
        )
        error_dialog.exec()

def refresh_sel_after_clear(main_window):
    """SEL 로그 초기화 후 이벤트 로그 갱신"""
    if hasattr(main_window, 'server_section'):
        main_window.server_section.update_log_count()

def show_all_status(parent):
    """CPU(GPU포함) 정보 / MEMORY 정보 / STORAGE 정보 / NIC 정보 / PSU 정보 / iDRAC MAC 정보를 통합하여 테이블 형식으로 반환"""
    logger.debug("시스템 상태 정보 조회 시도")
    
    main_window = parent.window()
    if not hasattr(main_window, 'server_section'):
        logger.warning("서버 섹션을 찾을 수 없음")
        error_dialog = ErrorDialog(
            "서버 연결 오류",
            "서버가 연결되어 있지 않습니다.",
            "서버를 먼저 연결한 후 다시 시도해주세요.",
            parent
        )
        error_dialog.exec()
        return
    
    server_info = main_window.server_section.current_server_info
    if not server_info:
        logger.warning("서버 정보가 없음")
        error_dialog = ErrorDialog(
            "서버 연결 오류",
            "서버 정보를 찾을 수 없습니다.",
            "서버를 선택한 후 다시 시도해주세요.",
            parent
        )
        error_dialog.exec()
        return
    
    # 진행률 다이얼로그 생성
    progress_dialog = QProgressDialog("시스템 상태 정보 로딩 중...", None, 0, 100, parent)
    progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
    progress_dialog.setWindowTitle("데이터 로드")
    progress_dialog.setAutoClose(True)
    progress_dialog.setMinimumDuration(0)
    
    status_dialog = QDialog(parent)
    status_dialog.setWindowTitle("System Information")
    status_dialog.resize(800, 600)

    layout = QVBoxLayout()
    status_dialog.setLayout(layout)

    button_layout = QHBoxLayout()
    expand_collapse_button = QPushButton("전체 펼치기")
    rebuild_monitor_toggle = QPushButton("리빌딩 모니터링")
    rebuild_monitor_toggle.setCheckable(True)
    rebuild_monitor_toggle.setStyleSheet("""
        QPushButton:checked {
            background-color: #FFA500;
            color: white;
        }
    """)
    
    button_layout.addWidget(expand_collapse_button)
    button_layout.addWidget(rebuild_monitor_toggle)
    layout.addLayout(button_layout)

    tree_widget = QTreeWidget()
    tree_widget.setHeaderLabels(["구성 요소", "Dell Attribute name", "value"])
    tree_widget.setColumnWidth(0, 250)
    tree_widget.setColumnWidth(1, 250)
    layout.addWidget(tree_widget)

    # 리빌딩 상태를 표시할 영역
    rebuild_status_layout = QVBoxLayout()
    rebuild_status_group = QGroupBox("리빌딩 상태")
    rebuild_status_group.setVisible(False)
    rebuild_status_tree = QTreeWidget()
    rebuild_status_tree.setHeaderLabels(["디스크 위치", "진행률", "예상 시간"])
    rebuild_status_layout.addWidget(rebuild_status_tree)
    rebuild_status_group.setLayout(rebuild_status_layout)
    layout.addWidget(rebuild_status_group)

    def check_disk_status(drive):
        status = drive.get('Oem', {}).get('Dell', {}).get('DellPhysicalDisk', {}).get('RaidStatus', 'N/A')
        
        status_colors = {
            'Online': QColor('green'),
            'Rebuilding': QColor('orange'),
            'Failed': QColor('red'),
            'Degraded': QColor('yellow'),
            'Offline': QColor('gray')
        }
        
        return (status, status_colors.get(status))

    def update_rebuild_status():
        rebuild_status_tree.clear()
        storage_info = server_manager.fetch_storage_info()
        rebuilding_exists = False
        
        for controller in storage_info.get('Controllers', []):
            volumes = controller.get('Volumes', [])
            drives = controller.get('Drives', [])
            
            for volume in volumes:
                volume_name = volume.get('Name', '')
                raid_type = volume.get('RAIDType', '')
                capacity = volume.get('CapacityBytes', 0) / (1024**4)
                
                volume_drive_ids = [link.get('@odata.id', '').split('/')[-1] 
                                for link in volume.get('Links', {}).get('Drives', [])]
                
                volume_item = QTreeWidgetItem(rebuild_status_tree)
                volume_item.setText(0, f"볼륨: {volume_name}")
                volume_item.setText(1, f"RAID {raid_type}")
                volume_item.setText(2, f"{capacity:.1f} TiB")
                volume_item.setBackground(0, QColor('#E6E6FA'))
                
                # 리빌딩 디스크 존재 여부 확인을 위한 플래그
                has_rebuilding_disk = False
                
                for drive in drives:
                    if drive.get('Id', '') in volume_drive_ids:
                        disk_id = drive.get('Id', '').split(':')[0]
                        
                        drive_item = QTreeWidgetItem(volume_item)
                        drive_item.setText(0, disk_id)
                        
                        status, color = check_disk_status(drive)
                        
                        if drive.get('Operations'):
                            for operation in drive.get('Operations', []):
                                if operation.get('OperationName') == "Rebuilding":
                                    rebuilding_exists = True
                                    has_rebuilding_disk = True  # 리빌딩 중인 디스크 발견
                                    progress = operation.get('PercentageComplete', 0)
                                    
                                    progress_bar = QProgressBar()
                                    progress_bar.setValue(progress)
                                    progress_bar.setStyleSheet("""
                                        QProgressBar {
                                            border: 2px solid grey;
                                            text-align: center;
                                        }
                                        QProgressBar::chunk {
                                            background-color: #FFA500;
                                        }
                                    """)
                                    rebuild_status_tree.setItemWidget(drive_item, 1, progress_bar)
                                    
                                    if progress > 0:
                                        remaining_minutes = int((100 - progress) * 2)
                                        drive_item.setText(2, f"{remaining_minutes}분")
                        else:
                            status_label = QLabel(status)
                            if color:
                                status_label.setStyleSheet(f"color: {color.name()}")
                            rebuild_status_tree.setItemWidget(drive_item, 1, status_label)
                            drive_item.setText(2, "-")
                
                # 볼륨의 펼침 상태 설정
                if has_rebuilding_disk:
                    rebuild_status_tree.expandItem(volume_item)  # 리빌딩 중인 디스크가 있는 볼륨은 펼치기
                else:
                    rebuild_status_tree.collapseItem(volume_item)  # 리빌딩 중인 디스크가 없는 볼륨은 접기
        
        if not rebuilding_exists:
            rebuild_monitor_toggle.setChecked(False)
            rebuild_status_group.setVisible(False)
    
    def toggle_rebuild_monitor(checked):
        rebuild_status_group.setVisible(checked)
        if checked:
            update_rebuild_status()
            timer.start(10000)  # 10초마다 갱신
        else:
            timer.stop()
    
    timer = QTimer()
    timer.timeout.connect(update_rebuild_status)
    rebuild_monitor_toggle.toggled.connect(toggle_rebuild_monitor)
    
    try:
        def toggle_all_sections():
            if expand_collapse_button.text() == "전체 펼치기":
                tree_widget.expandAll()
                expand_collapse_button.setText("전체 접기")
            else:
                tree_widget.collapseAll()
                expand_collapse_button.setText("전체 펼치기")
        
        expand_collapse_button.clicked.connect(toggle_all_sections)

        main_window = parent.window()
        if hasattr(main_window, 'server_section'):
            server_info = main_window.server_section.current_server_info
            if server_info:
                server_manager = DellServerManager(
                    ip=server_info['IP'],
                    port=server_info['PORT'],
                    auth=(server_info['USERNAME'], server_info['PASSWORD'])
                )
                
                progress_dialog.show()

                # 데이터 로드
                data = {
                    'processors': server_manager.fetch_processors_info(),
                    'memory': server_manager.fetch_memory_info(),
                    'storage': server_manager.fetch_storage_info(),
                    'nic': server_manager.fetch_network_adapters_info(),
                    'psu': server_manager.fetch_psu_info(),
                    'idrac': server_manager.fetch_detailed_info(server_manager.endpoints.idrac_mac_address),
                    'license': server_manager.check_idrac_license()
                }

                # 섹션별 설정 딕셔너리 정의
                processor_settings = {
                    "모델": "Model",
                    "제조사": "Manufacturer",
                    "코어 수": "TotalCores",
                    "스레드 수": "TotalThreads",
                    "최대 속도": "MaxSpeedMHz",
                    "현재 속도": "OperatingSpeedMHz",
                    "상태": "Status.Health"
                }
                dell_processor_settings = {
                    "하이퍼스레딩": "HyperThreadingEnabled",
                    "가상화 기술": "VirtualizationTechnologyEnabled",
                    "터보 모드": "TurboModeEnabled"
                }
                memory_settings = {
                    "제조사": "Manufacturer",
                    "타입": "MemoryDeviceType",
                    "동작 속도": "OperatingSpeedMhz",
                    "용량": "CapacityMiB",
                    "상태": "Status.Health"
                }
                storage_settings = {
                    "모델": "Model",
                    "펌웨어 버전": "FirmwareVersion",
                    "캐시": "TotalCacheSizeMiB",
                    "상태": "Status.Health"
                }
                volume_settings = {
                    "레이드": "RAIDType",
                    "미디어 타입": "MediaType",
                    "용량": "CapacityBytes",
                    "상태": "RaidStatus"
                }
                drive_settings = {
                    "제조사": "Manufacturer",
                    "파트 번호": "PartNumber",
                    "시리얼 번호": "SerialNumber",
                    "용량": "CapacityBytes",
                    "레이드 상태": "RaidStatus"
                }
                nic_settings = {
                    "모델": "Model",
                    "제조사": "Manufacturer",
                    "파트 번호": "PartNumber",
                    "시리얼 번호": "SerialNumber",
                    "상태": "Status.Health"
                }
                controller_settings = {
                    "펌웨어 버전": "FirmwarePackageVersion",
                    "가상화 지원": "VirtualizationOffload"
                }
                port_settings = {
                    "링크 상태": "LinkStatus",
                    "현재 속도": "CurrentLinkSpeedMbps",
                    "Flow Control 설정": "FlowControlConfiguration",
                    "Flow Control 상태": "FlowControlStatus",
                    "MAC 주소": "AssociatedNetworkAddresses"
                }
                transceiver_settings = {
                    "트랜시버 타입": "IdentifierType",
                    "인터페이스": "InterfaceType",
                    "트랜시버 제조사": "VendorName"
                }
                optical_settings = {
                    "온도": "Temperature",
                    "전압": "SupplyVoltage",
                    "TX 파워": "TxPower",
                    "RX 파워": "RxPower",
                    "레이저 바이어스 전류": "LaserBiasCurrent"
                }
                psu_settings = {
                    "모델": "Model",
                    "제조사": "Manufacturer",
                    "용량": "PowerCapacityWatts",
                    "상태": "Status.Health",
                    "펌웨어 버전": "FirmwareVersion",
                    "시리얼 번호": "SerialNumber",
                    "파트 번호": "PartNumber",
                }

                idrac_mac_settings = {
                    "MAC 주소": "CurrentNIC.1.MACAddress"
                }

                # 섹션 정의
                sections = [
                    ("프로세서 정보", data['processors'], processor_settings),
                    ("메모리 정보", data['memory'], memory_settings),
                    ("스토리지 정보", data['storage'], storage_settings),
                    ("NIC 정보", data['nic'], nic_settings),
                    ("PSU 정보", data['psu'], psu_settings),
                    ("iDRAC MAC 주소 정보", data['idrac'], idrac_mac_settings)
                ]

                # 섹션별 트리 아이템 생성
                for section_name, info_source, settings_dict in sections:
                    if info_source:
                        section_item = QTreeWidgetItem(tree_widget, [section_name])
                        
                        if section_name == "프로세서 정보":
                            if 'Members' in info_source:
                                for cpu in info_source['Members']:
                                    member_uri = cpu.get('@odata.id')
                                    if member_uri:
                                        cpu_response = requests.get(
                                            f"{server_manager.endpoints.base_url}{member_uri}",
                                            auth=server_manager.auth,
                                            verify=False
                                        )
                                        cpu_info = cpu_response.json()
                                        cpu_item = QTreeWidgetItem(section_item, [f"CPU {cpu_info.get('Id', 'N/A')}"])
                                        
                                        for key, value in settings_dict.items():
                                            item = QTreeWidgetItem(cpu_item)
                                            item.setText(0, key)
                                            item.setText(1, value)
                                            item.setText(2, str(cpu_info.get(value, 'N/A')))
                                            
                                            if key == "상태":
                                                status = cpu_info.get('Status', {})
                                                state = status.get('State')
                                                health = status.get('Health')
                                                
                                                if state == 'Enabled' and health == 'OK':
                                                    item.setText(2, 'OK')
                                                    item.setForeground(2, QColor('green'))
                                                elif state == 'Enabled' and health == 'Critical':
                                                    item.setText(2, 'Critical')
                                                    item.setForeground(2, QColor('red'))
                                                else:
                                                    item.setText(2, str(health))
                                        
                                        dell_info = cpu_info.get('Oem', {}).get('Dell', {}).get('DellProcessor', {})
                                        if dell_info:
                                            dell_section = QTreeWidgetItem(cpu_item, ["Dell 특정 정보"])
                                            for key, value in dell_processor_settings.items():
                                                item = QTreeWidgetItem(dell_section)
                                                item.setText(0, key)
                                                item.setText(1, value)
                                                enabled = "활성화" if dell_info.get(value) == "Yes" else "비활성화"
                                                item.setText(2, enabled)
                                                item.setForeground(2, QColor('green') if enabled == "활성화" else QColor('red'))
                        elif section_name == "메모리 정보":
                            if 'Members' in info_source:
                                sorted_members = sorted(info_source.get('Members', []), 
                                                    key=lambda x: x.get('@odata.id', ''))
                                for member in sorted_members:
                                    member_uri = member.get('@odata.id')
                                    if member_uri:
                                        memory_response = requests.get(
                                            f"{server_manager.endpoints.base_url}{member_uri}",
                                            auth=server_manager.auth,
                                            verify=False
                                        )
                                        memory_info = memory_response.json()
                                        
                                        memory_item = QTreeWidgetItem(section_item, 
                                                                    [f"메모리 {memory_info.get('Id', 'N/A')}"])
                                        
                                        for key, value in settings_dict.items():
                                            item = QTreeWidgetItem(memory_item)
                                            item.setText(0, key)
                                            item.setText(1, value)
                                            
                                            if key == "용량":
                                                value = convert_capacity(memory_info.get('CapacityMiB', 0), False)
                                            elif key == "동작 속도":
                                                value = f"{memory_info.get('OperatingSpeedMhz', 'N/A')} MHz"
                                            else:
                                                value = memory_info.get(value, 'N/A')
                                            
                                            item.setText(2, str(value))
                                            
                                            if key == "상태":
                                                status = memory_info.get('Status', {})
                                                state = status.get('State')
                                                health = status.get('Health')
                                                
                                                if state == 'Enabled' and health == 'OK':
                                                    item.setText(2, 'OK')
                                                    item.setForeground(2, QColor('green'))
                                                elif state == 'Enabled' and health == 'Critical':
                                                    item.setText(2, 'Critical')
                                                    item.setForeground(2, QColor('red'))
                                                else:
                                                    item.setText(2, str(health))

                        elif section_name == "스토리지 정보":
                            if 'Controllers' in info_source:
                                for controller in info_source['Controllers']:
                                    storage_controllers = controller.get('StorageControllers', [])
                                    if storage_controllers:
                                        controller_info = storage_controllers[0]
                                        controller_item = QTreeWidgetItem(section_item,
                                            [f"컨트롤러 {controller.get('Id', 'N/A')}"])
                                        
                                        # 컨트롤러 정보 표시
                                        for key, value in storage_settings.items():
                                            item = QTreeWidgetItem(controller_item)
                                            item.setText(0, key)
                                            item.setText(1, value)
                                            
                                            if key == "캐시":
                                                cache_value = controller_info.get('CacheSummary', {}).get('TotalCacheSizeMiB', 0)
                                                item.setText(2, convert_capacity(cache_value, False))
                                            elif key == "상태":
                                                status = controller.get('Status', {}).get('Health', 'N/A')
                                                item.setText(2, str(status))
                                                if status == 'OK':
                                                    item.setForeground(2, QColor('green'))
                                            else:
                                                item.setText(2, str(controller_info.get(value, 'N/A')))

                                        # 볼륨 정보 표시
                                        volumes = controller.get('Volumes', [])
                                        for volume in volumes:
                                            dell_volume = volume.get('Oem', {}).get('Dell', {}).get('DellVolume', {})
                                            volume_item = QTreeWidgetItem(controller_item,
                                                [f"볼륨: {volume.get('Name', 'N/A')}"])
                                            
                                            for key, value in volume_settings.items():
                                                item = QTreeWidgetItem(volume_item)
                                                item.setText(0, key)
                                                item.setText(1, value)
                                                
                                                if key == "용량":
                                                    item.setText(2, convert_capacity(volume.get('CapacityBytes', 0), True))
                                                elif key == "미디어 타입":
                                                    item.setText(2, str(dell_volume.get('MediaType', 'N/A')))
                                                elif key == "상태":
                                                    status = dell_volume.get('RaidStatus', 'N/A')
                                                    item.setText(2, str(status))
                                                    if status == 'Online':
                                                        item.setForeground(2, QColor('green'))
                                                else:
                                                    item.setText(2, str(volume.get(value, 'N/A')))

                                            # 드라이브 정보 표시
                                            drives = controller.get('Drives', [])
                                            volume_drive_ids = [link.get('@odata.id', '').split('/')[-1]
                                                                for link in volume.get('Links', {}).get('Drives', [])]
                                            volume_drives = [d for d in drives if d.get('Id', '') in volume_drive_ids]
                                            sorted_drives = sort_drives(volume_drives)

                                            for drive in sorted_drives:
                                                simplified_id = drive.get('Id', 'N/A').split(':')[0]  # drive 변수가 정의된 후에 사용
                                                drive_item = QTreeWidgetItem(volume_item, [f"드라이브: {simplified_id}"])
                                                
                                                for key, value in drive_settings.items():
                                                    item = QTreeWidgetItem(drive_item)
                                                    item.setText(0, key)
                                                    item.setText(1, value)
                                                    
                                                    if key == "용량":
                                                        item.setText(2, convert_capacity(drive.get('CapacityBytes', 0), True))
                                                    elif key == "레이드 상태":
                                                        status = drive.get('Oem', {}).get('Dell', {}).get('DellPhysicalDisk', {}).get('RaidStatus', 'N/A')
                                                        item.setText(2, str(status))
                                                        if status == 'Online':
                                                            item.setForeground(2, QColor('green'))
                                                        elif status == 'Rebuilding':
                                                            item.setForeground(2, QColor('orange'))
                                                    else:
                                                        item.setText(2, str(drive.get(value, 'N/A')))
                                                
                                                # 리빌딩 감지 및 모니터링 버튼 추가
                                                if drive.get('Operations'):
                                                    for operation in drive.get('Operations', []):
                                                        if operation.get('OperationName') == "Rebuilding":
                                                            # 리빌딩 상태 표시
                                                            rebuild_status = QTreeWidgetItem(drive_item)
                                                            rebuild_status.setText(0, "리빌딩 상태")
                                                            rebuild_status.setText(1, "RebuildStatus")
                                                            rebuild_status.setText(2, "진행 중")
                                                            rebuild_status.setForeground(2, QColor('orange'))
                                                            
                                                            # 진행률 표시
                                                            progress = operation.get('PercentageComplete', 0)
                                                            progress_item = QTreeWidgetItem(drive_item)
                                                            progress_item.setText(0, "진행률")
                                                            progress_item.setText(1, "PercentageComplete")
                                                            progress_item.setText(2, f"{progress}%")
                                                            
                                                            # 모니터링 버튼 추가
                                                            monitor_button = QPushButton("리빌딩 모니터링")
                                                            monitor_button.setStyleSheet("background-color: #FFA500; color: white;")

                                                            # 현재 드라이버의 리빌딩 상태에 따른 모니터링
                                                            def create_monitor_handler(current_drive):
                                                                def show_rebuild_monitor():
                                                                    monitor_dialog = QDialog(parent)
                                                                    monitor_dialog.setWindowTitle(f"리빌딩 모니터링 - 드라이브 {current_drive.get('Id', 'N/A')}")
                                                                    monitor_dialog.resize(400, 150)
                                                                    
                                                                    # 메인 레이아웃
                                                                    main_layout = QVBoxLayout()

                                                                    # 갱신 주기 설정
                                                                    refresh_layout = QHBoxLayout()
                                                                    refresh_label = QLabel("갱신 주기(초):")
                                                                    refresh_spin = QSpinBox()
                                                                    refresh_spin.setRange(5, 60)
                                                                    refresh_spin.setValue(10)
                                                                    refresh_spin.setToolTip("5초에서 60초 사이로 설정 가능합니다")
                                                                    refresh_layout.addWidget(refresh_label)
                                                                    refresh_layout.addWidget(refresh_spin)

                                                                    # 상태 표시 레이블 (진행률과 예상 시간)
                                                                    status_label = QLabel()
                                                                    status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                                                                    
                                                                    # 프로그레스바와 취소 버튼이 있는 영역
                                                                    progress_layout = QVBoxLayout()
                                                                    progress_bar = QProgressBar()
                                                                    progress_bar.setMinimum(0)
                                                                    progress_bar.setMaximum(100)
                                                                    cancel_button = QPushButton("모니터링 중지")
                                                                    progress_layout.addWidget(progress_bar)
                                                                    progress_layout.addWidget(cancel_button)

                                                                    # 레이아웃 구성
                                                                    main_layout.addLayout(refresh_layout)
                                                                    main_layout.addWidget(status_label)
                                                                    main_layout.addLayout(progress_layout)
                                                                    monitor_dialog.setLayout(main_layout)
                                                                    
                                                                    # 타이머 설정
                                                                    start_time = time.time()
                                                                    last_progress = 0
                                                                    timer = QTimer()
                                                                    
                                                                    def update_progress():
                                                                        try:
                                                                            drive_info = server_manager.fetch_drive_rebuild_status(current_drive)
                                                                            if drive_info and 'Operations' in drive_info:
                                                                                for op in drive_info['Operations']:
                                                                                    if op.get('OperationName') == "Rebuilding":
                                                                                        current_progress = op.get('PercentageComplete', 0)
                                                                                        
                                                                                        # 예상 시간 계산
                                                                                        elapsed_time = time.time() - start_time
                                                                                        if current_progress > 0:
                                                                                            total_time = (elapsed_time * 100) / current_progress
                                                                                            remaining_time = total_time - elapsed_time
                                                                                            remaining_minutes = int(remaining_time // 60)
                                                                                            remaining_seconds = int(remaining_time % 60)
                                                                                            
                                                                                            status_label.setText(
                                                                                                f"리빌딩 진행률: {current_progress}%\n"
                                                                                                f"예상 남은 시간: {remaining_minutes}분 {remaining_seconds}초"
                                                                                            )
                                                                                        
                                                                                        progress_bar.setValue(current_progress)
                                                                                        last_progress = current_progress
                                                                                        
                                                                        except Exception as e:
                                                                            logger.error(f"리빌딩 상태 업데이트 실패: {str(e)}")
                                                                        
                                                                        if last_progress == 100:
                                                                            timer.stop()
                                                                            monitor_dialog.close()
                                                                    
                                                                    def on_canceled():
                                                                        timer.stop()
                                                                        monitor_dialog.close()
                                                                    
                                                                    timer.timeout.connect(update_progress)
                                                                    cancel_button.clicked.connect(on_canceled)
                                                                    refresh_spin.valueChanged.connect(lambda: timer.setInterval(refresh_spin.value() * 1000))
                                                                    
                                                                    timer.start(refresh_spin.value() * 1000)
                                                                    monitor_dialog.exec()
                                                                
                                                                return show_rebuild_monitor

                                                            monitor_button.clicked.connect(create_monitor_handler(drive))
                                                            button_widget = QTreeWidgetItem(drive_item)
                                                            tree_widget.setItemWidget(button_widget, 2, monitor_button)

                        elif section_name == "NIC 정보":
                            if 'NetworkAdapters' in info_source:
                                sorted_adapters = sorted(info_source['NetworkAdapters'], key=lambda x: get_nic_order(x.get('Id', '')))
                                for adapter in sorted_adapters:
                                    adapter_item = QTreeWidgetItem(section_item, [f"NIC 어댑터: {adapter.get('Id', 'N/A')}"])
                                    
                                    # NIC 기본 정보
                                    for key, value in nic_settings.items():
                                        item = QTreeWidgetItem(adapter_item)
                                        item.setText(0, key)
                                        item.setText(1, value)
                                        if key == "상태":
                                            status = adapter.get('Status', {})
                                            health = status.get('Health', 'N/A')
                                            item.setText(2, health)
                                            if health == 'OK':
                                                item.setForeground(2, QColor('green'))
                                        else:
                                            item.setText(2, str(adapter.get(value, 'N/A')))

                                    # 컨트롤러 정보
                                    for controller in adapter.get('Controllers', []):
                                        controller_item = QTreeWidgetItem(adapter_item, ["컨트롤러 정보"])
                                        is_virtualization_supported = controller.get('ControllerCapabilities', {}).get(
                                            'VirtualizationOffload', {}).get('SRIOV', {}).get('SRIOVVEPACapable', False)

                                        for key, value in controller_settings.items():
                                            item = QTreeWidgetItem(controller_item)
                                            item.setText(0, key)
                                            item.setText(1, value)
                                            if key == "가상화 지원":
                                                item.setText(2, "가상화 지원 카드" if is_virtualization_supported else "가상화 미지원 카드")
                                            else:
                                                item.setText(2, str(controller.get(value, 'N/A')))

                                    # 포트 정보
                                    for port in adapter.get('NetworkPorts', []):
                                        port_id = port.get('Id', 'N/A')
                                        device_function_id = f"{port_id}-1"
                                        port_item = QTreeWidgetItem(adapter_item, [f"포트: {port_id}"])

                                        # 가상화 모드 정보
                                        virtualization_mode = 'N/A'
                                        if is_virtualization_supported:
                                            try:
                                                device_function_info = requests.get(
                                                    f"{server_manager.endpoints.base_url}/redfish/v1/Chassis/System.Embedded.1/NetworkAdapters/{adapter.get('Id')}/NetworkDeviceFunctions/{device_function_id}/Oem/Dell/DellNetworkAttributes/{device_function_id}",
                                                    auth=server_manager.auth,
                                                    verify=False
                                                ).json()
                                                virtualization_mode = device_function_info.get('Attributes', {}).get('VirtualizationMode', 'N/A')
                                            except:
                                                pass

                                        # 포트 설정 표시
                                        for key, value in port_settings.items():
                                            item = QTreeWidgetItem(port_item)
                                            item.setText(0, key)
                                            item.setText(1, value)
                                            if key == "현재 속도":
                                                item.setText(2, f"{port.get(value, 'N/A')} Mbps")
                                            elif key == "MAC 주소":
                                                addresses = port.get(value, ['N/A'])
                                                item.setText(2, addresses[0] if addresses else 'N/A')
                                            elif key == "링크 상태":
                                                status = port.get(value, 'N/A')
                                                item.setText(2, status)
                                                if status == 'Up':
                                                    item.setForeground(2, QColor('green'))
                                                elif status == 'Down':
                                                    item.setForeground(2, QColor('red'))
                                            else:
                                                item.setText(2, str(port.get(value, 'N/A')))

                                        if is_virtualization_supported:
                                            virt_item = QTreeWidgetItem(port_item)
                                            virt_item.setText(0, "가상화 모드")
                                            virt_item.setText(1, "VirtualizationMode")
                                            virt_item.setText(2, virtualization_mode)

                                        # 트랜시버 정보
                                        transceiver = port.get('Oem', {}).get('Dell', {}).get('DellNetworkTransceiver', {})
                                        if transceiver and data.get('license') and 'enterprise' in data['license']['type'].lower():
                                            transceiver_item = QTreeWidgetItem(port_item, ["트랜시버 정보"])
                                            
                                            for key, value in transceiver_settings.items():
                                                item = QTreeWidgetItem(transceiver_item)
                                                item.setText(0, key)
                                                item.setText(1, value)
                                                item.setText(2, str(transceiver.get(value, 'N/A')))

                                            # 광 레벨 정보
                                            if 'datacenter' in data['license']['type'].lower():
                                                optical_data = transceiver.get('OpticalData', {})
                                                if optical_data:
                                                    optical_item = QTreeWidgetItem(transceiver_item, ["광 레벨 정보"])
                                                    
                                                    for key, value in optical_settings.items():
                                                        item = QTreeWidgetItem(optical_item)
                                                        item.setText(0, key)
                                                        item.setText(1, value)
                                                        if value in optical_data:
                                                            if value == "Temperature":
                                                                display_value = f"{optical_data[value]} °C"
                                                            elif value == "SupplyVoltage":
                                                                display_value = f"{optical_data[value]} V"
                                                            elif value in ["TxPower", "RxPower"]:
                                                                display_value = f"{optical_data[value]} dBm"
                                                            elif value == "LaserBiasCurrent":
                                                                display_value = f"{optical_data[value]} mA"
                                                            else:
                                                                display_value = str(optical_data[value])
                                                        else:
                                                            display_value = 'N/A'
                                                        item.setText(2, display_value)
                        
                        elif section_name == "PSU 정보":
                            # PSU 정보 추가
                            if info_source and 'PowerSupplies' in info_source:
                                for psu in info_source['PowerSupplies']:
                                    psu_id = f"PSU {psu.get('MemberId', 'N/A')}"
                                    psu_item = QTreeWidgetItem(section_item, [psu_id])
                                    
                                    for key, value in settings_dict.items():
                                        item = QTreeWidgetItem(psu_item)
                                        item.setText(0, key)
                                        item.setText(1, value)
                                        
                                        # 특별한 형식이 필요한 필드들 처리
                                        if key == "용량":
                                            item.setText(2, f"{psu.get(value, 'N/A')}W")
                                        elif key == "상태":
                                            status = psu.get('Status', {})
                                            health = status.get('Health', 'N/A')
                                            item.setText(2, str(health))
                                            if health == "OK":
                                                item.setForeground(2, QColor('green'))
                                            elif health == "Critical":
                                                item.setForeground(2, QColor('red'))
                                        else:
                                            item.setText(2, str(psu.get(value, 'N/A')))

                        elif section_name == "iDRAC MAC 주소 정보":
                            # iDRAC MAC 주소 정보 추가
                            if 'Attributes' in info_source:
                                mac_address = info_source.get('Attributes', {}).get('CurrentNIC.1.MACAddress', 'N/A')
                                item = QTreeWidgetItem(section_item)
                                item.setText(0, "MAC 주소")
                                item.setText(1, "CurrentNIC.1.MACAddress")
                                item.setText(2, str(mac_address))

                tree_widget.collapseAll()
                progress_dialog.setValue(100)

                def show_status_dialog():
                    progress_dialog.close()
                    status_dialog.exec()

                QTimer.singleShot(500, show_status_dialog)

    except Exception as e:
        progress_dialog.close()
        logger.error(f"시스템 상태 정보 조회/표시 실패: {str(e)}")
        logger.exception(e)
        error_dialog = ErrorDialog(
            "시스템 상태 조회 오류",
            "시스템 상태 정보를 조회하는 중 오류가 발생했습니다.",
            str(e),
            parent
        )
        error_dialog.exec()
                
def show_system_info(parent):
    """BIOS 정보 / iDRAC 정보 / 네트워크 설정 정보를 통합하여 테이블 형식으로 반환"""
    logger.debug("시스템 정보 조회 시도")
    
    main_window = parent.window()
    if not hasattr(main_window, 'server_section'):
        logger.warning("서버 섹션을 찾을 수 없음")
        error_dialog = ErrorDialog(
            "서버 연결 오류",
            "서버가 연결되어 있지 않습니다.",
            "서버를 먼저 연결한 후 다시 시도해주세요.",
            parent
        )
        error_dialog.exec()
        return
    
    server_info = main_window.server_section.current_server_info
    if not server_info:
        logger.warning("서버 정보가 없음")
        error_dialog = ErrorDialog(
            "서버 연결 오류",
            "서버 정보를 찾을 수 없습니다.",
            "서버를 선택한 후 다시 시도해주세요.",
            parent
        )
        error_dialog.exec()
        return
    
    # 진행률 다이얼로그 생성
    progress_dialog = QProgressDialog("시스템 정보 로딩 중...", None, 0, 100, parent)
    progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
    progress_dialog.setWindowTitle("데이터 로드")
    progress_dialog.setAutoClose(True)
    progress_dialog.setMinimumDuration(0)
    
    status_dialog = QDialog(parent)
    status_dialog.setWindowTitle("System Information")
    status_dialog.resize(800, 600)
    
    layout = QVBoxLayout()
    expand_collapse_button = QPushButton("전체 펼치기")
    button_layout = QHBoxLayout()
    button_layout.addWidget(expand_collapse_button)
    layout.addLayout(button_layout)
    tree_widget = QTreeWidget()
    tree_widget.setHeaderLabels(["Settings", "Dell Attribute name", "value"])
    tree_widget.setColumnWidth(0, 250)
    tree_widget.setColumnWidth(1, 250)
    layout.addWidget(tree_widget)
    status_dialog.setLayout(layout)
    
    try:
        def toggle_all_sections():
            if expand_collapse_button.text() == "전체 펼치기":
                tree_widget.expandAll()
                expand_collapse_button.setText("전체 접기")
            else:
                tree_widget.collapseAll()
                expand_collapse_button.setText("전체 펼치기")
        
        expand_collapse_button.clicked.connect(toggle_all_sections)
        
        # 진행률 다이얼로그 생성
        main_window = parent.window()
        if hasattr(main_window, 'server_section'):
            server_info = main_window.server_section.current_server_info
            if server_info:
                server_manager = DellServerManager(
                    ip=server_info['IP'],
                    port=server_info['PORT'],
                    auth=(server_info['USERNAME'], server_info['PASSWORD'])
                )
                progress_dialog.show()
                
                # 데이터 로드
                bios_info = server_manager.fetch_bios_info()
                idrac_info = server_manager.fetch_idrac_info()
                idrac_pwr_info = server_manager.fetch_idrac_pwr_info()
                nic_data = server_manager.fetch_network_adapters_info()

                # 섹션별 설정 딕셔너리 정의
                system_info_settings = {
                    'System Model Name': 'SystemModelName',
                    '제조사': 'SystemManufacturer',
                    'BIOS 버전': 'SystemBiosVersion',
                    'System Service Tag': 'SystemServiceTag'
                }
                
                processor_settings = {
                    'Logical Processor': 'LogicalProc',
                    'Virtualization Technology': 'ProcVirtualization',
                    'Sub NUMA Cluster': 'SubNumaCluster',
                    'x2APIC Mode': 'ProcX2Apic'
                }
                
                boot_settings = {
                    'Boot Mode': 'BootMode'
                }
                
                network_settings = {
                    'PXE Device1': 'PxeDev1EnDis',
                    'NIC ID': 'PxeDev1Interface',
                    'PXE Device2': 'PxeDev2EnDis',
                    'NIC ID': 'PxeDev2Interface',
                    'PXE Device3': 'PxeDev3EnDis',
                    'NIC ID': 'PxeDev3Interface',
                    'PXE Device4': 'PxeDev4EnDis',
                    'NIC ID': 'PxeDev4Interface'
                }
                
                integrated_devices = {
                    'SR-IOV Global Enable': 'SriovGlobalEnable',
                    'OS Watchdog Timer': 'OsWatchdogTimer'
                }

                system_profile_settings = {
                    'System Profile': 'SysProfile',
                    'CPU Power Management': 'ProcPwrPerf',
                    'Memory Frequency': 'ProcCStates',
                    'C1E': 'ProcC1E',
                    'Turbo Boost': 'ProcTurboMode',
                    'Energy Efficiency Policy': 'EnergyPerformanceBias',
                    'Memory Patrol Scrub': 'MemPatrolScrub',
                    
                }

                # AMD CPU 전용 설정
                amd_specific_settings = {
                    'Determinism Slider': 'DeterminismSlider',
                    'Power Profile Select': 'PowerProfileSelect',
                    'PCIE Speed PMM Control': 'PCIESpeedPMMControl',
                    'EQ Bypass To Highest Rate': 'EQBypassToHighestRate',
                    'DF PState Frequency Optimizer': 'DFPstateFrequencyOptimizer',
                    'DF PState Latency Optimizer': 'DFPstateLatencyOptimizer',
                    'DF CState': 'DfCState',
                    'Host System Management Port': 'HSMPSupport',
                    'Boost FMax': 'BoostFMax',
                    'Algorithm Performance Boost Disable': 'ApbDis',
                }

                miscellaneous_settings = {
                    'F1/F2 Prompt On Error': 'ErrPrompt'
                }

                idrac_settings = {
                    'Mac Address': 'NIC.1.MACAddress',
                    'Enable IPv4': 'IPv4.1.Enable',
                    'Enable DHCP': 'IPv4.1.DHCPEnable',
                    'Static IP Address': 'IPv4Static.1.Address',
                    'Static Gateway': 'IPv4Static.1.Gateway',
                    'Static Subnet Mask': 'IPv4Static.1.Netmask',
                    'Enable IPMI Over LAN': 'IPMILan.1.Enable',
                    'Enable VLAN ID': 'NIC.1.VLanEnable'
                }

                power_settings = {
                    'Redundancy Policy': 'ServerPwr.1.PSRedPolicy',
                    'Enable Hot Spare': 'ServerPwr.1.PSRapidOn'
                }

                nic_configuration_settings = {
                    'NIC ID': 'Id',
                    '가상화 모드': 'VirtualizationMode'
                }

                # 섹션별 트리 아이템 생성
                sections = [
                    ("System Information", bios_info, system_info_settings),
                    ("Processor Settings", bios_info, processor_settings),
                    ("Boot Settings", bios_info, boot_settings),
                    ("Network Settings", bios_info, network_settings),
                    ("Integrated Devices", bios_info, integrated_devices),
                    ("System Profile Settings", bios_info, system_profile_settings),
                    ("Miscellaneous Settings", bios_info, miscellaneous_settings),
                    ("iDRAC Settings", idrac_info, idrac_settings),
                    ("Power Configuration", idrac_pwr_info, power_settings),
                    ("NIC Configuration", nic_data, nic_configuration_settings)
                ]

                for section_name, info_source, settings_dict in sections:
                    icon_base64 = get_icon_base64(section_name)
                    section_item = QTreeWidgetItem(tree_widget)
                    section_item.setText(0, section_name)
                    section_item.setIcon(0, QIcon(QPixmap.fromImage(QImage.fromData(base64.b64decode(icon_base64)))))
                    
                    if section_name == "NIC Configuration" and info_source and 'NetworkAdapters' in info_source:
                        for adapter in info_source['NetworkAdapters']:
                            for func in adapter.get('NetworkDeviceFunctions', []):
                                if func_id := func.get('Id'):
                                    virt_info = server_manager.fetch_network_virtualization_info(
                                        adapter.get('Id'), func_id)
                                    if virt_info and 'Attributes' in virt_info:
                                        child_item = QTreeWidgetItem(section_item)
                                        child_item.setText(0, f"가상화 모드: {func_id}")
                                        child_item.setText(1, "VirtualizationMode")
                                        
                                        virt_mode = virt_info['Attributes'].get('VirtualizationMode', 'N/A')
                                        child_item.setText(2, virt_mode)
                                        
                                        # 툴팁 추가
                                        tooltip_text = get_tooltip('VirtualizationMode')
                                        child_item.setToolTip(0, tooltip_text)
                                        child_item.setToolTip(1, tooltip_text)
                                        child_item.setToolTip(2, tooltip_text)
                    
                    elif info_source and 'Attributes' in info_source:
                        # CPU 종류 확인
                        cpu_brand = info_source['Attributes'].get('Proc1Brand', '')
                        is_amd_cpu = 'AMD' in cpu_brand

                        # AMD CPU인 경우에만 추가 설정 병합
                        if is_amd_cpu:
                            settings_dict.update(amd_specific_settings)

                        for display_name, attr_name in settings_dict.items():
                            value = info_source['Attributes'].get(attr_name, 'N/A')
                            
                            child_item = QTreeWidgetItem(section_item)
                            child_item.setText(0, display_name)
                            child_item.setText(1, attr_name)
                            child_item.setText(2, str(value))
                            
                            # 툴팁 추가
                            tooltip_text = get_tooltip(attr_name)
                            child_item.setToolTip(0, tooltip_text)
                            child_item.setToolTip(1, tooltip_text)
                            child_item.setToolTip(2, tooltip_text)
                            
                            # Enabled/Disabled 값에 따른 색상 설정
                            if value == 'Enabled':
                                child_item.setForeground(2, QColor('green'))
                            elif value == 'Disabled':
                                child_item.setForeground(2, QColor('red'))

                tree_widget.collapseAll()
                progress_dialog.setValue(100)
                
                def show_status_dialog():
                    progress_dialog.close()
                    status_dialog.exec()
                
                QTimer.singleShot(500, show_status_dialog)
                
    except Exception as e:
        progress_dialog.close()
        logger.error(f"시스템 정보 조회/표시 실패: {str(e)}")
        logger.exception(e)
        error_dialog = ErrorDialog(
            "시스템 정보 조회 오류",
            "시스템 정보를 조회하는 중 오류가 발생했습니다.",
            str(e),
            parent
        )
        error_dialog.exec()

def get_theme_color(parent):
    """현재 테마의 텍스트 색상 반환"""
    palette = parent.palette()
    return palette.text().color().name()

# NIC 정렬을 위한 순서 정의
def get_nic_order(component_id):
    """기본 타입 순서"""
    if 'NIC.Embedded.' in component_id:
        order = 0
    elif 'NIC.Integrated.' in component_id:
        order = 1
    elif 'NIC.Slot.' in component_id:
        order = 2
    else:
        return (3, 0, 0)  # 기타 항목
    
    """숫자 부분 추출 및 정렬을 위한 처리"""
    try:
        # NIC.Slot.1-2-1 또는 NIC.Embedded.1-1-1 등에서 숫자 추출
        parts = component_id.split('.')[-1].split('-')
        primary = int(parts[0])
        secondary = int(parts[1]) if len(parts) > 1 else 0
        tertiary = int(parts[2]) if len(parts) > 2 else 0
    except (ValueError, IndexError):
        primary = 0
        secondary = 0
        tertiary = 0
        
    return (order, primary, secondary, tertiary)

def get_icon_base64(section_name):
    """섹션 이름에 따라 적절한 아이콘의 Base64 인코딩 문자열 반환"""
    icon_map = {
        "System Information": "system_icon.png",
        "Processor Settings": "cpu_icon.png",
        "Boot Settings": "boot_icon.png",
        "Network Settings": "network_icon.png",
        "Integrated Devices": "device_icon.png",
        "System Profile Settings": "profile_icon.png",
        "Miscellaneous Settings": "misc_icon.png",
        "iDRAC Settings": "idrac_icon.png",
        "Power Configuration": "power_icon.png",
        "NIC Configuration": "nic_icon.png"
    }
    
    # 현재 스크립트의 디렉토리를 기준으로 상대 경로 설정
    current_dir = Path(os.path.dirname(os.path.abspath(__file__)))
    icon_dir = current_dir.parent.parent / "icon"
    icon_path = icon_dir / icon_map.get(section_name, "default_icon.png")
    
    try:
        with open(icon_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode("utf-8")
    except FileNotFoundError:
        print(f"아이콘 파일을 찾을 수 없습니다: {icon_path}")
        return ""  # 아이콘을 찾지 못한 경우 빈 문자열 반환

def get_section_settings(section_name, info_source):
    """섹션 이름에 따라 해당 섹션의 설정 딕셔너리 반환"""
    # 이미 정의된 섹션별 설정 딕셔너리 사용
    return globals().get(f"{section_name.lower().replace(' ', '_')}_settings", {})

def get_attribute_value(info_source, attr_name):
    """정보 소스에서 특정 속성의 값을 가져옴"""
    if isinstance(info_source, dict) and 'Attributes' in info_source:
        return info_source['Attributes'].get(attr_name, 'N/A')
    return 'N/A'

def get_value_style(value):
    """값에 따라 적절한 스타일 반환"""
    if value == 'Enabled':
        return "color: green;"
    elif value == 'Disabled':
        return "color: red;"
    return ""

def get_tooltip(attr_name):
    """속성 이름에 따른 툴팁 텍스트 반환"""
    tooltips = {
        # System Information
        "SystemModelName": "서버 모델 이름",
        "SystemManufacturer": "서버 제조사 정보",
        "SystemBiosVersion": "현재 설치된 BIOS 버전",
        "SystemServiceTag": "서버의 고유 식별 번호",
        
        # Processor Settings
        "LogicalProc": "논리 프로세서 활성화 여부",
        "ProcVirtualization": "프로세서 가상화 기술 활성화 여부",
        "SubNumaCluster": "NUMA 노드 내의 프로세서 코어 그룹 설정",
        "ProcX2Apic": "프로세서의 x2APIC 모드 활성화 여부",
        
        # Boot Settings
        "BootMode": "시스템 부팅 모드 (UEFI 또는 BIOS)",
        
        # Network Settings
        "PxeDev1EnDis": "첫 번째 PXE 장치 활성화/비활성화",
        "PxeDev1Interface": "첫 번째 PXE 장치의 네트워크 인터페이스",
        "PxeDev2EnDis": "두 번째 PXE 장치 활성화/비활성화",
        "PxeDev2Interface": "두 번째 PXE 장치의 네트워크 인터페이스",
        "PxeDev3EnDis": "세 번째 PXE 장치 활성화/비활성화",
        "PxeDev3Interface": "세 번째 PXE 장치의 네트워크 인터페이스",
        "PxeDev4EnDis": "네 번째 PXE 장치 활성화/비활성화",
        "PxeDev4Interface": "네 번째 PXE 장치의 네트워크 인터페이스",
        
        # Integrated Devices
        "SriovGlobalEnable": "SR-IOV 전역 활성화 여부",
        "OsWatchdogTimer": "운영 체제 감시 타이머 활성화 여부",
        
        # System Profile Settings
        "SysProfile": "시스템 프로필 설정",
        "ProcPwrPerf": "CPU 전원 관리 설정",
        "ProcCStates": "프로세서 C-States 설정",
        "ProcC1E": "프로세서 C1E 상태 활성화 여부",
        "ProcTurboMode": "프로세서 터보 부스트 모드 설정",
        "EnergyPerformanceBias": "에너지 효율성 정책 설정",
        "MemPatrolScrub": "메모리 패트롤 스크럽 기능 설정",
        
        # Miscellaneous Settings
        "ErrPrompt": "오류 발생 시 F1/F2 프롬프트 표시 여부",
        
        # iDRAC Settings
        "NIC.1.MACAddress": "iDRAC 네트워크 인터페이스의 MAC 주소",
        "IPv4.1.Enable": "IPv4 프로토콜 활성화 여부",
        "IPv4.1.DHCPEnable": "DHCP 사용 여부",
        "IPv4Static.1.Address": "고정 IP 주소 설정",
        "IPv4Static.1.Gateway": "고정 게이트웨이 주소",
        "IPv4Static.1.Netmask": "고정 서브넷 마스크",
        "IPMILan.1.Enable": "IPMI over LAN 활성화 여부",
        "NIC.1.VLanEnable": "VLAN 기능 활성화 여부",
        
        # Power Configuration
        "ServerPwr.1.PSRedPolicy": "전원 공급 장치 중복성 정책",
        "ServerPwr.1.PSRapidOn": "전원 공급 장치 핫 스페어 기능 활성화 여부",
        
        # NIC Configuration
        "VirtualizationMode": "NIC 가상화 모드 설정"
    }
    return tooltips.get(attr_name, "설정에 대한 추가 정보")

def show_firmware_info(parent):
    """펌웨어 정보 조회"""
    logger.debug("펌웨어 정보 조회 시도")
    
    main_window = parent.window()
    if not hasattr(main_window, 'server_section'):
        logger.warning("서버 섹션을 찾을 수 없음")
        error_dialog = ErrorDialog(
            "서버 연결 오류",
            "서버가 연결되어 있지 않습니다.",
            "서버를 먼저 연결한 후 다시 시도해주세요.",
            parent
        )
        error_dialog.exec()
        return
    
    server_info = main_window.server_section.current_server_info
    if not server_info:
        logger.warning("서버 정보가 없음")
        error_dialog = ErrorDialog(
            "서버 연결 오류",
            "서버 정보를 찾을 수 없습니다.",
            "서버를 선택한 후 다시 시도해주세요.",
            parent
        )
        error_dialog.exec()
        return
    
    progress_dialog = QProgressDialog("펌웨어 정보 로딩 중...", None, 0, 100, parent)
    progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
    progress_dialog.setWindowTitle("데이터 로드")
    progress_dialog.setAutoClose(True)
    progress_dialog.setMinimumDuration(0)

    main_window = parent.window()
    if hasattr(main_window, 'server_section'):
        try:
            server_info = main_window.server_section.current_server_info
            if server_info:
                server_manager = DellServerManager(
                    ip=server_info['IP'],
                    port=server_info['PORT'],
                    auth=(server_info['USERNAME'], server_info['PASSWORD'])
                )
                
                progress_dialog.show()
                progress_dialog.setValue(30)
                
                firmware_data = server_manager.fetch_firmware_inventory()
                
                if firmware_data:
                    status_dialog = QDialog(parent)
                    status_dialog.setWindowTitle("펌웨어 정보")
                    status_dialog.resize(800, 600)
                    layout = QVBoxLayout()

                    expand_collapse_button = QPushButton("전체 펼치기")
                    button_layout = QHBoxLayout()
                    button_layout.addWidget(expand_collapse_button)
                    layout.addLayout(button_layout)

                    tree_widget = QTreeWidget()
                    tree_widget.setHeaderLabels(["구성 요소", "속성", "값"])
                    tree_widget.setColumnWidth(0, 400)
                    tree_widget.setColumnWidth(1, 250)
                    tree_widget.setColumnWidth(2, 200)
                    layout.addWidget(tree_widget)
                    
                    status_dialog.setLayout(layout)

                    def toggle_all_sections():
                        if expand_collapse_button.text() == "전체 펼치기":
                            tree_widget.expandAll()
                            expand_collapse_button.setText("전체 접기")
                        else:
                            tree_widget.collapseAll()
                            expand_collapse_button.setText("전체 펼치기")
                    
                    expand_collapse_button.clicked.connect(toggle_all_sections)

                    progress_dialog.setValue(50)
                    
                    firmware_groups = {
                        'BIOS': [],
                        'iDRAC': [],
                        'RAID': [],
                        'NIC': [],
                        'Others': []
                    }

                    total_components = len(firmware_data.get('Members', []))
                    for idx, member in enumerate(firmware_data.get('Members', [])):
                        member_uri = member.get('@odata.id')
                        if member_uri:
                            component_id = member_uri.split('/')[-1]
                            component_info = server_manager.fetch_firmware_component(component_id)
                            
                            if 'BIOS' in component_id:
                                firmware_groups['BIOS'].append(component_info)
                            elif 'iDRAC' in component_id:
                                firmware_groups['iDRAC'].append(component_info)
                            elif 'PERC' in component_info.get('Name', ''):
                                firmware_groups['RAID'].append(component_info)
                            elif 'NIC' in component_id:
                                firmware_groups['NIC'].append(component_info)
                            else:
                                firmware_groups['Others'].append(component_info)
                                
                            progress_dialog.setValue(50 + (40 * idx // total_components))

                    for group_name, components in firmware_groups.items():
                        if components:
                            if group_name == 'NIC':
                                # 중복 제거를 위한 딕셔너리
                                unique_nics = {}
                                for component in components:
                                    if 'Installed' in component.get('Id', ''):
                                        name = component.get('Name', 'N/A')
                                        # MAC 주소 제거 및 이름 정리
                                        if ' - ' in name:
                                            name = name.split(' - ')[0]  # MAC 주소 부분 제거
                                        
                                        version = component.get('Version', 'N/A')
                                        install_date = component.get('Oem', {}).get('Dell', {}).get(
                                            'DellSoftwareInventory', {}).get('InstallationDate', 'N/A')
                                        
                                        # 중복 체크 및 최신 버전 유지
                                        if name not in unique_nics or (
                                            version >= unique_nics[name]['version'] and 
                                            install_date > unique_nics[name]['install_date']
                                        ):
                                            unique_nics[name] = {
                                                'component': component,
                                                'version': version,
                                                'install_date': install_date
                                            }
                                
                                # 정렬된 고유 NIC 컴포넌트 추가
                                group_item = QTreeWidgetItem(tree_widget, [f"{group_name} 펌웨어"])
                                sorted_nics = sorted(unique_nics.items(), 
                                                key=lambda x: get_nic_order(x[1]['component'].get('Id', '')))
                                
                                for name, nic_info in sorted_nics:
                                    component = nic_info['component']
                                    component_item = QTreeWidgetItem(group_item, [name])  # MAC 주소가 제거된 이름 사용
                                    
                                    # ID 정보 추가 (필요한 경우)
                                    component_id = component.get('Id', '')
                                    if '__' in component_id:
                                        nic_id = component_id.split('__')[1]
                                        QTreeWidgetItem(component_item, ["ID", "", nic_id])
                                    
                                    QTreeWidgetItem(component_item, ["버전", "", nic_info['version']])
                                    
                                    # 날짜 형식 처리
                                    install_date = nic_info['install_date']
                                    if install_date and install_date != 'N/A':
                                        date_parts = install_date.split('T')
                                        if len(date_parts) == 2:
                                            install_date = f"{date_parts[0]} {date_parts[1][:5]}"
                                    QTreeWidgetItem(component_item, ["설치 날짜", "", install_date])
                            
                            else:
                                # 다른 그룹들은 기존 처리 방식 유지
                                group_item = QTreeWidgetItem(tree_widget, [f"{group_name} 펌웨어"])
                                for component in components:
                                    if 'Installed' in component.get('Id', ''):
                                        component_item = QTreeWidgetItem(group_item, [component.get('Name', 'N/A')])
                                        QTreeWidgetItem(component_item, ["버전", "", component.get('Version', 'N/A')])
                                        
                                        dell_info = component.get('Oem', {}).get('Dell', {}).get('DellSoftwareInventory', {})
                                        if dell_info:
                                            install_date = dell_info.get('InstallationDate', 'N/A')
                                            if install_date and install_date != 'N/A':
                                                date_parts = install_date.split('T')
                                                if len(date_parts) == 2:
                                                    install_date = f"{date_parts[0]} {date_parts[1][:5]}"
                                            QTreeWidgetItem(component_item, ["설치 날짜", "", install_date])

                    tree_widget.collapseAll()
                    
                    def show_status_dialog():
                        progress_dialog.close()
                        status_dialog.exec()
                    
                    progress_dialog.setValue(100)
                    QTimer.singleShot(500, show_status_dialog)
                    
                    logger.debug("펌웨어 정보 업데이트 완료")
                
        except Exception as e:
            progress_dialog.close()
            logger.error(f"펌웨어 정보 조회/표시 실패: {str(e)}")
            logger.exception(e)
            error_dialog = ErrorDialog(
                "펌웨어 정보 조회 오류",
                "펌웨어 정보를 조회하는 중 오류가 발생했습니다.",
                str(e),
                parent
            )
            error_dialog.exec()

def sort_drives(drive_info):
    def sort_key(drive):
        # Disk.Bay.숫자:Enclosure... 형식에서 숫자만 추출하여 정렬
        match = re.search(r"Disk\.Bay\.(\d+)", drive.get('Id', ''))
        if match:
            return int(match.group(1))
        return float('inf')

    return sorted(drive_info, key=sort_key)

def show_log_popup(parent, log_type):
    logger.debug(f"{log_type.upper()} 로그 팝업창 열기 시도")
    
    main_window = parent.window()
    if not hasattr(main_window, 'server_section'):
        logger.warning("서버 섹션을 찾을 수 없음")
        error_dialog = ErrorDialog(
            "서버 연결 오류",
            "서버가 연결되어 있지 않습니다.",
            "서버를 먼저 연결한 후 다시 시도해주세요.",
            parent
        )
        error_dialog.exec()
        return
    
    server_info = main_window.server_section.current_server_info
    if not server_info:
        logger.warning("서버 정보가 없음")
        error_dialog = ErrorDialog(
            "서버 연결 오류",
            "서버 정보를 찾을 수 없습니다.",
            "서버를 선택한 후 다시 시도해주세요.",
            parent
        )
        error_dialog.exec()
        return
    
    progress_dialog = QProgressDialog(f"{log_type.upper()} 로그 로딩 중...", None, 0, 100, parent)
    progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
    progress_dialog.setWindowTitle("데이터 로드")
    progress_dialog.setAutoClose(True)
    progress_dialog.setMinimumDuration(0)
    
    try:
        server_manager = DellServerManager(
            ip=server_info['IP'],
            port=server_info['PORT'],
            auth=(server_info['USERNAME'], server_info['PASSWORD'])
        )
        
        def update_progress(progress):
            progress_dialog.setLabelText(f"{log_type.upper()} 로그 로드 중... {int(progress)}%")
            progress_dialog.setValue(int(progress))
        
        progress_dialog.show()
        log_entries = server_manager.fetch_log_entries(log_type, progress_callback=update_progress)
        
        if log_entries:
            popup = SystemEventPopup(parent)
            popup.update_events(log_entries)
            
            def show_popup():
                progress_dialog.close()
                popup.exec()
            
            QTimer.singleShot(500, show_popup)
            logger.debug(f"{log_type.upper()} 로그 데이터 업데이트: {len(log_entries.get('Members', []))}개 항목")
            
    except Exception as e:
        progress_dialog.close()
        logger.error(f"{log_type.upper()} 로그 데이터 조회/표시 실패: {str(e)}")
        logger.exception(e)
        error_dialog = ErrorDialog(
            f"{log_type.upper()} 로그 조회 오류",
            "로그 데이터를 조회하는 중 오류가 발생했습니다.",
            str(e),
            parent
        )
        error_dialog.exec()

def show_sel_log_popup(parent):
    show_log_popup(parent, 'sel')

def show_lc_log_popup(parent):
    show_log_popup(parent, 'lc')

def update_all_status():
    """모든 시스템 상태 정보 업데이트"""
    try:
        main_window = get_main_window()
        if not main_window or not hasattr(main_window, 'server_section'):
            return
            
        server_info = main_window.server_section.current_server_info
        if not server_info:
            return
            
        server_manager = main_window.server_section.server_manager
        if not server_manager:
            return
            
        # CPU 정보 업데이트
        cpu_info = server_manager.fetch_processors_info()
        if cpu_info:
            # CPU 상태 업데이트 로직
            pass
            
        # 메모리 정보 업데이트
        memory_info = server_manager.fetch_memory_info()
        if memory_info:
            # 메모리 상태 업데이트 로직
            pass
            
        # 스토리지 정보 업데이트
        storage_info = server_manager.fetch_storage_info()
        if storage_info:
            # 스토리지 상태 업데이트 로직
            pass
            
        # 전원 정보 업데이트
        power_info = server_manager.fetch_psu_info()
        if power_info:
            # 전원 상태 업데이트 로직
            pass
            
        logger.debug("시스템 상태 정보 업데이트 완료")
        
    except Exception as e:
        logger.error(f"시스템 상태 정보 업데이트 실패: {str(e)}")
