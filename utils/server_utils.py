from dataclasses import asdict
from config.data.models import IDRACConfig

def convert_to_idrac_config(server_info: dict) -> IDRACConfig:
    return IDRACConfig(
        NAME=server_info.get('NAME', ''),
        IP=server_info.get('IP', ''),
        PORT=server_info.get('PORT', '443'),
        USERNAME=server_info.get('USERNAME', ''),
        PASSWORD=server_info.get('PASSWORD', '')
    )

def convert_to_dict(idrac_config: IDRACConfig) -> dict:
    return asdict(idrac_config)

def create_connection_info(idrac_config: IDRACConfig) -> dict:
    return {
        'ip': idrac_config.IP,
        'port': idrac_config.PORT,
        'username': idrac_config.USERNAME,
        'password': idrac_config.PASSWORD
    }

# ServerConfig를 사용하는 함수가 필요한 경우, 동적 임포트 사용
def get_server_config():
    from config.server_config import ServerConfig
    return ServerConfig()