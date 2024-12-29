import os
import sys
import shutil
import zipfile
import subprocess
import tempfile
from PyQt6.QtWidgets import QApplication, QMessageBox, QProgressDialog
from PyQt6.QtCore import Qt
from config.system.log_config import setup_logging
import requests

logger = setup_logging()

def check_for_updates(current_version):
    try:
        api_url = "https://api.github.com/repos/Luceberia/DellProject/releases/latest"
        response = requests.get(api_url)
        if response.status_code == 200:
            latest_release = response.json()
            latest_version = latest_release['tag_name'].replace('v', '')
            
            # 버전 비교를 위해 튜플로 변환
            current = tuple(map(int, current_version.split('.')))
            latest = tuple(map(int, latest_version.split('.')))
            
            logger.debug(f"현재 버전: {current_version}, 최신 버전: {latest_version}")
            
            if latest > current:
                return latest_release
    except Exception as e:
        logger.error(f"업데이트 확인 중 오류 발생: {e}")
    return None

def get_app_version():
    try:
        bundle_path = os.path.abspath(os.path.join(os.path.dirname(sys.executable), '..', 'Info.plist'))
        with open(bundle_path, 'rb') as fp:
            pl = plistlib.load(fp)
            return pl.get('CFBundleShortVersionString', '0.0.0')
    except Exception as e:
        logger.error(f"버전 확인 중 오류: {e}")
        return '0.0.0'

def download_and_apply_update(download_url, progress_dialog):
    progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
    progress_dialog.show()
    logger.debug("업데이트 프로세스 시작")

    if not download_url:
        logger.error("다운로드 URL이 유효하지 않습니다")
        return False
        
    if not os.path.exists(sys.executable):
        logger.error("현재 실행 파일 경로를 찾을 수 없습니다")
        return False

    update_path = None
    try:
        # 현재 실행 중인 앱의 경로 확인
        current_app = os.path.abspath(sys.executable)
        if '.app' not in current_app:
            current_app = os.path.dirname(os.path.dirname(current_app))
            if os.path.exists(current_app + '.app'):
                current_app = current_app + '.app'
        elif 'Contents/MacOS' in current_app:
            current_app = os.path.dirname(os.path.dirname(os.path.dirname(current_app)))
            
        # macOS 앱 번들 경로 확인
        if not current_app.endswith('.app'):
            current_app = '/Applications/DellIDRACMonitor.app'
            
        logger.debug(f"현재 앱 경로: {current_app}")

        # 임시 디렉토리 생성
        update_path = os.path.join(tempfile.gettempdir(), 'DellIDRACMonitor_update')
        logger.debug(f"업데이트 임시 디렉토리 생성: {update_path}")
        os.makedirs(update_path, exist_ok=True)

        # 다운로드 처리
        zip_path = os.path.join(update_path, "update.zip")
        logger.debug(f"다운로드 파일 경로: {zip_path}")
        logger.debug(f"업데이트 파일 다운로드 시작: {download_url}")

        response = requests.get(download_url, stream=True)
        total_size = int(response.headers.get('content-length', 0))
        block_size = 8192
        progress = 0
        last_logged_percent = -1

        with open(zip_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=block_size):
                if chunk:
                    f.write(chunk)
                    progress += len(chunk)
                    percent = int(progress * 100 / total_size)
                    progress_dialog.setValue(percent)
                    
                    current_ten_percent = (percent // 10) * 10
                    if current_ten_percent > last_logged_percent:
                        logger.debug(f"다운로드 진행률: {current_ten_percent}%")
                        last_logged_percent = current_ten_percent
                    
                    QApplication.processEvents()

        # 압축 해제
        logger.debug("ZIP 파일 압축 해제 시작")
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            logger.debug(f"ZIP 파일 내용: {zip_ref.namelist()}")
            zip_ref.extractall(update_path)

        logger.debug(f"압축 해제된 디렉토리 내용: {os.listdir(update_path)}")

        # 새 앱 찾기
        app_name = "DellIDRACMonitor.app"
        new_app = None
        for root, dirs, files in os.walk(update_path):
            if app_name in dirs:
                new_app = os.path.join(root, app_name)
                logger.debug(f"앱 발견: {new_app}")
                break

        if not new_app:
            logger.error(f"새 버전 앱을 찾을 수 없음")
            return False

        # 업데이트 스크립트 생성
        update_script = os.path.join(update_path, "update.sh")
        script_content = f'''#!/bin/bash
        sleep 2
        osascript -e 'do shell script "rm -rf \\"{current_app}\\" && cp -R \\"{new_app}\\" \\"/Applications/\\" && chmod -R 755 \\"/Applications/DellIDRACMonitor.app\\" && xattr -rd com.apple.quarantine \\"/Applications/DellIDRACMonitor.app\\" && rm -rf \\"{update_path}\\"" with administrator privileges'
        open "/Applications/DellIDRACMonitor.app"
        '''

        with open(update_script, 'w') as f:
            f.write(script_content)
        os.chmod(update_script, 0o755)

        # 스크립트 실행
        try:
            subprocess.run(['/bin/bash', update_script], check=True)
            logger.debug("업데이트 스크립트 실행 완료")
            QMessageBox.information(None, "업데이트 알림", "업데이트가 완료되었습니다. 프로그램을 다시 시작합니다.")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"스크립트 실행 실패: {e}")
            QMessageBox.critical(None, "업데이트 오류", "업데이트 적용 중 오류가 발생했습니다.")
            return False

    except Exception as e:
        logger.error(f"업데이트 중 오류 발생: {str(e)}", exc_info=True)
        return False

    finally:
        if update_path and os.path.exists(update_path):
            logger.debug(f"임시 디렉토리 정리: {update_path}")
            try:
                shutil.rmtree(update_path)
            except Exception as cleanup_error:
                logger.error(f"임시 디렉토리 정리 중 오류: {str(cleanup_error)}")
