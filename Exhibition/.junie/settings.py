"""
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
