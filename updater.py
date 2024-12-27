import requests
from version import __version__
from PyQt6.QtWidgets import QMessageBox, QProgressDialog
from PyQt6.QtCore import Qt

def check_for_updates():
    api_url = "https://api.github.com/repos/your_username/your_repo/releases/latest"
    response = requests.get(api_url)
    if response.status_code == 200:
        latest_release = response.json()
        latest_version = latest_release['tag_name']
        if latest_version > __version__:
            return latest_release
    return None

def download_and_apply_update(release_info):
    download_url = release_info['assets'][0]['browser_download_url']
    response = requests.get(download_url, stream=True)
    if response.status_code == 200:
        # 업데이트 파일 다운로드 및 적용 로직 구현
        return True
    return False

def update_application(parent):
    update_info = check_for_updates()
    if update_info:
        reply = QMessageBox.question(parent, '업데이트 가능', '새로운 버전이 있습니다. 업데이트하시겠습니까?',
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, 
                                     QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            progress = QProgressDialog("업데이트 중...", "취소", 0, 100, parent)
            progress.setWindowModality(Qt.WindowModality.WindowModal)
            progress.show()
            
            if download_and_apply_update(update_info):
                QMessageBox.information(parent, "업데이트 완료", "업데이트가 완료되었습니다. 프로그램을 재시작해주세요.")
                parent.close()
            else:
                QMessageBox.warning(parent, "업데이트 실패", "업데이트 중 오류가 발생했습니다.")
            
            progress.close()
