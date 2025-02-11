from typing import List, Dict, Optional
from config.system.log_config import setup_logging

logger = setup_logging()

class Cafe24Manager:
    def __init__(self):
        self.commands = {
            "option1": self._handle_option1,
            "option1_custom": self._handle_option1_custom,
            "option2": self._handle_option2,
            "option3": self._handle_option3,
            "option4": self._handle_option4,
        }
    
    def execute_command(self, selected_options: List[str], custom_inputs: Dict[str, str] = None) -> str:
        """선택된 옵션들에 대한 명령어를 실행합니다."""
        if custom_inputs is None:
            custom_inputs = {}
            
        commands = []
        for option in selected_options:
            if option in self.commands:
                command = self.commands[option](custom_inputs.get(option))
                if command:
                    commands.append(command)
        
        if not commands:
            return ""
        
        # 여러 명령어를 && 로 연결
        return " && ".join(commands)
    
    def _handle_option1(self, _=None) -> str:
        """패스워드를 기본값(calvin)으로 변경"""
        # 패스워드 정책을 먼저 변경한 후 패스워드 변경
        return "racadm set idrac.security.minimumpasswordscore 0 && racadm set iDRAC.Users.2.Password calvin"
    
    def _handle_option1_custom(self, password: str) -> str:
        """패스워드를 사용자가 입력한 값으로 변경"""
        if not password:
            logger.warning("패스워드가 입력되지 않았습니다.")
            return ""
        # 패스워드 정책을 먼저 변경한 후 패스워드 변경
        return f"racadm set idrac.security.minimumpasswordscore 0 && racadm set iDRAC.Users.2.Password {password}"
    
    def _handle_option2(self, _=None) -> str:
        """논리 프로세서(Logical Processor) HyperThreading 설정 조회."""
        return "racadm get BIOS.ProcSettings.LogicalProc"
    
    def _handle_option3(self, _=None) -> str:
        """BIOS 부트 모드 조회."""
        return "racadm get BIOS.BiosBootSettings.BootMode"
    
    def _handle_option4(self, _=None) -> str:
        """프로파일 설정 조회"""
        return "racadm get BIOS.SysProfileSettings.ProcPwrPerf"

# 싱글톤 인스턴스 생성
cafe24_manager = Cafe24Manager()
