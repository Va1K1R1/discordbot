"""
입력 검증 유틸리티
"""

import re
import logging
from typing import Optional, List

logger = logging.getLogger(__name__)

# Discord 예약어 목록
DISCORD_RESERVED_WORDS = {
    'help', 'info', 'ping', 'admin', 'mod', 'moderator', 'ban', 'kick', 
    'mute', 'unmute', 'warn', 'clear', 'purge', 'role', 'channel',
    'server', 'guild', 'user', 'member', 'everyone', 'here'
}


def validate_command_name(name: str) -> tuple[bool, Optional[str]]:
    """커맨드 이름 유효성 검사"""
    if not name:
        return False, "커맨드 이름이 비어있습니다."

    # 길이 검사
    if len(name) < 1 or len(name) > 32:
        return False, "커맨드 이름은 1-32자 사이여야 합니다."

    # 문자 규칙 검사 (영문 소문자, 숫자, 언더스코어만 허용)
    if not re.match(r'^[a-z0-9_]+$', name):
        return False, "커맨드 이름은 영문 소문자, 숫자, 언더스코어만 사용할 수 있습니다."

    # 숫자로 시작하는지 검사
    if name[0].isdigit():
        return False, "커맨드 이름은 숫자로 시작할 수 없습니다."

    # 언더스코어로만 구성되었는지 검사
    if name.replace('_', '') == '':
        return False, "커맨드 이름은 언더스코어로만 구성될 수 없습니다."

    # 예약어 검사
    if name.lower() in DISCORD_RESERVED_WORDS:
        return False, f"'{name}'은 Discord 예약어이므로 사용할 수 없습니다."

    return True, None


def validate_command_description(description: str) -> tuple[bool, Optional[str]]:
    """커맨드 설명 유효성 검사"""
    if not description:
        return False, "커맨드 설명이 비어있습니다."

    if len(description) < 1 or len(description) > 100:
        return False, "커맨드 설명은 1-100자 사이여야 합니다."

    # 특수 문자 검사 (기본적인 문장 부호만 허용)
    if re.search(r'[<>@#&]', description):
        return False, "커맨드 설명에 특수 문자 (<, >, @, #, &)는 사용할 수 없습니다."

    return True, None


def validate_response_template(template: str) -> tuple[bool, Optional[str]]:
    """응답 템플릿 유효성 검사"""
    if not template:
        return False, "응답 템플릿이 비어있습니다."

    if len(template) > 2000:
        return False, "응답 템플릿은 2000자를 초과할 수 없습니다."

    # 금지된 멘션 패턴 검사
    forbidden_patterns = [
        r'@everyone',
        r'@here',
        r'<@&\d+>',  # 역할 멘션
    ]

    for pattern in forbidden_patterns:
        if re.search(pattern, template, re.IGNORECASE):
            return False, "응답 템플릿에 전체 멘션(@everyone, @here)이나 역할 멘션은 사용할 수 없습니다."

    return True, None


def validate_ai_prompt(prompt: str) -> tuple[bool, Optional[str]]:
    """AI 프롬프트 유효성 검사"""
    if not prompt:
        return False, "AI 프롬프트가 비어있습니다."

    if len(prompt) > 1000:
        return False, "AI 프롬프트는 1000자를 초과할 수 없습니다."

    # 유해한 키워드 검사
    harmful_keywords = [
        'hack', 'exploit', 'ddos', 'dos attack', 'malware', 'virus',
        'password', 'token', 'secret', 'api key', 'private key'
    ]

    prompt_lower = prompt.lower()
    for keyword in harmful_keywords:
        if keyword in prompt_lower:
            return False, f"AI 프롬프트에 보안상 위험한 키워드 '{keyword}'가 포함되어 있습니다."

    return True, None


def validate_user_input(user_input: str, max_length: int = 500) -> tuple[bool, Optional[str]]:
    """사용자 입력 유효성 검사"""
    if len(user_input) > max_length:
        return False, f"입력은 {max_length}자를 초과할 수 없습니다."

    # SQL 인젝션 패턴 검사
    sql_patterns = [
        r'(union|select|insert|update|delete|drop|create|alter|exec|execute)',
        r'(script|javascript|vbscript)',
        r'(<script|</script>|<iframe|</iframe>)'
    ]

    input_lower = user_input.lower()
    for pattern in sql_patterns:
        if re.search(pattern, input_lower):
            return False, "입력에 허용되지 않는 패턴이 포함되어 있습니다."

    return True, None


def sanitize_input(text: str) -> str:
    """입력 텍스트 정화"""
    if not text:
        return ""

    # HTML 태그 제거
    text = re.sub(r'<[^>]*>', '', text)

    # 연속된 공백을 하나로 변경
    text = re.sub(r'\s+', ' ', text)

    # 앞뒤 공백 제거
    text = text.strip()

    return text


def validate_role_names(role_names: List[str]) -> tuple[bool, Optional[str]]:
    """역할 이름 목록 유효성 검사"""
    if not role_names:
        return True, None  # 빈 목록은 허용

    for role_name in role_names:
        if not role_name or not role_name.strip():
            return False, "빈 역할 이름은 허용되지 않습니다."

        if len(role_name) > 100:
            return False, f"역할 이름 '{role_name}'이 너무 깁니다 (최대 100자)."

        # 특수 문자 검사
        if re.search(r'[<>@#&]', role_name):
            return False, f"역할 이름 '{role_name}'에 허용되지 않는 특수 문자가 포함되어 있습니다."

    return True, None


def validate_guild_id(guild_id: str) -> tuple[bool, Optional[str]]:
    """길드 ID 유효성 검사"""
    if not guild_id:
        return False, "길드 ID가 비어있습니다."

    # Discord 길드 ID는 일반적으로 18-19자리 숫자
    if not guild_id.isdigit() or len(guild_id) < 17 or len(guild_id) > 20:
        return False, "올바르지 않은 길드 ID 형식입니다."

    return True, None


def is_safe_content(content: str) -> bool:
    """콘텐츠 안전성 기본 검사"""
    # 기본적인 안전성 검사
    unsafe_patterns = [
        r'(http|https|ftp)://\S+',  # URL
        r'discord\.gg/\S+',         # Discord 초대 링크
        r'@everyone|@here',         # 전체 멘션
    ]

    for pattern in unsafe_patterns:
        if re.search(pattern, content, re.IGNORECASE):
            return False

    return True
