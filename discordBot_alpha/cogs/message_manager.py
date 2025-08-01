import discord
from discord import app_commands
from discord.ext import commands, tasks
import asyncio
import logging
from datetime import datetime, timedelta
from utils.decorators import error_handler
from utils.helpers import MessageFormatter, InputValidator
from utils.permissions import PermissionLevel, PermissionChecker

class MessageManager(commands.Cog):
    """
    Message management cog for deleting, purging, and managing messages.
    """
    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger(__name__)
        self.deletion_model = bot.scheduled_deletion_model
        self.formatter = MessageFormatter()
        
        # Start scheduled deletion checker
        self.deletion_checker.start()

    def cog_unload(self):
        """Clean up when cog is unloaded"""
        self.deletion_checker.cancel()

    @tasks.loop(seconds=30)
    async def deletion_checker(self):
        """Check for scheduled deletions every 30 seconds"""
        try:
            await self.process_scheduled_deletion()
        except Exception as e:
            self.logger.error(f"Error in deletion checker: {e}")

    @deletion_checker.before_loop
    async def before_deletion_checker(self):
        """Wait until bot is ready before starting deletion checker"""
        await self.bot.wait_until_ready()

    async def process_scheduled_deletion(self):
        """Process scheduled message deletions"""
        if not self.deletion_model:
            return
            
        try:
            pending_deletions = await self.deletion_model.get_pending_deletions()
            
            for deletion in pending_deletions:
                try:
                    channel = self.bot.get_channel(deletion['channel_id'])
                    if not channel:
                        await self.deletion_model.remove_scheduled_deletion(deletion['message_id'])
                        continue
                    
                    try:
                        message = await channel.fetch_message(deletion['message_id'])
                        await message.delete()
                        
                        # Log deletion
                        self.logger.info(f"Scheduled deletion executed for message {deletion['message_id']}")
                        
                        # Send log message if log channel exists
                        if self.bot.log_channel:
                            embed = discord.Embed(
                                title="🗑️ 예약 삭제 실행",
                                description=f"메시지가 예약된 시간에 삭제되었습니다.",
                                color=discord.Color.orange(),
                                timestamp=datetime.now()
                            )
                            embed.add_field(name="채널", value=f"<#{deletion['channel_id']}>", inline=True)
                            embed.add_field(name="요청자", value=f"<@{deletion['requester_id']}>", inline=True)
                            await self.bot.log_channel.send(embed=embed)
                            
                    except discord.NotFound:
                        self.logger.info(f"Message {deletion['message_id']} already deleted")
                    
                    await self.deletion_model.remove_scheduled_deletion(deletion['message_id'])
                    
                except Exception as e:
                    self.logger.error(f"Error processing scheduled deletion: {e}")
                    
        except Exception as e:
            self.logger.error(f"Error getting pending deletions: {e}")

    @app_commands.command(name="예약삭제", description="메시지를 지정된 시간 후에 삭제합니다")
    @app_commands.describe(
        message_id="삭제할 메시지 ID",
        delay_minutes="몇 분 후에 삭제할지 (기본: 5분)"
    )
    async def schedule_deletion_slash(self, interaction: discord.Interaction, message_id: str, delay_minutes: int = 5):
        """슬래시 명령어로 예약 삭제"""
        # 권한 체크
        checker = PermissionChecker()
        permission_level = checker.get_permission_level(interaction.user, interaction.guild)
        
        if permission_level.value < PermissionLevel.MODERATOR.value:
            await interaction.response.send_message("❌ 이 명령어를 사용할 권한이 없습니다.", ephemeral=True)
            return
        
        if delay_minutes < 1 or delay_minutes > 1440:  # Max 24 hours
            await interaction.response.send_message("❌ 삭제 지연 시간은 1분에서 1440분(24시간) 사이여야 합니다.", ephemeral=True)
            return
        
        try:
            message_id_int = int(message_id)
            
            # Check if message exists
            try:
                message = await interaction.channel.fetch_message(message_id_int)
            except discord.NotFound:
                await interaction.response.send_message("❌ 해당 메시지를 찾을 수 없습니다.", ephemeral=True)
                return
            
            # Schedule deletion
            delete_at = datetime.now() + timedelta(minutes=delay_minutes)
            
            await self.deletion_model.schedule_deletion(
                message_id=message_id_int,
                channel_id=interaction.channel.id,
                requester_id=interaction.user.id,
                delete_at=delete_at
            )
            
            embed = discord.Embed(
                title="⏰ 삭제 예약 완료",
                description=f"메시지가 {delay_minutes}분 후에 삭제됩니다.",
                color=discord.Color.green()
            )
            embed.add_field(name="삭제 시간", value=delete_at.strftime("%Y-%m-%d %H:%M:%S"), inline=True)
            embed.add_field(name="메시지 ID", value=message_id, inline=True)
            
            await interaction.response.send_message(embed=embed)
            
        except ValueError:
            await interaction.response.send_message("❌ 올바른 메시지 ID를 입력해주세요.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ 예약 삭제 설정 중 오류가 발생했습니다: {e}", ephemeral=True)

    @commands.command(name="예약삭제", aliases=["schedule_delete", "delayed_delete"])
    @error_handler
    async def schedule_deletion(self, ctx, message_id: int, delay_minutes: int = 5):
        """
        Schedule a message for deletion after specified time.
        
        Args:
            message_id: ID of the message to delete
            delay_minutes: Minutes to wait before deletion (default: 5, max: 1440)
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
        
        # Validate delay time
        if delay_minutes < 1:
            embed = self.formatter.create_error_embed(
                title="잘못된 시간",
                description="삭제 지연 시간은 최소 1분이어야 합니다."
            )
            await ctx.send(embed=embed)
            return
            
        if delay_minutes > 1440:  # 24 hours max
            embed = self.formatter.create_error_embed(
                title="시간 제한 초과",
                description="삭제 지연 시간은 최대 1440분(24시간)입니다."
            )
            await ctx.send(embed=embed)
            return
        
        try:
            # Check if message exists
            try:
                message = await ctx.channel.fetch_message(message_id)
            except discord.NotFound:
                embed = self.formatter.create_error_embed(
                    title="메시지 없음",
                    description="해당 ID의 메시지를 찾을 수 없습니다."
                )
                await ctx.send(embed=embed)
                return
            
            # Calculate deletion time
            delete_at = datetime.now() + timedelta(minutes=delay_minutes)
            
            # Schedule the deletion
            await self.deletion_model.schedule_deletion(
                message_id=message_id,
                channel_id=ctx.channel.id,
                requester_id=ctx.author.id,
                delete_at=delete_at
            )
            
            embed = self.formatter.create_success_embed(
                title="⏰ 삭제 예약 완료",
                description=f"메시지가 **{delay_minutes}분** 후에 삭제됩니다."
            )
            embed.add_field(name="삭제 시간", value=delete_at.strftime("%Y-%m-%d %H:%M:%S"), inline=True)
            embed.add_field(name="요청자", value=ctx.author.mention, inline=True)
            embed.add_field(name="메시지 ID", value=str(message_id), inline=True)
            
            # Show preview of message to be deleted
            if len(message.content) > 0:
                preview = message.content[:100] + "..." if len(message.content) > 100 else message.content
                embed.add_field(name="메시지 미리보기", value=f"```{preview}```", inline=False)
            
            await ctx.send(embed=embed)
            
            # Log the action
            self.logger.info(f"Scheduled deletion for message {message_id} in {delay_minutes} minutes by {ctx.author}")
            
        except Exception as e:
            embed = self.formatter.create_error_embed(
                title="오류 발생",
                description=f"예약 삭제 설정 중 오류가 발생했습니다: {e}"
            )
            await ctx.send(embed=embed)

    @app_commands.command(name="예약삭제취소", description="예약된 삭제를 취소합니다")
    @app_commands.describe(message_id="취소할 메시지 ID")
    async def cancel_scheduled_deletion_slash(self, interaction: discord.Interaction, message_id: str):
        """슬래시 명령어로 예약 삭제 취소"""
        # 권한 체크
        checker = PermissionChecker()
        permission_level = checker.get_permission_level(interaction.user, interaction.guild)
        
        if permission_level.value < PermissionLevel.MODERATOR.value:
            await interaction.response.send_message("❌ 이 명령어를 사용할 권한이 없습니다.", ephemeral=True)
            return
        
        try:
            message_id_int = int(message_id)
            
            success = await self.deletion_model.cancel_scheduled_deletion(message_id_int)
            
            if success:
                embed = discord.Embed(
                    title="✅ 예약 삭제 취소",
                    description="예약된 삭제가 취소되었습니다.",
                    color=discord.Color.green()
                )
            else:
                embed = discord.Embed(
                    title="❌ 취소 실패",
                    description="해당 메시지의 예약 삭제를 찾을 수 없습니다.",
                    color=discord.Color.red()
                )
            
            await interaction.response.send_message(embed=embed)
            
        except ValueError:
            await interaction.response.send_message("❌ 올바른 메시지 ID를 입력해주세요.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ 예약 삭제 취소 중 오류가 발생했습니다: {e}", ephemeral=True)

    @commands.command(name="예약삭제취소", aliases=["cancel_delete", "unschedule"])
    @error_handler
    async def cancel_scheduled_deletion(self, ctx, message_id: int):
        """
        Cancel a scheduled message deletion.
        
        Args:
            message_id: ID of the message to cancel deletion for
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
        
        try:
            success = await self.deletion_model.cancel_scheduled_deletion(message_id)
            
            if success:
                embed = self.formatter.create_success_embed(
                    title="✅ 예약 삭제 취소",
                    description="예약된 삭제가 성공적으로 취소되었습니다."
                )
                embed.add_field(name="메시지 ID", value=str(message_id), inline=True)
                embed.add_field(name="취소자", value=ctx.author.mention, inline=True)
            else:
                embed = self.formatter.create_warning_embed(
                    title="취소 실패",
                    description="해당 메시지의 예약 삭제를 찾을 수 없습니다."
                )
                embed.add_field(name="메시지 ID", value=str(message_id), inline=True)
            
            await ctx.send(embed=embed)
            
            # Log the action
            if success:
                self.logger.info(f"Cancelled scheduled deletion for message {message_id} by {ctx.author}")
            
        except Exception as e:
            embed = self.formatter.create_error_embed(
                title="오류 발생",
                description=f"예약 삭제 취소 중 오류가 발생했습니다: {e}"
            )
            await ctx.send(embed=embed)

    @app_commands.command(name="청소", description="메시지를 대량 삭제합니다")
    @app_commands.describe(
        amount="삭제할 메시지 수 (기본: 10, 최대: 100)",
        user="특정 사용자의 메시지만 삭제 (선택사항)"
    )
    async def purge_messages_slash(self, interaction: discord.Interaction, amount: int = 10, user: discord.Member = None):
        """슬래시 명령어로 메시지 청소"""
        # 권한 체크
        checker = PermissionChecker()
        permission_level = checker.get_permission_level(interaction.user, interaction.guild)
        
        if permission_level.value < PermissionLevel.MODERATOR.value:
            await interaction.response.send_message("❌ 이 명령어를 사용할 권한이 없습니다.", ephemeral=True)
            return
        
        if amount < 1 or amount > 100:
            await interaction.response.send_message("❌ 삭제할 메시지 수는 1-100개 사이여야 합니다.", ephemeral=True)
            return
        
        try:
            await interaction.response.defer()
            
            def check(message):
                if user:
                    return message.author == user
                return True
            
            deleted = await interaction.channel.purge(limit=amount, check=check)
            
            embed = discord.Embed(
                title="🧹 메시지 청소 완료",
                description=f"{len(deleted)}개의 메시지를 삭제했습니다.",
                color=discord.Color.green()
            )
            
            if user:
                embed.add_field(name="대상 사용자", value=user.mention, inline=True)
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            await interaction.followup.send(f"❌ 메시지 청소 중 오류가 발생했습니다: {e}")

    @commands.command(name="청소", aliases=["purge", "clear"])
    @error_handler
    async def purge_messages(self, ctx, amount: int = 10, user: discord.Member = None):
        """
        Purge messages from the channel.
        
        Args:
            amount: Number of messages to delete (max: 100)
            user: Specific user to delete messages from (optional)
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
        
        # Validate amount
        if amount < 1:
            embed = self.formatter.create_error_embed(
                title="잘못된 수량",
                description="삭제할 메시지 수는 1개 이상이어야 합니다."
            )
            await ctx.send(embed=embed)
            return
            
        if amount > 100:
            embed = self.formatter.create_error_embed(
                title="수량 제한",
                description="한 번에 최대 100개의 메시지만 삭제할 수 있습니다."
            )
            await ctx.send(embed=embed)
            return
        
        try:
            # Delete the command message first
            await ctx.message.delete()
            
            # Set up check function
            def check(message):
                # Skip messages older than 14 days (Discord limitation)
                if (datetime.now() - message.created_at).days >= 14:
                    return False
                    
                if user:
                    return message.author == user
                return True
            
            # Purge messages
            deleted = await ctx.channel.purge(limit=amount, check=check)
            
            # Send confirmation message
            embed = self.formatter.create_success_embed(
                title="🧹 메시지 청소 완료",
                description=f"**{len(deleted)}개**의 메시지를 삭제했습니다."
            )
            embed.add_field(name="실행자", value=ctx.author.mention, inline=True)
            embed.add_field(name="채널", value=ctx.channel.mention, inline=True)
            
            if user:
                embed.add_field(name="대상 사용자", value=user.mention, inline=True)
            
            # Send confirmation and auto-delete after 5 seconds
            confirmation = await ctx.send(embed=embed)
            await asyncio.sleep(5)
            await confirmation.delete()
            
            # Log the action
            self.logger.info(f"{ctx.author} purged {len(deleted)} messages in {ctx.channel}")
            
        except discord.Forbidden:
            embed = self.formatter.create_error_embed(
                title="권한 부족",
                description="봇이 메시지를 삭제할 권한이 없습니다."
            )
            await ctx.send(embed=embed)
        except Exception as e:
            embed = self.formatter.create_error_embed(
                title="오류 발생",
                description=f"메시지 청소 중 오류가 발생했습니다: {e}"
            )
            await ctx.send(embed=embed)

    @app_commands.command(name="사용자메시지삭제", description="특정 사용자의 메시지를 모두 삭제합니다")
    @app_commands.describe(
        user="메시지를 삭제할 사용자",
        limit="확인할 메시지 범위 (기본: 100)"
    )
    async def delete_user_messages_slash(self, interaction: discord.Interaction, user: discord.Member, limit: int = 100):
        """슬래시 명령어로 사용자 메시지 삭제"""
        # 권한 체크
        checker = PermissionChecker()
        permission_level = checker.get_permission_level(interaction.user, interaction.guild)
        
        if permission_level.value < PermissionLevel.MODERATOR.value:
            await interaction.response.send_message("❌ 이 명령어를 사용할 권한이 없습니다.", ephemeral=True)
            return
        
        if limit < 1 or limit > 1000:
            await interaction.response.send_message("❌ 검색 범위는 1-1000개 사이여야 합니다.", ephemeral=True)
            return
        
        try:
            await interaction.response.defer()
            
            def check(message):
                return message.author == user and (datetime.now() - message.created_at).days < 14
            
            deleted = await interaction.channel.purge(limit=limit, check=check)
            
            embed = discord.Embed(
                title="🗑️ 사용자 메시지 삭제 완료",
                description=f"{user.mention}의 메시지 {len(deleted)}개를 삭제했습니다.",
                color=discord.Color.green()
            )
            embed.add_field(name="검색 범위", value=f"{limit}개 메시지", inline=True)
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            await interaction.followup.send(f"❌ 메시지 삭제 중 오류가 발생했습니다: {e}")

    @commands.command(name="사용자메시지삭제", aliases=["delete_user_messages", "clear_user"])
    @error_handler
    async def delete_user_messages(self, ctx, user: discord.Member, limit: int = 100):
        """
        Delete all messages from a specific user in the channel.
        
        Args:
            user: User whose messages to delete
            limit: Number of messages to search through (max: 1000)
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
            
        if limit < 1:
            limit = 100
        elif limit > 1000:
            limit = 1000
        
        try:
            # Delete the command message
            await ctx.message.delete()
            
            # Set up check function
            def check(message):
                # Skip messages older than 14 days
                if (datetime.now() - message.created_at).days >= 14:
                    return False
                return message.author == user
            
            # Delete messages
            deleted = await ctx.channel.purge(limit=limit, check=check)
            
            embed = self.formatter.create_success_embed(
                title="🗑️ 사용자 메시지 삭제 완료",
                description=f"**{user.display_name}**의 메시지 **{len(deleted)}개**를 삭제했습니다."
            )
            embed.add_field(name="실행자", value=ctx.author.mention, inline=True)
            embed.add_field(name="대상", value=user.mention, inline=True)
            embed.add_field(name="검색 범위", value=f"{limit}개 메시지", inline=True)
            
            # Send confirmation and auto-delete
            confirmation = await ctx.send(embed=embed)
            await asyncio.sleep(10)
            await confirmation.delete()
            
            # Log the action
            self.logger.info(f"{ctx.author} deleted {len(deleted)} messages from {user} in {ctx.channel}")
            
        except discord.Forbidden:
            embed = self.formatter.create_error_embed(
                title="권한 부족",
                description="봇이 메시지를 삭제할 권한이 없습니다."
            )
            await ctx.send(embed=embed)
        except Exception as e:
            embed = self.formatter.create_error_embed(
                title="오류 발생",
                description=f"메시지 삭제 중 오류가 발생했습니다: {e}"
            )
            await ctx.send(embed=embed)

    @commands.command(name="메시지삭제필터", aliases=["delete_filtered", "filter_delete"])
    @error_handler
    async def delete_filtered_messages(self, ctx, *, filter_text: str):
        """
        Delete messages containing specific text.
        
        Args:
            filter_text: Text to search for in messages
        """
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
        
        if len(filter_text.strip()) < 3:
            embed = self.formatter.create_error_embed(
                title="검색어 부족",
                description="검색어는 최소 3글자 이상이어야 합니다."
            )
            await ctx.send(embed=embed)
            return
        
        try:
            # Delete the command message
            await ctx.message.delete()
            
            # Set up check function
            def check(message):
                if (datetime.now() - message.created_at).days >= 14:
                    return False
                return filter_text.lower() in message.content.lower()
            
            # Confirm deletion
            embed = self.formatter.create_embed(
                title="⚠️ 메시지 삭제 확인",
                description=f"'{filter_text}' 텍스트를 포함한 메시지를 삭제하시겠습니까?",
                color=self.formatter.colors['warning']
            )
            embed.add_field(name="검색어", value=f"`{filter_text}`", inline=True)
            embed.add_field(name="실행자", value=ctx.author.mention, inline=True)
            embed.add_field(name="참고", value="이 작업은 되돌릴 수 없습니다.", inline=False)
            
            confirmation = await ctx.send(embed=embed)
            await confirmation.add_reaction("✅")
            await confirmation.add_reaction("❌")
            
            def reaction_check(reaction, user):
                return user == ctx.author and str(reaction.emoji) in ["✅", "❌"] and reaction.message.id == confirmation.id
            
            try:
                reaction, user = await self.bot.wait_for('reaction_add', timeout=30.0, check=reaction_check)
                
                if str(reaction.emoji) == "✅":
                    # Delete messages
                    deleted = await ctx.channel.purge(limit=500, check=check)
                    
                    embed = self.formatter.create_success_embed(
                        title="🗑️ 필터 삭제 완료",
                        description=f"'{filter_text}'를 포함한 **{len(deleted)}개**의 메시지를 삭제했습니다."
                    )
                    embed.add_field(name="실행자", value=ctx.author.mention, inline=True)
                    embed.add_field(name="검색어", value=f"`{filter_text}`", inline=True)
                    
                    await confirmation.edit(embed=embed)
                    
                    # Log the action
                    self.logger.info(f"{ctx.author} deleted {len(deleted)} messages containing '{filter_text}' in {ctx.channel}")
                    
                else:
                    embed = self.formatter.create_embed(
                        title="❌ 삭제 취소",
                        description="메시지 삭제가 취소되었습니다.",
                        color=self.formatter.colors['error']
                    )
                    await confirmation.edit(embed=embed)
                
                # Remove reactions
                await confirmation.clear_reactions()
                
            except asyncio.TimeoutError:
                embed = self.formatter.create_embed(
                    title="⏰ 시간 초과",
                    description="30초 내에 응답하지 않아 삭제가 취소되었습니다.",
                    color=self.formatter.colors['warning']
                )
                await confirmation.edit(embed=embed)
                await confirmation.clear_reactions()
            
        except discord.Forbidden:
            embed = self.formatter.create_error_embed(
                title="권한 부족",
                description="봇이 메시지를 삭제할 권한이 없습니다."
            )
            await ctx.send(embed=embed)
        except Exception as e:
            embed = self.formatter.create_error_embed(
                title="오류 발생",
                description=f"필터 삭제 중 오류가 발생했습니다: {e}"
            )
            await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(MessageManager(bot))