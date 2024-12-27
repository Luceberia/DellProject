import subprocess
import platform
from config.system.log_config import setup_logging

logger = setup_logging()

def open_ssh_terminal(host, username, key_path="~/.ssh/id_rsa", password=None, command=None):
    try:
        system = platform.system()
        if system == "Darwin":  # macOS
            if password:  # 패스워드가 제공된 경우
                applescript = f'''
                    tell application "Terminal"
                        if not (exists window 1) then
                            do script ""
                        end if
                        
                        # SSH 연결 명령어 실행
                        do script "ssh {username}@{host}" in window 1
                        delay 1
                        
                        # 패스워드 입력
                        do script "{password}" in window 1
                        
                        # 선택된 명령어가 있으면 입력 (실행은 하지 않음)
                        if "{command}" is not "" then
                            delay 2
                            do script "{command}" in window 1
                        end if
                        
                        activate
                    end tell
                '''
            else:  # SSH 키 사용
                applescript = f'''
                    tell application "Terminal"
                        if not (exists window 1) then
                            do script ""
                        end if
                        do script "ssh -i {key_path} {username}@{host}" in window 1
                        
                        # 선택된 명령어가 있으면 입력 (실행은 하지 않음)
                        if "{command}" is not "" then
                            delay 2
                            do script "{command}" in window 1
                        end if
                        
                        activate
                    end tell
                '''
            subprocess.run(['osascript', '-e', applescript])
            
    except Exception as e:
        logger.error(f"SSH 터미널 실행 실패: {str(e)}")
        raise