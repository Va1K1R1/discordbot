import discord
from discord.ext import commands
import asyncio
from datetime import datetime, timedelta
import logging
import random

from utils.permissions import PermissionLevel, PermissionChecker
from utils.decorators import require_permission, error_handler, cooldown
from utils.helpers import MessageFormatter, InputValidator
from database.models import UserPointsModel
from database.gambling_models import GamblingModel
from config.settings import Settings

class Gambling(commands.Cog):
    """
    Gambling system for the bot.
    Includes loot boxes and other gambling features.
    """
    
    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger('discord_bot.gambling')
        self.point_model = UserPointsModel(bot.db)
        self.gambling_model = GamblingModel(bot.db)
        self.formatter = MessageFormatter()
        
    @commands.group(name="상자", aliases=["box", "lootbox"], invoke_without_command=True)
    @error_handler
    async def lootbox(self, ctx):
        """상자 명령어 그룹"""
        boxes = await self.gambling_model.get_box_types(ctx.guild.id)
        
        if not boxes:
            embed = discord.Embed(
                title="🎁 상자 상점",
                description="현재 구매 가능한 상자가 없습니다.",
                color=discord.Color.orange()
            )
            await ctx.send(embed=embed)
            return
            
        embed = discord.Embed(
            title="🎁 상자 상점",
            description="포인트로 구매할 수 있는 상자 목록입니다.",
            color=discord.Color.blue()
        )
        
        for box in boxes:
            embed.add_field(
                name=f"{box['name']} - {box['price']:,} 포인트",
                value=box['description'] or "설명 없음",
                inline=False
            )
            
        embed.set_footer(text=f"상자를 구매하려면 '{ctx.prefix}상자 구매 [상자이름]' 명령어를 사용하세요.")
        
        await ctx.send(embed=embed)
        
    @lootbox.command(name="구매", aliases=["buy", "open"])
    @cooldown(1, 5)  # 5초 쿨다운
    @error_handler
    async def buy_lootbox(self, ctx, *, box_name: str):
        """
        상자를 구매하고 열어 보상을 받습니다.
        
        Args:
            box_name (str): 구매할 상자 이름
        """
        # Get the box type
        box = await self.gambling_model.get_box_type_by_name(ctx.guild.id, box_name)
        
        if not box:
            await ctx.send(f"❌ '{box_name}' 상자를 찾을 수 없습니다.")
            return
            
        # Check if the user has enough points
        user_points = await self.point_model.get_user_points(ctx.author.id)
        
        if not user_points or user_points['points'] < box['price']:
            await ctx.send(f"❌ 포인트가 부족합니다. 필요한 포인트: {box['price']:,}")
            return
            
        # Remove points from user
        success, message = await self.point_model.remove_points(
            user_id=ctx.author.id,
            amount=box['price'],
            reason=f"상자 구매: {box['name']}"
        )
        
        if not success:
            await ctx.send(f"❌ 포인트 차감 중 오류가 발생했습니다: {message}")
            return
            
        # Get a random reward
        reward = await self.gambling_model.get_random_reward(box['id'])
        
        if not reward:
            # Refund points if no reward is available
            await self.point_model.add_points(
                user_id=ctx.author.id,
                username=str(ctx.author),
                amount=box['price'],
                reason=f"상자 구매 실패 환불: {box['name']}"
            )
            
            await ctx.send("❌ 상자에서 보상을 찾을 수 없습니다. 포인트가 환불되었습니다.")
            return
            
        # Process the reward
        points_won = 0
        role_id = None
        item_name = None
        
        # Create suspense with typing and delay
        async with ctx.typing():
            await asyncio.sleep(2)
            
            opening_msg = await ctx.send(f"🎁 {ctx.author.mention}님이 **{box['name']}** 상자를 열고 있습니다...")
            await asyncio.sleep(1.5)
            
            # Show opening animation
            for i in range(3):
                await opening_msg.edit(content=f"🎁 {ctx.author.mention}님이 **{box['name']}** 상자를 열고 있습니다{'.' * (i+1)}")
                await asyncio.sleep(0.7)
                
            await asyncio.sleep(0.5)
            
        # Process reward based on type
        if reward['reward_type'] == 'POINTS':
            points_won = reward['reward_amount']
            
            # Add points to user
            await self.point_model.add_points(
                user_id=ctx.author.id,
                username=str(ctx.author),
                amount=points_won,
                reason=f"상자 보상: {box['name']}"
            )
            
            result_description = f"🎉 축하합니다! **{points_won:,} 포인트**를 획득했습니다!"
            
        elif reward['reward_type'] == 'ROLE':
            role_id = int(reward['reward_value'])
            role = ctx.guild.get_role(role_id)
            
            if role:
                try:
                    # Add role to user
                    await ctx.author.add_roles(role, reason=f"상자 보상: {box['name']}")
                    
                    # Record the role purchase
                    await self.gambling_model.record_gambling(
                        user_id=ctx.author.id,
                        guild_id=ctx.guild.id,
                        box_type_id=box['id'],
                        reward_id=reward['id'],
                        points_spent=box['price'],
                        role_id=role_id
                    )
                    
                    result_description = f"🎉 축하합니다! **{role.name}** 역할을 획득했습니다!"
                    
                except discord.Forbidden:
                    # Refund points if role assignment fails
                    await self.point_model.add_points(
                        user_id=ctx.author.id,
                        username=str(ctx.author),
                        amount=box['price'],
                        reason=f"상자 보상 실패 환불: {box['name']}"
                    )
                    
                    await ctx.send("❌ 역할을 부여할 권한이 없습니다. 포인트가 환불되었습니다.")
                    return
                    
            else:
                # Fallback to points if role doesn't exist
                points_won = box['price'] * 2  # Double the points as compensation
                
                await self.point_model.add_points(
                    user_id=ctx.author.id,
                    username=str(ctx.author),
                    amount=points_won,
                    reason=f"상자 보상 (역할 없음): {box['name']}"
                )
                
                result_description = f"🎉 역할을 찾을 수 없어 대신 **{points_won:,} 포인트**를 획득했습니다!"
                
        elif reward['reward_type'] == 'ITEM':
            item_name = reward['reward_value']
            
            # Record the item reward
            await self.gambling_model.record_gambling(
                user_id=ctx.author.id,
                guild_id=ctx.guild.id,
                box_type_id=box['id'],
                reward_id=reward['id'],
                points_spent=box['price'],
                item_name=item_name
            )
            
            result_description = f"🎉 축하합니다! **{item_name}** 아이템을 획득했습니다!"
            
        else:
            # Unknown reward type, give points instead
            points_won = box['price']
            
            await self.point_model.add_points(
                user_id=ctx.author.id,
                username=str(ctx.author),
                amount=points_won,
                reason=f"상자 보상 (알 수 없는 유형): {box['name']}"
            )
            
            result_description = f"🎉 **{points_won:,} 포인트**를 획득했습니다!"
            
        # Record the gambling transaction if not already recorded
        if reward['reward_type'] == 'POINTS':
            await self.gambling_model.record_gambling(
                user_id=ctx.author.id,
                guild_id=ctx.guild.id,
                box_type_id=box['id'],
                reward_id=reward['id'],
                points_spent=box['price'],
                points_won=points_won
            )
            
        # Send result message
        embed = discord.Embed(
            title=f"🎁 {box['name']} 상자 결과",
            description=result_description,
            color=discord.Color.gold()
        )
        
        if reward['description']:
            embed.add_field(name="보상 설명", value=reward['description'], inline=False)
            
        embed.set_footer(text=f"소모한 포인트: {box['price']:,}")
        embed.set_thumbnail(url=ctx.author.avatar.url if ctx.author.avatar else None)
        
        await ctx.send(embed=embed)
        
        # Log the gambling
        if hasattr(self.bot, 'log_channel') and self.bot.log_channel:
            log_embed = discord.Embed(
                title="🎲 상자 구매",
                description=f"{ctx.author.mention}님이 '{box['name']}' 상자를 구매했습니다.",
                color=discord.Color.purple(),
                timestamp=datetime.now()
            )
            log_embed.add_field(name="소모 포인트", value=f"{box['price']:,}", inline=True)
            
            if points_won > 0:
                log_embed.add_field(name="획득 포인트", value=f"{points_won:,}", inline=True)
            elif role_id:
                role = ctx.guild.get_role(role_id)
                log_embed.add_field(name="획득 역할", value=role.name if role else f"ID: {role_id}", inline=True)
            elif item_name:
                log_embed.add_field(name="획득 아이템", value=item_name, inline=True)
                
            await self.bot.log_channel.send(embed=embed)
            
    @lootbox.command(name="기록", aliases=["history"])
    @error_handler
    async def gambling_history(self, ctx, limit: int = 5):
        """
        상자 구매 기록을 확인합니다.
        
        Args:
            limit (int, optional): 표시할 기록 수 (기본값: 5)
        """
        if limit < 1 or limit > 20:
            limit = 5
            
        history = await self.gambling_model.get_user_gambling_history(ctx.author.id, limit)
        
        if not history:
            embed = discord.Embed(
                title="📜 상자 구매 기록",
                description="상자 구매 기록이 없습니다.",
                color=discord.Color.orange()
            )
            await ctx.send(embed=embed)
            return
            
        embed = discord.Embed(
            title="📜 상자 구매 기록",
            description=f"{ctx.author.mention}님의 최근 {len(history)}개 상자 구매 기록입니다.",
            color=discord.Color.blue()
        )
        
        for entry in history:
            # Determine what was won
            if entry['points_won'] > 0:
                reward = f"{entry['points_won']:,} 포인트"
            elif entry['role_id']:
                role = ctx.guild.get_role(entry['role_id'])
                reward = f"역할: {role.name if role else f'ID: {entry['role_id']}'}"
            elif entry['item_name']:
                reward = f"아이템: {entry['item_name']}"
            else:
                reward = "알 수 없음"
                
            embed.add_field(
                name=f"{entry['box_name']} ({entry['gambled_at'].strftime('%Y-%m-%d %H:%M')})",
                value=f"소모: {entry['points_spent']:,} 포인트\n획득: {reward}",
                inline=False
            )
            
        await ctx.send(embed=embed)
        
    @lootbox.group(name="관리", aliases=["admin"], invoke_without_command=True)
    @require_permission(PermissionLevel.ADMIN)
    @error_handler
    async def lootbox_admin(self, ctx):
        """상자 관리 명령어 그룹"""
        embed = discord.Embed(
            title="🛠️ 상자 관리",
            description="상자 관리 명령어 목록입니다.",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="상자 관리",
            value=(
                f"`{ctx.prefix}상자 관리 추가 [이름] [가격] [설명]` - 새 상자를 추가합니다.\n"
                f"`{ctx.prefix}상자 관리 제거 [이름]` - 상자를 제거합니다."
            ),
            inline=False
        )
        
        embed.add_field(
            name="보상 관리",
            value=(
                f"`{ctx.prefix}상자 관리 보상추가 [상자이름] [유형] [값] [확률] [설명]` - 상자에 보상을 추가합니다.\n"
                f"유형: points(포인트), role(역할), item(아이템)"
            ),
            inline=False
        )
        
        await ctx.send(embed=embed)
        
    @lootbox_admin.command(name="추가", aliases=["add"])
    @require_permission(PermissionLevel.ADMIN)
    @error_handler
    async def add_box(self, ctx, name: str, price: int, *, description: str = None):
        """
        새 상자를 추가합니다.
        
        Args:
            name (str): 상자 이름
            price (int): 상자 가격
            description (str, optional): 상자 설명
        """
        # Validate price
        if not InputValidator.validate_amount(price, 1, 1000000):
            await ctx.send("❌ 가격은 1에서 1,000,000 사이여야 합니다.")
            return
            
        # Add the box to the database
        box_id = await self.gambling_model.add_box_type(
            guild_id=ctx.guild.id,
            name=name,
            price=price,
            description=description
        )
        
        if box_id:
            embed = discord.Embed(
                title="✅ 상자 추가 완료",
                description=f"'{name}' 상자가 추가되었습니다.",
                color=discord.Color.green()
            )
            embed.add_field(name="가격", value=f"{price:,} 포인트", inline=True)
            if description:
                embed.add_field(name="설명", value=description, inline=False)
                
            embed.set_footer(text=f"이제 '{ctx.prefix}상자 관리 보상추가' 명령어로 보상을 추가하세요.")
        else:
            embed = discord.Embed(
                title="❌ 오류 발생",
                description="상자를 추가하는 데 실패했습니다.",
                color=discord.Color.red()
            )
            
        await ctx.send(embed=embed)
        
    @lootbox_admin.command(name="제거", aliases=["remove"])
    @require_permission(PermissionLevel.ADMIN)
    @error_handler
    async def remove_box(self, ctx, *, name: str):
        """
        상자를 제거합니다.
        
        Args:
            name (str): 제거할 상자 이름
        """
        # Get the box type
        box = await self.gambling_model.get_box_type_by_name(ctx.guild.id, name)
        
        if not box:
            await ctx.send(f"❌ '{name}' 상자를 찾을 수 없습니다.")
            return
            
        # Remove the box
        success = await self.gambling_model.remove_box_type(box['id'])
        
        if success:
            embed = discord.Embed(
                title="✅ 상자 제거 완료",
                description=f"'{name}' 상자가 제거되었습니다.",
                color=discord.Color.green()
            )
        else:
            embed = discord.Embed(
                title="❌ 오류 발생",
                description="상자를 제거하는 데 실패했습니다.",
                color=discord.Color.red()
            )
            
        await ctx.send(embed=embed)
        
    @lootbox_admin.command(name="보상추가", aliases=["addreward"])
    @require_permission(PermissionLevel.ADMIN)
    @error_handler
    async def add_reward(self, ctx, box_name: str, reward_type: str, reward_value: str, 
                        probability: float, *, description: str = None):
        """
        상자에 보상을 추가합니다.
        
        Args:
            box_name (str): 상자 이름
            reward_type (str): 보상 유형 (points, role, item)
            reward_value (str): 보상 값 (포인트 수, 역할 ID 또는 이름, 아이템 이름)
            probability (float): 확률 (0-1 사이의 값)
            description (str, optional): 보상 설명
        """
        # Get the box type
        box = await self.gambling_model.get_box_type_by_name(ctx.guild.id, box_name)
        
        if not box:
            await ctx.send(f"❌ '{box_name}' 상자를 찾을 수 없습니다.")
            return
            
        # Validate reward type
        reward_type = reward_type.upper()
        if reward_type not in ['POINTS', 'ROLE', 'ITEM']:
            await ctx.send("❌ 보상 유형은 'points', 'role', 'item' 중 하나여야 합니다.")
            return
            
        # Validate probability
        try:
            probability = float(probability)
            if probability <= 0 or probability > 1:
                await ctx.send("❌ 확률은 0보다 크고 1 이하여야 합니다.")
                return
        except ValueError:
            await ctx.send("❌ 확률은 숫자여야 합니다.")
            return
            
        # Process reward value based on type
        reward_amount = 0
        
        if reward_type == 'POINTS':
            try:
                reward_amount = int(reward_value)
                if reward_amount <= 0:
                    await ctx.send("❌ 포인트 보상은 양수여야 합니다.")
                    return
            except ValueError:
                await ctx.send("❌ 포인트 보상은 숫자여야 합니다.")
                return
                
        elif reward_type == 'ROLE':
            # Check if reward_value is a role ID or name
            try:
                role_id = int(reward_value)
                role = ctx.guild.get_role(role_id)
            except ValueError:
                # Try to find role by name
                role = discord.utils.find(lambda r: r.name.lower() == reward_value.lower(), ctx.guild.roles)
                
            if not role:
                await ctx.send(f"❌ '{reward_value}' 역할을 찾을 수 없습니다.")
                return
                
            reward_value = str(role.id)
            
        # Add the reward
        reward_id = await self.gambling_model.add_reward(
            box_type_id=box['id'],
            reward_type=reward_type,
            reward_value=reward_value,
            reward_amount=reward_amount,
            probability=probability,
            description=description
        )
        
        if reward_id:
            embed = discord.Embed(
                title="✅ 보상 추가 완료",
                description=f"'{box_name}' 상자에 보상이 추가되었습니다.",
                color=discord.Color.green()
            )
            
            if reward_type == 'POINTS':
                embed.add_field(name="보상 유형", value="포인트", inline=True)
                embed.add_field(name="보상 값", value=f"{reward_amount:,} 포인트", inline=True)
            elif reward_type == 'ROLE':
                embed.add_field(name="보상 유형", value="역할", inline=True)
                embed.add_field(name="보상 값", value=role.mention if role else reward_value, inline=True)
            else:  # ITEM
                embed.add_field(name="보상 유형", value="아이템", inline=True)
                embed.add_field(name="보상 값", value=reward_value, inline=True)
                
            embed.add_field(name="확률", value=f"{probability:.2%}", inline=True)
            
            if description:
                embed.add_field(name="설명", value=description, inline=False)
        else:
            embed = discord.Embed(
                title="❌ 오류 발생",
                description="보상을 추가하는 데 실패했습니다.",
                color=discord.Color.red()
            )
            
        await ctx.send(embed=embed)

async def setup(bot):
    """Add the cog to the bot."""
    await bot.add_cog(Gambling(bot))