# 핵심 모듈 파일들 생성

# config/settings.py
settings_content = '''"""
애플리케이션 설정 관리
"""

import os
from typing import List, Optional
from pydantic import BaseSettings, validator


class Settings(BaseSettings):
    """애플리케이션 설정"""
    
    # Discord 설정
    discord_token: str
    discord_guild_id: Optional[int] = None
    
    # OpenAI 설정
    openai_api_key: str
    openai_model: str = "gpt-4"
    openai_max_tokens: int = 1000
    openai_temperature: float = 0.7
    
    # 데이터베이스 설정
    database_url: str = "sqlite:///./bot_database.db"
    
    # Redis 설정 (선택사항)
    redis_url: Optional[str] = None
    
    # 로깅 설정
    log_level: str = "INFO"
    log_file: str = "logs/bot.log"
    
    # 보안 설정
    admin_user_ids: List[int] = []
    allowed_guild_ids: List[int] = []
    max_command_length: int = 2000
    
    # API 제한
    max_requests_per_minute: int = 60
    max_ai_requests_per_user_per_hour: int = 20
    
    # 기능 토글
    enable_natural_language_processing: bool = True
    enable_command_generation: bool = True
    enable_ai_responses: bool = True
    enable_conversation_memory: bool = True
    
    @validator('admin_user_ids', pre=True)
    def parse_admin_ids(cls, v):
        if isinstance(v, str):
            return [int(x.strip()) for x in v.split(',') if x.strip()]
        return v
    
    @validator('allowed_guild_ids', pre=True)
    def parse_guild_ids(cls, v):
        if isinstance(v, str):
            return [int(x.strip()) for x in v.split(',') if x.strip()]
        return v
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# 전역 설정 인스턴스
settings = Settings()
'''

# config/logging_config.py
logging_config_content = '''"""
로깅 시스템 설정
"""

import logging
import logging.handlers
import sys
from pathlib import Path


def setup_logging(log_level: str = "INFO", log_file: str = "logs/bot.log"):
    """로깅 시스템 설정"""
    
    # 로그 디렉토리 생성
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    
    # 로거 설정
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # 기존 핸들러 제거
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # 포맷터 생성
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 콘솔 핸들러
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # 파일 핸들러 (로테이션)
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    # Discord.py 로그 레벨 조정
    logging.getLogger('discord').setLevel(logging.WARNING)
    logging.getLogger('discord.http').setLevel(logging.WARNING)
    logging.getLogger('aiohttp').setLevel(logging.WARNING)
    
    return logger
'''

# models/database.py
database_content = '''"""
데이터베이스 연결 및 세션 관리
"""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from config.settings import settings
import logging

logger = logging.getLogger(__name__)

# SQLAlchemy 설정
if settings.database_url.startswith("sqlite"):
    engine = create_engine(
        settings.database_url,
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
        echo=False
    )
else:
    engine = create_engine(
        settings.database_url,
        pool_pre_ping=True,
        pool_recycle=300,
        echo=False
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db() -> Session:
    """데이터베이스 세션 생성"""
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        logger.error(f"데이터베이스 오류: {e}")
        db.rollback()
        raise
    finally:
        db.close()


async def init_database():
    """데이터베이스 초기화"""
    try:
        # 모든 테이블 생성
        Base.metadata.create_all(bind=engine)
        logger.info("데이터베이스 초기화 완료")
    except Exception as e:
        logger.error(f"데이터베이스 초기화 실패: {e}")
        raise


async def close_database():
    """데이터베이스 연결 종료"""
    try:
        engine.dispose()
        logger.info("데이터베이스 연결 종료")
    except Exception as e:
        logger.error(f"데이터베이스 종료 실패: {e}")
'''

# 디렉토리 생성
import os

directories = [
    "src/config",
    "src/models", 
    "src/commands",
    "src/services",
    "src/utils",
    "src/exceptions",
    "tests",
    "logs",
    "docs"
]

for directory in directories:
    os.makedirs(directory, exist_ok=True)
    # __init__.py 파일 생성
    if directory.startswith("src/"):
        init_file = os.path.join(directory, "__init__.py")
        with open(init_file, "w") as f:
            f.write("")

# 파일 저장
with open("src/config/settings.py", "w", encoding="utf-8") as f:
    f.write(settings_content)

with open("src/config/logging_config.py", "w", encoding="utf-8") as f:
    f.write(logging_config_content)

with open("src/models/database.py", "w", encoding="utf-8") as f:
    f.write(database_content)

print("핵심 모듈 파일들이 생성되었습니다.")
print("생성된 디렉토리:", directories)