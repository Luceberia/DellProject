import os
from PyQt6.QtWidgets import QMessageBox, QDialog
from config.system.log_config import setup_logging
from ui.components.update_dialog import UpdateDialog
from version import __version__
from packaging import version
import requests
import webbrowser

logger = setup_logging()

# 시스템의 기본 인증서 사용
os.environ['SSL_CERT_FILE'] = '/etc/ssl/cert.pem'
os.environ['REQUESTS_CA_BUNDLE'] = '/etc/ssl/cert.pem'

def check_for_updates(current_version, parent=None):
    try:
        api_url = "https://api.github.com/repos/Luceberia/DellProject/releases/latest"
        response = requests.get(api_url, headers={'Accept': 'application/vnd.github.v3+json'})
        
        if response.status_code == 200:
            latest_release = response.json()
            latest_version = latest_release['tag_name'].replace('v', '')
            
            version_info = {
                'current': current_version,
                'latest': latest_version
            }
            
            logger.debug(f"현재 버전: {current_version}, 최신 버전: {latest_version}")
            
            if version.parse(latest_version) > version.parse(current_version):
                dialog = UpdateDialog(parent, version_info, is_update=True)
            else:
                version_info['current'] = "현재 최신 버전을 사용 중입니다."
                dialog = UpdateDialog(parent, version_info, is_update=False)
            
            result = dialog.exec()
            if result == QDialog.DialogCode.Accepted and version.parse(latest_version) > version.parse(current_version):
                logger.info("사용자가 업데이트를 승인했습니다.")
                webbrowser.open(latest_release['html_url'])
                
    except Exception as e:
        logger.error(f"업데이트 확인 중 오류 발생: {e}")
        error_dialog = UpdateDialog(parent, {'current': str(e)}, is_update=False)
        error_dialog.exec()