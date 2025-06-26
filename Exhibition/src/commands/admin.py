import discord
from discord import app_commands
from discord.ext import commands
import logging
from typing import Optional, List
from src.services.permission_service import check_admin_permission, check_role_permission
from src.services.command_service import command_service
from src.utils.helpers import create_embed
from src.exceptions.custom_exceptions import (
    CommandNotFoundError,
    CommandAlreadyExistsError,
    ValidationError,
    DatabaseError
)

logger = logging.getLogger(__name__)


class AdminCog(commands.Cog):
    """관리자 명령어"""
    
    def __init__(self, bot):
        self.bot = bot
    
    @commands.command(name="sync")
    @commands.has_permissions(administrator=True)
    async def sync_commands(self, ctx, scope: Optional[str] = None):
        """슬래시 커맨드 수동 동기화"""
        try:
            if scope == "global":
                # 전역 동기화
                synced = await self.bot.tree.sync()
                await ctx.send(f"✅ {len(synced)}개의 전역 슬래시 커맨드가 동기화되었습니다.")
                
            elif scope == "guild" or scope is None:
                # 현재 길드 동기화
                synced = await self.bot.tree.sync(guild=ctx.guild)
                await ctx.send(f"✅ {len(synced)}개의 길드 슬래시 커맨드가 동기화되었습니다.")
                
            elif scope == "clear":
                # 길드 커맨드 초기화
                self.bot.tree.clear_commands(guild=ctx.guild)
                await self.bot.tree.sync(guild=ctx.guild)
                await ctx.send("✅ 길드 슬래시 커맨드가 초기화되었습니다.")
                
            elif scope == "copy":
                # 전역 커맨드를 현재 길드로 복사
                self.bot.tree.copy_global_to(guild=ctx.guild)
                synced = await self.bot.tree.sync(guild=ctx.guild)
                await ctx.send(f"✅ {len(synced)}개의 전역 커맨드가 길드로 복사되었습니다.")
                
            else:
                await ctx.send(
                    "❌ 올바른 옵션을 사용해주세요:\n"
                    "`!sync` - 현재 길드 동기화\n"
                    "`!sync global` - 전역 동기화\n"
                    "`!sync clear` - 길드 커맨드 초기화\n"
                    "`!sync copy` - 전역 커맨드를 길드로 복사"
                )
                
        except Exception as e:
            logger.error(f"커맨드 동기화 실패: {e}")
            await ctx.send(f"❌ 동기화 중 오류가 발생했습니다: {str(e)}")
    
    @sync_commands.error
    async def sync_error(self, ctx, error):
        """sync 명령어 오류 처리"""
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ 이 명령어를 사용하려면 관리자 권한이 필요합니다.")
        else:
            await ctx.send(f"❌ 오류가 발생했습니다: {str(error)}")
    
    @app_commands.command(name="상태", description="봇 상태 정보를 확인합니다")
    @check_admin_permission()
    async def status(self, interaction: discord.Interaction):
        """봇 상태 정보 확인"""
        try:
            # 봇 정보 수집
            uptime = discord.utils.utcnow() - self.bot.start_time
            uptime_str = f"{uptime.days}일 {uptime.seconds // 3600}시간 {(uptime.seconds // 60) % 60}분"
            
            guild_count = len(self.bot.guilds)
            user_count = sum(guild.member_count for guild in self.bot.guilds)
            
            # 명령어 수 조회
            commands = await command_service.get_all_commands(str(interaction.guild.id))
            command_count = len(commands)
            
            # 슬래시 커맨드 수 조회
            slash_commands = len(self.bot.tree.get_commands())
            guild_commands = len(self.bot.tree.get_commands(guild=interaction.guild))
            
            # 임베드 생성
            embed = create_embed(
                title="🤖 봇 상태 정보",
                color=0x00ff00,
                fields=[
                    {"name": "가동 시간", "value": uptime_str, "inline": True},
                    {"name": "서버 수", "value": str(guild_count), "inline": True},
                    {"name": "사용자 수", "value": str(user_count), "inline": True},
                    {"name": "커스텀 명령어", "value": str(command_count), "inline": True},
                    {"name": "전역 슬래시 커맨드", "value": str(slash_commands), "inline": True},
                    {"name": "길드 슬래시 커맨드", "value": str(guild_commands), "inline": True},
                    {"name": "핑", "value": f"{round(self.bot.latency * 1000)}ms", "inline": True},
                    {"name": "버전", "value": "1.0.0", "inline": True}
                ],
                footer=f"요청자: {interaction.user.name}"
            )
            
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            logger.error(f"상태 명령어 실행 실패: {e}")
            await interaction.response.send_message(
                "❌ 상태 정보를 가져오는 중 오류가 발생했습니다.",
                ephemeral=True
            )
    
    @app_commands.command(name="명령어삭제", description="커스텀 명령어를 삭제합니다")
    @app_commands.describe(name="삭제할 명령어 이름")
    @check_admin_permission()
    async def delete_command(self, interaction: discord.Interaction, name: str):
        """커스텀 명령어 삭제"""
        try:
            await interaction.response.defer(ephemeral=True)
            
            # 명령어 삭제
            await command_service.delete_command(str(interaction.guild.id), name)
            
            # Discord 명령어 트리에서 제거
            for cmd in self.bot.tree.get_commands():
                if cmd.name == name:
                    self.bot.tree.remove_command(cmd.name, guild=interaction.guild)
                    break
            
            # 명령어 트리 동기화
            await self.bot.tree.sync(guild=interaction.guild)
            
            await interaction.followup.send(
                f"✅ 명령어 `{name}`이(가) 성공적으로 삭제되었습니다.",
                ephemeral=True
            )
            
        except CommandNotFoundError:
            await interaction.followup.send(
                f"❌ 명령어 `{name}`을(를) 찾을 수 없습니다.",
                ephemeral=True
            )
        except Exception as e:
            logger.error(f"명령어 삭제 실패: {e}")
            await interaction.followup.send(
                "❌ 명령어 삭제 중 오류가 발생했습니다.",
                ephemeral=True
            )
    
    @app_commands.command(name="역할설정", description="명령어에 허용된 역할을 설정합니다")
    @app_commands.describe(
        command_name="설정할 명령어 이름",
        roles="허용할 역할 (쉼표로 구분, 비워두면 모든 사용자 허용)"
    )
    @check_admin_permission()
    async def set_roles(
        self, 
        interaction: discord.Interaction, 
        command_name: str, 
        roles: Optional[str] = None
    ):
        """명령어에 허용된 역할 설정"""
        try:
            await interaction.response.defer(ephemeral=True)
            
            # 역할 목록 파싱
            allowed_roles = []
            if roles:
                allowed_roles = [role.strip() for role in roles.split(",") if role.strip()]
            
            # 명령어 업데이트
            command = await command_service.update_command(
                guild_id=str(interaction.guild.id),
                name=command_name,
                allowed_roles=allowed_roles
            )
            
            # 응답 메시지 생성
            if allowed_roles:
                roles_text = ", ".join(f"`{role}`" for role in allowed_roles)
                message = f"✅ 명령어 `{command_name}`에 다음 역할이 허용되었습니다: {roles_text}"
            else:
                message = f"✅ 명령어 `{command_name}`이(가) 모든 사용자에게 허용되었습니다."
            
            await interaction.followup.send(message, ephemeral=True)
            
        except CommandNotFoundError:
            await interaction.followup.send(
                f"❌ 명령어 `{command_name}`을(를) 찾을 수 없습니다.",
                ephemeral=True
            )
        except Exception as e:
            logger.error(f"역할 설정 실패: {e}")
            await interaction.followup.send(
                "❌ 역할 설정 중 오류가 발생했습니다.",
                ephemeral=True
            )
    
    @app_commands.command(name="명령어정보", description="명령어의 상세 정보를 확인합니다")
    @app_commands.describe(name="확인할 명령어 이름")
    @check_admin_permission()
    async def command_info(self, interaction: discord.Interaction, name: str):
        """명령어 상세 정보 확인"""
        try:
            await interaction.response.defer(ephemeral=True)
            
            # 명령어 조회
            command = await command_service.get_command(str(interaction.guild.id), name)
            
            # 허용된 역할 조회
            allowed_roles = command.get_allowed_roles()
            roles_text = ", ".join(f"`{role}`" for role in allowed_roles) if allowed_roles else "모든 사용자"
            
            # 임베드 생성
            embed = create_embed(
                title=f"/{command.name} 명령어 정보",
                description=command.description,
                color=0x3498db,
                fields=[
                    {"name": "응답 템플릿", "value": command.response_template[:1024], "inline": False},
                    {"name": "AI 사용", "value": "예" if command.use_ai else "아니오", "inline": True},
                    {"name": "허용된 역할", "value": roles_text, "inline": True},
                    {"name": "사용 횟수", "value": str(command.usage_count), "inline": True},
                    {"name": "생성자", "value": f"<@{command.created_by}>", "inline": True},
                    {"name": "생성일", "value": command.created_at.strftime("%Y-%m-%d %H:%M"), "inline": True}
                ],
                footer=f"명령어 ID: {command.id}"
            )
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except CommandNotFoundError:
            await interaction.followup.send(
                f"❌ 명령어 `{name}`을(를) 찾을 수 없습니다.",
                ephemeral=True
            )
        except Exception as e:
            logger.error(f"명령어 정보 조회 실패: {e}")
            await interaction.followup.send(
                "❌ 명령어 정보를 가져오는 중 오류가 발생했습니다.",
                ephemeral=True
            )


async def setup(bot):
    # 봇 시작 시간 설정
    bot.start_time = discord.utils.utcnow()
    
    await bot.add_cog(AdminCog(bot))
    logger.info("AdminCog 로드 완료")