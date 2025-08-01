import discord
from discord import app_commands
from discord.ext import commands
import logging
from utils.permissions import PermissionLevel, PermissionChecker
from utils.decorators import error_handler
from utils.helpers import MessageFormatter, InputValidator

class Permissions(commands.Cog):
    """
    Permissions management cog for handling user roles and permissions.
    """
    def __init__(self, bot):
        self.bot = bot
        self.formatter = MessageFormatter()

    async def check_permission(self, user, guild):
        """Check user's permission level"""
        checker = PermissionChecker()
        return checker.get_permission_level(user, guild)

    @app_commands.command(name="권한확인", description="사용자의 권한 레벨을 확인합니다")
    @app_commands.describe(user="권한을 확인할 사용자 (선택사항)")
    async def check_permission_slash(self, interaction: discord.Interaction, user: discord.Member = None):
        """슬래시 명령어로 권한 확인"""
        target_user = user or interaction.user
        
        try:
            permission_level = await self.check_permission(target_user, interaction.guild)
            
            embed = discord.Embed(
                title="🔐 권한 확인",
                color=discord.Color.blue()
            )
            embed.add_field(
                name="사용자", 
                value=f"{target_user.mention} ({target_user.display_name})", 
                inline=False
            )
            embed.add_field(
                name="권한 레벨", 
                value=f"**{permission_level.name}** (레벨 {permission_level.value})", 
                inline=False
            )
            
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            await interaction.response.send_message(
                f"❌ 권한 확인 중 오류가 발생했습니다: {e}", 
                ephemeral=True
            )

    @commands.command(name="권한확인")
    @error_handler
    async def check_permission_cmd(self, ctx, user: discord.Member = None):
        """
        Check user's permission level.
        
        Args:
            user: User to check permissions for (optional, defaults to command author)
        """
        if user is None:
            user = ctx.author

        try:
            permission_level = await self.check_permission(user, ctx.guild)
            
            embed = self.formatter.create_embed(
                title="🔐 권한 확인",
                color=discord.Color.blue()
            )
            embed.add_field(
                name="사용자", 
                value=f"{user.mention} ({user.display_name})", 
                inline=False
            )
            embed.add_field(
                name="권한 레벨", 
                value=f"**{permission_level.name}** (레벨 {permission_level.value})", 
                inline=False
            )
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            embed = self.formatter.create_error_embed(
                title="오류 발생",
                description=f"권한 확인 중 오류가 발생했습니다: {e}"
            )
            await ctx.send(embed=embed)

    @app_commands.command(name="역할부여", description="사용자에게 역할을 부여합니다")
    @app_commands.describe(
        user="역할을 부여할 사용자",
        role="부여할 역할"
    )
    async def give_role_slash(self, interaction: discord.Interaction, user: discord.Member, role: discord.Role):
        """슬래시 명령어로 역할 부여"""
        # 권한 체크
        user_permission = await self.check_permission(interaction.user, interaction.guild)
        if user_permission.value < PermissionLevel.MODERATOR.value:
            await interaction.response.send_message("❌ 이 명령어를 사용할 권한이 없습니다.", ephemeral=True)
            return

        try:
            await user.add_roles(role, reason=f"역할 부여 by {interaction.user}")
            embed = discord.Embed(
                title="✅ 역할 부여 완료",
                description=f"{user.mention}에게 {role.mention} 역할을 부여했습니다.",
                color=discord.Color.green()
            )
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            await interaction.response.send_message(
                f"❌ 역할 부여 중 오류가 발생했습니다: {e}", 
                ephemeral=True
            )

    @commands.command(name="역할부여", aliases=["give_role"])
    @error_handler
    async def give_role(self, ctx, user: discord.Member, role: discord.Role):
        """
        Give a role to a user.
        
        Args:
            user: User to give the role to
            role: Role to give
        """
        # Check if user has permission
        user_permission = await self.check_permission(ctx.author, ctx.guild)
        if user_permission.value < PermissionLevel.MODERATOR.value:
            embed = self.formatter.create_error_embed(
                title="권한 부족",
                description="이 명령어를 사용하려면 모더레이터 권한이 필요합니다."
            )
            await ctx.send(embed=embed)
            return

        # Validate inputs
        if not InputValidator.is_valid_user(user):
            embed = self.formatter.create_error_embed(
                title="잘못된 사용자",
                description="유효한 사용자를 지정해주세요."
            )
            await ctx.send(embed=embed)
            return

        if not InputValidator.is_valid_role(role):
            embed = self.formatter.create_error_embed(
                title="잘못된 역할",
                description="유효한 역할을 지정해주세요."
            )
            await ctx.send(embed=embed)
            return

        # Check if user already has the role
        if role in user.roles:
            embed = self.formatter.create_warning_embed(
                title="역할 중복",
                description=f"{user.mention}은 이미 {role.mention} 역할을 가지고 있습니다."
            )
            await ctx.send(embed=embed)
            return

        try:
            # Check if bot can manage the role
            if role >= ctx.guild.me.top_role:
                embed = self.formatter.create_error_embed(
                    title="권한 부족",
                    description="봇이 해당 역할을 관리할 수 없습니다. (역할 계층 문제)"
                )
                await ctx.send(embed=embed)
                return

            # Check if role is manageable
            if not role.is_assignable():
                embed = self.formatter.create_error_embed(
                    title="역할 부여 불가",
                    description="해당 역할은 부여할 수 없습니다."
                )
                await ctx.send(embed=embed)
                return

            # Give the role
            await user.add_roles(role, reason=f"Role given by {ctx.author} via command")
            
            embed = self.formatter.create_success_embed(
                title="역할 부여 완료",
                description=f"{user.mention}에게 {role.mention} 역할을 부여했습니다."
            )
            embed.add_field(name="실행자", value=ctx.author.mention, inline=True)
            embed.add_field(name="대상", value=user.mention, inline=True)
            embed.add_field(name="역할", value=role.mention, inline=True)
            
            await ctx.send(embed=embed)
            
            # Log the action
            logging.info(f"Role {role.name} given to {user} by {ctx.author} in {ctx.guild}")
            
        except discord.Forbidden:
            embed = self.formatter.create_error_embed(
                title="권한 부족",
                description="봇이 해당 역할을 부여할 권한이 없습니다."
            )
            await ctx.send(embed=embed)
        except discord.HTTPException as e:
            embed = self.formatter.create_error_embed(
                title="오류 발생",
                description=f"역할 부여 중 오류가 발생했습니다: {e}"
            )
            await ctx.send(embed=embed)
        except Exception as e:
            embed = self.formatter.create_error_embed(
                title="예상치 못한 오류",
                description=f"역할 부여 중 예상치 못한 오류가 발생했습니다: {e}"
            )
            await ctx.send(embed=embed)

    @app_commands.command(name="역할제거", description="사용자에게서 역할을 제거합니다")
    @app_commands.describe(
        user="역할을 제거할 사용자",
        role="제거할 역할"
    )
    async def remove_role_slash(self, interaction: discord.Interaction, user: discord.Member, role: discord.Role):
        """슬래시 명령어로 역할 제거"""
        # 권한 체크
        user_permission = await self.check_permission(interaction.user, interaction.guild)
        if user_permission.value < PermissionLevel.MODERATOR.value:
            await interaction.response.send_message("❌ 이 명령어를 사용할 권한이 없습니다.", ephemeral=True)
            return

        try:
            await user.remove_roles(role, reason=f"역할 제거 by {interaction.user}")
            embed = discord.Embed(
                title="✅ 역할 제거 완료",
                description=f"{user.mention}에게서 {role.mention} 역할을 제거했습니다.",
                color=discord.Color.green()
            )
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            await interaction.response.send_message(
                f"❌ 역할 제거 중 오류가 발생했습니다: {e}", 
                ephemeral=True
            )

    @commands.command(name="역할제거", aliases=["remove_role"])
    @error_handler
    async def remove_role(self, ctx, user: discord.Member, role: discord.Role):
        """
        Remove a role from a user.
        
        Args:
            user: User to remove the role from
            role: Role to remove
        """
        # Check if user has permission
        user_permission = await self.check_permission(ctx.author, ctx.guild)
        if user_permission.value < PermissionLevel.MODERATOR.value:
            embed = self.formatter.create_error_embed(
                title="권한 부족",
                description="이 명령어를 사용하려면 모더레이터 권한이 필요합니다."
            )
            await ctx.send(embed=embed)
            return

        # Validate inputs
        if not InputValidator.is_valid_user(user):
            embed = self.formatter.create_error_embed(
                title="잘못된 사용자",
                description="유효한 사용자를 지정해주세요."
            )
            await ctx.send(embed=embed)
            return

        if not InputValidator.is_valid_role(role):
            embed = self.formatter.create_error_embed(
                title="잘못된 역할",
                description="유효한 역할을 지정해주세요."
            )
            await ctx.send(embed=embed)
            return

        # Check if user has the role
        if role not in user.roles:
            embed = self.formatter.create_warning_embed(
                title="역할 없음",
                description=f"{user.mention}은 {role.mention} 역할을 가지고 있지 않습니다."
            )
            await ctx.send(embed=embed)
            return

        try:
            # Check if bot can manage the role
            if role >= ctx.guild.me.top_role:
                embed = self.formatter.create_error_embed(
                    title="권한 부족",
                    description="봇이 해당 역할을 관리할 수 없습니다. (역할 계층 문제)"
                )
                await ctx.send(embed=embed)
                return

            # Remove the role
            await user.remove_roles(role, reason=f"Role removed by {ctx.author} via command")
            
            embed = self.formatter.create_success_embed(
                title="역할 제거 완료",
                description=f"{user.mention}에게서 {role.mention} 역할을 제거했습니다."
            )
            embed.add_field(name="실행자", value=ctx.author.mention, inline=True)
            embed.add_field(name="대상", value=user.mention, inline=True)
            embed.add_field(name="역할", value=role.mention, inline=True)
            
            await ctx.send(embed=embed)
            
            # Log the action
            logging.info(f"Role {role.name} removed from {user} by {ctx.author} in {ctx.guild}")
            
        except discord.Forbidden:
            embed = self.formatter.create_error_embed(
                title="권한 부족",
                description="봇이 해당 역할을 제거할 권한이 없습니다."
            )
            await ctx.send(embed=embed)
        except discord.HTTPException as e:
            embed = self.formatter.create_error_embed(
                title="오류 발생",
                description=f"역할 제거 중 오류가 발생했습니다: {e}"
            )
            await ctx.send(embed=embed)
        except Exception as e:
            embed = self.formatter.create_error_embed(
                title="예상치 못한 오류",
                description=f"역할 제거 중 예상치 못한 오류가 발생했습니다: {e}"
            )
            await ctx.send(embed=embed)

    @app_commands.command(name="역할목록", description="서버의 모든 역할을 표시합니다")
    async def list_roles_slash(self, interaction: discord.Interaction):
        """슬래시 명령어로 역할 목록 표시"""
        try:
            roles = sorted(interaction.guild.roles, key=lambda r: r.position, reverse=True)
            
            embed = discord.Embed(
                title=f"🎭 {interaction.guild.name} 역할 목록",
                color=discord.Color.blue()
            )
            
            role_list = []
            for role in roles:
                if role.name != "@everyone":
                    role_list.append(f"{role.mention} (멤버: {len(role.members)})")
            
            if role_list:
                # 너무 길면 나누어서 표시
                if len(role_list) > 20:
                    role_list = role_list[:20]
                    embed.add_field(
                        name="역할 (상위 20개)",
                        value="\n".join(role_list) + f"\n... 총 {len(roles)-1}개 역할",
                        inline=False
                    )
                else:
                    embed.add_field(
                        name="역할",
                        value="\n".join(role_list),
                        inline=False
                    )
            else:
                embed.add_field(
                    name="역할",
                    value="역할이 없습니다.",
                    inline=False
                )
            
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            await interaction.response.send_message(
                f"❌ 역할 목록을 가져오는 중 오류가 발생했습니다: {e}", 
                ephemeral=True
            )

    @commands.command(name="역할목록", aliases=["list_roles", "roles"])
    @error_handler
    async def list_roles(self, ctx):
        """
        List all roles in the server.
        """
        try:
            roles = sorted(ctx.guild.roles, key=lambda r: r.position, reverse=True)
            
            embed = self.formatter.create_embed(
                title=f"🎭 {ctx.guild.name} 역할 목록",
                color=discord.Color.blue()
            )
            
            role_list = []
            for role in roles:
                if role.name != "@everyone":
                    member_count = len(role.members)
                    color_hex = f"#{role.color.value:06x}" if role.color.value != 0 else "기본색"
                    role_list.append(f"{role.mention} - 멤버: {member_count}, 색상: {color_hex}")
            
            if role_list:
                # Split into chunks if too long
                chunk_size = 10
                for i in range(0, len(role_list), chunk_size):
                    chunk = role_list[i:i+chunk_size]
                    field_name = f"역할 ({i+1}-{min(i+chunk_size, len(role_list))})"
                    embed.add_field(
                        name=field_name,
                        value="\n".join(chunk),
                        inline=False
                    )
            else:
                embed.add_field(
                    name="역할",
                    value="이 서버에는 역할이 없습니다.",
                    inline=False
                )
            
            embed.set_footer(text=f"총 {len(roles)-1}개의 역할 (excluding @everyone)")
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            embed = self.formatter.create_error_embed(
                title="오류 발생",
                description=f"역할 목록을 가져오는 중 오류가 발생했습니다: {e}"
            )
            await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Permissions(bot))