import discord
from discord import app_commands
from discord.ext import commands
from sqlalchemy.orm import Session
import logging
from typing import Optional, Dict, Any, List

from src.models.database import get_db
from src.models.command import Command
from src.services.ai_service import ai_service
from src.services.command_service import command_service
from src.services.permission_service import check_admin_permission, check_role_permission
from src.utils.helpers import create_embed
from src.utils.validators import validate_user_input, sanitize_user_input
from src.exceptions.custom_exceptions import (
    CommandNotFoundError,
    CommandAlreadyExistsError,
    ValidationError,
    DatabaseError
)

logger = logging.getLogger(__name__)


class AddCommandModal(discord.ui.Modal):
    """새 커맨드 추가 모달"""
    
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
        """모달 제출 시 처리"""
        await interaction.response.defer(ephemeral=True)
        
        try:
            # AI로 커맨드 메타데이터 생성
            metadata = await ai_service.generate_command_metadata(
                self.command_description.value
            )
            
            # 허용된 역할 파싱
            allowed_roles = []
            if self.allowed_roles.value:
                allowed_roles = [role.strip() for role in self.allowed_roles.value.split(",") if role.strip()]
            
            # 새 커맨드 생성
            new_command = await command_service.create_command(
                guild_id=str(interaction.guild.id),
                name=metadata["name"],
                description=metadata["description"],
                response_template=metadata["response_template"],
                created_by=str(interaction.user.id),
                use_ai=self.use_ai.value.lower() == "true",
                ai_prompt=self.command_description.value,
                allowed_roles=allowed_roles
            )
            
            # 동적 명령어 등록
            await self.register_dynamic_command(interaction, new_command)
            
            # 응답 임베드 생성
            embed = create_embed(
                title="✅ 커맨드 생성 완료",
                description=f"커맨드 `/{metadata['name']}`이(가) 성공적으로 생성되었습니다!",
                color=discord.Color.green().value,
                fields=[
                    {"name": "설명", "value": metadata["description"], "inline": False},
                    {"name": "AI 사용", "value": "예" if new_command.use_ai else "아니오", "inline": True},
                    {"name": "허용된 역할", "value": ", ".join(allowed_roles) if allowed_roles else "모든 사용자", "inline": True}
                ]
            )
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except CommandAlreadyExistsError as e:
            await interaction.followup.send(
                f"❌ 커맨드 `{e.command_name}`이(가) 이미 존재합니다.",
                ephemeral=True
            )
        except ValidationError as e:
            await interaction.followup.send(
                f"❌ 유효성 검사 실패: {e.message}",
                ephemeral=True
            )
        except Exception as e:
            logger.error(f"커맨드 생성 실패: {e}")
            await interaction.followup.send(
                f"❌ 커맨드 생성 중 오류가 발생했습니다: {str(e)}",
                ephemeral=True
            )
    
    async def register_dynamic_command(self, interaction: discord.Interaction, command: Command):
        """동적 슬래시 커맨드 등록"""
        try:
            # 봇 인스턴스 가져오기
            bot = interaction.client
            
            # 명령어 생성
            @app_commands.command(name=command.name, description=command.description)
            @app_commands.describe(user_input="입력 (선택사항)")
            async def dynamic_command(interaction: discord.Interaction, user_input: Optional[str] = ""):
                await self.execute_dynamic_command(interaction, command, user_input)
            
            # 봇의 명령어 트리에 추가
            bot.tree.add_command(dynamic_command, guild=interaction.guild)
            await bot.tree.sync(guild=interaction.guild)
            
            logger.info(f"동적 커맨드 등록 성공: {command.name}")
            
        except Exception as e:
            logger.error(f"동적 커맨드 등록 실패: {e}")
            raise
    
    async def execute_dynamic_command(
        self, 
        interaction: discord.Interaction, 
        command: Command, 
        user_input: str
    ):
        """동적 커맨드 실행"""
        try:
            await interaction.response.defer()
            
            # 권한 확인
            allowed_roles = command.get_allowed_roles()
            if allowed_roles:
                user_roles = [role.name for role in interaction.user.roles]
                if not any(role in allowed_roles for role in user_roles):
                    await interaction.followup.send(
                        "❌ 이 커맨드를 사용할 권한이 없습니다.",
                        ephemeral=True
                    )
                    return
            
            # 사용자 입력 검증
            if user_input:
                is_valid, error_message = validate_user_input(user_input)
                if not is_valid:
                    await interaction.followup.send(
                        f"❌ 입력 오류: {error_message}",
                        ephemeral=True
                    )
                    return
                
                # 입력 정제
                user_input = sanitize_user_input(user_input)
            
            # 응답 생성
            if command.use_ai:
                response = await ai_service.enhance_response(
                    command.response_template,
                    user_input,
                    {
                        "command_name": command.name,
                        "user": interaction.user.name,
                        "guild": interaction.guild.name
                    }
                )
            else:
                # 기본 템플릿 사용
                context = {
                    "user": interaction.user.mention,
                    "input": user_input,
                    "guild": interaction.guild.name
                }
                response = command.response_template.format(**context)
            
            # 사용 통계 업데이트
            db = next(get_db())
            command.increment_usage()
            db.commit()
            
            # 응답 전송
            await interaction.followup.send(response)
            
        except Exception as e:
            logger.error(f"동적 커맨드 실행 실패: {e}")
            await interaction.followup.send(
                "❌ 커맨드 실행 중 오류가 발생했습니다.",
                ephemeral=True
            )


class DynamicCommandsCog(commands.Cog):
    """동적 커맨드 관리"""
    
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
        try:
            await interaction.response.defer(ephemeral=True)
            
            # 커맨드 목록 조회
            commands = await command_service.get_all_commands(str(interaction.guild.id))
            
            if not commands:
                await interaction.followup.send(
                    "이 서버에는 아직 커스텀 커맨드가 없습니다.",
                    ephemeral=True
                )
                return
            
            # 임베드 생성
            embed = create_embed(
                title="📋 서버 커맨드 목록",
                color=discord.Color.blue().value
            )
            
            # 최대 10개만 표시
            for cmd in commands[:10]:
                embed.add_field(
                    name=f"/{cmd.name}",
                    value=f"{cmd.description}\n사용 횟수: {cmd.usage_count}",
                    inline=False
                )
            
            if len(commands) > 10:
                embed.set_footer(text=f"총 {len(commands)}개 커맨드 중 10개만 표시")
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"커맨드 목록 조회 실패: {e}")
            await interaction.followup.send(
                "❌ 커맨드 목록을 가져오는 중 오류가 발생했습니다.",
                ephemeral=True
            )
    
    async def load_existing_commands(self):
        """기존 커맨드 로드"""
        try:
            # 모든 길드에 대해 처리
            for guild in self.bot.guilds:
                # 길드의 모든 커맨드 조회
                commands = await command_service.get_all_commands(str(guild.id))
                
                # 각 커맨드에 대해 동적 명령어 등록
                for command in commands:
                    modal = AddCommandModal()
                    await modal.register_dynamic_command(
                        interaction=None,  # 초기 로드 시에는 interaction이 없음
                        command=command
                    )
                
                logger.info(f"길드 {guild.name}({guild.id})의 기존 커맨드 {len(commands)}개 로드 완료")
                
        except Exception as e:
            logger.error(f"기존 커맨드 로드 실패: {e}")


async def setup(bot):
    cog = DynamicCommandsCog(bot)
    await bot.add_cog(cog)
    
    # 봇이 준비되면 기존 커맨드 로드
    @bot.event
    async def on_ready():
        await cog.load_existing_commands()
    
    logger.info("DynamicCommandsCog 로드 완료")