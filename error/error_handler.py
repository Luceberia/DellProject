import logging
from PyQt6.QtWidgets import QMessageBox
import functools
from utils.async_utils import run_with_timeout
from enum import Enum
from typing import Optional, Tuple
from dell_logging.log_config import logger, setup_logging

setup_logging()

class ConnectionErrorType(Enum):
    NETWORK_ERROR = "network_error"
    TIMEOUT_ERROR = "timeout_error"
    AUTH_ERROR = "auth_error"
    SERVER_ERROR = "server_error"
    INITIALIZATION_ERROR = "init_error"
    UNKNOWN_ERROR = "unknown_error"

class ConfigErrorType(Enum):
    INVALID_SETTINGS = "invalid_settings"
    MISSING_CONFIG = "missing_config"
    INVALID_FORMAT = "invalid_format"

class DataErrorType(Enum):
    INVALID_DATA = "invalid_data"
    CONVERSION_ERROR = "conversion_error"
    MISSING_FIELD = "missing_field"

class ErrorHandler:
    """에러 처리를 위한 클래스"""
    logger = logging.getLogger(__name__)

    @staticmethod
    def showErrorMessage(main_app, title: str, message: str):
        """에러 메시지를 표시합니다."""
        if not hasattr(main_app, 'theme_manager'):
            # 테마 매니저가 없는 경우 기본 에러 다이얼로그 표시
            error_dialog = QMessageBox(main_app)
            error_dialog.setWindowTitle(title)
            error_dialog.setText(message)
            error_dialog.setIcon(QMessageBox.Icon.Critical)
            error_dialog.exec()
        else:
            # 테마 매니저를 통한 스타일 적용
            error_dialog = main_app.theme_manager.create_error_dialog(main_app, title, message)
            error_dialog.exec()
        
        # 에러 로깅
        ErrorHandler.logger.error(f"{title}: {message}")

    @staticmethod
    def handle_error(func):
        """에러 처리 데코레이터"""
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except aiohttp.ClientError as e:
                message = "네트워크 연결에 문제가 있습니다. 인터넷 연결을 확인해 주세요."
                ErrorHandler.logger.error(f"Network error in {func.__name__}: {e}")
                ErrorHandler.showErrorMessage(args[0].main_app, "네트워크 오류", message)
            except asyncio.TimeoutError:
                message = "서버 응답 시간이 너무 깁니다. 잠시 후 다시 시도해 주세요."
                ErrorHandler.logger.error(f"Timeout error in {func.__name__}")
                ErrorHandler.showErrorMessage(args[0].main_app, "시간 초과", message)
            except Exception as e:
                message = f"예기치 않은 오류가 발생했습니다: {str(e)}"
                ErrorHandler.logger.error(f"Error in {func.__name__}: {e}", exc_info=True)
                ErrorHandler.showErrorMessage(args[0].main_app, "오류", message)
        return wrapper

    @staticmethod
    def connection_error(main_app):
        """연결 오류를 표시합니다."""
        ErrorHandler.show_error(main_app, "연결 오류", "서버에 연결할 수 없습니다.")

    @staticmethod
    def timeout_error(main_app, action: str):
        """시간 초과 오류를 표시합니다."""
        ErrorHandler.show_error(main_app, "시간 초과", f"{action} 작업이 시간 초과되었습니다.")

    @staticmethod
    def general_error(main_app, action: str, error: Exception):
        """일반 오류를 표시합니다."""
        ErrorHandler.show_error(main_app, "오류", f"{action} 중 오류 발생: {str(error)}")

    @staticmethod
    def handle_connection_error(error_type: ConnectionErrorType, error: Exception, main_app) -> Tuple[bool, str]:
        """연결 관련 에러를 처리하고 적절한 메시지를 반환합니다."""
        error_messages = {
            ConnectionErrorType.NETWORK_ERROR: "네트워크 연결에 문제가 있습니다. 인터넷 연결을 확인해 주세요.",
            ConnectionErrorType.TIMEOUT_ERROR: "서버 응답 시간이 너무 깁니다. 잠시 후 다시 시도해 주세요.",
            ConnectionErrorType.AUTH_ERROR: "인증에 실패했습니다. 사용자 정보를 확인해 주세요.",
            ConnectionErrorType.SERVER_ERROR: "서버에서 오류가 발생했습니다.",
            ConnectionErrorType.INITIALIZATION_ERROR: "초기화에 실패했습니다.",
            ConnectionErrorType.UNKNOWN_ERROR: "예기치 않은 오류가 발생했습니다."
        }

        error_message = error_messages.get(error_type, str(error))
        ErrorHandler.logger.error(f"{error_type.value}: {str(error)}")
        ErrorHandler.showErrorMessage(main_app, error_type.value, error_message)
        return False, error_message

    @staticmethod
    def classify_connection_error(error: Exception) -> ConnectionErrorType:
        """예외 타입을 ConnectionErrorType으로 분류합니다."""
        if isinstance(error, aiohttp.ClientError):
            return ConnectionErrorType.NETWORK_ERROR
        elif isinstance(error, asyncio.TimeoutError):
            return ConnectionErrorType.TIMEOUT_ERROR
        elif isinstance(error, aiohttp.ClientResponseError):
            if error.status == 401:
                return ConnectionErrorType.AUTH_ERROR
            elif 500 <= error.status < 600:
                return ConnectionErrorType.SERVER_ERROR
        return ConnectionErrorType.UNKNOWN_ERROR

    @staticmethod
    def handle_config_error(error_type: ConfigErrorType, error: Exception, main_app, message: str = None) -> tuple[bool, str]:
        """설정 관련 에러를 처리하고 적절한 메시지를 반환합니다."""
        error_messages = {
            ConfigErrorType.INVALID_SETTINGS: "설정값이 올바르지 않습니다.",
            ConfigErrorType.MISSING_CONFIG: "필수 설정이 누락되었습니다.",
            ConfigErrorType.INVALID_FORMAT: "설정 형식이 올바르지 않습니다.",
            ConfigErrorType.INITIALIZATION_ERROR: "초기화 중 오류가 발생했습니다."
        }
