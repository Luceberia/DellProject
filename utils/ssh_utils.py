import subprocess
import platform
from config.system.log_config import setup_logging

logger = setup_logging()

def setup_ssh_config():
    """SSH 설정을 초기화하고 iDRAC 서버에 대한 설정을 추가합니다."""
    try:
        import os
        from pathlib import Path
        
        # SSH 설정 디렉토리 및 파일 경로
        ssh_dir = Path.home() / '.ssh'
        config_file = ssh_dir / 'config'
        
        # .ssh 디렉토리가 없으면 생성
        if not ssh_dir.exists():
            ssh_dir.mkdir(mode=0o700)
        
        # 기존 설정 읽기
        config_content = ""
        if config_file.exists():
            with open(config_file, 'r') as f:
                config_content = f.read()
        
        # Dell iDRAC 설정이 없으면 추가
        configs_to_add = []
        
        if 'Host 169.254.*' not in config_content:
            configs_to_add.append("""
# Dell iDRAC 서버 설정
Host 169.254.*
    StrictHostKeyChecking no
    UserKnownHostsFile /dev/null
    LogLevel ERROR""")
            
        if 'Host 127.0.0.1' not in config_content:
            configs_to_add.append("""
# 로컬호스트 설정
Host 127.0.0.1
    StrictHostKeyChecking no
    UserKnownHostsFile /dev/null
    LogLevel ERROR""")
            
        if configs_to_add:
            # 설정 파일에 추가
            with open(config_file, 'a') as f:
                f.write('\n'.join(configs_to_add))
            
            # 권한 설정
            config_file.chmod(0o600)
            
            logger.info("SSH 설정이 추가되었습니다.")
    
    except Exception as e:
        logger.error(f"SSH 설정 초기화 실패: {str(e)}")
        raise

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