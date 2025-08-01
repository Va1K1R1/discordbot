from enum import Enum
from config.settings import Settings
import discord

class PermissionLevel(Enum):
    """
    Enum representing permission levels for the bot.
    Higher values indicate higher permission levels.
    """
    OWNER = 5        # Bot owner
    ADMIN = 4        # Server administrator
    MODERATOR = 3    # Moderator
    TRUSTED = 2      # Trusted user
    MEMBER = 1       # Regular member
    RESTRICTED = 0   # Restricted user

class PermissionChecker:
    """
    Utility class for checking user permissions.
    """
    
    @staticmethod
    async def check_permission(member, required_level: PermissionLevel):
        """
        Check if a member has the required permission level.
        
        Args:
            member (discord.Member): The member to check
            required_level (PermissionLevel): The required permission level
            
        Returns:
            bool: True if the member has the required permission level, False otherwise
        """
        user_level = await PermissionChecker.get_user_level(member)
        return user_level.value >= required_level.value
    
    @staticmethod
    async def get_user_level(member):
        """
        Get the permission level of a member.
        
        Args:
            member (discord.Member): The member to check
            
        Returns:
            PermissionLevel: The member's permission level
        """
        # Check if the member is the bot owner
        if member.id == Settings.BOT_OWNER_ID:
            return PermissionLevel.OWNER
            
        # Check if the member is a server administrator
        if member.guild_permissions.administrator:
            return PermissionLevel.ADMIN
            
        # Check role-based permissions
        role_permissions = {
            Settings.ADMIN_ROLE_ID: PermissionLevel.ADMIN,
            Settings.MODERATOR_ROLE_ID: PermissionLevel.MODERATOR,
            Settings.TRUSTED_ROLE_ID: PermissionLevel.TRUSTED
        }
        
        # Get the highest permission level from the member's roles
        highest_level = PermissionLevel.MEMBER
        for role in member.roles:
            if role.id in role_permissions:
                level = role_permissions[role.id]
                if level.value > highest_level.value:
                    highest_level = level
                    
        return highest_level