import os
from PyQt6.QtWidgets import QMessageBox, QDialog
from config.system.log_config import setup_logging
from ui.components.update_dialog import UpdateDialog
from version import __version__
from packaging.version import parse as parse_version
import requests
import webbrowser

logger = setup_logging()

def check_for_updates(current_version, parent=None):
    try:
        api_url = "https://api.github.com/repos/Luceberia/DellProject/releases/latest"
        response = requests.get(api_url, headers={'Accept': 'application/vnd.github.v3+json'})
        
        if response.status_code == 200:
            latest_release = response.json()
            latest_version = latest_release['tag_name'].replace('v', '')
            
            # 버전 비교 로직 추가
            if parse_version(latest_version) > parse_version(current_version):
                version_info = {
                    'current': current_version,
                    'latest': latest_version
                }
                
                logger.debug(f"현재 버전: {current_version}, 최신 버전: {latest_version}")
                dialog = UpdateDialog(parent, version_info, is_update=True)
                result = dialog.exec()
                
                if result == QDialog.DialogCode.Accepted:
                    logger.info("사용자가 업데이트를 승인했습니다.")
                    webbrowser.open(latest_release['html_url'])
            else:
                logger.info("최신 버전을 사용 중입니다.")
                QMessageBox.information(parent, "업데이트 확인", "현재 최신 버전을 사용 중입니다.")
                
    except Exception as e:
        logger.error(f"업데이트 확인 중 오류 발생: {e}")
        error_dialog = UpdateDialog(parent, {'current': str(e)}, is_update=False)
        error_dialog.exec()