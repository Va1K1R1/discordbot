import discord
from discord.ext import commands
import asyncio
from datetime import datetime, timedelta
import logging

from utils.permissions import PermissionLevel, PermissionChecker
from utils.decorators import require_permission, error_handler, cooldown
from utils.helpers import MessageFormatter, InputValidator
from database.models import UserPointsModel
from database.shop_models import ShopModel
from config.settings import Settings

class Shop(commands.Cog):
    """
    Shop system for purchasing roles and channel access with points.
    """
    
    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger('discord_bot.shop')
        self.point_model = UserPointsModel(bot.db)
        self.shop_model = ShopModel(bot.db)
        self.formatter = MessageFormatter()
        
    @commands.group(name="상점", aliases=["shop"], invoke_without_command=True)
    @error_handler
    async def shop(self, ctx):
        """상점 명령어 그룹"""
        embed = discord.Embed(
            title="🛒 포인트 상점",
            description="포인트로 다양한 아이템을 구매할 수 있습니다.",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="역할 상점",
            value=f"`{ctx.prefix}상점 역할` - 구매 가능한 역할 목록을 확인합니다.",
            inline=False
        )
        
        embed.add_field(
            name="채널 상점",
            value=f"`{ctx.prefix}상점 채널` - 구매 가능한 채널 목록을 확인합니다.",
            inline=False
        )
        
        embed.add_field(
            name="상자 상점",
            value=f"`{ctx.prefix}상자` - 구매 가능한 상자 목록을 확인합니다.",
            inline=False
        )
        
        embed.add_field(
            name="관리자 명령어",
            value=f"`{ctx.prefix}상점 관리` - 상점 관리 명령어를 확인합니다.",
            inline=False
        )
        
        await ctx.send(embed=embed)
        
    @shop.command(name="역할", aliases=["roles"])
    @error_handler
    async def shop_roles(self, ctx):
        """구매 가능한 역할 목록을 표시합니다."""
        roles = await self.shop_model.get_purchasable_roles(ctx.guild.id)
        
        if not roles:
            embed = discord.Embed(
                title="🛒 역할 상점",
                description="현재 구매 가능한 역할이 없습니다.",
                color=discord.Color.orange()
            )
            await ctx.send(embed=embed)
            return
            
        embed = discord.Embed(
            title="🛒 역할 상점",
            description="포인트로 구매할 수 있는 역할 목록입니다.",
            color=discord.Color.blue()
        )
        
        for role_data in roles:
            role = ctx.guild.get_role(role_data['role_id'])
            if not role:
                continue
                
            embed.add_field(
                name=f"{role.name} - {role_data['price']:,} 포인트",
                value=role_data['description'] or "설명 없음",
                inline=False
            )
            
        embed.set_footer(text=f"역할을 구매하려면 '{ctx.prefix}역할구매 [역할이름]' 명령어를 사용하세요.")
        
        await ctx.send(embed=embed)
        
    @shop.command(name="채널", aliases=["channels"])
    @error_handler
    async def shop_channels(self, ctx):
        """구매 가능한 채널 목록을 표시합니다."""
        channels = await self.shop_model.get_purchasable_channels(ctx.guild.id)
        
        if not channels:
            embed = discord.Embed(
                title="🛒 채널 상점",
                description="현재 구매 가능한 채널이 없습니다.",
                color=discord.Color.orange()
            )
            await ctx.send(embed=embed)
            return
            
        embed = discord.Embed(
            title="🛒 채널 상점",
            description="포인트로 접근 권한을 구매할 수 있는 채널 목록입니다.",
            color=discord.Color.blue()
        )
        
        for channel_data in channels:
            channel = ctx.guild.get_channel(channel_data['channel_id'])
            if not channel:
                continue
                
            embed.add_field(
                name=f"{channel.name} - {channel_data['price']:,} 포인트",
                value=channel_data['description'] or "설명 없음",
                inline=False
            )
            
        embed.set_footer(text=f"채널 접근 권한을 구매하려면 '{ctx.prefix}채널구매 [채널이름]' 명령어를 사용하세요.")
        
        await ctx.send(embed=embed)
        
    @commands.command(name="역할구매", aliases=["buyrole"])
    @error_handler
    async def buy_role(self, ctx, *, role_name: str):
        """
        포인트로 역할을 구매합니다.
        
        Args:
            role_name (str): 구매할 역할 이름
        """
        # Find the role by name
        role = discord.utils.find(lambda r: r.name.lower() == role_name.lower(), ctx.guild.roles)
        
        if not role:
            await ctx.send(f"❌ '{role_name}' 역할을 찾을 수 없습니다.")
            return
            
        # Check if the role is purchasable
        role_data = await self.shop_model.get_purchasable_role(ctx.guild.id, role.id)
        
        if not role_data:
            await ctx.send(f"❌ '{role.name}' 역할은 구매할 수 없습니다.")
            return
            
        # Check if the user already has the role
        if role in ctx.author.roles:
            await ctx.send(f"❌ 이미 '{role.name}' 역할을 가지고 있습니다.")
            return
            
        # Check if the user has enough points
        user_points = await self.point_model.get_user_points(ctx.author.id)
        
        if not user_points or user_points['points'] < role_data['price']:
            await ctx.send(f"❌ 포인트가 부족합니다. 필요한 포인트: {role_data['price']:,}")
            return
            
        # Confirm purchase
        confirm_msg = await ctx.send(
            f"⚠️ {ctx.author.mention}, '{role.name}' 역할을 {role_data['price']:,} 포인트에 구매하시겠습니까? "
            f"(30초 내에 ✅ 를 클릭하여 확인하세요.)"
        )
        
        await confirm_msg.add_reaction("✅")
        await confirm_msg.add_reaction("❌")
        
        def check(reaction, user):
            return user == ctx.author and str(reaction.emoji) in ["✅", "❌"] and reaction.message.id == confirm_msg.id
            
        try:
            reaction, user = await self.bot.wait_for('reaction_add', timeout=30.0, check=check)
            
            if str(reaction.emoji) == "❌":
                await confirm_msg.delete()
                await ctx.send("❌ 구매가 취소되었습니다.")
                return
                
            if str(reaction.emoji) != "✅":
                return
                
        except asyncio.TimeoutError:
            await confirm_msg.delete()
            await ctx.send("❌ 시간이 초과되어 구매가 취소되었습니다.")
            return
            
        # Remove points from user
        success, message = await self.point_model.remove_points(
            user_id=ctx.author.id,
            amount=role_data['price'],
            reason=f"역할 구매: {role.name}"
        )
        
        if not success:
            await ctx.send(f"❌ 포인트 차감 중 오류가 발생했습니다: {message}")
            return
            
        # Add role to user
        try:
            await ctx.author.add_roles(role, reason=f"포인트로 구매: {role_data['price']} 포인트")
            
            # Record the purchase
            await self.shop_model.purchase_role(ctx.author.id, ctx.guild.id, role.id)
            
            embed = discord.Embed(
                title="✅ 역할 구매 완료",
                description=f"{ctx.author.mention}님이 '{role.name}' 역할을 {role_data['price']:,} 포인트에 구매했습니다!",
                color=discord.Color.green()
            )
            
            await ctx.send(embed=embed)
            
            # Log the purchase
            if hasattr(self.bot, 'log_channel') and self.bot.log_channel:
                log_embed = discord.Embed(
                    title="💰 역할 구매",
                    description=f"{ctx.author.mention}님이 '{role.name}' 역할을 {role_data['price']:,} 포인트에 구매했습니다.",
                    color=discord.Color.gold(),
                    timestamp=datetime.now()
                )
                await self.bot.log_channel.send(embed=log_embed)
                
        except discord.Forbidden:
            # Refund points
            await self.point_model.add_points(
                user_id=ctx.author.id,
                username=str(ctx.author),
                amount=role_data['price'],
                reason=f"역할 구매 실패 환불: {role.name}"
            )
            
            await ctx.send("❌ 역할을 부여할 권한이 없습니다. 포인트가 환불되었습니다.")
            
        except Exception as e:
            # Refund points
            await self.point_model.add_points(
                user_id=ctx.author.id,
                username=str(ctx.author),
                amount=role_data['price'],
                reason=f"역할 구매 실패 환불: {role.name}"
            )
            
            self.logger.error(f"Error adding role: {e}")
            await ctx.send(f"❌ 역할 부여 중 오류가 발생했습니다. 포인트가 환불되었습니다.")
            
    @commands.command(name="채널구매", aliases=["buychannel"])
    @error_handler
    async def buy_channel(self, ctx, *, channel_name: str):
        """
        포인트로 채널 접근 권한을 구매합니다.
        
        Args:
            channel_name (str): 구매할 채널 이름
        """
        # Find the channel by name
        channel = discord.utils.find(lambda c: c.name.lower() == channel_name.lower(), ctx.guild.channels)
        
        if not channel:
            await ctx.send(f"❌ '{channel_name}' 채널을 찾을 수 없습니다.")
            return
            
        # Check if the channel is purchasable
        channel_data = await self.shop_model.get_purchasable_channel(ctx.guild.id, channel.id)
        
        if not channel_data:
            await ctx.send(f"❌ '{channel.name}' 채널은 구매할 수 없습니다.")
            return
            
        # Get the access role
        access_role = ctx.guild.get_role(channel_data['access_role_id'])
        
        if not access_role:
            await ctx.send(f"❌ 채널 접근 역할을 찾을 수 없습니다. 관리자에게 문의하세요.")
            return
            
        # Check if the user already has access
        if access_role in ctx.author.roles:
            await ctx.send(f"❌ 이미 '{channel.name}' 채널에 접근할 수 있습니다.")
            return
            
        # Check if the user has enough points
        user_points = await self.point_model.get_user_points(ctx.author.id)
        
        if not user_points or user_points['points'] < channel_data['price']:
            await ctx.send(f"❌ 포인트가 부족합니다. 필요한 포인트: {channel_data['price']:,}")
            return
            
        # Confirm purchase
        confirm_msg = await ctx.send(
            f"⚠️ {ctx.author.mention}, '{channel.name}' 채널 접근 권한을 {channel_data['price']:,} 포인트에 구매하시겠습니까? "
            f"(30초 내에 ✅ 를 클릭하여 확인하세요.)"
        )
        
        await confirm_msg.add_reaction("✅")
        await confirm_msg.add_reaction("❌")
        
        def check(reaction, user):
            return user == ctx.author and str(reaction.emoji) in ["✅", "❌"] and reaction.message.id == confirm_msg.id
            
        try:
            reaction, user = await self.bot.wait_for('reaction_add', timeout=30.0, check=check)
            
            if str(reaction.emoji) == "❌":
                await confirm_msg.delete()
                await ctx.send("❌ 구매가 취소되었습니다.")
                return
                
            if str(reaction.emoji) != "✅":
                return
                
        except asyncio.TimeoutError:
            await confirm_msg.delete()
            await ctx.send("❌ 시간이 초과되어 구매가 취소되었습니다.")
            return
            
        # Remove points from user
        success, message = await self.point_model.remove_points(
            user_id=ctx.author.id,
            amount=channel_data['price'],
            reason=f"채널 접근 구매: {channel.name}"
        )
        
        if not success:
            await ctx.send(f"❌ 포인트 차감 중 오류가 발생했습니다: {message}")
            return
            
        # Add role to user
        try:
            await ctx.author.add_roles(access_role, reason=f"채널 접근 구매: {channel_data['price']} 포인트")
            
            # Record the purchase
            await self.shop_model.purchase_channel(ctx.author.id, ctx.guild.id, channel.id)
            
            embed = discord.Embed(
                title="✅ 채널 접근 구매 완료",
                description=f"{ctx.author.mention}님이 '{channel.name}' 채널 접근 권한을 {channel_data['price']:,} 포인트에 구매했습니다!",
                color=discord.Color.green()
            )
            
            await ctx.send(embed=embed)
            
            # Log the purchase
            if hasattr(self.bot, 'log_channel') and self.bot.log_channel:
                log_embed = discord.Embed(
                    title="💰 채널 접근 구매",
                    description=f"{ctx.author.mention}님이 '{channel.name}' 채널 접근 권한을 {channel_data['price']:,} 포인트에 구매했습니다.",
                    color=discord.Color.gold(),
                    timestamp=datetime.now()
                )
                await self.bot.log_channel.send(embed=log_embed)
                
        except discord.Forbidden:
            # Refund points
            await self.point_model.add_points(
                user_id=ctx.author.id,
                username=str(ctx.author),
                amount=channel_data['price'],
                reason=f"채널 접근 구매 실패 환불: {channel.name}"
            )
            
            await ctx.send("❌ 역할을 부여할 권한이 없습니다. 포인트가 환불되었습니다.")
            
        except Exception as e:
            # Refund points
            await self.point_model.add_points(
                user_id=ctx.author.id,
                username=str(ctx.author),
                amount=channel_data['price'],
                reason=f"채널 접근 구매 실패 환불: {channel.name}"
            )
            
            self.logger.error(f"Error adding role: {e}")
            await ctx.send(f"❌ 역할 부여 중 오류가 발생했습니다. 포인트가 환불되었습니다.")
            
    @shop.group(name="관리", aliases=["admin"], invoke_without_command=True)
    @require_permission(PermissionLevel.ADMIN)
    @error_handler
    async def shop_admin(self, ctx):
        """상점 관리 명령어 그룹"""
        embed = discord.Embed(
            title="🛠️ 상점 관리",
            description="상점 관리 명령어 목록입니다.",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="역할 관리",
            value=(
                f"`{ctx.prefix}상점 관리 역할추가 [역할] [가격] [설명]` - 구매 가능한 역할을 추가합니다.\n"
                f"`{ctx.prefix}상점 관리 역할제거 [역할]` - 구매 가능한 역할을 제거합니다."
            ),
            inline=False
        )
        
        embed.add_field(
            name="채널 관리",
            value=(
                f"`{ctx.prefix}상점 관리 채널추가 [채널] [가격] [접근역할] [설명]` - 구매 가능한 채널을 추가합니다.\n"
                f"`{ctx.prefix}상점 관리 채널제거 [채널]` - 구매 가능한 채널을 제거합니다."
            ),
            inline=False
        )
        
        await ctx.send(embed=embed)
        
    @shop_admin.command(name="역할추가", aliases=["addrole"])
    @require_permission(PermissionLevel.ADMIN)
    @error_handler
    async def add_purchasable_role(self, ctx, role: discord.Role, price: int, *, description: str = None):
        """
        구매 가능한 역할을 추가합니다.
        
        Args:
            role (discord.Role): 추가할 역할
            price (int): 역할 가격
            description (str, optional): 역할 설명
        """
        # Validate price
        if not InputValidator.validate_amount(price, 1, 1000000):
            await ctx.send("❌ 가격은 1에서 1,000,000 사이여야 합니다.")
            return
            
        # Add the role to the database
        success = await self.shop_model.add_purchasable_role(
            guild_id=ctx.guild.id,
            role_id=role.id,
            role_name=role.name,
            price=price,
            description=description
        )
        
        if success:
            embed = discord.Embed(
                title="✅ 역할 추가 완료",
                description=f"'{role.name}' 역할이 상점에 추가되었습니다.",
                color=discord.Color.green()
            )
            embed.add_field(name="가격", value=f"{price:,} 포인트", inline=True)
            if description:
                embed.add_field(name="설명", value=description, inline=False)
        else:
            embed = discord.Embed(
                title="❌ 오류 발생",
                description="역할을 추가하는 데 실패했습니다.",
                color=discord.Color.red()
            )
            
        await ctx.send(embed=embed)
        
    @shop_admin.command(name="역할제거", aliases=["removerole"])
    @require_permission(PermissionLevel.ADMIN)
    @error_handler
    async def remove_purchasable_role(self, ctx, role: discord.Role):
        """
        구매 가능한 역할을 제거합니다.
        
        Args:
            role (discord.Role): 제거할 역할
        """
        # Remove the role from the database
        success = await self.shop_model.remove_purchasable_role(ctx.guild.id, role.id)
        
        if success:
            embed = discord.Embed(
                title="✅ 역할 제거 완료",
                description=f"'{role.name}' 역할이 상점에서 제거되었습니다.",
                color=discord.Color.green()
            )
        else:
            embed = discord.Embed(
                title="❌ 오류 발생",
                description="역할을 제거하는 데 실패했습니다.",
                color=discord.Color.red()
            )
            
        await ctx.send(embed=embed)
        
    @shop_admin.command(name="채널추가", aliases=["addchannel"])
    @require_permission(PermissionLevel.ADMIN)
    @error_handler
    async def add_purchasable_channel(self, ctx, channel: discord.TextChannel, price: int, 
                                     access_role: discord.Role, *, description: str = None):
        """
        구매 가능한 채널을 추가합니다.
        
        Args:
            channel (discord.TextChannel): 추가할 채널
            price (int): 채널 가격
            access_role (discord.Role): 채널 접근 역할
            description (str, optional): 채널 설명
        """
        # Validate price
        if not InputValidator.validate_amount(price, 1, 1000000):
            await ctx.send("❌ 가격은 1에서 1,000,000 사이여야 합니다.")
            return
            
        # Add the channel to the database
        success = await self.shop_model.add_purchasable_channel(
            guild_id=ctx.guild.id,
            channel_id=channel.id,
            channel_name=channel.name,
            price=price,
            access_role_id=access_role.id,
            description=description
        )
        
        if success:
            embed = discord.Embed(
                title="✅ 채널 추가 완료",
                description=f"'{channel.name}' 채널이 상점에 추가되었습니다.",
                color=discord.Color.green()
            )
            embed.add_field(name="가격", value=f"{price:,} 포인트", inline=True)
            embed.add_field(name="접근 역할", value=access_role.mention, inline=True)
            if description:
                embed.add_field(name="설명", value=description, inline=False)
        else:
            embed = discord.Embed(
                title="❌ 오류 발생",
                description="채널을 추가하는 데 실패했습니다.",
                color=discord.Color.red()
            )
            
        await ctx.send(embed=embed)
        
    @shop_admin.command(name="채널제거", aliases=["removechannel"])
    @require_permission(PermissionLevel.ADMIN)
    @error_handler
    async def remove_purchasable_channel(self, ctx, channel: discord.TextChannel):
        """
        구매 가능한 채널을 제거합니다.
        
        Args:
            channel (discord.TextChannel): 제거할 채널
        """
        # Remove the channel from the database
        success = await self.shop_model.remove_purchasable_channel(ctx.guild.id, channel.id)
        
        if success:
            embed = discord.Embed(
                title="✅ 채널 제거 완료",
                description=f"'{channel.name}' 채널이 상점에서 제거되었습니다.",
                color=discord.Color.green()
            )
        else:
            embed = discord.Embed(
                title="❌ 오류 발생",
                description="채널을 제거하는 데 실패했습니다.",
                color=discord.Color.red()
            )
            
        await ctx.send(embed=embed)

async def setup(bot):
    """Add the cog to the bot."""
    await bot.add_cog(Shop(bot))