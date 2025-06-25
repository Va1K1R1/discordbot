import os
from pathlib import Path
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator

# 디버깅: 현재 경로와 .env 파일 위치 확인
current_dir = Path(__file__).parent
project_root = current_dir.parent.parent
env_file_path = project_root / ".env"

print(f"현재 파일 위치: {Path(__file__)}")
print(f"프로젝트 루트: {project_root}")
print(f".env 파일 경로: {env_file_path}")
print(f".env 파일 존재 여부: {env_file_path.exists()}")

if env_file_path.exists():
    print(f".env 파일 내용:")
    with open(env_file_path, 'r', encoding='utf-8') as f:
        content = f.read()
        # 토큰 정보는 보안상 일부만 표시
        lines = content.split('\n')
        for line in lines:
            if line.strip() and not line.startswith('#'):
                key, _, value = line.partition('=')
                if 'TOKEN' in key or 'KEY' in key:
                    print(f"{key}={'*' * min(10, len(value))}")
                else:
                    print(f"{key}={value}")


class Settings(BaseSettings):
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

    # 로깅 설정
    log_level: str = "INFO"
    log_file: str = "../logs/bot.log"

    # 보안 설정
    admin_user_ids: List[int] = []
    allowed_guild_ids: List[int] = []
    max_command_length: int = 2000

    # Pydantic v2 설정 - 여러 경로 시도
    model_config = SettingsConfigDict(
        env_file=[
            str(env_file_path),  # 프로젝트 루트의 .env
            ".env",  # 현재 디렉토리의 .env
            "../.env",  # 상위 디렉토리의 .env
            "../../.env"  # 상위의 상위 디렉토리의 .env
        ],
        env_file_encoding='utf-8',
        case_sensitive=False,
        extra='ignore'
    )

    @field_validator('admin_user_ids', mode='before')
    @classmethod
    def parse_admin_ids(cls, v):
        if isinstance(v, str):
            return [int(x.strip()) for x in v.split(',') if x.strip()]
        return v

    @field_validator('allowed_guild_ids', mode='before')
    @classmethod
    def parse_guild_ids(cls, v):
        if isinstance(v, str):
            return [int(x.strip()) for x in v.split(',') if x.strip()]
        return v


# 전역 설정 인스턴스
try:
    settings = Settings()
    print("✅ Settings 로드 성공!")
except Exception as e:
    print(f"❌ Settings 로드 실패: {e}")
    print("환경 변수로부터 직접 로드를 시도합니다...")

    # 환경 변수에서 직접 읽기
    discord_token = os.getenv('DISCORD_TOKEN')
    openai_api_key = os.getenv('OPENAI_API_KEY')

    print(f"DISCORD_TOKEN 환경 변수: {'있음' if discord_token else '없음'}")
    print(f"OPENAI_API_KEY 환경 변수: {'있음' if openai_api_key else '없음'}")

    raise e
