from dataclasses import dataclass

@dataclass
class AppConfig:
    CACHE_TIMEOUT: int = 300  # 5분
    CONNECTION_CHECK_INTERVAL: int = 5000  # 5초
    PERIODIC_CONNECTION_CHECK_INTERVAL: int = 30  # 30초
    FETCH_TIMEOUT: int = 60  # 30초
    MAX_RETRIES: int = 3
    BASE_DELAY: int = 2
    MAX_DELAY: int = 30
    UI_UPDATE_INTERVAL: int = 100  # 100ms