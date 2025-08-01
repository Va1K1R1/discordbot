import asyncio
import logging
import os
import sys
from pathlib import Path
import signal
import time

import discord
from discord.ext import commands

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.config.settings import settings
from src.models.database import init_database  # ✅ 동기 함수로 import
from src.config.logging_config import setup_logging

# AI 로깅 시스템 안전하게 import
try:
    from src.config.logging_config import ai_logger, AI_LOGGING_ENABLED
    print("✅ AI 로깅 시스템 로드 성공")
except ImportError as e:
    print(f"⚠️ AI 로깅 시스템 로드 실패: {e}")
    AI_LOGGING_ENABLED = False
    ai_logger = None

# 기본 로깅 설정
setup_logging()
logger = logging.getLogger(__name__)

class DiscordBot(commands.Bot):
    """메인 Discord 봇 클래스 - AI 로깅 통합"""
    
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
        
        # ✅ 시작 시간 기록 (float 타입으로 일관성 유지)
        self.start_time = time.time()
        
        # AI 로깅 시작
        if AI_LOGGING_ENABLED:
            ai_logger.log_user_activity(
                user_id=0,
                user_name="SYSTEM",
                activity_data={
                    "action": "BOT_INITIALIZATION",
                    "timestamp": self.start_time  # ✅ 같은 타입 사용
                }
            )
    
    async def setup_hook(self):
        """봇 설정 후크"""
        logger.info("🔄 확장 모듈 로드 시작...")
        
        # AI 로깅 초기화 확인
        if AI_LOGGING_ENABLED:
            logger.info("🤖 AI 로깅 시스템 활성화됨")
            ai_logger.log_user_activity(
                user_id=0,
                user_name="SYSTEM",
                activity_data={
                    "action": "EXTENSIONS_LOADING_START",
                    "extensions": self.initial_extensions
                }
            )
        else:
            logger.warning("⚠️ AI 로깅 시스템이 비활성화됨")
        
        # 현재 파일과 프로젝트 루트 정보 로깅
        current_file = Path(__file__).resolve()
        project_root = current_file.parent.parent
        commands_dir = project_root / "src" / "commands"
        
        logger.info(f"현재 파일: {current_file}")
        logger.info(f"프로젝트 루트: {project_root}")
        logger.info(f"Commands 디렉토리: {commands_dir}")
        logger.info(f"Commands 디렉토리 존재 여부: {commands_dir.exists()}")
        
        # 확장 모듈 로드
        successful_extensions = []
        failed_extensions = []
        
        for extension in self.initial_extensions:
            try:
                logger.info(f"🔄 확장 모듈 로드 시도: {extension}")
                await self.load_extension(extension)
                logger.info(f"✅ 확장 모듈 로드 성공: {extension}")
                logger.info(f"📊 현재 트리 커맨드 수: {len(self.tree.get_commands())}")
                successful_extensions.append(extension)
                
            except Exception as e:
                logger.error(f"❌ 확장 모듈 로드 실패 {extension}: {e}")
                failed_extensions.append((extension, str(e)))
        
        logger.info(f"📊 총 {len(successful_extensions)}개의 확장 모듈이 로드되었습니다.")
        
        # AI 로깅 - 확장 모듈 로드 결과
        if AI_LOGGING_ENABLED:
            ai_logger.log_user_activity(
                user_id=0,
                user_name="SYSTEM",
                activity_data={
                    "action": "EXTENSIONS_LOADED",
                    "successful": successful_extensions,
                    "failed": failed_extensions,
                    "total_commands": len(self.tree.get_commands())
                }
            )
    
    async def on_ready(self):
        """봇이 준비되었을 때 실행"""
        try:
            # 타입 안전한 시간 계산
            startup_time = time.time() - float(self.start_time) if isinstance(self.start_time, (int, float)) else 0
            
            logger.info(f"🔗 {self.user.name}#{self.user.discriminator}로 Discord에 로그인했습니다!")
            logger.info(f"봇 ID: {self.user.id}")
            logger.info(f"연결된 서버 수: {len(self.guilds)}")
            
            # 나머지 로직...
            
        except Exception as e:
            logger.error(f"on_ready 에러: {e}")
            import traceback
            traceback.print_exc()
        #logger.info(f"🔗 {self.user}로 Discord에 로그인했습니다!")
        #logger.info(f"봇 ID: {self.user.id}")
        #logger.info(f"연결된 서버 수: {len(self.guilds)}")
        
        # ✅ 시작 시간 계산 (안전한 타입 처리)
        try:
            current_time = time.time()
            startup_time = current_time - self.start_time
            logger.info(f"⏱️ 봇 시작 완료 시간: {startup_time:.2f}초")
        except Exception as e:
            logger.warning(f"시작 시간 계산 실패: {e}")
            startup_time = 0.0
        
        # AI 로깅 - 봇 준비 완료
        if AI_LOGGING_ENABLED:
            try:
                # 안전한 길드 정보 수집
                guild_ids = []
                total_members = 0
                bot_permissions = []
                
                for guild in self.guilds:
                    try:
                        guild_ids.append(guild.id)
                        if guild.member_count:
                            total_members += guild.member_count
                        if guild.me and guild.me.guild_permissions:
                            bot_permissions.append(guild.me.guild_permissions.value)
                    except Exception as guild_error:
                        logger.warning(f"길드 정보 수집 실패 {guild.id}: {guild_error}")
                
                ai_logger.log_user_activity(
                    user_id=self.user.id,
                    user_name=str(self.user),
                    activity_data={
                        "action": "BOT_READY",
                        "startup_time_seconds": startup_time,
                        "connected_guilds": len(self.guilds),
                        "guild_ids": guild_ids,
                        "total_members": total_members,
                        "bot_permissions": bot_permissions
                    }
                )
            except Exception as log_error:
                logger.error(f"AI 로깅 실패: {log_error}")
        
        # 길드별 기존 커맨드 로드
        try:
            dynamic_cog = self.get_cog('UniversalDynamicCog')
            if dynamic_cog:
                await dynamic_cog.load_existing_commands()
                logger.info("✅ 기존 동적 커맨드 로드 완료")
        except Exception as e:
            logger.error(f"❌ 동적 커맨드 로드 실패: {e}")
        
        # 슬래시 커맨드 동기화
        await self.sync_commands()
        
        logger.info("✅ 봇이 완전히 준비되었습니다!")
        
        # AI 로깅 시스템 통계 출력
        if AI_LOGGING_ENABLED:
            try:
                stats = ai_logger.get_stats()
                logger.info(f"📊 AI 로깅 통계: {stats}")
            except Exception as stats_error:
                logger.warning(f"AI 통계 수집 실패: {stats_error}")
    
    async def sync_commands(self):
        """슬래시 커맨드 동기화"""
        try:
            logger.info("🔄 슬래시 커맨드 동기화 시작...")
            logger.info(f"📊 동기화 전 봇 트리 커맨드 수: {len(self.tree.get_commands())}")
            
            sync_results = []
            
            # 전역 커맨드 동기화
            synced = await self.tree.sync()
            logger.info(f"🔄 {len(synced)}개의 전역 슬래시 커맨드가 동기화되었습니다.")
            sync_results.append({"type": "global", "count": len(synced)})
            
            for cmd in synced:
                logger.info(f"  ✅ 전역 동기화됨: /{cmd.name}")
            
            # 길드별 커맨드 동기화
            guild_sync_results = []
            for guild_id in settings.allowed_guild_ids:
                guild = self.get_guild(guild_id)
                if guild:
                    try:
                        guild_synced = await self.tree.sync(guild=guild)
                        logger.info(f"🔄 {guild.name}({guild.id})에 {len(guild_synced)}개의 슬래시 커맨드가 동기화되었습니다.")
                        guild_sync_results.append({
                            "guild_id": guild.id,
                            "guild_name": guild.name,
                            "count": len(guild_synced)
                        })
                    except Exception as e:
                        logger.error(f"❌ 길드 {guild.name}({guild.id}) 동기화 실패: {e}")
                        guild_sync_results.append({
                            "guild_id": guild.id,
                            "guild_name": guild.name,
                            "error": str(e)
                        })
                else:
                    logger.warning(f"⚠️ 길드 ID {guild_id}를 찾을 수 없습니다.")
            
            # AI 로깅 - 커맨드 동기화 결과
            if AI_LOGGING_ENABLED:
                try:
                    ai_logger.log_user_activity(
                        user_id=0,
                        user_name="SYSTEM",
                        activity_data={
                            "action": "COMMANDS_SYNCED",
                            "global_commands": len(synced),
                            "guild_sync_results": guild_sync_results,
                            "command_names": [cmd.name for cmd in synced]
                        }
                    )
                except Exception as log_error:
                    logger.warning(f"동기화 로깅 실패: {log_error}")
            
        except Exception as e:
            logger.error(f"❌ 슬래시 커맨드 동기화 실패: {e}")
            
            # AI 로깅 - 동기화 실패
            if AI_LOGGING_ENABLED:
                try:
                    ai_logger.log_ai_error(
                        user_id=0,
                        user_name="SYSTEM",
                        guild_id=0,
                        channel_id=0,
                        error_message=str(e),
                        error_type="COMMAND_SYNC_ERROR",
                        model="system"
                    )
                except Exception as log_error:
                    logger.warning(f"에러 로깅 실패: {log_error}")
    
    async def on_app_command_error(self, interaction: discord.Interaction, error: Exception):
        """앱 커맨드 오류 처리 - AI 로깅 통합"""
        logger.error(f"앱 커맨드 오류: {error}")
        
        # AI 관련 명령어 오류인 경우 AI 로거에도 기록
        if AI_LOGGING_ENABLED and hasattr(interaction.command, 'name'):
            try:
                command_name = interaction.command.name.lower()
                
                # AI 관련 커맨드 판별
                if any(keyword in command_name for keyword in ['ai', 'chat', 'generate', 'ask']):
                    ai_logger.log_ai_error(
                        user_id=interaction.user.id,
                        user_name=str(interaction.user),
                        guild_id=interaction.guild_id or 0,
                        channel_id=interaction.channel_id or 0,
                        error_message=str(error),
                        error_type=type(error).__name__,
                        request_message="",
                        model="discord_command"
                    )
                
                # 일반 커맨드 오류도 기록
                ai_logger.log_user_activity(
                    user_id=interaction.user.id,
                    user_name=str(interaction.user),
                    activity_data={
                        "action": "COMMAND_ERROR",
                        "command": command_name,
                        "error": str(error),
                        "error_type": type(error).__name__,
                        "guild_id": interaction.guild_id,
                        "channel_id": interaction.channel_id
                    }
                )
            except Exception as log_error:
                logger.warning(f"커맨드 에러 로깅 실패: {log_error}")
        
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    "❌ 명령어 처리 중 오류가 발생했습니다.",
                    ephemeral=True
                )
        except Exception as response_error:
            logger.error(f"에러 응답 전송 실패: {response_error}")
    
    async def on_command_completion(self, ctx):
        """명령어 완료 시 로깅"""
        if AI_LOGGING_ENABLED:
            try:
                ai_logger.log_user_activity(
                    user_id=ctx.author.id,
                    user_name=str(ctx.author),
                    activity_data={
                        "action": "COMMAND_COMPLETED",
                        "command": ctx.command.name if ctx.command else "unknown",
                        "guild_id": ctx.guild.id if ctx.guild else None,
                        "channel_id": ctx.channel.id if ctx.channel else None
                    }
                )
            except Exception as log_error:
                logger.warning(f"커맨드 완료 로깅 실패: {log_error}")
    
    async def on_guild_join(self, guild):
        """서버 참가 시 로깅"""
        logger.info(f"새 서버 참가: {guild.name} ({guild.id})")
        
        if AI_LOGGING_ENABLED:
            try:
                ai_logger.log_user_activity(
                    user_id=0,
                    user_name="SYSTEM",
                    activity_data={
                        "action": "GUILD_JOIN",
                        "guild_id": guild.id,
                        "guild_name": guild.name,
                        "member_count": guild.member_count or 0,
                        "owner_id": guild.owner_id
                    }
                )
            except Exception as log_error:
                logger.warning(f"길드 참가 로깅 실패: {log_error}")
    
    async def on_guild_remove(self, guild):
        """서버 퇴장 시 로깅"""
        logger.info(f"서버 퇴장: {guild.name} ({guild.id})")
        
        if AI_LOGGING_ENABLED:
            try:
                ai_logger.log_user_activity(
                    user_id=0,
                    user_name="SYSTEM",
                    activity_data={
                        "action": "GUILD_REMOVE",
                        "guild_id": guild.id,
                        "guild_name": guild.name
                    }
                )
            except Exception as log_error:
                logger.warning(f"길드 퇴장 로깅 실패: {log_error}")
    
    async def close(self):
        """봇 종료 처리"""
        logger.info("🛑 봇이 종료되었습니다.")
        
        # ✅ 종료 시간 계산 (안전한 타입 처리)
        try:
            current_time = time.time()
            shutdown_time = current_time - self.start_time
        except Exception as e:
            logger.warning(f"종료 시간 계산 실패: {e}")
            shutdown_time = 0.0
        
        # AI 로깅 - 봇 종료
        if AI_LOGGING_ENABLED:
            try:
                final_stats = ai_logger.get_stats()
                ai_logger.log_user_activity(
                    user_id=0,
                    user_name="SYSTEM",
                    activity_data={
                        "action": "BOT_SHUTDOWN",
                        "uptime_seconds": shutdown_time,
                        "final_ai_stats": final_stats
                    }
                )
                
                logger.info(f"📊 최종 AI 로깅 통계: {final_stats}")
            except Exception as log_error:
                logger.warning(f"종료 로깅 실패: {log_error}")
        
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
        
        # AI 로깅 상태 확인
        if AI_LOGGING_ENABLED:
            logger.info("🤖 AI 로깅 시스템이 활성화되어 있습니다.")
        else:
            logger.warning("⚠️ AI 로깅 시스템이 비활성화되어 있습니다.")
        
        # 봇 실행 (무한 대기)
        await bot.start(settings.discord_token)
        
    except KeyboardInterrupt:
        logger.info("키보드 인터럽트로 봇이 종료되었습니다.")
    except Exception as e:
        logger.error(f"봇 실행 중 오류 발생: {e}")
        
        # 중요한 오류는 AI 로깅에도 기록
        if AI_LOGGING_ENABLED:
            try:
                ai_logger.log_ai_error(
                    user_id=0,
                    user_name="SYSTEM",
                    guild_id=0,
                    channel_id=0,
                    error_message=str(e),
                    error_type="CRITICAL_BOT_ERROR",
                    model="system"
                )
            except Exception as log_error:
                logger.warning(f"치명적 오류 로깅 실패: {log_error}")
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