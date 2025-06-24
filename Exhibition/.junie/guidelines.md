# AI Discord 봇 개발 가이드

## 목차
1. [개발 환경 설정](#개발-환경-설정)
2. [프로젝트 구조](#프로젝트-구조)
3. [핵심 모듈 구현](#핵심-모듈-구현)
4. [IntelliJ IDEA 설정](#intellij-idea-설정)
5. [테스트 및 디버깅](#테스트-및-디버깅)
6. [배포 및 운영](#배포-및-운영)

## 개발 환경 설정

### 1. 필수 소프트웨어 설치

#### Python 설치
```bash
# Windows (Chocolatey 사용)
choco install python

# macOS (Homebrew 사용)
brew install python

# Ubuntu/Debian
sudo apt update
sudo apt install python3 python3-pip python3-venv
```

#### IntelliJ IDEA 설정
1. **IntelliJ IDEA Community/Ultimate** 다운로드 및 설치
2. **Python 플러그인** 설치 (Community Edition 사용 시)
3. **Git 플러그인** 활성화 확인

### 2. 프로젝트 초기화

```bash
# 프로젝트 디렉토리 생성
mkdir ai-discord-bot
cd ai-discord-bot

# Git 저장소 초기화
git init

# 가상 환경 생성
python -m venv venv

# 가상 환경 활성화
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate

# 의존성 설치
pip install -r requirements.txt
```

### 3. 환경 변수 설정

`.env` 파일 생성:
```env
# Discord Bot 설정
DISCORD_TOKEN=your_discord_bot_token
DISCORD_GUILD_ID=your_test_guild_id

# OpenAI API 설정
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=gpt-4

# 데이터베이스 설정
DATABASE_URL=sqlite:///./bot_database.db
# 프로덕션 환경에서는 PostgreSQL 사용
# DATABASE_URL=postgresql://user:password@localhost:5432/botdb

# 로깅 설정
LOG_LEVEL=INFO
LOG_FILE=logs/bot.log

# 보안 설정
ADMIN_USER_IDS=123456789,987654321
ALLOWED_GUILD_IDS=111111111,222222222
```

## 프로젝트 구조

```
ai-discord-bot/
├── src/
│   ├── __init__.py
│   ├── main.py                 # 메인 봇 실행 파일
│   ├── config/
│   │   ├── __init__.py
│   │   ├── settings.py         # 설정 관리
│   │   └── logging_config.py   # 로깅 설정
│   ├── models/
│   │   ├── __init__.py
│   │   ├── database.py         # 데이터베이스 연결
│   │   ├── user.py            # 사용자 모델
│   │   ├── command.py         # 커맨드 모델
│   │   └── conversation.py    # 대화 기록 모델
│   ├── commands/
│   │   ├── __init__.py
│   │   ├── admin.py           # 관리자 명령어
│   │   ├── dynamic.py         # 동적 커맨드 관리
│   │   └── ai_chat.py         # AI 채팅 명령어
│   ├── services/
│   │   ├── __init__.py
│   │   ├── ai_service.py      # OpenAI API 연동
│   │   ├── command_service.py # 커맨드 관리 서비스
│   │   ├── permission_service.py # 권한 관리
│   │   └── nlp_service.py     # 자연어 처리 서비스
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── decorators.py      # 유틸리티 데코레이터
│   │   ├── validators.py      # 입력 검증
│   │   └── helpers.py         # 도우미 함수
│   └── exceptions/
│       ├── __init__.py
│       └── custom_exceptions.py
├── tests/
│   ├── __init__.py
│   ├── test_commands.py
│   ├── test_services.py
│   └── test_models.py
├── logs/
├── docs/
│   ├── api.md
│   └── user_guide.md
├── requirements.txt
├── requirements-dev.txt
├── .env.example
├── .gitignore
├── README.md
├── docker-compose.yml
├── Dockerfile
└── pytest.ini
```

## 핵심 모듈 구현

### 1. 설정 관리 (config/settings.py)

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

### 2. 데이터베이스 모델 (models/command.py)

```python
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
from typing import Optional, Dict, Any
import json

Base = declarative_base()


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

### 3. AI 서비스 (services/ai_service.py)

```python
import openai
import asyncio
import json
from typing import Dict, List, Optional, Tuple
from src.config.settings import settings
from src.models.conversation import ConversationHistory
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

### 4. 동적 커맨드 관리 (commands/dynamic.py)

```python
import discord
from discord import app_commands
from discord.ext import commands
from sqlalchemy.orm import Session
from src.models.database import get_db
from src.models.command import Command
from src.services.ai_service import ai_service
from src.services.permission_service import check_admin_permission
from src.utils.validators import validate_command_name, validate_command_description
import logging

logger = logging.getLogger(__name__)


class AddCommandModal(discord.ui.Modal):
    def __init__(self):
        super().__init__(title="새 커맨드 추가")
        
        self.command_description = discord.ui.TextInput(
            label="커맨드 설명",
            placeholder="만들고 싶은 기능을 자연어로 설명해주세요",
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=1000
        )
        
        self.use_ai = discord.ui.TextInput(
            label="AI 응답 사용 (true/false)",
            placeholder="true 또는 false",
            default="true",
            required=True,
            max_length=5
        )
        
        self.allowed_roles = discord.ui.TextInput(
            label="허용된 역할 (쉼표로 구분)",
            placeholder="Admin,Moderator (비워두면 모든 사용자)",
            required=False,
            max_length=200
        )
        
        self.add_item(self.command_description)
        self.add_item(self.use_ai)
        self.add_item(self.allowed_roles)
    
    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        try:
            # AI로 커맨드 메타데이터 생성
            metadata = await ai_service.generate_command_metadata(
                self.command_description.value
            )
            
            # 데이터베이스에 저장
            db = next(get_db())
            
            # 커맨드 이름 중복 확인
            existing_command = db.query(Command).filter(
                Command.guild_id == str(interaction.guild.id),
                Command.name == metadata["name"]
            ).first()
            
            if existing_command:
                await interaction.followup.send(
                    f"❌ 커맨드 `{metadata['name']}`이 이미 존재합니다.",
                    ephemeral=True
                )
                return
            
            # 새 커맨드 생성
            new_command = Command(
                guild_id=str(interaction.guild.id),
                name=metadata["name"],
                description=metadata["description"],
                response_template=metadata["response_template"],
                use_ai=self.use_ai.value.lower() == "true",
                ai_prompt=self.command_description.value,
                created_by=str(interaction.user.id)
            )
            
            # 허용된 역할 설정
            if self.allowed_roles.value:
                roles = [role.strip() for role in self.allowed_roles.value.split(",")]
                new_command.set_allowed_roles(roles)
            
            db.add(new_command)
            db.commit()
            
            # Discord에 슬래시 커맨드 등록
            await self.register_slash_command(interaction, new_command)
            
            embed = discord.Embed(
                title="✅ 커맨드 생성 완료",
                description=f"커맨드 `/{metadata['name']}`이 성공적으로 생성되었습니다!",
                color=discord.Color.green()
            )
            embed.add_field(name="설명", value=metadata["description"], inline=False)
            embed.add_field(name="AI 사용", value="예" if new_command.use_ai else "아니오", inline=True)
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"커맨드 생성 실패: {e}")
            await interaction.followup.send(
                f"❌ 커맨드 생성 중 오류가 발생했습니다: {str(e)}",
                ephemeral=True
            )
    
    async def register_slash_command(self, interaction: discord.Interaction, command: Command):
        """동적으로 슬래시 커맨드 등록"""
        @app_commands.command(name=command.name, description=command.description)
        async def dynamic_command(interaction: discord.Interaction, user_input: str = ""):
            await self.execute_dynamic_command(interaction, command, user_input)
        
        # 봇의 명령어 트리에 추가
        interaction.client.tree.add_command(dynamic_command, guild=interaction.guild)
        await interaction.client.tree.sync(guild=interaction.guild)
    
    async def execute_dynamic_command(
        self, 
        interaction: discord.Interaction, 
        command: Command, 
        user_input: str
    ):
        """동적 커맨드 실행"""
        await interaction.response.defer()
        
        try:
            # 권한 확인
            if command.get_allowed_roles():
                user_roles = [role.name for role in interaction.user.roles]
                if not any(role in command.get_allowed_roles() for role in user_roles):
                    await interaction.followup.send(
                        "❌ 이 커맨드를 사용할 권한이 없습니다.",
                        ephemeral=True
                    )
                    return
            
            # 응답 생성
            if command.use_ai:
                response = await ai_service.enhance_response(
                    command.response_template,
                    user_input,
                    {"command_name": command.name, "user": interaction.user.name}
                )
            else:
                response = command.response_template.format(
                    user=interaction.user.mention,
                    input=user_input
                )
            
            # 사용 통계 업데이트
            db = next(get_db())
            command.increment_usage()
            db.commit()
            
            await interaction.followup.send(response)
            
        except Exception as e:
            logger.error(f"동적 커맨드 실행 실패: {e}")
            await interaction.followup.send(
                "❌ 커맨드 실행 중 오류가 발생했습니다.",
                ephemeral=True
            )


class DynamicCommandsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @app_commands.command(name="추가", description="새로운 커맨드를 추가합니다")
    @check_admin_permission()
    async def add_command(self, interaction: discord.Interaction):
        """커맨드 추가 모달 표시"""
        modal = AddCommandModal()
        await interaction.response.send_modal(modal)
    
    @app_commands.command(name="커맨드목록", description="서버의 모든 커맨드를 확인합니다")
    async def list_commands(self, interaction: discord.Interaction):
        """서버의 모든 커맨드 목록 표시"""
        db = next(get_db())
        commands = db.query(Command).filter(
            Command.guild_id == str(interaction.guild.id),
            Command.is_active == True
        ).all()
        
        if not commands:
            await interaction.response.send_message(
                "이 서버에는 아직 커스텀 커맨드가 없습니다.",
                ephemeral=True
            )
            return
        
        embed = discord.Embed(
            title="📋 서버 커맨드 목록",
            color=discord.Color.blue()
        )
        
        for cmd in commands[:10]:  # 최대 10개만 표시
            embed.add_field(
                name=f"/{cmd.name}",
                value=f"{cmd.description}\n사용 횟수: {cmd.usage_count}",
                inline=False
            )
        
        if len(commands) > 10:
            embed.set_footer(text=f"총 {len(commands)}개 커맨드 중 10개만 표시")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(DynamicCommandsCog(bot))
```

## IntelliJ IDEA 설정

### 1. 프로젝트 설정

1. **프로젝트 열기**
   - IntelliJ IDEA 실행
   - "Open" 클릭하여 프로젝트 폴더 선택

2. **Python 인터프리터 설정**
   ```
   File → Project Structure → Project Settings → Project
   ```
   - Project SDK에서 가상환경의 Python 선택
   - `ai-discord-bot/venv/bin/python` (macOS/Linux)
   - `ai-discord-bot\venv\Scripts\python.exe` (Windows)

3. **모듈 설정**
   ```
   File → Project Structure → Project Settings → Modules
   ```
   - `src` 폴더를 Sources Root로 마크
   - `tests` 폴더를 Test Sources Root로 마크

### 2. 코딩 스타일 설정

```
File → Settings → Editor → Code Style → Python
```

- **Indentation**: 4 spaces
- **Maximum line length**: 88 (Black 스타일)
- **Import optimization**: Enable

### 3. 플러그인 설치

필수 플러그인:
- **Python** (Community Edition 사용 시)
- **Database Tools and SQL**
- **Git Integration**
- **Markdown**
- **.env files support**

선택적 플러그인:
- **Rainbow Brackets**
- **GitToolBox**
- **Key Promoter X**

### 4. 실행 구성 설정

#### 메인 봇 실행 구성
```
Run → Edit Configurations → + → Python
```
- **Name**: Discord Bot
- **Script path**: `src/main.py`
- **Working directory**: 프로젝트 루트
- **Environment variables**: `.env` 파일 내용 추가

#### 테스트 실행 구성
```
Run → Edit Configurations → + → Python tests → pytest
```
- **Target**: `tests/` 폴더
- **Working directory**: 프로젝트 루트

### 5. 디버깅 설정

1. **중단점 설정**: 코드 라인 번호 옆 클릭
2. **조건부 중단점**: 중단점 우클릭 → Condition 설정
3. **로그 포인트**: 중단점 우클릭 → More → Log

## 테스트 및 디버깅

### 1. 단위 테스트 작성

```python
# tests/test_ai_service.py
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
    
    async def test_analyze_intent(self, ai_service):
        with patch.object(ai_service, 'generate_response') as mock_generate:
            mock_generate.return_value = (
                '{"intent": "커맨드 생성", "confidence": 0.9}',
                {}
            )
            
            result = await ai_service.analyze_intent("새 커맨드 만들어줘")
            
            assert result["intent"] == "커맨드 생성"
            assert result["confidence"] == 0.9
```

### 2. 통합 테스트

```python
# tests/test_integration.py
import pytest
import discord
from discord.ext import commands
from unittest.mock import AsyncMock
from src.main import create_bot


@pytest.fixture
async def bot():
    """테스트용 봇 인스턴스 생성"""
    bot = create_bot()
    yield bot
    await bot.close()


async def test_add_command_integration(bot):
    """커맨드 추가 통합 테스트"""
    # Mock 길드와 채널 설정
    guild = AsyncMock(spec=discord.Guild)
    guild.id = 12345
    
    # 커맨드 추가 테스트
    cog = bot.get_cog('DynamicCommandsCog')
    assert cog is not None
    
    # 실제 커맨드 실행 시뮬레이션
    # (더 상세한 테스트 구현)
```

### 3. 성능 테스트

```python
# tests/test_performance.py
import time
import asyncio
import pytest
from src.services.ai_service import ai_service


async def test_ai_response_time():
    """AI 응답 시간 테스트"""
    start_time = time.time()
    
    response, _ = await ai_service.generate_response("간단한 테스트")
    
    end_time = time.time()
    response_time = end_time - start_time
    
    # 5초 이내 응답 확인
    assert response_time < 5.0
    assert len(response) > 0


async def test_concurrent_requests():
    """동시 요청 처리 테스트"""
    tasks = []
    for i in range(10):
        task = ai_service.generate_response(f"테스트 요청 {i}")
        tasks.append(task)
    
    start_time = time.time()
    results = await asyncio.gather(*tasks)
    end_time = time.time()
    
    # 모든 요청이 성공적으로 처리되었는지 확인
    assert len(results) == 10
    assert all(len(result[0]) > 0 for result in results)
    
    # 총 처리 시간이 합리적인지 확인 (순차 처리보다 빠른지)
    total_time = end_time - start_time
    assert total_time < 30.0  # 10개 요청을 30초 이내에 처리
```

## 배포 및 운영

### 1. Docker 컨테이너화

#### Dockerfile
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

#### docker-compose.yml
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

  redis:
    image: redis:6-alpine
    container_name: bot-redis
    restart: unless-stopped
    networks:
      - bot-network

volumes:
  postgres_data:

networks:
  bot-network:
    driver: bridge
```

### 2. GitHub Actions CI/CD

#### .github/workflows/ci.yml
```yaml
name: CI/CD Pipeline

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: [3.8, 3.9, 3.10]

    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v4
      with:
        python-version: ${{ matrix.python-version }}
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install -r requirements-dev.txt
    
    - name: Run linting
      run: |
        black --check src/
        isort --check-only src/
        mypy src/
    
    - name: Run tests
      run: |
        pytest tests/ --cov=src --cov-report=xml
    
    - name: Upload coverage to Codecov
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml

  deploy:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Deploy to production
      run: |
        # 배포 스크립트 실행
        echo "Production deployment would go here"
```

### 3. 모니터링 및 로깅

#### 로깅 설정 (config/logging_config.py)
```python
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

### 4. 운영 체크리스트

#### 배포 전 체크리스트
- [ ] 모든 테스트 통과
- [ ] 환경 변수 설정 확인
- [ ] 데이터베이스 마이그레이션 실행
- [ ] 로그 시스템 동작 확인
- [ ] 모니터링 설정 완료
- [ ] 백업 시스템 구성

#### 정기 운영 체크리스트
- [ ] 로그 파일 크기 확인
- [ ] 데이터베이스 백업 확인
- [ ] API 사용량 모니터링
- [ ] 에러 발생률 확인
- [ ] 성능 메트릭 검토
- [ ] 보안 업데이트 적용

이 가이드를 따라 개발하면 안정적이고 확장 가능한 AI Discord 봇을 구축할 수 있습니다.