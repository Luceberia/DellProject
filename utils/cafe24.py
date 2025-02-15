from typing import List, Dict, Optional
from config.system.log_config import setup_logging

logger = setup_logging()

class Cafe24Manager:
    def __init__(self):
        self.commands = {
            "check_policy": self._handle_check_policy,
            "option1": self._handle_option1,
            "option1_custom": self._handle_option1_custom,
            "option2": self._handle_option2,
            "option2_set": self._handle_option2_set,
            "option3": self._handle_option3,
            "option3_set": self._handle_option3_set,
            "option4": self._handle_option4,
            "option4_set": self._handle_option4_set,
            "option5": self._handle_option5,
            "check_all": self._handle_check_all,
            "set_all": self._handle_set_all,
        }
        
        # 패스워드 정책 레벨 설명
        self.password_policy_levels = {
            0: "No Protection (보안 없음)",
            1: "Weak Protection (약한 보안)",
            2: "Medium Protection (중간 보안)",
            3: "Strong Protection (강한 보안)"
        }
    
    def execute_command(self, selected_options: List[str], custom_inputs: Dict[str, str] = None) -> List[str]:
        """선택된 옵션들에 대한 명령어를 실행합니다."""
        if custom_inputs is None:
            custom_inputs = {}
            
        commands = []
        for option in selected_options:
            if option in self.commands:
                result = self.commands[option](custom_inputs.get(option))
                if isinstance(result, list):
                    commands.extend(result)
                elif result:
                    commands.append(result)
        
        if commands:
            commands.append("exit")
        return commands
    
    def _check_password_policy(self) -> str:
        """현재 패스워드 정책 레벨을 확인하는 명령어를 반환합니다."""
        return "racadm get idrac.security.minimumpasswordscore"
    
    def _change_password_policy(self, level: int) -> str:
        """패스워드 정책 레벨을 변경하는 명령어를 반환합니다."""
        return f"racadm set idrac.security.minimumpasswordscore {level}"
    
    def _handle_check_policy(self, _=None) -> str:
        """현재 패스워드 정책 레벨을 확인합니다."""
        return self._check_password_policy()
    
    def _handle_option1(self, _=None) -> List[str]:
        """패스워드를 기본값(calvin)으로 변경"""
        # calvin은 가장 기본적인 패스워드이므로 무조건 정책 레벨을 0으로 변경
        return [
            self._change_password_policy(0),
            "racadm set iDRAC.Users.2.Password calvin"
        ]
    
    def _handle_option1_custom(self, password: str) -> List[str]:
        """패스워드를 사용자가 입력한 값으로 변경"""
        if not password:
            logger.warning("패스워드가 입력되지 않았습니다.")
            return []
        
        # 패스워드 복잡성 검사
        score = 0
        if len(password) >= 8:  # 길이 8 이상
            score += 1
        if any(c.isupper() for c in password):  # 대문자 포함
            score += 1
        if any(c.islower() for c in password):  # 소문자 포함
            score += 1
        if any(c.isdigit() for c in password):  # 숫자 포함
            score += 1
        if any(not c.isalnum() for c in password):  # 특수문자 포함
            score += 1
            
        # 점수에 따라 정책 레벨 결정
        # 0-2: 레벨 0 (보안 없음)
        # 3-5: 레벨 1 (약한 보안)
        policy_level = 1 if score >= 3 else 0
        
        return [
            self._check_password_policy(),
            self._change_password_policy(policy_level),
            f"racadm set iDRAC.Users.2.Password {password}"
        ]
    
    def _handle_option2(self, _=None) -> str:
        """논리 프로세서(Logical Processor) HyperThreading 설정 조회."""
        return "racadm get BIOS.ProcSettings.LogicalProc"
    
    def _handle_option2_set(self, _=None) -> str:
        """논리 프로세서 설정을 Disabled로 변경"""
        return "racadm set BIOS.ProcSettings.LogicalProc Disabled"
    
    def _handle_option3(self, _=None) -> str:
        """BIOS 부트 모드 조회"""
        return "racadm get BIOS.BiosBootSettings.BootMode"
    
    def _handle_option3_set(self, _=None) -> str:
        """BIOS 모드로 변경"""
        return "racadm set BIOS.BiosBootSettings.BootMode Bios"
    
    def _handle_option4(self, _=None) -> str:
        """프로파일 설정 조회"""
        return "racadm get BIOS.SysProfileSettings.ProcPwrPerf"
    
    def _handle_option4_set(self, _=None) -> str:
        """프로파일 설정을 PerfOptimized로 변경"""
        return "racadm set BIOS.SysProfileSettings.ProcPwrPerf PerfOptimized"
    
    def _handle_option5(self, _=None) -> str:
        """변경된 BIOS 설정을 적용하기 위해 시스템 재시작"""
        return (
            "echo '변경된 BIOS 설정을 적용하기 위해 시스템을 재시작합니다.' && "
            "racadm jobqueue create BIOS.Setup.1-1 -r pwrcycle"
        )
    
    def _handle_check_all(self, _=None) -> List[str]:
        """모든 설정 조회 (논리 프로세서, BIOS 부트 모드, 프로파일 설정, 전원 공급 장치)"""
        return [
            "racadm get BIOS.ProcSettings.LogicalProc",
            "racadm get BIOS.BiosBootSettings.BootMode",
            "racadm get Bios.sysprofileSettings.SysProfile",
            "racadm get System.Power.RedundancyPolicy",
            "racadm get System.Power.Supply.1.PrimaryStatus",
            "racadm get System.Power.Supply.2.PrimaryStatus",
        ]
    
    def _handle_set_all(self, _=None) -> List[str]:
        """모든 설정 변경 (논리 프로세서 Disabled, BIOS 모드, 프로파일 Performance)"""
        return [
            "racadm set BIOS.ProcSettings.LogicalProc Disabled",
            "racadm get BIOS.ProcSettings.LogicalProc",
            "racadm set BIOS.BiosBootSettings.BootMode Bios",
            "racadm get BIOS.BiosBootSettings.BootMode",
            "racadm set BIOS.SysProfileSettings.ProcPwrPerf Performance",
            "racadm get Bios.sysprofileSettings.SysProfile",
        ]

# 싱글톤 인스턴스 생성
cafe24_manager = Cafe24Manager()
