import sys
import os
import discord
from discord.ext import commands
import asyncio
import logging

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 이제 기존 import들이 작동합니다
from src.config.settings import settings
import os
from pathlib import Path

# Python 경로 설정 (Docker 환경에서 중요)
current_dir = Path(__file__).parent.parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))


from src.config.logging_config import setup_logging

# 모든 모델 임포트 (테이블 생성을 위해 반드시 필요)
from src.models import (
    Base, 
    engine, 
    init_database, 
    create_database_if_not_exists,
    Command,              # 명시적 임포트
    User,                 # 명시적 임포트
    ConversationHistory   # 실제 클래스명 사용
)
from src.exceptions.custom_exceptions import BotBaseException

# 로깅 설정
logger = setup_logging()

# 데이터베이스 초기화
logger.info("데이터베이스 초기화 중...")
if create_database_if_not_exists():
    if init_database():
        logger.info("데이터베이스 초기화 완료")
    else:
        logger.error("데이터베이스 초기화 실패")
        exit(1)
else:
    logger.error("데이터베이스 생성 실패")
    exit(1)

# 인텐트 설정
intents = discord.Intents.default()
intents.message_content = True
intents.members = True


def create_bot():
    """봇 인스턴스 생성"""
    bot = commands.Bot(command_prefix="!", intents=intents)
    
    @bot.event
    async def on_ready():
        """봇이 준비되었을 때 호출"""
        logger.info(f"{bot.user.name}이(가) 준비되었습니다!")
        logger.info(f"Discord.py 버전: {discord.__version__}")
        logger.info(f"봇 ID: {bot.user.id}")
        logger.info(f"서버 수: {len(bot.guilds)}")
        
        # 슬래시 커맨드 동기화
        try:
            synced = await bot.tree.sync()
            logger.info(f"{len(synced)}개의 전역 슬래시 커맨드가 동기화되었습니다.")
            
            # 각 길드별 커맨드 동기화
            for guild in bot.guilds:
                guild_synced = await bot.tree.sync(guild=guild)
                logger.info(f"{guild.name}({guild.id})에 {len(guild_synced)}개의 슬래시 커맨드가 동기화되었습니다.")
        except Exception as e:
            logger.error(f"슬래시 커맨드 동기화 실패: {e}")
    
    @bot.event
    async def on_guild_join(guild):
        """봇이 새로운 서버에 참가했을 때 호출"""
        logger.info(f"새로운 서버에 참가: {guild.name} (ID: {guild.id})")
        
        # 서버별 슬래시 커맨드 동기화
        try:
            guild_synced = await bot.tree.sync(guild=guild)
            logger.info(f"{guild.name}({guild.id})에 {len(guild_synced)}개의 슬래시 커맨드가 동기화되었습니다.")
        except Exception as e:
            logger.error(f"서버 참가 시 슬래시 커맨드 동기화 실패: {e}")
    
    @bot.event
    async def on_command_error(ctx, error):
        """명령어 오류 처리"""
        if isinstance(error, commands.CommandNotFound):
            return
        
        if isinstance(error, BotBaseException):
            await ctx.send(f"오류: {error.message}")
            return
        
        logger.error(f"명령어 오류: {error}")
        await ctx.send("명령어 실행 중 오류가 발생했습니다.")
    
    @bot.tree.error
    async def on_app_command_error(interaction, error):
        """슬래시 커맨드 오류 처리"""
        if isinstance(error, discord.app_commands.CommandOnCooldown):
            await interaction.response.send_message(
                f"명령어 재사용 대기 중입니다. {error.retry_after:.1f}초 후에 다시 시도해주세요.",
                ephemeral=True
            )
            return
        
        if isinstance(error, discord.app_commands.CheckFailure):
            await interaction.response.send_message(
                "이 명령어를 사용할 권한이 없습니다.",
                ephemeral=True
            )
            return
        
        if isinstance(error, BotBaseException):
            await interaction.response.send_message(
                f"오류: {error.message}",
                ephemeral=True
            )
            return
        
        logger.error(f"슬래시 커맨드 오류: {error}")
        
        # 이미 응답이 시작되었는지 확인
        if interaction.response.is_done():
            await interaction.followup.send(
                "명령어 실행 중 오류가 발생했습니다.",
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                "명령어 실행 중 오류가 발생했습니다.",
                ephemeral=True
            )
    
    return bot


async def load_extensions(bot):
    """확장 모듈 로드"""
    # Docker 환경을 고려한 경로 설정
    current_file = Path(__file__)
    project_root = current_file.parent.parent
    commands_dir = project_root / "src" / "commands"
    
    logger.info(f"현재 파일: {current_file}")
    logger.info(f"프로젝트 루트: {project_root}")
    logger.info(f"Commands 디렉토리: {commands_dir}")
    logger.info(f"Commands 디렉토리 존재 여부: {commands_dir.exists()}")
    
    if not commands_dir.exists():
        logger.warning(f"Commands 디렉토리가 존재하지 않습니다: {commands_dir}")
        return
    
    # 확장 모듈 로드
    try:
        for file_path in commands_dir.iterdir():
            if file_path.is_file() and file_path.suffix == ".py" and not file_path.name.startswith("__"):
                extension = f"src.commands.{file_path.stem}"
                try:
                    await bot.load_extension(extension)
                    logger.info(f"확장 모듈 로드: {extension}")
                except Exception as e:
                    logger.error(f"확장 모듈 로드 실패 {extension}: {e}")
    except Exception as e:
        logger.error(f"Commands 디렉토리 스캔 실패: {e}")


async def main():
    """메인 함수"""
    bot = create_bot()
    
    # 확장 모듈 로드
    await load_extensions(bot)
    
    # 봇 실행
    try:
        logger.info("봇 시작 중...")
        await bot.start(settings.discord_token)
    except discord.LoginFailure:
        logger.error("봇 토큰이 유효하지 않습니다. .env 파일의 DISCORD_TOKEN을 확인해주세요.")
    except Exception as e:
        logger.error(f"봇 실행 실패: {e}")
    finally:
        await bot.close()
        logger.info("봇이 종료되었습니다.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("키보드 인터럽트로 봇이 종료되었습니다.")
    except Exception as e:
        logger.critical(f"예기치 않은 오류로 봇이 종료되었습니다: {e}")