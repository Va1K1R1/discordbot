<img src="https://r2cdn.perplexity.ai/pplx-full-logo-primary-dark%402x.png" class="logo" width="120"/>

# 파이썬으로 현재 구현 가능한 최신,안정된 방법으로 관리자-유저같이 특정역할에 따라 권한이 달라지고, 봇을 사용한 포인트 기능, 메시지 예약 삭제, 채널 내의 특정 유저 또는 유저들의 메시지를 갯수를 지정하여 삭제 하는 기능, 모든 채널의 모든 메시지를 특정 채널 또는 데이터베이스(mysql)에 로깅하는 기능등, 다기능 디스코드 봇을 제작 시 필요한 알고리즘과 이를 제작할 때 쓰일 매우 구체적인 지시사항이 담긴 작업 순서 목록과 해당 작업을 진행할 때 필요한 가이드라인 생성.

해당 가이드라인과 작업 순서 목록은 claude 3.0 opus 모델 기반의 AI 가 작업을 하기 위한 문서임.
실제 구현시 해당 구현된 파일 전부를 다시 이 스레드에 올려서 확인 할 예정임.

이제 충분한 정보를 수집했으니, 다기능 디스코드 봇 제작을 위한 구체적인 작업 순서 목록과 가이드라인을 생성하겠습니다.

# 다기능 디스코드 봇 제작 완전 가이드: Claude 3.0 Opus 기반 AI 개발 문서

## 목차

1. [프로젝트 개요 및 준비사항](#%ED%94%84%EB%A1%9C%EC%A0%9D%ED%8A%B8-%EA%B0%9C%EC%9A%94-%EB%B0%8F-%EC%A4%80%EB%B9%84%EC%82%AC%ED%95%AD)
2. [개발 환경 설정](#%EA%B0%9C%EB%B0%9C-%ED%99%98%EA%B2%BD-%EC%84%A4%EC%A0%95)
3. [핵심 기능별 구현 가이드](#%ED%95%B5%EC%8B%AC-%EA%B8%B0%EB%8A%A5%EB%B3%84-%EA%B5%AC%ED%98%84-%EA%B0%80%EC%9D%B4%EB%93%9C)
4. [단계별 구현 작업 순서](#%EB%8B%A8%EA%B3%84%EB%B3%84-%EA%B5%AC%ED%98%84-%EC%9E%91%EC%97%85-%EC%88%9C%EC%84%9C)
5. [코딩 가이드라인 및 베스트 프랙티스](#%EC%BD%94%EB%94%A9-%EA%B0%80%EC%9D%B4%EB%93%9C%EB%9D%BC%EC%9D%B8-%EB%B0%8F-%EB%B2%A0%EC%8A%A4%ED%8A%B8-%ED%94%84%EB%9E%99%ED%8B%B0%EC%8A%A4)
6. [테스팅 및 배포 지침](#%ED%85%8C%EC%8A%A4%ED%8C%85-%EB%B0%8F-%EB%B0%B0%ED%8F%AC-%EC%A7%80%EC%B9%A8)

## 프로젝트 개요 및 준비사항

### 기술 스택 및 버전 요구사항

- **Python**: 3.8 이상 (3.10 권장)
- **discord.py**: 2.3.2 이상 (최신 안정 버전)[1][2]
- **MySQL**: 8.0 이상
- **추가 라이브러리**: asyncio, aiosqlite, mysql-connector-python, python-dotenv, schedule


### 봇 기능 명세

1. **권한 관리 시스템**: 관리자-유저 계층 구조
2. **포인트 시스템**: 활동 기반 포인트 적립/차감
3. **메시지 예약 삭제**: 시간 지정 자동 삭제
4. **선택적 메시지 삭제**: 특정 유저/개수 지정 삭제
5. **통합 로깅 시스템**: 모든 채널 메시지 로깅

### 디스코드 봇 생성 및 초기 설정

```bash
# 1. Discord Developer Portal 접속
# https://discord.com/developers/applications

# 2. New Application 생성
# 3. Bot 탭에서 토큰 발급
# 4. Privileged Gateway Intents 모두 활성화
# - PRESENCE INTENT
# - SERVER MEMBERS INTENT  
# - MESSAGE CONTENT INTENT
```


## 개발 환경 설정

### 1. 프로젝트 구조 생성

```
discord_bot/
├── main.py                 # 메인 실행 파일
├── config/
│   ├── __init__.py
│   ├── settings.py         # 설정 관리
│   └── database.py         # DB 연결 설정
├── cogs/                   # 기능별 모듈
│   ├── __init__.py
│   ├── permissions.py      # 권한 관리
│   ├── points.py          # 포인트 시스템
│   ├── message_manager.py # 메시지 관리
│   └── logging_system.py  # 로깅 시스템
├── utils/
│   ├── __init__.py
│   ├── helpers.py         # 헬퍼 함수
│   └── decorators.py      # 데코레이터
├── database/
│   ├── __init__.py
│   ├── models.py          # 데이터베이스 모델
│   └── migrations.sql     # 초기 DB 스키마
├── logs/                  # 로그 파일 저장
├── .env                   # 환경 변수
├── requirements.txt       # 의존성 목록
└── README.md             # 프로젝트 문서
```


### 2. 가상환경 및 의존성 설치

```bash
# 가상환경 생성
python -m venv discord_bot_env

# 가상환경 활성화 (Windows)
discord_bot_env\Scripts\activate

# 가상환경 활성화 (Linux/Mac)
source discord_bot_env/bin/activate

# 의존성 설치
pip install -r requirements.txt
```


### 3. requirements.txt 파일 내용

```txt
discord.py>=2.3.2
python-dotenv>=1.0.0
mysql-connector-python>=8.1.0
aiofiles>=23.1.0
asyncio-mqtt>=0.16.1
schedule>=1.2.0
python-dateutil>=2.8.2
```


### 4. 환경 변수 설정 (.env)

```env
# Discord 설정
DISCORD_TOKEN=your_bot_token_here
GUILD_ID=your_guild_id_here

# MySQL 데이터베이스 설정
DB_HOST=localhost
DB_PORT=3306
DB_USER=discord_bot_user
DB_PASSWORD=your_password_here
DB_NAME=discord_bot_db

# 로깅 설정
LOG_LEVEL=INFO
LOG_CHANNEL_ID=your_log_channel_id

# 봇 설정
COMMAND_PREFIX=!
ADMIN_ROLE_ID=your_admin_role_id
MODERATOR_ROLE_ID=your_moderator_role_id
```


## 핵심 기능별 구현 가이드

### 1. 권한 관리 시스템

#### 권한 레벨 정의

```python
# utils/permissions.py
from enum import Enum

class PermissionLevel(Enum):
    OWNER = 5        # 봇 소유자
    ADMIN = 4        # 서버 관리자
    MODERATOR = 3    # 모더레이터
    TRUSTED = 2      # 신뢰 유저
    MEMBER = 1       # 일반 멤버
    RESTRICTED = 0   # 제한 유저

class PermissionChecker:
    @staticmethod
    async def check_permission(member, required_level: PermissionLevel):
        """사용자 권한 확인"""
        user_level = await PermissionChecker.get_user_level(member)
        return user_level.value >= required_level.value
    
    @staticmethod
    async def get_user_level(member):
        """사용자 권한 레벨 조회"""
        # 봇 소유자 확인
        if member.id == BOT_OWNER_ID:
            return PermissionLevel.OWNER
            
        # 역할 기반 권한 확인
        role_permissions = {
            ADMIN_ROLE_ID: PermissionLevel.ADMIN,
            MODERATOR_ROLE_ID: PermissionLevel.MODERATOR,
            TRUSTED_ROLE_ID: PermissionLevel.TRUSTED
        }
        
        for role in member.roles:
            if role.id in role_permissions:
                return role_permissions[role.id]
                
        return PermissionLevel.MEMBER
```


#### 권한 데코레이터 구현[3][4]

```python
# utils/decorators.py
from functools import wraps
import discord
from discord.ext import commands

def require_permission(level: PermissionLevel):
    """권한 레벨 검증 데코레이터"""
    def decorator(func):
        @wraps(func)
        async def wrapper(self, ctx, *args, **kwargs):
            if not await PermissionChecker.check_permission(ctx.author, level):
                embed = discord.Embed(
                    title="❌ 권한 부족",
                    description=f"이 명령어를 사용하려면 {level.name} 권한이 필요합니다.",
                    color=discord.Color.red()
                )
                await ctx.send(embed=embed)
                return
            return await func(self, ctx, *args, **kwargs)
        return wrapper
    return decorator
```


### 2. 포인트 시스템 구현

#### 데이터베이스 스키마[5][6]

```sql
-- database/migrations.sql
CREATE TABLE IF NOT EXISTS user_points (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT NOT NULL UNIQUE,
    username VARCHAR(100) NOT NULL,
    points INT DEFAULT 0,
    total_earned INT DEFAULT 0,
    total_spent INT DEFAULT 0,
    level INT DEFAULT 1,
    experience INT DEFAULT 0,
    last_message_time TIMESTAMP NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_user_id (user_id),
    INDEX idx_points (points),
    INDEX idx_level (level)
);

CREATE TABLE IF NOT EXISTS point_transactions (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT NOT NULL,
    transaction_type ENUM('EARN', 'SPEND', 'ADMIN_ADD', 'ADMIN_REMOVE') NOT NULL,
    amount INT NOT NULL,
    reason VARCHAR(255) NOT NULL,
    admin_id BIGINT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_user_id (user_id),
    INDEX idx_transaction_type (transaction_type),
    INDEX idx_created_at (created_at),
    FOREIGN KEY (user_id) REFERENCES user_points(user_id) ON DELETE CASCADE
);
```


#### 포인트 시스템 클래스[7][8]

```python
# cogs/points.py
import discord
from discord.ext import commands
import asyncio
from datetime import datetime, timedelta
import mysql.connector.aio

class PointSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.message_cooldown = {}  # 메시지 쿨다운 관리
        self.point_rates = {
            'message': 1,           # 메시지당 포인트
            'reaction': 0.5,        # 반응당 포인트
            'voice_minute': 2,      # 음성 채팅 분당 포인트
            'daily_bonus': 50       # 일일 보너스
        }
        
    async def add_points(self, user_id: int, amount: int, reason: str, admin_id: int = None):
        """포인트 추가"""
        async with self.bot.db_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                # 사용자 포인트 업데이트
                await cursor.execute("""
                    INSERT INTO user_points (user_id, username, points, total_earned) 
                    VALUES (%s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE 
                    points = points + %s,
                    total_earned = total_earned + %s,
                    updated_at = CURRENT_TIMESTAMP
                """, (user_id, "Unknown", amount, amount, amount, amount))
                
                # 거래 기록 추가
                transaction_type = 'ADMIN_ADD' if admin_id else 'EARN'
                await cursor.execute("""
                    INSERT INTO point_transactions 
                    (user_id, transaction_type, amount, reason, admin_id)
                    VALUES (%s, %s, %s, %s, %s)
                """, (user_id, transaction_type, amount, reason, admin_id))
                
                await conn.commit()
    
    async def remove_points(self, user_id: int, amount: int, reason: str, admin_id: int = None):
        """포인트 차감"""
        async with self.bot.db_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                # 현재 포인트 확인
                await cursor.execute("SELECT points FROM user_points WHERE user_id = %s", (user_id,))
                result = await cursor.fetchone()
                
                if not result or result[0] < amount:
                    return False, "포인트가 부족합니다."
                
                # 포인트 차감
                await cursor.execute("""
                    UPDATE user_points 
                    SET points = points - %s, total_spent = total_spent + %s,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = %s
                """, (amount, amount, user_id))
                
                # 거래 기록 추가
                transaction_type = 'ADMIN_REMOVE' if admin_id else 'SPEND'
                await cursor.execute("""
                    INSERT INTO point_transactions 
                    (user_id, transaction_type, amount, reason, admin_id)
                    VALUES (%s, %s, %s, %s, %s)
                """, (user_id, transaction_type, amount, reason, admin_id))
                
                await conn.commit()
                return True, "포인트가 성공적으로 차감되었습니다."

    @commands.Cog.listener()
    async def on_message(self, message):
        """메시지 기반 포인트 적립[24]"""
        if message.author.bot:
            return
            
        user_id = message.author.id
        current_time = datetime.now()
        
        # 쿨다운 확인 (1분당 1번만 적립)
        if user_id in self.message_cooldown:
            if current_time - self.message_cooldown[user_id] < timedelta(minutes=1):
                return
        
        self.message_cooldown[user_id] = current_time
        
        # 포인트 적립
        await self.add_points(user_id, self.point_rates['message'], "메시지 전송")
        
        # 경험치 시스템 (레벨업 확인)
        await self.check_level_up(user_id)

    @commands.command(name="포인트")
    async def check_points(self, ctx, member: discord.Member = None):
        """포인트 조회"""
        target = member or ctx.author
        
        async with self.bot.db_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("""
                    SELECT points, total_earned, total_spent, level 
                    FROM user_points WHERE user_id = %s
                """, (target.id,))
                result = await cursor.fetchone()
                
                if not result:
                    embed = discord.Embed(
                        title="📊 포인트 정보",
                        description=f"{target.display_name}님의 포인트 정보를 찾을 수 없습니다.",
                        color=discord.Color.orange()
                    )
                else:
                    points, total_earned, total_spent, level = result
                    embed = discord.Embed(
                        title="📊 포인트 정보",
                        color=discord.Color.blue()
                    )
                    embed.add_field(name="현재 포인트", value=f"{points:,}", inline=True)
                    embed.add_field(name="총 획득", value=f"{total_earned:,}", inline=True)
                    embed.add_field(name="총 사용", value=f"{total_spent:,}", inline=True)
                    embed.add_field(name="레벨", value=f"{level}", inline=True)
                    embed.set_thumbnail(url=target.avatar.url if target.avatar else None)
                
                await ctx.send(embed=embed)

    @commands.command(name="포인트추가")
    @require_permission(PermissionLevel.ADMIN)
    async def admin_add_points(self, ctx, member: discord.Member, amount: int, *, reason: str = "관리자 지급"):
        """관리자 포인트 추가"""
        if amount <= 0:
            await ctx.send("❌ 포인트는 양수여야 합니다.")
            return
            
        await self.add_points(member.id, amount, reason, ctx.author.id)
        
        embed = discord.Embed(
            title="✅ 포인트 지급 완료",
            description=f"{member.display_name}님에게 {amount:,} 포인트를 지급했습니다.",
            color=discord.Color.green()
        )
        embed.add_field(name="사유", value=reason, inline=False)
        await ctx.send(embed=embed)
```


### 3. 메시지 예약 삭제 시스템

#### 예약 삭제 스케줄러[9][10]

```python
# cogs/message_manager.py
import discord
from discord.ext import commands, tasks
from datetime import datetime, timedelta
import asyncio
import json

class MessageManager(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.scheduled_deletions = {}  # 예약된 삭제 작업
        self.deletion_checker.start()
        
    @tasks.loop(minutes=1)
    async def deletion_checker(self):
        """예약된 삭제 작업 확인"""
        current_time = datetime.now()
        to_delete = []
        
        for message_id, deletion_data in self.scheduled_deletions.items():
            if current_time >= deletion_data['delete_at']:
                to_delete.append(message_id)
                
        for message_id in to_delete:
            await self.execute_scheduled_deletion(message_id)
            
    async def execute_scheduled_deletion(self, message_id):
        """예약된 삭제 실행"""
        try:
            deletion_data = self.scheduled_deletions.pop(message_id, None)
            if not deletion_data:
                return
                
            channel = self.bot.get_channel(deletion_data['channel_id'])
            if not channel:
                return
                
            message = await channel.fetch_message(message_id)
            await message.delete()
            
            # 삭제 로그
            log_embed = discord.Embed(
                title="🗑️ 예약 삭제 실행",
                description=f"메시지가 예약된 시간에 삭제되었습니다.",
                color=discord.Color.orange(),
                timestamp=datetime.now()
            )
            log_embed.add_field(name="채널", value=channel.mention, inline=True)
            log_embed.add_field(name="삭제자", value=f"<@{deletion_data['requester_id']}>", inline=True)
            
            await self.bot.log_channel.send(embed=log_embed)
            
        except discord.NotFound:
            # 메시지가 이미 삭제됨
            pass
        except Exception as e:
            print(f"예약 삭제 실행 중 오류: {e}")

    @commands.command(name="예약삭제")
    @require_permission(PermissionLevel.MODERATOR)
    async def schedule_deletion(self, ctx, message_id: int, delay_minutes: int, *, reason: str = "예약 삭제"):
        """메시지 예약 삭제[78][81]"""
        if delay_minutes <= 0 or delay_minutes > 10080:  # 최대 7일
            await ctx.send("❌ 삭제 시간은 1분에서 7일(10080분) 사이여야 합니다.")
            return
            
        try:
            message = await ctx.channel.fetch_message(message_id)
        except discord.NotFound:
            await ctx.send("❌ 메시지를 찾을 수 없습니다.")
            return
            
        delete_at = datetime.now() + timedelta(minutes=delay_minutes)
        
        # 예약 삭제 등록
        self.scheduled_deletions[message_id] = {
            'channel_id': ctx.channel.id,
            'delete_at': delete_at,
            'requester_id': ctx.author.id,
            'reason': reason
        }
        
        embed = discord.Embed(
            title="⏰ 메시지 삭제 예약",
            description=f"메시지가 {delay_minutes}분 후에 삭제됩니다.",
            color=discord.Color.yellow()
        )
        embed.add_field(name="삭제 예정 시간", value=delete_at.strftime("%Y-%m-%d %H:%M:%S"), inline=False)
        embed.add_field(name="사유", value=reason, inline=False)
        
        await ctx.send(embed=embed)

    @commands.command(name="삭제취소")
    @require_permission(PermissionLevel.MODERATOR)
    async def cancel_deletion(self, ctx, message_id: int):
        """예약 삭제 취소"""
        if message_id in self.scheduled_deletions:
            del self.scheduled_deletions[message_id]
            await ctx.send("✅ 예약된 삭제가 취소되었습니다.")
        else:
            await ctx.send("❌ 해당 메시지에 대한 예약 삭제를 찾을 수 없습니다.")
```


### 4. 선택적 메시지 삭제 시스템[11][12]

```python
# cogs/message_manager.py (계속)

    @commands.command(name="청소", aliases=["purge", "clear"])
    @require_permission(PermissionLevel.MODERATOR)
    async def purge_messages(self, ctx, amount: int = 10, target: discord.Member = None):
        """메시지 대량 삭제[22][25]"""
        if amount <= 0 or amount > 1000:
            await ctx.send("❌ 삭제할 메시지 수는 1-1000 사이여야 합니다.")
            return
            
        # 명령어 메시지 삭제
        await ctx.message.delete()
        
        def check_message(message):
            if target:
                return message.author == target
            return True
            
        try:
            deleted = await ctx.channel.purge(limit=amount, check=check_message)
            
            # 결과 메시지 (5초 후 자동 삭제)
            result_msg = await ctx.send(f"✅ {len(deleted)}개의 메시지를 삭제했습니다.")
            await asyncio.sleep(5)
            await result_msg.delete()
            
            # 로깅
            log_embed = discord.Embed(
                title="🧹 메시지 대량 삭제",
                color=discord.Color.orange(),
                timestamp=datetime.now()
            )
            log_embed.add_field(name="채널", value=ctx.channel.mention, inline=True)
            log_embed.add_field(name="삭제자", value=ctx.author.mention, inline=True)
            log_embed.add_field(name="삭제된 메시지 수", value=len(deleted), inline=True)
            if target:
                log_embed.add_field(name="대상 유저", value=target.mention, inline=True)
                
            await self.bot.log_channel.send(embed=log_embed)
            
        except discord.Forbidden:
            await ctx.send("❌ 메시지를 삭제할 권한이 없습니다.")
        except discord.HTTPException:
            await ctx.send("❌ 2주 이상 된 메시지는 삭제할 수 없습니다.")

    @commands.command(name="유저삭제")
    @require_permission(PermissionLevel.MODERATOR)
    async def delete_user_messages(self, ctx, target: discord.Member, amount: int = 50):
        """특정 유저의 메시지 삭제"""
        if amount <= 0 or amount > 500:
            await ctx.send("❌ 삭제할 메시지 수는 1-500 사이여야 합니다.")
            return
            
        deleted_count = 0
        async for message in ctx.channel.history(limit=amount * 2):  # 여유롭게 검색
            if message.author == target and deleted_count < amount:
                try:
                    await message.delete()
                    deleted_count += 1
                    await asyncio.sleep(0.5)  # API 레이트 리밋 방지
                except:
                    continue
                    
        embed = discord.Embed(
            title="🗑️ 유저 메시지 삭제 완료",
            description=f"{target.display_name}님의 메시지 {deleted_count}개를 삭제했습니다.",
            color=discord.Color.green()
        )
        
        await ctx.send(embed=embed)
```


### 5. 통합 로깅 시스템[13]

#### 로깅 설정 및 데이터베이스 스키마

```sql
-- 메시지 로깅 테이블
CREATE TABLE IF NOT EXISTS message_logs (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    message_id BIGINT NOT NULL,
    channel_id BIGINT NOT NULL,
    channel_name VARCHAR(100) NOT NULL,
    author_id BIGINT NOT NULL,
    author_name VARCHAR(100) NOT NULL,
    content TEXT,
    attachments JSON,
    embeds JSON,
    message_type ENUM('text', 'embed', 'file', 'image') DEFAULT 'text',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_message_id (message_id),
    INDEX idx_channel_id (channel_id),
    INDEX idx_author_id (author_id),
    INDEX idx_created_at (created_at)
);

-- 이벤트 로깅 테이블
CREATE TABLE IF NOT EXISTS event_logs (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    event_type VARCHAR(50) NOT NULL,
    user_id BIGINT,
    channel_id BIGINT,
    details JSON,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_event_type (event_type),
    INDEX idx_user_id (user_id),
    INDEX idx_timestamp (timestamp)
);
```


#### 로깅 시스템 구현

```python
# cogs/logging_system.py
import discord
from discord.ext import commands
import json
from datetime import datetime
import logging

class LoggingSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.setup_logging()
        
    def setup_logging(self):
        """파일 로깅 설정[39]"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s:%(levelname)s:%(name)s: %(message)s',
            handlers=[
                logging.FileHandler('logs/discord_bot.log', encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger('discord_bot')

    @commands.Cog.listener()
    async def on_message(self, message):
        """모든 메시지 로깅"""
        if message.author.bot:
            return
            
        # 첨부파일 정보 추출
        attachments = []
        if message.attachments:
            for attachment in message.attachments:
                attachments.append({
                    'filename': attachment.filename,
                    'size': attachment.size,
                    'url': attachment.url
                })
        
        # 임베드 정보 추출
        embeds = []
        if message.embeds:
            for embed in message.embeds:
                embeds.append({
                    'title': embed.title,
                    'description': embed.description,
                    'color': embed.color.value if embed.color else None
                })
        
        # 메시지 타입 결정
        message_type = 'text'
        if message.attachments:
            if any(att.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp')) 
                   for att in message.attachments):
                message_type = 'image'
            else:
                message_type = 'file'
        elif message.embeds:
            message_type = 'embed'
            
        # 데이터베이스 로깅
        async with self.bot.db_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("""
                    INSERT INTO message_logs 
                    (message_id, channel_id, channel_name, author_id, author_name, 
                     content, attachments, embeds, message_type)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    message.id, message.channel.id, message.channel.name,
                    message.author.id, message.author.display_name,
                    message.content, json.dumps(attachments), json.dumps(embeds), message_type
                ))
                await conn.commit()
        
        # 특정 채널에 로깅 (선택사항)
        if self.bot.log_channel and message.channel.id != self.bot.log_channel.id:
            embed = discord.Embed(
                description=message.content[:1000] if message.content else "*첨부파일*",
                color=discord.Color.blue(),
                timestamp=message.created_at
            )
            embed.set_author(
                name=f"{message.author.display_name} ({message.author})",
                icon_url=message.author.avatar.url if message.author.avatar else None
            )
            embed.add_field(name="채널", value=message.channel.mention, inline=True)
            embed.add_field(name="메시지 ID", value=message.id, inline=True)
            
            if attachments:
                embed.add_field(name="첨부파일", value=f"{len(attachments)}개", inline=True)
                
            await self.bot.log_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_message_delete(self, message):
        """메시지 삭제 로깅"""
        if message.author.bot:
            return
            
        # 이벤트 로깅
        await self.log_event('message_delete', {
            'message_id': message.id,
            'channel_id': message.channel.id,
            'author_id': message.author.id,
            'content': message.content,
            'deleted_at': datetime.now().isoformat()
        })
        
        # 채널 로깅
        if self.bot.log_channel:
            embed = discord.Embed(
                title="🗑️ 메시지 삭제됨",
                description=message.content[:1000] if message.content else "*내용 없음*",
                color=discord.Color.red(),
                timestamp=datetime.now()
            )
            embed.set_author(
                name=f"{message.author.display_name} ({message.author})",
                icon_url=message.author.avatar.url if message.author.avatar else None
            )
            embed.add_field(name="채널", value=message.channel.mention, inline=True)
            embed.add_field(name="메시지 ID", value=message.id, inline=True)
            
            await self.bot.log_channel.send(embed=embed)

    async def log_event(self, event_type: str, details: dict, user_id: int = None, channel_id: int = None):
        """이벤트 로깅"""
        async with self.bot.db_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("""
                    INSERT INTO event_logs (event_type, user_id, channel_id, details)
                    VALUES (%s, %s, %s, %s)
                """, (event_type, user_id, channel_id, json.dumps(details)))
                await conn.commit()

    @commands.command(name="로그검색")
    @require_permission(PermissionLevel.ADMIN)
    async def search_logs(self, ctx, user: discord.Member = None, limit: int = 10):
        """로그 검색"""
        if limit > 50:
            limit = 50
            
        async with self.bot.db_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                if user:
                    await cursor.execute("""
                        SELECT channel_name, content, created_at 
                        FROM message_logs 
                        WHERE author_id = %s 
                        ORDER BY created_at DESC 
                        LIMIT %s
                    """, (user.id, limit))
                else:
                    await cursor.execute("""
                        SELECT channel_name, author_name, content, created_at 
                        FROM message_logs 
                        ORDER BY created_at DESC 
                        LIMIT %s
                    """, (limit,))
                
                results = await cursor.fetchall()
                
        if not results:
            await ctx.send("검색 결과가 없습니다.")
            return
            
        embed = discord.Embed(
            title=f"📋 로그 검색 결과 (최근 {len(results)}개)",
            color=discord.Color.blue()
        )
        
        for result in results:
            if user:
                channel_name, content, created_at = result
                embed.add_field(
                    name=f"#{channel_name} - {created_at.strftime('%m/%d %H:%M')}",
                    value=content[:100] + "..." if len(content) > 100 else content,
                    inline=False
                )
            else:
                channel_name, author_name, content, created_at = result
                embed.add_field(
                    name=f"#{channel_name} - {author_name} - {created_at.strftime('%m/%d %H:%M')}",
                    value=content[:100] + "..." if len(content) > 100 else content,
                    inline=False
                )
                
        await ctx.send(embed=embed)
```


## 단계별 구현 작업 순서

### Phase 1: 기초 인프라 구축 (1-2일)

1. **개발 환경 설정**
    - Python 가상환경 생성 및 활성화
    - 필요한 라이브러리 설치 (`pip install -r requirements.txt`)
    - 프로젝트 폴더 구조 생성
    - 환경 변수 파일(.env) 설정
2. **데이터베이스 설정**
    - MySQL 서버 설치 및 구성
    - 데이터베이스 및 사용자 계정 생성
    - 초기 테이블 스키마 생성 (`database/migrations.sql` 실행)
    - 연결 테스트
3. **봇 기본 틀 구성**

```python
# main.py 기본 구조 작성
import discord
from discord.ext import commands
import asyncio
from config.settings import Settings
from config.database import DatabaseManager

class DiscordBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all()
        super().__init__(command_prefix=Settings.COMMAND_PREFIX, intents=intents)
        self.db = DatabaseManager()
        
    async def setup_hook(self):
        await self.db.initialize()
        await self.load_extension('cogs.permissions')
        await self.load_extension('cogs.points')
        await self.load_extension('cogs.message_manager')
        await self.load_extension('cogs.logging_system')
        
    async def on_ready(self):
        print(f'{self.user} 온라인!')
        
if __name__ == "__main__":
    bot = DiscordBot()
    bot.run(Settings.DISCORD_TOKEN)
```


### Phase 2: 권한 시스템 구현 (2-3일)

4. **권한 레벨 정의**
    - `utils/permissions.py`에 PermissionLevel enum 작성
    - PermissionChecker 클래스 구현
    - 권한 확인 로직 작성
5. **권한 데코레이터 구현**
    - `utils/decorators.py`에 @require_permission 데코레이터 작성
    - 권한 부족 시 에러 메시지 표시 로직
    - 테스트 명령어로 권한 시스템 검증
6. **권한 관리 Cog 작성**

```python
# cogs/permissions.py 핵심 기능
@commands.command(name="권한확인")
async def check_permission(self, ctx, member: discord.Member = None):
    # 사용자 권한 레벨 표시
    
@commands.command(name="권한부여")
@require_permission(PermissionLevel.ADMIN)
async def grant_permission(self, ctx, member: discord.Member, role: discord.Role):
    # 역할 부여 기능
```


### Phase 3: 포인트 시스템 구현 (3-4일)

7. **포인트 데이터베이스 모델 완성**
    - `user_points` 테이블 최적화
    - `point_transactions` 테이블 관계 설정
    - 인덱스 및 제약조건 추가
8. **포인트 시스템 Cog 구현**
    - 메시지 기반 포인트 적립 (`on_message` 이벤트)
    - 쿨다운 시스템 구현 (1분당 1회 적립)
    - 포인트 조회/추가/차감 명령어
9. **레벨 시스템 추가**

```python
async def calculate_level(self, experience: int) -> int:
    # 경험치 기반 레벨 계산 공식
    return int((experience / 100) ** 0.5) + 1
    
async def check_level_up(self, user_id: int):
    # 레벨업 확인 및 축하 메시지
```

10. **포인트 상점 시스템 (선택사항)**
    - 아이템 구매 기능
    - 역할 구매 시스템
    - 포인트 이력 조회

### Phase 4: 메시지 관리 시스템 (2-3일)

11. **메시지 예약 삭제 기능**
    - 스케줄러 시스템 구현 (`@tasks.loop`)
    - 예약 삭제 데이터 저장 구조
    - 예약/취소 명령어 구현
12. **대량 메시지 삭제 기능**
    - 권한 확인 로직
    - 안전한 삭제 (2주 제한, 개수 제한)
    - 진행 상황 표시
13. **선택적 메시지 삭제**
    - 특정 유저 메시지 삭제
    - 키워드 기반 삭제
    - 파일/이미지만 삭제 등 고급 필터

### Phase 5: 로깅 시스템 구현 (2-3일)

14. **메시지 로깅 시스템**
    - 모든 채널 메시지 실시간 로깅
    - 첨부파일 및 임베드 정보 저장
    - 효율적인 데이터베이스 저장
15. **이벤트 로깅**
    - 메시지 삭제/수정 로깅
    - 멤버 입장/퇴장 로깅
    - 역할 변경 로깅
16. **로그 검색 및 분석 기능**
    - 사용자별 메시지 검색
    - 기간별 통계
    - 로그 내보내기

### Phase 6: 통합 및 최적화 (2-3일)

17. **에러 처리 및 예외 상황 대응**
    - 글로벌 에러 핸들러
    - 권한 에러 처리
    - 네트워크 연결 실패 처리
18. **성능 최적화**
    - 데이터베이스 쿼리 최적화
    - 메모리 사용량 모니터링
    - 비동기 처리 개선
19. **테스트 및 디버깅**
    - 각 기능별 단위 테스트
    - 통합 테스트
    - 부하 테스트

### Phase 7: 고급 기능 및 배포 (1-2일)

20. **관리자 패널 웹 인터페이스 (선택사항)**
    - Flask/FastAPI 기반 웹 대시보드
    - 통계 시각화
    - 원격 봇 관리
21. **백업 및 복구 시스템**
    - 데이터베이스 자동 백업
    - 설정 파일 백업
    - 장애 복구 절차
22. **배포 및 모니터링**
    - Docker 컨테이너화
    - 프로세스 매니저 설정 (PM2, systemd)
    - 로그 모니터링 시스템

## 코딩 가이드라인 및 베스트 프랙티스

### 1. 코드 구조 및 스타일 가이드

#### PEP 8 준수 및 코딩 컨벤션

```python
# 좋은 예시
class MessageManager(commands.Cog):
    """메시지 관리 시스템
    
    주요 기능:
    - 메시지 예약 삭제
    - 대량 메시지 정리
    - 선택적 메시지 삭제
    """
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.scheduled_deletions: Dict[int, Dict[str, Any]] = {}
        
    async def validate_message_deletion(
        self, 
        ctx: commands.Context, 
        message_id: int,
        permission_required: PermissionLevel = PermissionLevel.MODERATOR
    ) -> Tuple[bool, Optional[discord.Message]]:
        """메시지 삭제 유효성 검사
        
        Args:
            ctx: 명령어 컨텍스트
            message_id: 삭제할 메시지 ID
            permission_required: 필요한 권한 레벨
            
        Returns:
            (성공 여부, 메시지 객체)
        """
        # 권한 확인
        if not await PermissionChecker.check_permission(ctx.author, permission_required):
            return False, None
            
        # 메시지 존재 확인
        try:
            message = await ctx.channel.fetch_message(message_id)
            return True, message
        except discord.NotFound:
            return False, None
```


#### 타입 힌트 활용

```python
from typing import Optional, Dict, List, Tuple, Union, Any
from datetime import datetime, timedelta

class PointSystem:
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.cooldowns: Dict[int, datetime] = {}
        
    async def add_points(
        self, 
        user_id: int, 
        amount: int, 
        reason: str,
        admin_id: Optional[int] = None
    ) -> Tuple[bool, str]:
        """포인트 추가
        
        Returns:
            (성공 여부, 결과 메시지)
        """
        pass
```


### 2. 비동기 프로그래밍 가이드라인

#### 효율적인 비동기 처리

```python
# 좋은 예시: 병렬 처리
async def bulk_delete_messages(
    self, 
    channel: discord.TextChannel, 
    message_ids: List[int]
) -> List[int]:
    """메시지 대량 삭제 (병렬 처리)"""
    
    async def delete_single_message(message_id: int) -> Optional[int]:
        try:
            message = await channel.fetch_message(message_id)
            await message.delete()
            return message_id
        except discord.NotFound:
            return None
    
    # 동시 실행 (최대 5개씩)
    semaphore = asyncio.Semaphore(5)
    
    async def limited_delete(message_id: int):
        async with semaphore:
            return await delete_single_message(message_id)
    
    tasks = [limited_delete(msg_id) for msg_id in message_ids]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    return [result for result in results if isinstance(result, int)]

# 나쁜 예시: 순차 처리
async def bulk_delete_messages_bad(self, channel, message_ids):
    """비효율적인 순차 삭제"""
    deleted = []
    for message_id in message_ids:
        try:
            message = await channel.fetch_message(message_id)
            await message.delete()
            deleted.append(message_id)
            await asyncio.sleep(1)  # 불필요한 지연
        except:
            continue
    return deleted
```


#### 데이터베이스 연결 관리

```python
class DatabaseManager:
    def __init__(self):
        self.pool: Optional[aiomysql.Pool] = None
        
    async def initialize(self):
        """데이터베이스 연결 풀 초기화"""
        self.pool = await aiomysql.create_pool(
            host=Settings.DB_HOST,
            port=Settings.DB_PORT,
            user=Settings.DB_USER,
            password=Settings.DB_PASSWORD,
            db=Settings.DB_NAME,
            minsize=1,
            maxsize=10,
            autocommit=False
        )
        
    async def execute_query(
        self, 
        query: str, 
        params: Optional[Tuple] = None
    ) -> List[Dict[str, Any]]:
        """안전한 쿼리 실행"""
        async with self.pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                await cursor.execute(query, params)
                if query.strip().upper().startswith('SELECT'):
                    return await cursor.fetchall()
                else:
                    await conn.commit()
                    return []
```


### 3. 에러 처리 및 로깅

#### 포괄적인 에러 핸들링

```python
class ErrorHandler(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, error: commands.CommandError):
        """글로벌 명령어 에러 핸들러"""
        
        # 권한 에러
        if isinstance(error, commands.MissingPermissions):
            embed = discord.Embed(
                title="❌ 권한 부족",
                description="이 명령어를 사용할 권한이 없습니다.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            
        # 쿨다운 에러
        elif isinstance(error, commands.CommandOnCooldown):
            embed = discord.Embed(
                title="⏰ 쿨다운",
                description=f"이 명령어는 {error.retry_after:.1f}초 후에 사용할 수 있습니다.",
                color=discord.Color.orange()
            )
            await ctx.send(embed=embed)
            
        # 인수 에러
        elif isinstance(error, commands.BadArgument):
            embed = discord.Embed(
                title="❓ 잘못된 인수",
                description="명령어 사용법을 확인해주세요.",
                color=discord.Color.yellow()
            )
            embed.add_field(
                name="사용법", 
                value=f"`{ctx.prefix}{ctx.command.qualified_name} {ctx.command.signature}`",
                inline=False
            )
            await ctx.send(embed=embed)
            
        # 기타 에러
        else:
            self.bot.logger.error(f"명령어 에러: {ctx.command}", exc_info=error)
            
            embed = discord.Embed(
                title="🔧 내부 오류",
                description="명령어 처리 중 오류가 발생했습니다. 관리자에게 문의해주세요.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)

# 개별 명령어 에러 처리
@commands.command(name="포인트추가")
async def add_points_command(self, ctx, member: discord.Member, amount: int):
    try:
        # 입력값 검증
        if amount <= 0:
            raise ValueError("포인트는 양수여야 합니다.")
        if amount > 1000000:
            raise ValueError("한 번에 추가할 수 있는 포인트는 최대 1,000,000점입니다.")
            
        # 포인트 추가 실행
        success, message = await self.add_points(member.id, amount, "관리자 지급", ctx.author.id)
        
        if success:
            embed = discord.Embed(
                title="✅ 포인트 지급 완료",
                description=message,
                color=discord.Color.green()
            )
        else:
            embed = discord.Embed(
                title="❌ 포인트 지급 실패",
                description=message,
                color=discord.Color.red()
            )
            
        await ctx.send(embed=embed)
        
    except ValueError as e:
        await ctx.send(f"❌ 입력 오류: {e}")
    except Exception as e:
        self.bot.logger.error(f"포인트 추가 중 오류: {e}")
        await ctx.send("❌ 포인트 지급 중 오류가 발생했습니다.")
```


### 4. 보안 및 데이터 검증

#### SQL 인젝션 방지

```python
# 좋은 예시: 매개변수화된 쿼리
async def get_user_points(self, user_id: int) -> Optional[Dict[str, Any]]:
    query = "SELECT * FROM user_points WHERE user_id = %s"
    results = await self.db.execute_query(query, (user_id,))
    return results[0] if results else None

# 나쁜 예시: 문자열 포맷팅 (보안 위험)
async def get_user_points_bad(self, user_id: int):
    query = f"SELECT * FROM user_points WHERE user_id = {user_id}"  # 위험!
    return await self.db.execute_query(query)
```


#### 입력값 검증 및 정리

```python
class InputValidator:
    @staticmethod
    def sanitize_message_content(content: str) -> str:
        """메시지 내용 정리"""
        # HTML 태그 제거
        import re
        content = re.sub(r'<[^>]+>', '', content)
        
        # 특수문자 이스케이프
        content = content.replace('`', '\\`').replace('*', '\\*')
        
        # 길이 제한
        if len(content) > 2000:
            content = content[:1997] + "..."
            
        return content
    
    @staticmethod
    def validate_amount(amount: int, min_val: int = 1, max_val: int = 1000000) -> bool:
        """포인트 수량 검증"""
        return min_val <= amount <= max_val
    
    @staticmethod
    def validate_time_format(time_str: str) -> Optional[datetime]:
        """시간 형식 검증"""
        formats = ["%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%m/%d %H:%M"]
        
        for fmt in formats:
            try:
                return datetime.strptime(time_str, fmt)
            except ValueError:
                continue
                
        return None
```


### 5. 성능 최적화 가이드라인

#### 데이터베이스 최적화

```python
# 인덱스 활용 쿼리 작성
CREATE INDEX idx_user_points_composite ON user_points(user_id, points, level);
CREATE INDEX idx_message_logs_channel_time ON message_logs(channel_id, created_at);

# 배치 처리 구현
async def batch_update_user_activity(self, user_activities: List[Dict[str, Any]]):
    """사용자 활동 배치 업데이트"""
    if not user_activities:
        return
        
    # 배치 쿼리 준비
    values = []
    for activity in user_activities:
        values.append((
            activity['user_id'],
            activity['points'],
            activity['experience'],
            activity['last_active']
        ))
    
    query = """
        INSERT INTO user_points (user_id, points, experience, last_message_time)
        VALUES (%s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
        points = points + VALUES(points),
        experience = experience + VALUES(experience),
        last_message_time = VALUES(last_message_time)
    """
    
    async with self.bot.db_pool.acquire() as conn:
        async with conn.cursor() as cursor:
            await cursor.executemany(query, values)
            await conn.commit()
```


#### 메모리 관리

```python
class MemoryEfficientCache:
    def __init__(self, max_size: int = 1000):
        self.cache: Dict[str, Any] = {}
        self.access_times: Dict[str, datetime] = {}
        self.max_size = max_size
        
    def get(self, key: str) -> Optional[Any]:
        if key in self.cache:
            self.access_times[key] = datetime.now()
            return self.cache[key]
        return None
        
    def set(self, key: str, value: Any):
        # 캐시 크기 제한
        if len(self.cache) >= self.max_size:
            self._evict_oldest()
            
        self.cache[key] = value
        self.access_times[key] = datetime.now()
        
    def _evict_oldest(self):
        """가장 오래된 항목 제거"""
        oldest_key = min(self.access_times.keys(), key=lambda k: self.access_times[k])
        del self.cache[oldest_key]
        del self.access_times[oldest_key]
```


## 테스팅 및 배포 지침

### 1. 단위 테스트 작성

```python
# tests/test_points.py
import unittest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from cogs.points import PointSystem

class TestPointSystem(unittest.TestCase):
    def setUp(self):
        self.bot = MagicMock()
        self.bot.db_pool = AsyncMock()
        self.point_system = PointSystem(self.bot)
        
    def test_point_validation(self):
        """포인트 검증 테스트"""
        # 정상적인 포인트
        self.assertTrue(self.point_system.validate_points(100))
        
        # 비정상적인 포인트
        self.assertFalse(self.point_system.validate_points(-10))
        self.assertFalse(self.point_system.validate_points(0))
        
    async def test_add_points(self):
        """포인트 추가 테스트"""
        # Mock 데이터베이스 응답
        mock_cursor = AsyncMock()
        mock_conn = AsyncMock()
        mock_conn.cursor.return_value.__aenter__.return_value = mock_cursor
        self.bot.db_pool.acquire.return_value.__aenter__.return_value = mock_conn
        
        # 포인트 추가 실행
        result = await self.point_system.add_points(12345, 100, "테스트")
        
        # 검증
        self.assertTrue(result[0])  # 성공 여부
        mock_cursor.execute.assert_called()

if __name__ == '__main__':
    unittest.main()
```


### 2. 통합 테스트

```python
# tests/test_integration.py
import asyncio
import pytest
from discord.ext import commands
from main import DiscordBot

@pytest.mark.asyncio
async def test_bot_startup():
    """봇 시작 테스트"""
    bot = DiscordBot()
    
    # 봇 설정 확인
    assert bot.command_prefix == "!"
    assert bot.intents.message_content == True
    
    # Cog 로딩 테스트
    await bot.setup_hook()
    
    # 확장 모듈 로딩 확인
    assert 'cogs.points' in bot.extensions
    assert 'cogs.permissions' in bot.extensions

@pytest.mark.asyncio
async def test_command_execution():
    """명령어 실행 테스트"""
    # 테스트용 컨텍스트 생성
    ctx = MagicMock()
    ctx.author.id = 12345
    ctx.send = AsyncMock()
    
    # 포인트 조회 명령어 테스트
    point_cog = bot.get_cog('PointSystem')
    await point_cog.check_points(ctx)
    
    # 응답 확인
    ctx.send.assert_called_once()
```


### 3. 배포 설정

#### Docker 컨테이너화

```dockerfile
# Dockerfile
FROM python:3.10-slim

WORKDIR /app

# 시스템 패키지 설치
RUN apt-get update && apt-get install -y \
    gcc \
    default-libmysqlclient-dev \
    && rm -rf /var/lib/apt/lists/*

# Python 의존성 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션 코드 복사
COPY . .

# 로그 디렉토리 생성
RUN mkdir -p logs

# 봇 실행
CMD ["python", "main.py"]
```


#### Docker Compose 설정

```yaml
# docker-compose.yml
version: '3.8'

services:
  discord-bot:
    build: .
    environment:
      - DISCORD_TOKEN=${DISCORD_TOKEN}
      - DB_HOST=mysql
      - DB_USER=${DB_USER}
      - DB_PASSWORD=${DB_PASSWORD}
      - DB_NAME=${DB_NAME}
    depends_on:
      - mysql
    volumes:
      - ./logs:/app/logs
    restart: unless-stopped
    
  mysql:
    image: mysql:8.0
    environment:
      - MYSQL_ROOT_PASSWORD=${MYSQL_ROOT_PASSWORD}
      - MYSQL_DATABASE=${DB_NAME}
      - MYSQL_USER=${DB_USER}
      - MYSQL_PASSWORD=${DB_PASSWORD}
    volumes:
      - mysql_data:/var/lib/mysql
      - ./database/migrations.sql:/docker-entrypoint-initdb.d/init.sql
    ports:
      - "3306:3306"
    restart: unless-stopped

volumes:
  mysql_data:
```


#### 프로덕션 실행 스크립트

```bash
#!/bin/bash
# deploy.sh

set -e

echo "🚀 디스코드 봇 배포 시작"

# 환경 변수 확인
if [ ! -f .env ]; then
    echo "❌ .env 파일이 없습니다."
    exit 1
fi

# Docker 이미지 빌드
echo "📦 Docker 이미지 빌드 중..."
docker-compose build

# 기존 컨테이너 중지 및 제거
echo "🛑 기존 컨테이너 중지 중..."
docker-compose down

# 새 컨테이너 시작
echo "▶️ 새 컨테이너 시작 중..."
docker-compose up -d

# 헬스 체크
echo "🔍 헬스 체크 중..."
sleep 10

if docker-compose ps | grep -q "Up"; then
    echo "✅ 배포 완료!"
else
    echo "❌ 배포 실패!"
    docker-compose logs
    exit 1
fi

echo "📊 컨테이너 상태:"
docker-compose ps
```


### 4. 모니터링 및 유지보수

#### 로그 모니터링 스크립트

```python
# monitoring/log_monitor.py
import asyncio
import aiofiles
from datetime import datetime, timedelta
import re

class LogMonitor:
    def __init__(self, log_file_path: str):
        self.log_file_path = log_file_path
        self.error_patterns = [
            r'ERROR',
            r'CRITICAL',
            r'Exception',
            r'Failed to connect'
        ]
        
    async def monitor_logs(self):
        """로그 파일 실시간 모니터링"""
        async with aiofiles.open(self.log_file_path, 'r') as file:
            # 파일 끝으로 이동
            await file.seek(0, 2)
            
            while True:
                line = await file.readline()
                if not line:
                    await asyncio.sleep(1)
                    continue
                    
                # 에러 패턴 확인
                for pattern in self.error_patterns:
                    if re.search(pattern, line, re.IGNORECASE):
                        await self.send_alert(line.strip())
                        break
                        
    async def send_alert(self, error_message: str):
        """에러 알림 전송"""
        # Discord 웹훅이나 이메일로 알림 전송
        print(f"🚨 ERROR DETECTED: {error_message}")
        
        # 여기에 실제 알림 로직 구현
        # - Discord 웹훅
        # - 이메일 전송
        # - Slack 알림 등

if __name__ == "__main__":
    monitor = LogMonitor("logs/discord_bot.log")
    asyncio.run(monitor.monitor_logs())
```


#### 자동 백업 스크립트

```bash
#!/bin/bash
# backup.sh

BACKUP_DIR="/backups/discord_bot"
DATE=$(date +%Y%m%d_%H%M%S)
DB_NAME="discord_bot_db"

# 백업 디렉토리 생성
mkdir -p $BACKUP_DIR

# 데이터베이스 백업
echo "📦 데이터베이스 백업 중..."
docker exec discord-bot-mysql mysqldump -u root -p$MYSQL_ROOT_PASSWORD $DB_NAME > $BACKUP_DIR/db_backup_$DATE.sql

# 설정 파일 백업
echo "📁 설정 파일 백업 중..."
cp .env $BACKUP_DIR/env_backup_$DATE.txt
cp docker-compose.yml $BACKUP_DIR/compose_backup_$DATE.yml

# 7일 이상된 백업 파일 삭제
find $BACKUP_DIR -name "*backup*" -mtime +7 -delete

echo "✅ 백업 완료: $BACKUP_DIR"
```


## 최종 확인 체크리스트

### 개발 완료 확인사항

- [ ] **환경 설정**: 모든 환경 변수가 올바르게 설정됨
- [ ] **데이터베이스**: 테이블 생성 및 관계 설정 완료
- [ ] **권한 시스템**: 관리자/모더레이터/일반 유저 권한 분리 동작
- [ ] **포인트 시스템**: 메시지 기반 포인트 적립 및 관리 기능 동작
- [ ] **메시지 관리**: 예약 삭제 및 대량 삭제 기능 동작
- [ ] **로깅 시스템**: 모든 메시지 및 이벤트 로깅 동작
- [ ] **에러 처리**: 모든 주요 에러 상황에 대한 적절한 처리
- [ ] **보안**: SQL 인젝션 방지 및 입력값 검증 구현
- [ ] **성능**: 대용량 처리 시 성능 최적화 적용
- [ ] **테스트**: 단위 테스트 및 통합 테스트 통과
- [ ] **문서화**: 코드 주석 및 사용법 문서 작성
- [ ] **배포**: Docker 컨테이너 배포 설정 완료


### 운영 준비 확인사항

- [ ] **모니터링**: 로그 모니터링 시스템 구축
- [ ] **백업**: 자동 백업 시스템 설정
- [ ] **알림**: 에러 발생 시 알림 시스템 구축
- [ ] **복구**: 장애 복구 절차 문서화
- [ ] **확장성**: 사용자 증가에 대비한 확장 계획

이 가이드를 따라 구현하면 안정적이고 확장 가능한 다기능 디스코드 봇을 개발할 수 있습니다. 각 단계별로 충분한 테스트를 거쳐 단계적으로 기능을 추가해 나가시기 바랍니다.

