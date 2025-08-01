from functools import wraps
import discord
from discord.ext import commands
from utils.permissions import PermissionLevel, PermissionChecker

def require_permission(level: PermissionLevel):
    """
    Decorator for commands that checks if the user has the required permission level.
    
    Args:
        level (PermissionLevel): The required permission level
        
    Returns:
        function: The decorated function
    """
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

def cooldown(rate: int, per: float, bucket=commands.BucketType.user):
    """
    Custom cooldown decorator that sends an embed message when on cooldown.
    
    Args:
        rate (int): Number of uses allowed before triggering cooldown
        per (float): Cooldown period in seconds
        bucket (BucketType): The cooldown bucket type
        
    Returns:
        function: The decorated function
    """
    cooldown_mapping = commands.CooldownMapping.from_cooldown(rate, per, bucket)
    
    def decorator(func):
        @wraps(func)
        async def wrapper(self, ctx, *args, **kwargs):
            # Get bucket and check for cooldown
            bucket = cooldown_mapping.get_bucket(ctx.message)
            retry_after = bucket.update_rate_limit()
            
            if retry_after:
                # User is on cooldown
                embed = discord.Embed(
                    title="⏰ 쿨다운",
                    description=f"이 명령어는 {retry_after:.1f}초 후에 다시 사용할 수 있습니다.",
                    color=discord.Color.orange()
                )
                await ctx.send(embed=embed)
                return
                
            return await func(self, ctx, *args, **kwargs)
        return wrapper
    return decorator

def error_handler(func):
    """
    Decorator that handles common errors for commands.
    
    Args:
        func: The command function
        
    Returns:
        function: The decorated function
    """
    @wraps(func)
    async def wrapper(self, ctx, *args, **kwargs):
        try:
            return await func(self, ctx, *args, **kwargs)
        except commands.MissingRequiredArgument as e:
            # Missing argument
            embed = discord.Embed(
                title="❓ 인수 부족",
                description=f"필수 인수가 누락되었습니다: {e.param.name}",
                color=discord.Color.yellow()
            )
            embed.add_field(
                name="사용법", 
                value=f"`{ctx.prefix}{ctx.command.qualified_name} {ctx.command.signature}`",
                inline=False
            )
            await ctx.send(embed=embed)
        except commands.BadArgument as e:
            # Invalid argument
            embed = discord.Embed(
                title="❓ 잘못된 인수",
                description=str(e),
                color=discord.Color.yellow()
            )
            embed.add_field(
                name="사용법", 
                value=f"`{ctx.prefix}{ctx.command.qualified_name} {ctx.command.signature}`",
                inline=False
            )
            await ctx.send(embed=embed)
        except Exception as e:
            # Other errors
            embed = discord.Embed(
                title="🔧 오류 발생",
                description=f"명령어 실행 중 오류가 발생했습니다: {str(e)}",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            
            # Log the error
            import logging
            logger = logging.getLogger('discord_bot')
            logger.error(f"Command error in {ctx.command}: {e}", exc_info=True)
    return wrapper