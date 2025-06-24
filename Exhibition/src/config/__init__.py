"""
설정 패키지
봇의 모든 설정 관련 모듈을 포함합니다.
"""

from .settings import settings
from .logging_config import setup_logging

__all__ = [
    'settings',
    'setup_logging'
]