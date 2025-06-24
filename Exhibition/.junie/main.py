"""
AI 기반 자연어 처리 Discord 봇
"""

import asyncio
import logging
import sys
from pathlib import Path

import discord
from discord.ext import commands

# 프로젝트 모듈 import
from config.settings import settings
from config.logging_config import setup_logging
from models.database import init_database
from services.ai_service import ai_service

# 로깅 설정
logger = setup_logging(settings.log_level, settings.log_file)


class AIDiscordBot(commands.Bot):
    """AI Discord Bot 메인 클래스"""

    def __init__(self):
        # 인텐트 설정
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        intents.guild_messages = True
        intents.guild_reactions = True

        super().__init__(
            command_prefix='!',
            intents=intents,
            help_command=None
        )

        self.ai_service = ai_service

    async def setup_hook(self):
        """봇 시작 시 초기화 작업"""
        logger.info("봇 초기화 시작...")

        # 데이터베이스 초기화
        await init_database()

        # Cog 로드
        await self.load_cogs()

        # 슬래시 커맨드 동기화
        await self.sync_commands()

        logger.info("봇 초기화 완료")

    async def load_cogs(self):
        """Cog 파일들 로드"""
        cog_files = [
            'commands.admin',
            'commands.dynamic', 
            'commands.ai_chat'
        ]

        for cog in cog_files:
            try:
                await self.load_extension(cog)
                logger.info(f"Cog {cog} 로드 완료")
            except Exception as e:
                logger.error(f"Cog {cog} 로드 실패: {e}")

    async def sync_commands(self):
        """슬래시 커맨드 동기화"""
        try:
            if settings.discord_guild_id:
                # 특정 길드에만 동기화 (개발용)
                guild = discord.Object(id=settings.discord_guild_id)
                await self.tree.sync(guild=guild)
                logger.info(f"길드 {settings.discord_guild_id}에 커맨드 동기화 완료")
            else:
                # 전역 동기화 (프로덕션용)
                await self.tree.sync()
                logger.info("전역 커맨드 동기화 완료")
        except Exception as e:
            logger.error(f"커맨드 동기화 실패: {e}")

    async def on_ready(self):
        """봇이 준비되었을 때"""
        logger.info(f"{self.user}로 로그인했습니다!")
        logger.info(f"봇 ID: {self.user.id}")
        logger.info(f"연결된 서버 수: {len(self.guilds)}")

        # 봇 상태 설정
        activity = discord.Activity(
            type=discord.ActivityType.listening,
            name="자연어 명령어 | /도움말"
        )
        await self.change_presence(activity=activity)

    async def on_guild_join(self, guild):
        """새 서버에 참가했을 때"""
        logger.info(f"새 서버 참가: {guild.name} (ID: {guild.id})")

        # 서버별 초기 설정
        await self.setup_guild(guild)

    async def setup_guild(self, guild):
        """서버별 초기 설정"""
        try:
            # 길드별 커맨드 동기화
            await self.tree.sync(guild=guild)
            logger.info(f"서버 {guild.name}에 커맨드 동기화 완료")
        except Exception as e:
            logger.error(f"서버 {guild.name} 설정 실패: {e}")

    async def on_message(self, message):
        """메시지 수신 시"""
        # 봇 자신의 메시지는 무시
        if message.author == self.user:
            return

        # 자연어 처리
        await self.process_natural_language(message)

        # 일반 명령어 처리
        await self.process_commands(message)

    async def process_natural_language(self, message):
        """자연어 메시지 처리"""
        try:
            # AI로 의도 분석
            intent_data = await self.ai_service.analyze_intent(message.content)

            # 커맨드 생성 의도인 경우
            if intent_data.get("intent") == "커맨드 생성" and intent_data.get("confidence", 0) > 0.8:
                # 관리자 권한 확인
                if not self.is_admin(message.author):
                    await message.reply("❌ 커맨드 생성은 관리자만 가능합니다.")
                    return

                # 자동 커맨드 생성 안내
                embed = discord.Embed(
                    title="🤖 커맨드 생성 감지",
                    description="새 커맨드를 생성하시겠습니까?",
                    color=discord.Color.blue()
                )
                embed.add_field(
                    name="감지된 내용",
                    value=message.content[:100] + "..." if len(message.content) > 100 else message.content,
                    inline=False
                )

                view = ConfirmCommandCreationView(message.content)
                await message.reply(embed=embed, view=view)

        except Exception as e:
            logger.error(f"자연어 처리 실패: {e}")

    def is_admin(self, user):
        """관리자 권한 확인"""
        return user.id in settings.admin_user_ids or any(
            role.permissions.administrator for role in getattr(user, 'roles', [])
        )

    async def on_error(self, event, *args, **kwargs):
        """에러 처리"""
        logger.error(f"에러 발생 - 이벤트: {event}", exc_info=sys.exc_info())

    async def on_command_error(self, ctx, error):
        """명령어 에러 처리"""
        if isinstance(error, commands.CommandNotFound):
            return  # 존재하지 않는 명령어는 무시

        logger.error(f"명령어 에러: {error}", exc_info=error)

        embed = discord.Embed(
            title="❌ 오류 발생",
            description="명령어 실행 중 오류가 발생했습니다.",
            color=discord.Color.red()
        )

        if hasattr(ctx, 'send'):
            await ctx.send(embed=embed, ephemeral=True)


class ConfirmCommandCreationView(discord.ui.View):
    """커맨드 생성 확인 뷰"""

    def __init__(self, user_description: str):
        super().__init__(timeout=60)
        self.user_description = user_description

    @discord.ui.button(label="네, 생성하기", style=discord.ButtonStyle.green, emoji="✅")
    async def confirm_creation(self, interaction: discord.Interaction, button: discord.ui.Button):
        """커맨드 생성 확인"""
        from commands.dynamic import AddCommandModal

        modal = AddCommandModal()
        modal.command_description.default = self.user_description
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="아니오", style=discord.ButtonStyle.red, emoji="❌")
    async def cancel_creation(self, interaction: discord.Interaction, button: discord.ui.Button):
        """커맨드 생성 취소"""
        await interaction.response.edit_message(
            content="커맨드 생성이 취소되었습니다.",
            embed=None,
            view=None
        )


async def main():
    """메인 함수"""
    # Discord 토큰 확인
    if not settings.discord_token:
        logger.error("DISCORD_TOKEN이 설정되지 않았습니다.")
        return

    # OpenAI API 키 확인
    if not settings.openai_api_key:
        logger.error("OPENAI_API_KEY가 설정되지 않았습니다.")
        return

    # 봇 인스턴스 생성 및 실행
    async with AIDiscordBot() as bot:
        try:
            await bot.start(settings.discord_token)
        except discord.LoginFailure:
            logger.error("Discord 로그인 실패: 토큰을 확인해주세요.")
        except Exception as e:
            logger.error(f"봇 실행 실패: {e}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("봇이 사용자에 의해 중단되었습니다.")
    except Exception as e:
        logger.error(f"예상치 못한 오류: {e}")
