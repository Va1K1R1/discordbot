import asyncio
import logging
import os
import sys
from pathlib import Path
import signal

import discord
from discord.ext import commands

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.config.settings import settings
from src.models.database import init_database  # ✅ 동기 함수로 import
from src.config.logging_config import setup_logging

# 로깅 설정
setup_logging()
logger = logging.getLogger(__name__)

class DiscordBot(commands.Bot):
    """메인 Discord 봇 클래스"""
    
    def __init__(self):
        # 인텐트 설정
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        intents.guild_messages = True
        
        super().__init__(
            command_prefix='!',
            intents=intents,
            help_command=None
        )
        
        self.initial_extensions = [
            'src.commands.basic',
            'src.commands.admin',
            'src.commands.ai_chat', 
            'src.commands.dynamic'
        ]
        
        # 봇 종료 플래그
        self.shutdown_flag = False
    
    async def setup_hook(self):
        """봇 설정 후크"""
        logger.info("🔄 확장 모듈 로드 시작...")
        
        # 현재 파일과 프로젝트 루트 정보 로깅
        current_file = Path(__file__).resolve()
        project_root = current_file.parent.parent
        commands_dir = project_root / "src" / "commands"
        
        logger.info(f"현재 파일: {current_file}")
        logger.info(f"프로젝트 루트: {project_root}")
        logger.info(f"Commands 디렉토리: {commands_dir}")
        logger.info(f"Commands 디렉토리 존재 여부: {commands_dir.exists()}")
        
        # 확장 모듈 로드
        for extension in self.initial_extensions:
            try:
                logger.info(f"🔄 확장 모듈 로드 시도: {extension}")
                await self.load_extension(extension)
                logger.info(f"✅ 확장 모듈 로드 성공: {extension}")
                logger.info(f"📊 현재 트리 커맨드 수: {len(self.tree.get_commands())}")
            except Exception as e:
                logger.error(f"❌ 확장 모듈 로드 실패 {extension}: {e}")
        
        logger.info(f"📊 총 {len(self.initial_extensions)}개의 확장 모듈이 로드되었습니다.")
    
    async def on_ready(self):
        """봇이 준비되었을 때 호출"""
        logger.info(f"🔗 {self.user}로 Discord에 로그인했습니다!")
        logger.info(f"봇 ID: {self.user.id}")
        logger.info(f"연결된 서버 수: {len(self.guilds)}")
        
        # 길드별 기존 커맨드 로드
        from src.commands.dynamic import DynamicCommandsCog
        dynamic_cog = self.get_cog('DynamicCommandsCog')
        if dynamic_cog:
            await dynamic_cog.load_existing_commands()
        
        # 슬래시 커맨드 동기화
        await self.sync_commands()
        
        logger.info("✅ 봇이 완전히 준비되었습니다!")
    
    async def sync_commands(self):
        """슬래시 커맨드 동기화"""
        try:
            logger.info("🔄 슬래시 커맨드 동기화 시작...")
            logger.info(f"📊 동기화 전 봇 트리 커맨드 수: {len(self.tree.get_commands())}")
            
            # 전역 커맨드 동기화
            synced = await self.tree.sync()
            logger.info(f"🔄 {len(synced)}개의 전역 슬래시 커맨드가 동기화되었습니다.")
            
            for cmd in synced:
                logger.info(f"  ✅ 전역 동기화됨: /{cmd.name}")
            
            # 길드별 커맨드 동기화
            for guild_id in settings.allowed_guild_ids:
                guild = self.get_guild(guild_id)
                if guild:
                    try:
                        guild_synced = await self.tree.sync(guild=guild)
                        logger.info(f"🔄 {guild.name}({guild.id})에 {len(guild_synced)}개의 슬래시 커맨드가 동기화되었습니다.")
                    except Exception as e:
                        logger.error(f"❌ 길드 {guild.name}({guild.id}) 동기화 실패: {e}")
                else:
                    logger.warning(f"⚠️ 길드 ID {guild_id}를 찾을 수 없습니다.")
            
        except Exception as e:
            logger.error(f"❌ 슬래시 커맨드 동기화 실패: {e}")
    
    async def on_app_command_error(self, interaction: discord.Interaction, error: Exception):
        """앱 커맨드 오류 처리"""
        logger.error(f"앱 커맨드 오류: {error}")
        
        if not interaction.response.is_done():
            await interaction.response.send_message(
                "❌ 명령어 처리 중 오류가 발생했습니다.",
                ephemeral=True
            )
    
    async def close(self):
        """봇 종료 처리"""
        logger.info("🛑 봇이 종료되었습니다.")
        await super().close()

async def discord_connection():
    """Discord API 연결 테스트"""
    try:
        logger.info("Discord API 연결 테스트 중...")
        
        # 간단한 연결 테스트
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.get('https://discord.com/api/gateway') as resp:
                data = await resp.json()
                logger.info(f"✅ Discord API 연결 성공: {data['url']}")
                return True
    except Exception as e:
        logger.error(f"❌ Discord API 연결 실패: {e}")
        return False

async def main():
    """메인 함수"""
    try:
        # 데이터베이스 초기화 (동기 함수로 호출)
        logger.info("데이터베이스 초기화 중...")
        init_database()  # ✅ await 제거
        logger.info("데이터베이스 초기화 완료")
        
        # Discord API 연결 테스트
        if not await discord_connection():
            logger.error("Discord API 연결에 실패했습니다.")
            return
        
        # 봇 생성 및 시작
        logger.info("🔄 WebSocket 연결 시도 중...")
        bot = DiscordBot()
        
        # 신호 핸들러 설정 (graceful shutdown)
        def signal_handler(signum, frame):
            logger.info("종료 신호를 받았습니다.")
            bot.shutdown_flag = True
            asyncio.create_task(bot.close())
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # 봇 시작 로깅
        logger.info("🚀 봇 시작 중...")
        logger.info(f"🔑 토큰 길이: {len(settings.discord_token)} 문자")
        logger.info(f"🔑 토큰 시작 부분: {settings.discord_token[:20]}...")
        
        # 봇 실행 (무한 대기)
        await bot.start(settings.discord_token)
        
    except KeyboardInterrupt:
        logger.info("키보드 인터럽트로 봇이 종료되었습니다.")
    except Exception as e:
        logger.error(f"봇 실행 중 오류 발생: {e}")
        raise
    finally:
        # 정리 작업
        if 'bot' in locals():
            await bot.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("봇이 사용자에 의해 중단되었습니다.")
    except Exception as e:
        print(f"봇 실행 중 치명적 오류: {e}")
        sys.exit(1)