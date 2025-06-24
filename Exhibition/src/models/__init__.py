"""
모델 패키지 초기화
모든 모델을 임포트하여 Base.metadata.create_all()이 제대로 작동하도록 함
"""

from .database import Base, engine, get_db, init_database, create_database_if_not_exists

# 모든 모델 임포트 (실제 파일명에 맞춰 수정)
from .command import Command
from .user import User
from .conversation import ConversationHistory


__all__ = [
    'Base',
    'engine',
    'get_db',
    'init_database',
    'create_database_if_not_exists',
    'Command',
    'User',
    'ConversationHistory'
]