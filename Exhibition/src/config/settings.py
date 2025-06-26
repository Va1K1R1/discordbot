import os
from pathlib import Path
from typing import List, Optional, Union
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator, Field
from dotenv import load_dotenv

import pymysql
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import OperationalError
from contextlib import contextmanager


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

logger = logging.getLogger(__name__)

# 데이터베이스 엔진 및 세션 설정
engine = None
SessionLocal = None
Base = declarative_base()

def init_database():
    """데이터베이스 초기화 (동기 함수)"""
    global engine, SessionLocal
    
    try:
        logger.info("데이터베이스 초기화 중...")
        
        # MySQL 데이터베이스 생성 (존재하지 않는 경우)
        create_database_if_not_exists()
        
        # SQLAlchemy 엔진 생성
        database_url = (
            f"mysql+pymysql://{settings.mysql_user}:{settings.mysql_password}"
            f"@{settings.mysql_host}:{settings.mysql_port}/{settings.mysql_database}"
            f"?charset=utf8mb4"
        )
        
        logger.info(f"MySQL 데이터베이스 URL: {database_url}")
        
        engine = create_engine(
            database_url,
            echo=False,
            pool_recycle=3600,
            pool_pre_ping=True
        )
        
        # 연결 테스트
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("MySQL 데이터베이스 연결 성공")
        
        # 세션 팩토리 생성
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        
        # 기존 테이블 확인
        from sqlalchemy import inspect
        inspector = inspect(engine)
        existing_tables = inspector.get_table_names()
        logger.info(f"기존 테이블: {existing_tables}")
        
        # 테이블 생성
        Base.metadata.create_all(bind=engine)
        
        # 생성된 테이블 확인
        inspector = inspect(engine)
        created_tables = inspector.get_table_names()
        logger.info(f"데이터베이스 테이블 생성 완료")
        logger.info(f"생성된 테이블: {created_tables}")
        
        return True
        
    except Exception as e:
        logger.error(f"데이터베이스 초기화 실패: {e}")
        # SQLite로 폴백
        logger.info("SQLite로 폴백합니다...")
        return init_sqlite_fallback()

def create_database_if_not_exists():
    """데이터베이스가 존재하지 않으면 생성"""
    try:
        logger.info(f"MySQL 연결 시도: {settings.mysql_user}@{settings.mysql_host}:{settings.mysql_port}")
        
        # MySQL 서버에 연결 (데이터베이스 지정하지 않음)
        connection = pymysql.connect(
            host=settings.mysql_host,
            port=settings.mysql_port,
            user=settings.mysql_user,
            password=settings.mysql_password,
            charset='utf8mb4'
        )
        
        with connection.cursor() as cursor:
            # 데이터베이스 존재 확인
            cursor.execute(f"SHOW DATABASES LIKE '{settings.mysql_database}'")
            result = cursor.fetchone()
            
            if result:
                logger.info(f"데이터베이스 '{settings.mysql_database}' 이미 존재")
            else:
                # 데이터베이스 생성
                cursor.execute(f"CREATE DATABASE {settings.mysql_database} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
                logger.info(f"데이터베이스 '{settings.mysql_database}' 생성 완료")
        
        connection.close()
        
    except Exception as e:
        logger.error(f"데이터베이스 생성 실패: {e}")
        raise

def init_sqlite_fallback():
    """SQLite 폴백 초기화"""
    global engine, SessionLocal
    
    try:
        logger.info("SQLite 데이터베이스로 초기화 중...")
        
        # SQLite 엔진 생성
        database_url = "sqlite:///./bot_database.db"
        logger.info(f"SQLite 데이터베이스 URL: {database_url}")
        
        engine = create_engine(
            database_url,
            connect_args={"check_same_thread": False}
        )
        
        # 연결 테스트
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("SQLite 데이터베이스 연결 성공")
        
        # 세션 팩토리 생성
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        
        # 테이블 생성
        Base.metadata.create_all(bind=engine)
        logger.info("SQLite 데이터베이스 테이블 생성 완료")
        
        return True
        
    except Exception as e:
        logger.error(f"SQLite 초기화 실패: {e}")
        raise

def get_db():
    """데이터베이스 세션 제공 함수"""
    if SessionLocal is None:
        raise RuntimeError("데이터베이스가 초기화되지 않았습니다. init_database()를 먼저 호출하세요.")
    
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@contextmanager
def get_safe_db():
    """안전한 데이터베이스 세션 (자동 커밋/롤백)"""
    if SessionLocal is None:
        raise RuntimeError("데이터베이스가 초기화되지 않았습니다.")
    
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"데이터베이스 트랜잭션 오류: {e}")
        raise
    finally:
        db.close()

def get_engine():
    """데이터베이스 엔진 반환"""
    if engine is None:
        raise RuntimeError("데이터베이스가 초기화되지 않았습니다. init_database()를 먼저 호출하세요.")
    return engine