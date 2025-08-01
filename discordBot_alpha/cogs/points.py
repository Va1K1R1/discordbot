import discord
from discord import app_commands
from discord.ext import commands, tasks
import asyncio
import logging
from datetime import datetime, timedelta
from utils.decorators import error_handler
from utils.helpers import MessageFormatter, InputValidator
from utils.permissions import PermissionLevel, PermissionChecker

class Points(commands.Cog):
    """
    Points system cog for managing user points, experience, and levels.
    """
    
    # Point settings for different activities
    # 🎯 포인트 시스템 설정 변수들 (쉽게 변경 가능)
    POINT_SETTINGS = {
        'message': 5,
        'voice_per_minute': 2,
        'daily_bonus': 100,
        'level_up_bonus': 50
    }
    
    # Role multipliers for point earning
    # 🏷️ 역할별 포인트 배율 설정 (역할 ID: 배율)
    ROLE_MULTIPLIERS = {
        'VIP': 2.0,
        'Premium': 1.5,
        'Supporter': 1.2
    }
    
    # Rank medals for leaderboard
    # 🏆 순위 메달 설정
    RANK_MEDALS = {
        1: "🥇",
        2: "🥈", 
        3: "🥉"
        # 4등부터는 숫자로 표시
    }
    
    # Color scheme
    # 🎨 임베드 색상 설정
    COLORS = {
        'success': discord.Color.green(),
        'error': discord.Color.red(),
        'warning': discord.Color.orange(),
        'info': discord.Color.blue(),
        'points': discord.Color.gold()
    }

    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger(__name__)
        self.point_model = bot.point_model
        self.formatter = MessageFormatter()
        
        # Cooldown tracking for message points
        self.message_cooldowns = {}
        
        # Voice channel tracking
        self.voice_users = {}
        
        # Start voice point task
        # 음성채팅 포인트 지급 태스크 시작
        self.voice_point_task.start()

    def cog_unload(self):
        """Clean up when cog is unloaded"""
        self.voice_point_task.cancel()

    async def get_user_role_multiplier(self, user):
        """Get point multiplier based on user roles"""
        multiplier = 1.0
        
        # 멤버의 모든 역할을 확인하여 가장 높은 배율 찾기
        for role in user.roles:
            role_name = role.name
            if role_name in self.ROLE_MULTIPLIERS:
                role_multiplier = self.ROLE_MULTIPLIERS[role_name]
                if role_multiplier > multiplier:
                    multiplier = role_multiplier
        
        return multiplier

    def get_level_exp_requirement(self, level):
        """Calculate experience required for a specific level"""
        if level <= 1:
            
            return 0
        # Exponential growth: level^2 * 100
        return (level ** 2) * 100

    def get_rank_medal(self, rank):
        """Get medal emoji for rank"""
        return self.RANK_MEDALS.get(rank, f"#{rank}")

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        """Track voice channel activity"""
        if member.bot:
            return
            
        user_id = member.id
        current_time = datetime.now()
        
        # User joined a voice channel
        # 음성채팅에 입장
        if before.channel is None and after.channel is not None:
            self.voice_users[user_id] = {
                'join_time': current_time,
                'channel_id': after.channel.id
            }
            self.logger.info(f"User {member} joined voice channel {after.channel.name}")
            
        # User left a voice channel
        # 음성채팅에서 퇴장
        elif before.channel is not None and after.channel is None:
            if user_id in self.voice_users:
                voice_data = self.voice_users.pop(user_id)
                time_spent = current_time - voice_data['join_time']
                minutes_spent = int(time_spent.total_seconds() / 60)
                
                if minutes_spent > 0:
                    await self.award_voice_points(member, minutes_spent)
                    
                self.logger.info(f"User {member} left voice channel after {minutes_spent} minutes")
                
        # User moved between voice channels
        # 음성채팅 채널 변경
        elif before.channel != after.channel and after.channel is not None:
            if user_id in self.voice_users:
                self.voice_users[user_id]['channel_id'] = after.channel.id
                self.logger.info(f"User {member} moved to voice channel {after.channel.name}")

    @tasks.loop(minutes=1)
    async def voice_point_task(self):
        """Award points to users in voice channels every minute"""
        current_time = datetime.now()
        
        for user_id, voice_data in list(self.voice_users.items()):
            try:
                user = self.bot.get_user(user_id)
                if user and not user.bot:
                    # Check if user is still in voice channel
                    guild = None
                    for g in self.bot.guilds:
                        member = g.get_member(user_id)
                        if member and member.voice and member.voice.channel:
                            guild = g
                            break
                    
                    if guild:
                        await self.award_voice_points(member, 1)
                    else:
                        # User is no longer in voice, remove from tracking
                        
                        # 시간 업데이트 (중복 지급 방지)
                        self.voice_users.pop(user_id, None)
                        
            except Exception as e:
                self.logger.error(f"Error awarding voice points to user {user_id}: {e}")

    @voice_point_task.before_loop
    async def before_voice_point_task(self):
        """Wait until bot is ready before starting voice point task"""
        await self.bot.wait_until_ready()

    async def award_voice_points(self, member, minutes):
        """Award points for voice channel activity"""
        if not self.point_model:
            return
            
        try:
            # Calculate points with role multiplier
            base_points = self.POINT_SETTINGS['voice_per_minute'] * minutes
            # 역할별 배율 가져오기
            multiplier = await self.get_user_role_multiplier(member)
            points_to_award = int(base_points * multiplier)
            
            if points_to_award > 0:
                await self.point_model.add_points(
                    user_id=member.id,
                    username=str(member),
                    amount=points_to_award,
                    reason=f"음성 채널 활동 ({minutes}분)"
                )
                
                # Award experience (2x points)
                exp_to_award = points_to_award * 2
            # 경험치 업데이트 및 레벨업 확인
                level_up_info = await self.point_model.update_experience(
                    user_id=member.id,
                    username=str(member),
                    exp_amount=exp_to_award
                )
                
                # Send level up notification if applicable
                if level_up_info and hasattr(member, 'guild'):
                    # Find a suitable channel to send level up message
                    channel = None
                    for ch in member.guild.text_channels:
                        if ch.permissions_for(member.guild.me).send_messages:
                            channel = ch
                        # 시스템 채널이나 일반 채널에 알림 (옵션)
                        # 너무 많은 알림을 방지하기 위해 주석 처리
                        # system_channel = guild.system_channel
                        # if system_channel:
                        #     embed = discord.Embed(
                        #         title="🎤 음성채팅 포인트",
                        #         description=f"{member.mention}님이 {minutes}분간 음성채팅 참여로 {total_points:,} 포인트를 획득했습니다!",
                        #         color=self.COLORS['SUCCESS']
                        #     )
                        #     if multiplier_info['voice_multiplier'] > 1.0:
                        #         embed.add_field(
                        #             name="특별 보너스",
                        #             value=f"{multiplier_info['role_emoji']} {multiplier_info['role_name']} 역할 {multiplier_info['voice_multiplier']}x 배율 적용!",
                        #             inline=False
                        #         )
                        #     await system_channel.send(embed=embed)
                            break
                    
            # 레벨업 처리
                    if channel:
                        embed = discord.Embed(
                            title="🎉 레벨 업!",
                            description=f"{member.mention}님이 레벨 {level_up_info['old_level']}에서 레벨 {level_up_info['new_level']}로 올라갔습니다! (음성 채널 활동으로)",
                            color=discord.Color.gold()
                        )
                        embed.set_thumbnail(url=member.avatar.url if member.avatar else None)
                        await channel.send(embed=embed)
                
                self.logger.info(f"Awarded {points_to_award} points to {member} for {minutes} minutes of voice activity")
                
        except Exception as e:
            self.logger.error(f"Error awarding voice points to {member}: {e}")

    @commands.Cog.listener()
    async def on_message(self, message):
        """Award points for messages (backup system)"""
        if message.author.bot or not self.point_model:
            return
            
        # Check cooldown
        user_id = message.author.id
        current_time = datetime.now()
        
        # Check cooldown
        if user_id in self.message_cooldowns:
            time_diff = current_time - self.message_cooldowns[user_id]
            if time_diff.total_seconds() < 60:  # 1 minute cooldown
                return
        
        # Update cooldown
        self.message_cooldowns[user_id] = current_time
        
        try:
            # Calculate points with role multiplier
            base_points = self.POINT_SETTINGS['message']
            multiplier = await self.get_user_role_multiplier(message.author)
            points_to_award = int(base_points * multiplier)
            
            await self.point_model.add_points(
                user_id=user_id,
                username=str(message.author),
                amount=points_to_award,
                reason="메시지 작성"
            )
            
            # Award experience
            exp_to_award = points_to_award * 2
            # Update experience and check for level up
            level_up_info = await self.point_model.update_experience(
                user_id=user_id,
                username=str(message.author),
                exp_amount=exp_to_award
            )
            
            # Send level up message if applicable
            if level_up_info:
                embed = discord.Embed(
                    title="🎉 레벨 업!",
                    description=f"{message.author.mention}님이 레벨 {level_up_info['old_level']}에서 레벨 {level_up_info['new_level']}로 올라갔습니다!",
                    color=discord.Color.gold()
                )
                embed.set_thumbnail(url=message.author.avatar.url if message.author.avatar else None)
                await message.channel.send(embed=embed)
                
        except Exception as e:
            self.logger.error(f"Error awarding message points to {message.author}: {e}")

    @app_commands.command(name="포인트", description="자신 또는 다른 사용자의 포인트를 확인합니다")
    @app_commands.describe(user="포인트를 확인할 사용자 (선택사항)")
    async def check_points_slash(self, interaction: discord.Interaction, user: discord.Member = None):
        """슬래시 명령어로 포인트 확인"""
        target_user = user or interaction.user
        
        try:
            user_data = await self.point_model.get_user_points(target_user.id)
            
            if not user_data:
                embed = discord.Embed(
                    title="📊 포인트 정보",
                    description=f"{target_user.display_name}님의 포인트 기록이 없습니다.",
                    color=self.COLORS['info']
                )
                await interaction.response.send_message(embed=embed)
                return
            
            # Calculate level progress
            current_level = user_data.get('level', 1)
            current_exp = user_data.get('experience', 0)
            exp_for_current = self.get_level_exp_requirement(current_level)
            exp_for_next = self.get_level_exp_requirement(current_level + 1)
            exp_progress = current_exp - exp_for_current
            exp_needed = exp_for_next - exp_for_current
            
            # Create progress bar
            progress_bar = self.create_progress_bar(exp_progress, exp_needed)
            
            embed = discord.Embed(
                title=f"📊 {target_user.display_name}님의 포인트 정보",
                color=self.COLORS['points']
            )
            
            embed.add_field(
                name="💰 포인트",
                value=f"{user_data.get('points', 0):,}",
                inline=True
            )
            embed.add_field(
                name="⭐ 레벨",
                value=f"{current_level}",
                inline=True
            )
            embed.add_field(
                name="🎯 경험치",
                value=f"{current_exp:,}",
                inline=True
            )
            embed.add_field(
                name="📈 다음 레벨까지",
                value=f"{progress_bar}\n{exp_progress:,} / {exp_needed:,} EXP",
                inline=False
            )
            
            if target_user.avatar:
                embed.set_thumbnail(url=target_user.avatar.url)
                
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            await interaction.response.send_message(
                f"❌ 포인트 정보를 가져오는 중 오류가 발생했습니다: {e}",
                ephemeral=True
            )

    def create_progress_bar(self, current, maximum, length=10):
        """Create a visual progress bar"""
        if maximum == 0:
            filled = 0
        else:
            filled = int((current / maximum) * length)
        
        bar = "█" * filled + "░" * (length - filled)
        percentage = (current / maximum * 100) if maximum > 0 else 0
        return f"`{bar}` {percentage:.1f}%"

    @commands.command(name="포인트", aliases=["points", "pt"])
    @error_handler
    async def check_points(self, ctx, user: discord.Member = None):
        """
        Check points for yourself or another user.
        
        Args:
            user: User to check points for (optional)
        """
        if user is None:
            user = ctx.author
            
        try:
        # Get user points
            user_data = await self.point_model.get_user_points(user.id)
            
            if not user_data:
                embed = self.formatter.create_embed(
                    title="📊 포인트 정보",
                    description=f"{user.display_name}님의 포인트 기록이 없습니다.",
                    color=self.COLORS['info']
                )
                await ctx.send(embed=embed)
                return
            
            # Get rank
            rank = await self.point_model.get_user_rank(user.id)
            
            # Calculate level progress
            current_level = user_data.get('level', 1)
            current_exp = user_data.get('experience', 0)
            exp_for_current = self.get_level_exp_requirement(current_level)
            exp_for_next = self.get_level_exp_requirement(current_level + 1)
            exp_progress = current_exp - exp_for_current
            exp_needed = exp_for_next - exp_for_current
            
            # Create progress bar
            progress_bar = self.create_progress_bar(exp_progress, exp_needed)
            
            embed = self.formatter.create_embed(
                title=f"📊 {user.display_name}님의 포인트 정보",
                color=self.COLORS['points']
            )
            
            embed.add_field(
                name="💰 포인트",
                value=f"{user_data.get('points', 0):,}",
                inline=True
            )
            embed.add_field(
                name="🏆 순위",
                value=f"#{rank}" if rank else "순위 없음",
                inline=True
            )
            embed.add_field(
                name="⭐ 레벨",
                value=f"{current_level}",
                inline=True
            )
            embed.add_field(
                name="🎯 경험치",
                value=f"{current_exp:,}",
                inline=True
            )
            embed.add_field(
                name="📅 마지막 일일보상",
                value=user_data.get('last_daily', 'N/A'),
                inline=True
            )
            embed.add_field(
                name="🔢 총 메시지",
                value=f"{user_data.get('total_messages', 0):,}",
                inline=True
            )
            embed.add_field(
                name="📈 다음 레벨까지",
                value=f"{progress_bar}\n{exp_progress:,} / {exp_needed:,} EXP",
                inline=False
            )
            
            if user.avatar:
        # Set thumbnail
                embed.set_thumbnail(url=user.avatar.url)
                
            await ctx.send(embed=embed)
            
        except Exception as e:
            embed = self.formatter.create_error_embed(
                title="오류 발생",
                description=f"포인트 정보를 가져오는 중 오류가 발생했습니다: {e}"
            )
            await ctx.send(embed=embed)

    @app_commands.command(name="포인트추가", description="사용자에게 포인트를 추가합니다 (관리자 전용)")
    @app_commands.describe(
        user="포인트를 추가할 사용자",
        amount="추가할 포인트 양",
        reason="추가 이유 (선택사항)"
    )
    async def add_points_slash(self, interaction: discord.Interaction, user: discord.Member, amount: int, reason: str = "관리자 지급"):
        """슬래시 명령어로 포인트 추가"""
        # 권한 체크
        checker = PermissionChecker()
        permission_level = checker.get_permission_level(interaction.user, interaction.guild)
        
        if permission_level.value < PermissionLevel.MODERATOR.value:
            await interaction.response.send_message("❌ 이 명령어를 사용할 권한이 없습니다.", ephemeral=True)
            return
            
        if amount <= 0:
            await interaction.response.send_message("❌ 포인트는 0보다 커야 합니다.", ephemeral=True)
            return
            
        try:
            await self.point_model.add_points(
                user_id=user.id,
                username=str(user),
                amount=amount,
                reason=reason
            )
            
            embed = discord.Embed(
                title="✅ 포인트 추가 완료",
                description=f"{user.mention}님에게 {amount:,} 포인트를 추가했습니다.",
                color=discord.Color.green()
            )
            embed.add_field(name="사유", value=reason, inline=False)
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            await interaction.response.send_message(
                f"❌ 포인트 추가 중 오류가 발생했습니다: {e}",
                ephemeral=True
            )

    @commands.command(name="포인트추가", aliases=["add_points", "give_points"])
    @error_handler
    async def add_points(self, ctx, user: discord.Member, amount: int, *, reason: str = "관리자 지급"):
        """
        Add points to a user (Admin only).
        
        Args:
            user: User to add points to
            amount: Amount of points to add
            reason: Reason for adding points
        """
        # Check permissions
        checker = PermissionChecker()
        permission_level = checker.get_permission_level(ctx.author, ctx.guild)
        
        if permission_level.value < PermissionLevel.MODERATOR.value:
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
            
        if amount <= 0:
            embed = self.formatter.create_error_embed(
                title="잘못된 수량",
                description="포인트는 0보다 커야 합니다."
            )
            await ctx.send(embed=embed)
            return
            
        if amount > 1000000:  # Reasonable limit
            embed = self.formatter.create_error_embed(
                title="수량 제한",
                description="한 번에 1,000,000 포인트까지만 추가할 수 있습니다."
            )
            await ctx.send(embed=embed)
            return
            
        try:
        # Add points
            await self.point_model.add_points(
                user_id=user.id,
                username=str(user),
                amount=amount,
                reason=reason
            )
            
            embed = self.formatter.create_success_embed(
                title="포인트 추가 완료",
                description=f"{user.mention}님에게 {amount:,} 포인트를 추가했습니다."
            )
            embed.add_field(name="실행자", value=ctx.author.mention, inline=True)
            embed.add_field(name="대상", value=user.mention, inline=True)
            embed.add_field(name="수량", value=f"{amount:,}", inline=True)
            embed.add_field(name="사유", value=reason, inline=False)
            
            await ctx.send(embed=embed)
            
            # Log the action
            self.logger.info(f"{ctx.author} added {amount} points to {user} for reason: {reason}")
            
        except Exception as e:
            embed = self.formatter.create_error_embed(
                title="오류 발생",
                description=f"포인트 추가 중 오류가 발생했습니다: {e}"
            )
            await ctx.send(embed=embed)

    @app_commands.command(name="포인트제거", description="사용자에게서 포인트를 제거합니다 (관리자 전용)")
    @app_commands.describe(
        user="포인트를 제거할 사용자",
        amount="제거할 포인트 양",
        reason="제거 이유 (선택사항)"
    )
    async def remove_points_slash(self, interaction: discord.Interaction, user: discord.Member, amount: int, reason: str = "관리자 차감"):
        """슬래시 명령어로 포인트 제거"""
        # 권한 체크
        checker = PermissionChecker()
        permission_level = checker.get_permission_level(interaction.user, interaction.guild)
        
        if permission_level.value < PermissionLevel.MODERATOR.value:
            await interaction.response.send_message("❌ 이 명령어를 사용할 권한이 없습니다.", ephemeral=True)
            return
            
        if amount <= 0:
            await interaction.response.send_message("❌ 포인트는 0보다 커야 합니다.", ephemeral=True)
            return
            
        try:
            success = await self.point_model.deduct_points(
                user_id=user.id,
                username=str(user),
                amount=amount,
                reason=reason
            )
            
            if success:
                embed = discord.Embed(
                    title="✅ 포인트 제거 완료",
                    description=f"{user.mention}님에게서 {amount:,} 포인트를 제거했습니다.",
                    color=discord.Color.green()
                )
                embed.add_field(name="사유", value=reason, inline=False)
            else:
                embed = discord.Embed(
                    title="❌ 포인트 부족",
                    description=f"{user.mention}님이 보유한 포인트가 부족합니다.",
                    color=discord.Color.red()
                )
                
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            await interaction.response.send_message(
                f"❌ 포인트 제거 중 오류가 발생했습니다: {e}",
                ephemeral=True
            )

    @commands.command(name="포인트제거", aliases=["remove_points", "deduct_points"])
    @error_handler
    async def remove_points(self, ctx, user: discord.Member, amount: int, *, reason: str = "관리자 차감"):
        """
        Remove points from a user (Admin only).
        
        Args:
            user: User to remove points from
            amount: Amount of points to remove
            reason: Reason for removing points
        """
        # Check permissions
        checker = PermissionChecker()
        permission_level = checker.get_permission_level(ctx.author, ctx.guild)
        
        if permission_level.value < PermissionLevel.MODERATOR.value:
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
            
        if amount <= 0:
            embed = self.formatter.create_error_embed(
                title="잘못된 수량",
                description="포인트는 0보다 커야 합니다."
            )
            await ctx.send(embed=embed)
            return
            
        try:
            # Check current points
            user_data = await self.point_model.get_user_points(user.id)
            current_points = user_data.get('points', 0) if user_data else 0
            
            if current_points < amount:
                embed = self.formatter.create_warning_embed(
                    title="포인트 부족",
                    description=f"{user.mention}님의 현재 포인트: {current_points:,}\n제거하려는 포인트: {amount:,}"
                )
                await ctx.send(embed=embed)
                return
            
            success = await self.point_model.deduct_points(
                user_id=user.id,
                username=str(user),
                amount=amount,
                reason=reason
            )
            
            if success:
                embed = self.formatter.create_success_embed(
                    title="포인트 제거 완료",
                    description=f"{user.mention}님에게서 {amount:,} 포인트를 제거했습니다."
                )
                embed.add_field(name="실행자", value=ctx.author.mention, inline=True)
                embed.add_field(name="대상", value=user.mention, inline=True)
                embed.add_field(name="수량", value=f"{amount:,}", inline=True)
                embed.add_field(name="사유", value=reason, inline=False)
                embed.add_field(name="남은 포인트", value=f"{current_points - amount:,}", inline=True)
            else:
                embed = self.formatter.create_error_embed(
                    title="포인트 제거 실패",
                    description="포인트 제거에 실패했습니다."
                )
            
            await ctx.send(embed=embed)
            
            # Log the action
            self.logger.info(f"{ctx.author} removed {amount} points from {user} for reason: {reason}")
            
        except Exception as e:
            embed = self.formatter.create_error_embed(
                title="오류 발생",
                description=f"포인트 제거 중 오류가 발생했습니다: {e}"
            )
            await ctx.send(embed=embed)

    @app_commands.command(name="랭킹", description="포인트 랭킹을 표시합니다")
    @app_commands.describe(limit="표시할 사용자 수 (기본: 10)")
    async def leaderboard_slash(self, interaction: discord.Interaction, limit: int = 10):
        """슬래시 명령어로 랭킹 표시"""
        if limit < 1 or limit > 50:
            await interaction.response.send_message("❌ 랭킹은 1-50명까지만 표시할 수 있습니다.", ephemeral=True)
            return
            
        try:
            leaderboard = await self.point_model.get_leaderboard(limit)
            
            if not leaderboard:
                embed = discord.Embed(
                    title="🏆 포인트 랭킹",
                    description="랭킹 데이터가 없습니다.",
                    color=self.COLORS['info']
                )
                await interaction.response.send_message(embed=embed)
                return
            
            embed = discord.Embed(
                title="🏆 포인트 랭킹",
                color=self.COLORS['points']
            )
            
            ranking_text = []
            for i, user_data in enumerate(leaderboard, 1):
                user_id = user_data.get('user_id')
                username = user_data.get('username', 'Unknown')
                points = user_data.get('points', 0)
                level = user_data.get('level', 1)
                
                medal = self.get_rank_medal(i)
                ranking_text.append(
                    f"{medal} **{username}**\n"
                    f"     └ 포인트: {points:,} | 레벨: {level}"
                )
            
            embed.add_field(
                name=f"Top {len(leaderboard)}",
                value="\n".join(ranking_text),
                inline=False
            )
            
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            await interaction.response.send_message(
                f"❌ 랭킹을 가져오는 중 오류가 발생했습니다: {e}",
                ephemeral=True
            )

    @commands.command(name="랭킹", aliases=["leaderboard", "top", "순위"])
    @error_handler
    async def leaderboard(self, ctx, limit: int = 10):
        """
        Show points leaderboard.
        
        Args:
            limit: Number of users to show (default: 10, max: 50)
        """
        if limit < 1:
            limit = 10
        elif limit > 50:
            limit = 50
            
        try:
        # Get leaderboard
            leaderboard = await self.point_model.get_leaderboard(limit)
            
            if not leaderboard:
                embed = self.formatter.create_embed(
                    title="🏆 포인트 랭킹",
                    description="아직 랭킹 데이터가 없습니다.",
                    color=self.COLORS['info']
                )
                await ctx.send(embed=embed)
                return
            
        # Create embed
            embed = self.formatter.create_embed(
                title="🏆 포인트 랭킹",
                color=self.COLORS['points']
            )
            
            ranking_text = []
        # Format leaderboard entries
            for i, user_data in enumerate(leaderboard, 1):
                user_id = user_data.get('user_id')
                username = user_data.get('username', 'Unknown')
                points = user_data.get('points', 0)
                level = user_data.get('level', 1)
                
                # Try to get actual user for better display
                user = self.bot.get_user(user_id)
                if user:
                    display_name = user.display_name
                else:
                    display_name = username
                
                medal = self.get_rank_medal(i)
                ranking_text.append(
                    f"{medal} **{display_name}**\n"
                    f"     └ 포인트: {points:,} | 레벨: {level}"
                )
            
            embed.add_field(
                name=f"Top {len(leaderboard)}",
                value="\n".join(ranking_text),
                inline=False
            )
            
            # Add user's rank if not in top list
            if ctx.author.id not in [user['user_id'] for user in leaderboard]:
                user_rank = await self.point_model.get_user_rank(ctx.author.id)
                if user_rank:
                    user_data = await self.point_model.get_user_points(ctx.author.id)
                    if user_data:
                        embed.add_field(
                            name="당신의 순위",
                            value=f"#{user_rank} | 포인트: {user_data.get('points', 0):,}",
                            inline=False
                        )
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            embed = self.formatter.create_error_embed(
                title="오류 발생",
                description=f"랭킹을 가져오는 중 오류가 발생했습니다: {e}"
            )
            await ctx.send(embed=embed)

    @app_commands.command(name="일일보상", description="일일 보상을 받습니다")
    async def daily_bonus_slash(self, interaction: discord.Interaction):
        """슬래시 명령어로 일일 보상"""
        try:
            can_claim, time_until_next = await self.point_model.can_claim_daily_bonus(interaction.user.id)
            
            if not can_claim:
                embed = discord.Embed(
                    title="⏰ 일일 보상",
                    description=f"다음 일일 보상까지: {time_until_next}",
                    color=discord.Color.orange()
                )
                await interaction.response.send_message(embed=embed)
                return
            
            # Calculate bonus with multiplier
            base_bonus = self.POINT_SETTINGS['daily_bonus']
            multiplier = await self.get_user_role_multiplier(interaction.user)
            bonus_amount = int(base_bonus * multiplier)
            
            await self.point_model.claim_daily_bonus(
                user_id=interaction.user.id,
                username=str(interaction.user),
                amount=bonus_amount
            )
            
            embed = discord.Embed(
                title="🎁 일일 보상 획득!",
                description=f"{bonus_amount:,} 포인트를 받았습니다!",
                color=discord.Color.green()
            )
            
            if multiplier > 1.0:
                embed.add_field(
                    name="보너스 적용",
                    value=f"역할 배수: {multiplier}x",
                    inline=True
                )
            
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            await interaction.response.send_message(
                f"❌ 일일 보상 처리 중 오류가 발생했습니다: {e}",
                ephemeral=True
            )

    @commands.command(name="일일보상", aliases=["daily", "데일리"])
    @error_handler
    async def daily_bonus(self, ctx):
        """
        Claim daily bonus points.
        """
        try:
            can_claim, time_until_next = await self.point_model.can_claim_daily_bonus(ctx.author.id)
            
            if not can_claim:
                embed = self.formatter.create_embed(
                    title="⏰ 일일 보상",
                    description=f"이미 오늘의 일일 보상을 받았습니다.\n다음 보상까지: {time_until_next}",
                    color=self.COLORS['warning']
                )
                await ctx.send(embed=embed)
                return
            
            # Calculate bonus with role multiplier
            base_bonus = self.POINT_SETTINGS['daily_bonus']
            multiplier = await self.get_user_role_multiplier(ctx.author)
            bonus_amount = int(base_bonus * multiplier)
            
            # Additional streak bonus (if implemented)
            streak_bonus = 0  # Can be implemented later
            total_bonus = bonus_amount + streak_bonus
            
            # Claim the bonus
            await self.point_model.claim_daily_bonus(
                user_id=ctx.author.id,
                username=str(ctx.author),
                amount=total_bonus
            )
            
            embed = self.formatter.create_success_embed(
                title="🎁 일일 보상 획득!",
                description=f"**{total_bonus:,}** 포인트를 받았습니다!"
            )
            
            embed.add_field(name="기본 보상", value=f"{base_bonus:,}", inline=True)
            
            # 특별 역할 보너스 표시
            if multiplier > 1.0:
                embed.add_field(name="역할 배수", value=f"{multiplier}x", inline=True)
                embed.add_field(name="보너스", value=f"+{bonus_amount - base_bonus:,}", inline=True)
            
            if streak_bonus > 0:
                embed.add_field(name="연속 보너스", value=f"+{streak_bonus:,}", inline=True)
            
            embed.set_thumbnail(url=ctx.author.avatar.url if ctx.author.avatar else None)
            
            await ctx.send(embed=embed)
            
            # Log the action
            self.logger.info(f"{ctx.author} claimed daily bonus of {total_bonus} points")
            
        except Exception as e:
            embed = self.formatter.create_error_embed(
                title="오류 발생",
                description=f"일일 보상 처리 중 오류가 발생했습니다: {e}"
            )
            
            await ctx.send(embed=embed)

    @commands.command(name="포인트설정", aliases=["point_settings"])
    @error_handler
    async def show_point_settings(self, ctx):
        """Show current point settings"""
        # Check permissions
        checker = PermissionChecker()
        permission_level = checker.get_permission_level(ctx.author, ctx.guild)
        
        if permission_level.value < PermissionLevel.ADMIN.value:
            embed = self.formatter.create_error_embed(
                title="권한 부족",
                description="이 명령어를 사용하려면 관리자 권한이 필요합니다."
            )
            await ctx.send(embed=embed)
            return
            
        embed = self.formatter.create_embed(
            title="⚙️ 포인트 시스템 설정",
            color=self.COLORS['info']
        )
        
        # Point settings
        settings_text = []
        for activity, points in self.POINT_SETTINGS.items():
            settings_text.append(f"**{activity}**: {points} 포인트")
        
        # 경험치 설정
        embed.add_field(
            name="💰 포인트 획득량",
            value="\n".join(settings_text),
            inline=False
        )
        
        # Role multipliers
        if self.ROLE_MULTIPLIERS:
            multiplier_text = []
            for role, multiplier in self.ROLE_MULTIPLIERS.items():
                multiplier_text.append(f"**{role}**: {multiplier}x")
            
        # 순위 설정
            embed.add_field(
                name="🎭 역할 배수",
                value="\n".join(multiplier_text),
                inline=False
            )
        
        await ctx.send(embed=embed)

    @commands.command(name="역할배수", aliases=["role_multipliers"])
    @error_handler
    async def show_role_multipliers(self, ctx):
        """Show role multipliers for points"""
        embed = self.formatter.create_embed(
            title="🎭 역할별 포인트 배수",
            color=self.COLORS['info']
        )
        
        if not self.ROLE_MULTIPLIERS:
            embed.add_field(
                name="배수 없음",
                value="현재 설정된 역할 배수가 없습니다.",
                inline=False
            )
        else:
            multiplier_text = []
            for role_name, multiplier in sorted(self.ROLE_MULTIPLIERS.items(), key=lambda x: x[1], reverse=True):
                # Try to find the role in the guild
                # 길드에서 역할 찾기
                role = discord.utils.get(ctx.guild.roles, name=role_name)
                if role:
                    role_mention = role.mention
                    member_count = len(role.members)
                    multiplier_text.append(f"{role_mention}: **{multiplier}x** ({member_count}명)")
                else:
                    multiplier_text.append(f"**{role_name}**: {multiplier}x (역할 없음)")
            
            embed.add_field(
                name="🔢 배수 설정",
                value="\n".join(multiplier_text),
                inline=False
            )
            
            # Show user's current multiplier
            user_multiplier = await self.get_user_role_multiplier(ctx.author)
            embed.add_field(
                name="👤 당신의 배수",
                value=f"{user_multiplier}x",
                inline=False
            )
        
        await ctx.send(embed=embed)

    @commands.command(name="음성상태", aliases=["voice_status"])
    @error_handler
    async def voice_status(self, ctx):
        """Show voice channel point tracking status"""
        if not self.voice_users:
            embed = self.formatter.create_embed(
                title="🎤 음성 채널 추적 상태",
                description="현재 추적 중인 사용자가 없습니다.",
                color=self.COLORS['info']
            )
            await ctx.send(embed=embed)
            return
        
        embed = self.formatter.create_embed(
            title="🎤 음성 채널 추적 상태",
            color=self.COLORS['info']
        )
        
        tracked_users = []
        current_time = datetime.now()
        
        for user_id, voice_data in self.voice_users.items():
            user = self.bot.get_user(user_id)
            if user:
                channel = self.bot.get_channel(voice_data['channel_id'])
            
                time_in_voice = current_time - voice_data['join_time']
                minutes = int(time_in_voice.total_seconds() / 60)
                
                channel_name = channel.name if channel else "알 수 없음"
                tracked_users.append(f"**{user.display_name}**: {channel_name} ({minutes}분)")
        
        if tracked_users:
            embed.add_field(
                name=f"추적 중인 사용자 ({len(tracked_users)}명)",
                value="\n".join(tracked_users[:10]),  # Limit to 10 for display
                inline=False
            )
            
            if len(tracked_users) > 10:
                embed.add_field(
                    name="더 보기",
                    value=f"... 및 {len(tracked_users) - 10}명 더",
                    inline=False
                )
        
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Points(bot))