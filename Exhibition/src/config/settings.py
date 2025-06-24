import os
from pathlib import Path
from typing import List, Optional, Union
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator, Field
from dotenv import load_dotenv


# 올바른 프로젝트 루트 경로 설정
current_file = Path(__file__)
project_root = current_file.parent.parent.parent
env_file_path = project_root / ".env"

print(f"현재 파일 위치: {current_file}")
print(f"프로젝트 루트: {project_root}")
print(f".env 파일 경로: {env_file_path}")
print(f".env 파일 존재 여부: {env_file_path.exists()}")

# python-dotenv로 수동 로드
if env_file_path.exists():
    load_dotenv(env_file_path)
    print(f"✅ .env 파일 로드됨")
    
    # 디버깅: 로드된 환경 변수 확인
    admin_ids = os.getenv('ADMIN_USER_IDS')
    guild_ids = os.getenv('ALLOWED_GUILD_IDS')
    print(f"ADMIN_USER_IDS: {admin_ids}")
    print(f"ALLOWED_GUILD_IDS: {guild_ids}")
else:
    print(f"❌ .env 파일을 찾을 수 없습니다")


class Settings(BaseSettings):
    # Discord 설정
    discord_token: str
    discord_guild_id: Optional[int] = None
    
    # OpenAI 설정
    openai_api_key: str
    openai_model: str = "gpt-4"
    openai_max_tokens: int = 1000
    openai_temperature: float = 0.7
    
    # MySQL 데이터베이스 설정
    mysql_host: str = "localhost"
    mysql_port: int = 3306
    mysql_user: str = "j"
    mysql_password: str = "4820"
    mysql_database: str = "discord_bot"
    
    # 로깅 설정
    log_level: str = "INFO"
    log_file: str = "logs/bot.log"
    
    # 보안 설정 - Union 타입으로 문자열도 허용
    admin_user_ids: Union[List[int], str] = Field(default_factory=list)
    allowed_guild_ids: Union[List[int], str] = Field(default_factory=list)
    max_command_length: int = 2000
    
    model_config = SettingsConfigDict(
        case_sensitive=False,
        extra='ignore'
    )
    
    @property
    def database_url(self) -> str:
        """MySQL 데이터베이스 URL 생성"""
        return f"mysql+pymysql://{self.mysql_user}:{self.mysql_password}@{self.mysql_host}:{self.mysql_port}/{self.mysql_database}?charset=utf8mb4"
    
    @field_validator('admin_user_ids', mode='before')
    @classmethod
    def parse_admin_ids(cls, v):
        print(f"admin_user_ids validator 호출됨: {v} (타입: {type(v)})")
        if isinstance(v, str):
            if v.strip():
                result = [int(x.strip()) for x in v.split(',') if x.strip()]
                print(f"파싱 결과: {result}")
                return result
            return []
        elif isinstance(v, list):
            return v
        elif isinstance(v, int):
            return [v]
        return []
    
    @field_validator('allowed_guild_ids', mode='before')
    @classmethod
    def parse_guild_ids(cls, v):
        print(f"allowed_guild_ids validator 호출됨: {v} (타입: {type(v)})")
        if isinstance(v, str):
            if v.strip():
                result = [int(x.strip()) for x in v.split(',') if x.strip()]
                print(f"파싱 결과: {result}")
                return result
            return []
        elif isinstance(v, list):
            return v
        elif isinstance(v, int):
            return [v]
        return []
    
    def model_post_init(self, __context) -> None:
        """모델 초기화 후 타입 변환"""
        if isinstance(self.admin_user_ids, str):
            if self.admin_user_ids.strip():
                self.admin_user_ids = [int(x.strip()) for x in self.admin_user_ids.split(',') if x.strip()]
            else:
                self.admin_user_ids = []
        
        if isinstance(self.allowed_guild_ids, str):
            if self.allowed_guild_ids.strip():
                self.allowed_guild_ids = [int(x.strip()) for x in self.allowed_guild_ids.split(',') if x.strip()]
            else:
                self.allowed_guild_ids = []


# 전역 설정 인스턴스
settings = Settings()
print(f"최종 admin_user_ids: {settings.admin_user_ids}")
print(f"최종 allowed_guild_ids: {settings.allowed_guild_ids}")
print(f"MySQL 데이터베이스 URL: {settings.database_url}")