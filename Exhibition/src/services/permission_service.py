import discord
from discord import app_commands
import functools
from typing import Callable, TypeVar, Any, Optional, List
from src.config.settings import settings
import logging

logger = logging.getLogger(__name__)

T = TypeVar('T')


def check_admin_permission():
    """
    관리자 권한 확인 데코레이터
    
    Discord 슬래시 커맨드에서 사용자가 관리자인지 확인합니다.
    """
    def predicate(interaction: discord.Interaction) -> bool:
        # 설정에 지정된 관리자 ID 확인
        if int(interaction.user.id) in settings.admin_user_ids:
            return True
        
        # 서버 관리자 권한 확인
        if isinstance(interaction.user, discord.Member) and interaction.user.guild_permissions.administrator:
            return True
        
        return False
    
    # app_commands.check 데코레이터 반환
    return app_commands.check(predicate)


def check_guild_permission():
    """
    허용된 길드 확인 데코레이터
    
    Discord 슬래시 커맨드가 허용된 길드에서만 실행되도록 합니다.
    """
    def predicate(interaction: discord.Interaction) -> bool:
        # 설정에 허용된 길드가 없으면 모든 길드 허용
        if not settings.allowed_guild_ids:
            return True
        
        # 길드 ID 확인
        return interaction.guild_id in settings.allowed_guild_ids
    
    # app_commands.check 데코레이터 반환
    return app_commands.check(predicate)


def check_role_permission(allowed_roles: List[str]):
    """
    역할 권한 확인 데코레이터
    
    Discord 슬래시 커맨드에서 사용자가 필요한 역할을 가지고 있는지 확인합니다.
    """
    def predicate(interaction: discord.Interaction) -> bool:
        # 관리자는 항상 허용
        if int(interaction.user.id) in settings.admin_user_ids:
            return True
        
        # 서버 관리자 권한 확인
        if isinstance(interaction.user, discord.Member) and interaction.user.guild_permissions.administrator:
            return True
        
        # 역할 확인
        if isinstance(interaction.user, discord.Member):
            user_roles = [role.name for role in interaction.user.roles]
            return any(role in allowed_roles for role in user_roles)
        
        return False
    
    # app_commands.check 데코레이터 반환
    return app_commands.check(predicate)


async def handle_permission_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    """
    권한 오류 처리 함수
    
    권한 관련 오류 발생 시 사용자에게 적절한 메시지를 표시합니다.
    """
    if isinstance(error, app_commands.CheckFailure):
        await interaction.response.send_message(
            "❌ 이 명령어를 사용할 권한이 없습니다.",
            ephemeral=True
        )
        return True
    
    return False