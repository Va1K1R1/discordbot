import discord
from discord import app_commands
from discord.ext import commands
import logging
from datetime import datetime
import psutil
import platform
from src.utils.helpers import create_embed
from src.config.settings import settings

logger = logging.getLogger(__name__)

class BasicCog(commands.Cog):
    """기본 명령어들"""
    
    def __init__(self, bot):
        self.bot = bot
    
    @app_commands.command(name="명령어", description="봇의 모든 명령어 목록을 보여줍니다")
    async def help_command(self, interaction: discord.Interaction):
        """기본 명령어 목록 표시"""
        try:
            embed = create_embed(
                title="🤖 AI Discord Bot - 명령어 목록",
                description="사용 가능한 모든 명령어들입니다.",
                color=discord.Color.blue().value
            )
            
            # 기본 명령어
            basic_commands = """
            `/명령어` - 이 도움말을 표시합니다
            `/핑` - 봇의 응답 속도를 확인합니다  
            `/상태` - 봇의 현재 상태를 확인합니다
            """
            embed.add_field(
                name="🔧 기본 명령어", 
                value=basic_commands.strip(), 
                inline=False
            )
            
            # AI 명령어
            ai_commands = """
            `/질문 [질문내용]` - AI에게 질문하고 답변받기
            `/대화 [메시지]` - AI와 연속 대화하기
            `/대화초기화` - 현재 대화 컨텍스트 초기화
            `/대화기록` - 최근 대화 기록 확인
            """
            embed.add_field(
                name="🤖 AI 명령어", 
                value=ai_commands.strip(), 
                inline=False
            )
            
            # 커스텀 명령어 관리
            custom_commands = """
            `/추가 [이름] [설명] [응답]` - 새 커스텀 명령어 생성
            `/커맨드목록` - 현재 서버의 커스텀 명령어 목록
            `/명령어정보 [이름]` - 커스텀 명령어 상세 정보
            `/명령어삭제 [이름]` - 커스텀 명령어 삭제 (관리자만)
            `/역할설정 [명령어] [역할]` - 명령어 사용 권한 설정 (관리자만)
            """
            embed.add_field(
                name="⚙️ 커스텀 명령어 관리", 
                value=custom_commands.strip(), 
                inline=False
            )
            
            # 푸터 정보
            embed.set_footer(
                text=f"봇 버전: 1.0.0 | 서버: {interaction.guild.name}",
                icon_url=self.bot.user.avatar.url if self.bot.user.avatar else None
            )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            logger.info(f"도움말 표시: {interaction.user} in {interaction.guild.name}")
            
        except Exception as e:
            logger.error(f"도움말 명령어 오류: {e}")
            await interaction.response.send_message(
                "❌ 도움말을 표시하는 중 오류가 발생했습니다.",
                ephemeral=True
            )
    
    @app_commands.command(name="핑", description="봇의 응답 속도를 확인합니다")
    async def ping(self, interaction: discord.Interaction):
        """봇 핑 테스트"""
        try:
            # WebSocket 지연시간
            ws_latency = round(self.bot.latency * 1000, 2)
            
            # 응답 시간 측정
            start_time = datetime.now()
            await interaction.response.defer()
            end_time = datetime.now()
            
            api_latency = round((end_time - start_time).total_seconds() * 1000, 2)
            
            # 상태에 따른 이모지 선택
            if ws_latency < 100:
                status_emoji = "🟢"
                status_text = "매우 좋음"
            elif ws_latency < 200:
                status_emoji = "🟡" 
                status_text = "좋음"
            elif ws_latency < 300:
                status_emoji = "🟠"
                status_text = "보통"
            else:
                status_emoji = "🔴"
                status_text = "느림"
            
            embed = create_embed(
                title="🏓 퐁! 핑 테스트 결과",
                description=f"{status_emoji} **연결 상태: {status_text}**",
                color=discord.Color.green().value if ws_latency < 200 else discord.Color.orange().value
            )
            
            embed.add_field(
                name="📡 WebSocket 지연시간",
                value=f"`{ws_latency}ms`",
                inline=True
            )
            
            embed.add_field(
                name="⚡ API 응답시간", 
                value=f"`{api_latency}ms`",
                inline=True
            )
            
            embed.add_field(
                name="🕐 측정 시간",
                value=f"<t:{int(start_time.timestamp())}:T>",
                inline=True
            )
            
            await interaction.followup.send(embed=embed)
            logger.info(f"핑 테스트: {ws_latency}ms (WebSocket), {api_latency}ms (API) - {interaction.user}")
            
        except Exception as e:
            logger.error(f"핑 명령어 오류: {e}")
            await interaction.response.send_message(
                "❌ 핑 테스트 중 오류가 발생했습니다.",
                ephemeral=True
            )
    
    @app_commands.command(name="정보", description="봇과 서버의 상세 정보를 표시합니다")
    async def info(self, interaction: discord.Interaction):
        """봇 및 서버 정보"""
        try:
            await interaction.response.defer()
            
            # 봇 정보
            bot_user = self.bot.user
            bot_created = bot_user.created_at
            
            # 서버 정보
            guild = interaction.guild
            
            # 시스템 정보
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            
            embed = create_embed(
                title="📊 봇 & 서버 정보",
                description=f"**{bot_user.name}** 봇의 상세 정보입니다.",
                color=discord.Color.blue().value
            )
            
            # 봇 정보
            embed.add_field(
                name="🤖 봇 정보",
                value=f"""
                **이름:** {bot_user.name}
                **ID:** `{bot_user.id}`
                **생성일:** <t:{int(bot_created.timestamp())}:D>
                **서버 수:** {len(self.bot.guilds)}개
                **지연시간:** {round(self.bot.latency * 1000, 2)}ms
                """.strip(),
                inline=True
            )
            
            # 서버 정보
            embed.add_field(
                name="🏠 서버 정보", 
                value=f"""
                **이름:** {guild.name}
                **ID:** `{guild.id}`
                **멤버 수:** {guild.member_count}명
                **생성일:** <t:{int(guild.created_at.timestamp())}:D>
                **부스트 레벨:** {guild.premium_tier}
                """.strip(),
                inline=True
            )
            
            # 시스템 정보
            embed.add_field(
                name="💻 시스템 정보",
                value=f"""
                **OS:** {platform.system()} {platform.release()}
                **Python:** {platform.python_version()}
                **CPU 사용률:** {cpu_percent}%
                **메모리 사용률:** {memory.percent}%
                **Discord.py:** {discord.__version__}
                """.strip(),
                inline=False
            )
            
            # 봇 아바타 설정
            if bot_user.avatar:
                embed.set_thumbnail(url=bot_user.avatar.url)
            
            embed.set_footer(
                text=f"요청자: {interaction.user}",
                icon_url=interaction.user.avatar.url if interaction.user.avatar else None
            )
            
            await interaction.followup.send(embed=embed)
            logger.info(f"봇 정보 표시: {interaction.user} in {guild.name}")
            
        except Exception as e:
            logger.error(f"정보 명령어 오류: {e}")
            await interaction.followup.send(
                "❌ 봇 정보를 가져오는 중 오류가 발생했습니다.",
                ephemeral=True
            )
    
    @app_commands.command(name="초대", description="봇을 다른 서버에 초대할 수 있는 링크를 제공합니다")
    async def invite(self, interaction: discord.Interaction):
        """봇 초대 링크"""
        try:
            # 필요한 권한들
            permissions = discord.Permissions(
                read_messages=True,
                send_messages=True,
                embed_links=True,
                attach_files=True,
                read_message_history=True,
                use_slash_commands=True,
                manage_messages=True
            )
            
            # 초대 링크 생성
            invite_url = discord.utils.oauth_url(
                self.bot.user.id,
                permissions=permissions,
                scopes=['bot', 'applications.commands']
            )
            
            embed = create_embed(
                title="🎉 봇 초대하기",
                description="아래 링크를 클릭하여 다른 서버에 봇을 초대하세요!",
                color=discord.Color.green().value
            )
            
            embed.add_field(
                name="🔗 초대 링크",
                value=f"[여기를 클릭하여 봇 초대하기]({invite_url})",
                inline=False
            )
            
            embed.add_field(
                name="⚠️ 필요한 권한",
                value="""
                • 메시지 읽기/보내기
                • 임베드 링크 사용
                • 파일 첨부
                • 슬래시 명령어 사용
                • 메시지 관리
                """.strip(),
                inline=False
            )
            
            embed.set_footer(text="초대해 주셔서 감사합니다! 🙏")
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            logger.info(f"초대 링크 제공: {interaction.user}")
            
        except Exception as e:
            logger.error(f"초대 명령어 오류: {e}")
            await interaction.response.send_message(
                "❌ 초대 링크 생성 중 오류가 발생했습니다.",
                ephemeral=True
            )

async def setup(bot):
    await bot.add_cog(BasicCog(bot))
    logger.info("BasicCog 로드 완료")