# AI Discord 봇 구현 가이드

이 문서는 `task.md`에 나열된 작업을 구현하기 위한 단계별 가이드입니다.

## 1. 개발 환경 설정

### Python 설치 (3.8 이상)
```bash
# Windows (Chocolatey 사용)
choco install python

# macOS (Homebrew 사용)
brew install python

# Ubuntu/Debian
sudo apt update
sudo apt install python3 python3-pip python3-venv
```

### 프로젝트 디렉토리 생성 및 Git 저장소 초기화
```bash
mkdir ai-discord-bot
cd ai-discord-bot
git init
```

### 가상 환경 생성 및 활성화
```bash
# 가상 환경 생성
python -m venv venv

# 가상 환경 활성화
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate
```

### 필수 패키지 설치
requirements.txt 파일 생성:
```
discord.py==2.3.1
python-dotenv==1.0.0
openai==0.28.0
sqlalchemy==2.0.20
pydantic==2.3.0
pytest==7.4.0
pytest-asyncio==0.21.1
pytest-cov==4.1.0
black==23.7.0
isort==5.12.0
mypy==1.5.1
```

패키지 설치:
```bash
pip install -r requirements.txt
```

### .env 파일 생성
.env 파일 생성:
```
# Discord Bot 설정
DISCORD_TOKEN=your_discord_bot_token
DISCORD_GUILD_ID=your_test_guild_id

# OpenAI API 설정
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=gpt-4

# 데이터베이스 설정
DATABASE_URL=sqlite:///./bot_database.db

# 로깅 설정
LOG_LEVEL=INFO
LOG_FILE=logs/bot.log

# 보안 설정
ADMIN_USER_IDS=123456789,987654321
ALLOWED_GUILD_IDS=111111111,222222222
```

## 2. 프로젝트 구조 설정

### 기본 디렉토리 구조 생성
```bash
mkdir -p src/config src/models src/commands src/services src/utils src/exceptions
mkdir -p tests logs docs
```

### 기본 파일 생성
각 디렉토리에 `__init__.py` 파일 생성:
```bash
touch src/__init__.py src/config/__init__.py src/models/__init__.py src/commands/__init__.py src/services/__init__.py src/utils/__init__.py src/exceptions/__init__.py tests/__init__.py
```

## 3. 핵심 모듈 구현

### 3.1 설정 관리

#### settings.py 구현
`src/config/settings.py` 파일 생성:
```python
import os
from typing import List, Optional
from pydantic import BaseSettings, validator


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
    log_file: str = "logs/bot.log"
    
    # 보안 설정
    admin_user_ids: List[int] = []
    allowed_guild_ids: List[int] = []
    max_command_length: int = 2000
    
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
```

#### logging_config.py 구현
`src/config/logging_config.py` 파일 생성:
```python
import logging
import logging.handlers
import sys
from pathlib import Path
from src.config.settings import settings


def setup_logging():
    """로깅 시스템 설정"""
    
    # 로그 디렉토리 생성
    log_path = Path(settings.log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    
    # 로거 설정
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, settings.log_level.upper()))
    
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
        settings.log_file,
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    # Discord.py 로그 레벨 조정
    logging.getLogger('discord').setLevel(logging.WARNING)
    logging.getLogger('discord.http').setLevel(logging.WARNING)
    
    return logger
```

### 3.2 데이터베이스 모델

#### database.py 구현
`src/models/database.py` 파일 생성:
```python
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from src.config.settings import settings

# 데이터베이스 엔진 생성
engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
)

# 세션 팩토리 생성
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 모델 기본 클래스
Base = declarative_base()

# 데이터베이스 세션 제공 함수
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

#### user.py 구현
`src/models/user.py` 파일 생성:
```python
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
from src.models.database import Base


class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    discord_id = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_active = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 사용자 설정
    preferences = Column(Text)  # JSON 형태로 저장
    
    # 권한 관련
    is_admin = Column(Boolean, default=False)
    is_banned = Column(Boolean, default=False)
    
    # 사용 통계
    command_count = Column(Integer, default=0)
    message_count = Column(Integer, default=0)
```

#### command.py 구현
`src/models/command.py` 파일 생성:
```python
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
from typing import List
import json
from src.models.database import Base


class Command(Base):
    __tablename__ = "commands"
    
    id = Column(Integer, primary_key=True, index=True)
    guild_id = Column(String, index=True, nullable=False)
    name = Column(String, unique=True, index=True, nullable=False)
    description = Column(String, nullable=False)
    response_template = Column(Text)
    
    # AI 관련 필드
    use_ai = Column(Boolean, default=False)
    ai_prompt = Column(Text)
    ai_system_message = Column(Text)
    
    # 권한 및 메타데이터
    required_permissions = Column(Text)  # JSON 형태로 저장
    allowed_roles = Column(Text)  # JSON 형태로 저장
    created_by = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    
    # 사용 통계
    usage_count = Column(Integer, default=0)
    last_used = Column(DateTime)
    
    def get_required_permissions(self) -> List[str]:
        """필요한 권한 목록을 반환"""
        if self.required_permissions:
            return json.loads(self.required_permissions)
        return []
    
    def set_required_permissions(self, permissions: List[str]):
        """필요한 권한 목록을 설정"""
        self.required_permissions = json.dumps(permissions)
    
    def get_allowed_roles(self) -> List[str]:
        """허용된 역할 목록을 반환"""
        if self.allowed_roles:
            return json.loads(self.allowed_roles)
        return []
    
    def set_allowed_roles(self, roles: List[str]):
        """허용된 역할 목록을 설정"""
        self.allowed_roles = json.dumps(roles)
    
    def increment_usage(self):
        """사용 횟수 증가"""
        self.usage_count += 1
        self.last_used = datetime.utcnow()
```

#### conversation.py 구현
`src/models/conversation.py` 파일 생성:
```python
from sqlalchemy import Column, Integer, String, DateTime, Float, Text
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
from src.models.database import Base


class ConversationHistory(Base):
    __tablename__ = "conversation_history"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True, nullable=False)
    guild_id = Column(String, index=True, nullable=False)
    channel_id = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    response = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow)
    command_used = Column(String)
    
    # AI 관련 메타데이터
    tokens_used = Column(Integer)
    processing_time = Column(Float)
    intent = Column(String)  # 감지된 의도
    entities = Column(Text)  # JSON 형태로 저장된 엔터티
```

### 3.3 서비스 구현

#### ai_service.py 구현
`src/services/ai_service.py` 파일 생성:
```python
import openai
import asyncio
import json
from typing import Dict, List, Optional, Tuple, Any
from src.config.settings import settings
from src.utils.decorators import retry_with_backoff
import logging

logger = logging.getLogger(__name__)


class AIService:
    def __init__(self):
        openai.api_key = settings.openai_api_key
        self.model = settings.openai_model
        self.max_tokens = settings.openai_max_tokens
        self.temperature = settings.openai_temperature
    
    @retry_with_backoff(max_retries=3)
    async def generate_response(
        self, 
        prompt: str, 
        system_message: Optional[str] = None,
        context: Optional[List[Dict]] = None
    ) -> Tuple[str, Dict]:
        """AI 응답 생성"""
        try:
            messages = []
            
            # 시스템 메시지 추가
            if system_message:
                messages.append({"role": "system", "content": system_message})
            
            # 대화 컨텍스트 추가
            if context:
                messages.extend(context)
            
            # 사용자 메시지 추가
            messages.append({"role": "user", "content": prompt})
            
            response = await openai.ChatCompletion.acreate(
                model=self.model,
                messages=messages,
                max_tokens=self.max_tokens,
                temperature=self.temperature
            )
            
            content = response.choices[0].message.content
            metadata = {
                "tokens_used": response.usage.total_tokens,
                "model": self.model,
                "finish_reason": response.choices[0].finish_reason
            }
            
            return content, metadata
            
        except Exception as e:
            logger.error(f"AI 응답 생성 실패: {e}")
            raise
    
    async def analyze_intent(self, message: str) -> Dict[str, Any]:
        """사용자 메시지의 의도 분석"""
        system_message = """
        사용자의 메시지를 분석하여 다음 정보를 JSON 형태로 반환해주세요:
        {
            "intent": "커맨드 생성 | 정보 요청 | 일반 대화 | 도움말 요청",
            "confidence": 0.0-1.0,
            "entities": {
                "command_name": "추출된 커맨드 이름",
                "action": "수행할 작업",
                "parameters": ["매개변수1", "매개변수2"]
            }
        }
        """
        
        try:
            response, _ = await self.generate_response(
                message, 
                system_message=system_message
            )
            return json.loads(response)
        except Exception as e:
            logger.error(f"의도 분석 실패: {e}")
            return {"intent": "일반 대화", "confidence": 0.5, "entities": {}}
    
    async def generate_command_metadata(
        self, 
        user_description: str
    ) -> Dict[str, str]:
        """사용자 설명으로부터 커맨드 메타데이터 생성"""
        system_message = """
        사용자가 요청한 기능을 바탕으로 Discord 슬래시 커맨드의 메타데이터를 생성해주세요.
        다음 JSON 형태로 응답해주세요:
        {
            "name": "커맨드_이름",
            "description": "커맨드 설명 (100자 이내)",
            "response_template": "응답 템플릿 (변수는 {variable} 형태)",
            "parameters": ["param1", "param2"]
        }
        
        커맨드 이름은 영문 소문자, 숫자, 언더스코어만 사용하고, 
        Discord 규칙에 맞게 1-32자로 제한해주세요.
        """
        
        try:
            response, _ = await self.generate_response(
                user_description,
                system_message=system_message
            )
            return json.loads(response)
        except Exception as e:
            logger.error(f"커맨드 메타데이터 생성 실패: {e}")
            raise
    
    async def enhance_response(
        self, 
        base_template: str, 
        user_input: str,
        context: Optional[Dict] = None
    ) -> str:
        """기본 템플릿을 AI로 향상시킨 응답 생성"""
        system_message = f"""
        다음 템플릿을 기반으로 사용자의 입력에 맞는 자연스럽고 도움이 되는 응답을 생성해주세요:
        
        템플릿: {base_template}
        
        응답은 친근하고 도움이 되는 톤으로 작성하며, 
        사용자의 구체적인 요청에 맞게 개인화해주세요.
        """
        
        prompt = f"사용자 입력: {user_input}"
        if context:
            prompt += f"\n추가 컨텍스트: {json.dumps(context, ensure_ascii=False)}"
        
        try:
            response, _ = await self.generate_response(
                prompt,
                system_message=system_message
            )
            return response
        except Exception as e:
            logger.error(f"응답 향상 실패: {e}")
            return base_template  # 실패 시 기본 템플릿 반환


# 전역 AI 서비스 인스턴스
ai_service = AIService()
```

## 4. 메인 봇 구현

### main.py 구현
`src/main.py` 파일 생성:
```python
import discord
from discord.ext import commands
import asyncio
import logging
import os
from src.config.settings import settings
from src.config.logging_config import setup_logging
from src.models.database import Base, engine

# 로깅 설정
logger = setup_logging()

# 데이터베이스 테이블 생성
Base.metadata.create_all(bind=engine)

# 인텐트 설정
intents = discord.Intents.default()
intents.message_content = True
intents.members = True


def create_bot():
    """봇 인스턴스 생성"""
    bot = commands.Bot(command_prefix="!", intents=intents)
    
    @bot.event
    async def on_ready():
        logger.info(f"{bot.user.name}이(가) 준비되었습니다!")
        
        # 슬래시 커맨드 동기화
        try:
            synced = await bot.tree.sync()
            logger.info(f"{len(synced)}개의 슬래시 커맨드가 동기화되었습니다.")
        except Exception as e:
            logger.error(f"슬래시 커맨드 동기화 실패: {e}")
    
    @bot.event
    async def on_message(message):
        # 봇 자신의 메시지는 무시
        if message.author == bot.user:
            return
        
        # 명령어 처리
        await bot.process_commands(message)
    
    return bot


async def load_extensions(bot):
    """확장 모듈 로드"""
    for filename in os.listdir("src/commands"):
        if filename.endswith(".py") and not filename.startswith("__"):
            try:
                await bot.load_extension(f"src.commands.{filename[:-3]}")
                logger.info(f"확장 모듈 로드: {filename}")
            except Exception as e:
                logger.error(f"확장 모듈 로드 실패 {filename}: {e}")


async def main():
    """메인 함수"""
    bot = create_bot()
    await load_extensions(bot)
    
    try:
        await bot.start(settings.discord_token)
    except Exception as e:
        logger.error(f"봇 실행 실패: {e}")
    finally:
        await bot.close()


if __name__ == "__main__":
    asyncio.run(main())
```

## 5. 테스트 작성

### 단위 테스트 예시
`tests/test_ai_service.py` 파일 생성:
```python
import pytest
import asyncio
from unittest.mock import patch, AsyncMock
from src.services.ai_service import AIService


class TestAIService:
    @pytest.fixture
    def ai_service(self):
        return AIService()
    
    @patch('openai.ChatCompletion.acreate')
    async def test_generate_response(self, mock_openai, ai_service):
        # Mock OpenAI 응답
        mock_response = AsyncMock()
        mock_response.choices = [AsyncMock()]
        mock_response.choices[0].message.content = "테스트 응답"
        mock_response.usage.total_tokens = 100
        mock_openai.return_value = mock_response
        
        # 테스트 실행
        response, metadata = await ai_service.generate_response("테스트 프롬프트")
        
        # 검증
        assert response == "테스트 응답"
        assert metadata["tokens_used"] == 100
        mock_openai.assert_called_once()
```

## 6. 배포 준비

### Dockerfile 작성
`Dockerfile` 파일 생성:
```dockerfile
FROM python:3.9-slim

WORKDIR /app

# 시스템 의존성 설치
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Python 의존성 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션 코드 복사
COPY src/ ./src/
COPY .env .env

# 로그 디렉토리 생성
RUN mkdir -p logs

# 실행
CMD ["python", "src/main.py"]
```

### docker-compose.yml 작성
`docker-compose.yml` 파일 생성:
```yaml
version: '3.8'

services:
  discord-bot:
    build: .
    container_name: ai-discord-bot
    restart: unless-stopped
    environment:
      - DATABASE_URL=postgresql://bot_user:bot_password@postgres:5432/bot_db
    volumes:
      - ./logs:/app/logs
      - ./data:/app/data
    depends_on:
      - postgres
    networks:
      - bot-network

  postgres:
    image: postgres:13
    container_name: bot-postgres
    restart: unless-stopped
    environment:
      POSTGRES_DB: bot_db
      POSTGRES_USER: bot_user
      POSTGRES_PASSWORD: bot_password
    volumes:
      - postgres_data:/var/lib/postgresql/data
    networks:
      - bot-network

volumes:
  postgres_data:

networks:
  bot-network:
    driver: bridge
```

## 7. 배포 및 운영

### 배포 전 체크리스트
- 모든 테스트 통과 확인
- 환경 변수 설정 확인
- 데이터베이스 마이그레이션 준비
- 로그 시스템 동작 확인
- 모니터링 설정 완료
- 백업 시스템 구성

### Docker 컨테이너 배포
```bash
# 컨테이너 빌드 및 실행
docker-compose up -d

# 로그 확인
docker-compose logs -f discord-bot
```

## 8. 유지보수 계획

### 정기 업데이트 일정
- 매주 의존성 업데이트 확인
- 매월 보안 업데이트 적용
- 분기별 기능 개선 계획 수립

### 버그 추적 및 해결 프로세스
1. 이슈 등록 (GitHub Issues)
2. 우선순위 지정
3. 버그 수정 및 테스트
4. 코드 리뷰
5. 배포

### 성능 모니터링 및 최적화
- API 호출 모니터링
- 응답 시간 측정
- 리소스 사용량 추적
- 병목 현상 식별 및 해결