class BotBaseException(Exception):
    """봇 기본 예외 클래스"""
    def __init__(self, message: str = "봇 오류가 발생했습니다."):
        self.message = message
        super().__init__(self.message)


class CommandError(BotBaseException):
    """커맨드 관련 오류"""
    def __init__(self, message: str = "커맨드 실행 중 오류가 발생했습니다."):
        super().__init__(message)


class ValidationError(BotBaseException):
    """입력 유효성 검사 오류"""
    def __init__(self, message: str = "입력값이 유효하지 않습니다."):
        super().__init__(message)


class PermissionError(BotBaseException):
    """권한 관련 오류"""
    def __init__(self, message: str = "이 작업을 수행할 권한이 없습니다."):
        super().__init__(message)


class AIServiceError(BotBaseException):
    """AI 서비스 관련 오류"""
    def __init__(self, message: str = "AI 서비스 연결 중 오류가 발생했습니다."):
        super().__init__(message)


class DatabaseError(BotBaseException):
    """데이터베이스 관련 오류"""
    def __init__(self, message: str = "데이터베이스 작업 중 오류가 발생했습니다."):
        super().__init__(message)


class RateLimitError(BotBaseException):
    """속도 제한 관련 오류"""
    def __init__(self, message: str = "요청 횟수가 제한을 초과했습니다. 잠시 후 다시 시도해주세요."):
        super().__init__(message)


class ConfigurationError(BotBaseException):
    """설정 관련 오류"""
    def __init__(self, message: str = "봇 설정에 문제가 있습니다."):
        super().__init__(message)


class CommandNotFoundError(CommandError):
    """커맨드를 찾을 수 없는 오류"""
    def __init__(self, command_name: str):
        super().__init__(f"'{command_name}' 커맨드를 찾을 수 없습니다.")
        self.command_name = command_name


class CommandAlreadyExistsError(CommandError):
    """커맨드가 이미 존재하는 오류"""
    def __init__(self, command_name: str):
        super().__init__(f"'{command_name}' 커맨드가 이미 존재합니다.")
        self.command_name = command_name