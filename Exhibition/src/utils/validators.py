import re
from typing import Optional, Tuple, List
import logging

logger = logging.getLogger(__name__)


def validate_command_name(name: str) -> Tuple[bool, Optional[str]]:
    """
    Discord 슬래시 커맨드 이름 유효성 검사
    
    Args:
        name: 검사할 커맨드 이름
        
    Returns:
        (유효성 여부, 오류 메시지)
    """
    # 길이 검사 (1-32자)
    if not 1 <= len(name) <= 32:
        return False, f"커맨드 이름은 1-32자 사이여야 합니다. (현재: {len(name)}자)"
    
    # 문자 검사 (영문 소문자, 숫자, 언더스코어만 허용)
    if not re.match(r'^[a-z0-9_]+$', name):
        return False, "커맨드 이름은 영문 소문자, 숫자, 언더스코어(_)만 포함할 수 있습니다."
    
    return True, None


def validate_command_description(description: str) -> Tuple[bool, Optional[str]]:
    """
    Discord 슬래시 커맨드 설명 유효성 검사
    
    Args:
        description: 검사할 커맨드 설명
        
    Returns:
        (유효성 여부, 오류 메시지)
    """
    # 길이 검사 (1-100자)
    if not 1 <= len(description) <= 100:
        return False, f"커맨드 설명은 1-100자 사이여야 합니다. (현재: {len(description)}자)"
    
    return True, None


def validate_discord_id(discord_id: str) -> Tuple[bool, Optional[str]]:
    """
    Discord ID 유효성 검사
    
    Args:
        discord_id: 검사할 Discord ID
        
    Returns:
        (유효성 여부, 오류 메시지)
    """
    # 숫자만 허용
    if not discord_id.isdigit():
        return False, "Discord ID는 숫자만 포함할 수 있습니다."
    
    # 길이 검사 (17-19자)
    if not 17 <= len(discord_id) <= 19:
        return False, f"Discord ID는 17-19자 사이여야 합니다. (현재: {len(discord_id)}자)"
    
    return True, None


def validate_user_input(user_input: str, max_length: int = 2000) -> Tuple[bool, Optional[str]]:
    """
    사용자 입력 유효성 검사
    
    Args:
        user_input: 검사할 사용자 입력
        max_length: 최대 허용 길이
        
    Returns:
        (유효성 여부, 오류 메시지)
    """
    # 빈 입력 검사
    if not user_input.strip():
        return False, "입력이 비어있습니다."
    
    # 길이 검사
    if len(user_input) > max_length:
        return False, f"입력은 최대 {max_length}자까지 허용됩니다. (현재: {len(user_input)}자)"
    
    return True, None


def sanitize_user_input(user_input: str) -> str:
    """
    사용자 입력 정제
    
    Args:
        user_input: 정제할 사용자 입력
        
    Returns:
        정제된 입력
    """
    # 앞뒤 공백 제거
    sanitized = user_input.strip()
    
    # Discord 마크다운 이스케이프 처리
    sanitized = sanitized.replace('`', '\\`')
    sanitized = sanitized.replace('*', '\\*')
    sanitized = sanitized.replace('_', '\\_')
    sanitized = sanitized.replace('~', '\\~')
    sanitized = sanitized.replace('>', '\\>')
    
    return sanitized