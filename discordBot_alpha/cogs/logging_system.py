import discord
from discord.ext import commands
import json
import logging
from datetime import datetime
import asyncio

from utils.permissions import PermissionLevel, PermissionChecker
from utils.decorators import require_permission, error_handler
from utils.helpers import MessageFormatter, InputValidator
from database.models import MessageLogModel
from config.settings import Settings

class LoggingSystem(commands.Cog):
    """
    Logging system for the bot.
    Logs messages and events to a database and/or a log channel.
    """
    
    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger('discord_bot.logging')
        self.log_model = MessageLogModel(bot.db)
        self.formatter = MessageFormatter()
        self.setup_logging()
        
    def setup_logging(self):
        """Set up file logging."""
        try:
            # Configure file handler
            file_handler = logging.FileHandler('logs/discord_bot.log', encoding='utf-8')
            file_handler.setFormatter(logging.Formatter(
                '%(asctime)s:%(levelname)s:%(name)s: %(message)s'
            ))
            
            # Add handler to root logger
            root_logger = logging.getLogger()
            root_logger.addHandler(file_handler)
            
            # Set log level
            log_level = getattr(logging, Settings.LOG_LEVEL, logging.INFO)
            root_logger.setLevel(log_level)
            
            self.logger.info("Logging system initialized")
        except Exception as e:
            print(f"Error setting up logging: {e}")
            
    @commands.Cog.listener()
    async def on_ready(self):
        """Set up log channel when bot is ready."""
        if Settings.LOG_CHANNEL_ID:
            self.bot.log_channel = self.bot.get_channel(Settings.LOG_CHANNEL_ID)
            if self.bot.log_channel:
                self.logger.info(f"Log channel set to #{self.bot.log_channel.name}")
            else:
                self.logger.warning(f"Log channel with ID {Settings.LOG_CHANNEL_ID} not found")
                
    @commands.Cog.listener()
    async def on_message(self, message):
        """Log all messages."""
        # Ignore bot messages
        if message.author.bot:
            return
        
        # Skip if message is not from a guild (DM messages)
        if not message.guild:
            return
        
        # Extract message data
        try:
            # Extract attachments
            attachments = []
            if message.attachments:
                for attachment in message.attachments:
                    attachments.append({
                        'filename': attachment.filename,
                        'url': attachment.url,
                        'size': attachment.size,
                        'content_type': attachment.content_type
                    })
                
        # Extract embeds
            embeds = []
            if message.embeds:
                for embed in message.embeds:
                    embed_dict = embed.to_dict()
                    embeds.append(embed_dict)
        
            # Determine message type - FIXED VERSION
            message_type = 'SEND'  # Use 'SEND' for new messages
            # Note: We'll use 'SEND' for regular messages, 'EDIT' for edits, 'DELETE' for deletions
                
        # Log to database - ADD guild_id HERE
            await self.log_model.log_message(
                message_id=message.id,
                channel_id=message.channel.id,
                channel_name=message.channel.name,
                author_id=message.author.id,
                author_name=str(message.author),
                content=message.content,
                guild_id=message.guild.id,
                attachments=attachments,
                embeds=embeds,
                message_type=message_type  # Now uses 'SEND' which is valid
            )
            
        # Log to channel if enabled and not in the log channel itself
            if (hasattr(self.bot, 'log_channel') and 
                self.bot.log_channel and 
                message.channel.id != self.bot.log_channel.id):
                
                # Don't log commands to avoid spam
                if message.content.startswith(Settings.COMMAND_PREFIX):
                    return
                    
                # Create embed for log channel
                log_embed = discord.Embed(
                    description=message.content[:1000] if message.content else "*내용 없음*",
                    color=discord.Color.blue(),
                    timestamp=message.created_at
                )
                
                # Add author info
                log_embed.set_author(
                    name=f"{message.author.display_name} ({message.author})",
                    icon_url=message.author.avatar.url if message.author.avatar else None
                )
                
                # Add message info
                log_embed.add_field(name="채널", value=message.channel.mention, inline=True)
                log_embed.add_field(name="메시지 ID", value=message.id, inline=True)
                
                # Add attachment info if any
                if attachments:
                    if message_type == 'image':
                        # Show image preview
                        log_embed.set_image(url=message.attachments[0].url)
                        if len(message.attachments) > 1:
                            log_embed.add_field(
                                name="첨부파일", 
                                value=f"이미지 {len(message.attachments)}개", 
                                inline=True
                            )
                    else:
                        # List file attachments
                        files_text = "\n".join([
                            f"📎 {att['filename']} ({self.format_size(att['size'])})"
                            for att in attachments[:3]
                        ])
                        if len(attachments) > 3:
                            files_text += f"\n외 {len(attachments) - 3}개..."
                            
                        log_embed.add_field(name="첨부파일", value=files_text, inline=False)
                
                # Send to log channel
                await self.bot.log_channel.send(embed=log_embed)
                
        except Exception as e:
            self.logger.error(f"Error logging message: {e}")
            
    def format_size(self, size_bytes):
        """Format file size in human-readable format."""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"
            
    @commands.Cog.listener()
    async def on_message_delete(self, message):
        """Log message deletions."""
        # Ignore bot messages
        if message.author.bot:
            return
        
        # Skip if message is not from a guild (DM messages)
        if not message.guild:
            return
        
        try:
            # Log deletion to database using message_logs table
            await self.log_model.log_message(
                message_id=message.id,
                channel_id=message.channel.id,
                channel_name=message.channel.name,
                author_id=message.author.id,
                author_name=str(message.author),
                content=message.content,
                guild_id=message.guild.id,  # Add guild_id
                attachments=[{
                    'filename': att.filename,
                    'url': att.url,
                    'size': att.size,
                    'content_type': att.content_type
                } for att in message.attachments] if message.attachments else None,
                embeds=[embed.to_dict() for embed in message.embeds] if message.embeds else None,
                message_type='DELETE'  # Mark as deleted message
            )
        
            # Log to channel if enabled
            if hasattr(self.bot, 'log_channel') and self.bot.log_channel:
                embed = discord.Embed(
                    title="🗑️ 메시지 삭제됨",
                    description=message.content[:1000] if message.content else "*내용 없음*",
                    color=discord.Color.red(),
                    timestamp=datetime.now()
                )
            
                embed.set_author(
                    name=f"{message.author.display_name} ({message.author})",
                    icon_url=message.author.avatar.url if message.author.avatar else None
                )
            
                embed.add_field(name="채널", value=message.channel.mention, inline=True)
                embed.add_field(name="메시지 ID", value=message.id, inline=True)
            
                if message.attachments:
                    embed.add_field(
                        name="첨부파일", 
                        value=f"{len(message.attachments)}개 첨부파일이 포함되어 있었습니다.", 
                        inline=False
                    )
                
                await self.bot.log_channel.send(embed=embed)
        
        except Exception as e:
            self.logger.error(f"Error logging message deletion: {e}")

    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        """Log message edits."""
        # Ignore bot messages
        if before.author.bot:
            return
        
        # Skip if message is not from a guild (DM messages)
        if not before.guild:
            return
        
        # Skip if content didn't change
        if before.content == after.content:
            return
        
        try:
            # Log the edited message (after version) to database
            await self.log_model.log_message(
                message_id=after.id,
                channel_id=after.channel.id,
                channel_name=after.channel.name,
                author_id=after.author.id,
                author_name=str(after.author),
                content=after.content,
                guild_id=after.guild.id,  # Add guild_id
                attachments=[{
                    'filename': att.filename,
                    'url': att.url,
                    'size': att.size,
                    'content_type': att.content_type
                } for att in after.attachments] if after.attachments else None,
                embeds=[embed.to_dict() for embed in after.embeds] if after.embeds else None,
                message_type='EDIT'  # Mark as edited message
            )
        
            # Log to channel if enabled and not in the log channel itself
            if (hasattr(self.bot, 'log_channel') and 
                self.bot.log_channel and 
                before.channel.id != self.bot.log_channel.id):
            
                embed = discord.Embed(
                    title="✏️ 메시지 수정됨",
                    color=discord.Color.orange(),
                    timestamp=after.edited_at or datetime.now()
                )
            
                embed.set_author(
                    name=f"{before.author.display_name} ({before.author})",
                    icon_url=before.author.avatar.url if before.author.avatar else None
                )
            
                # Add before/after content
                if before.content:
                    embed.add_field(
                        name="이전 내용", 
                        value=before.content[:1000] if len(before.content) <= 1000 else before.content[:997] + "...", 
                        inline=False
                    )
                else:
                    embed.add_field(name="이전 내용", value="*내용 없음*", inline=False)
                
                if after.content:
                    embed.add_field(
                        name="새 내용", 
                        value=after.content[:1000] if len(after.content) <= 1000 else after.content[:997] + "...", 
                        inline=False
                    )
                else:
                    embed.add_field(name="새 내용", value="*내용 없음*", inline=False)
            
                embed.add_field(name="채널", value=before.channel.mention, inline=True)
                embed.add_field(name="메시지 ID", value=before.id, inline=True)
                embed.add_field(name="메시지 링크", value=f"[바로가기]({after.jump_url})", inline=True)
            
                await self.bot.log_channel.send(embed=embed)
        
        except Exception as e:
            self.logger.error(f"Error logging message edit: {e}")

    @commands.Cog.listener()
    async def on_member_join(self, member):
        """Log when members join the server."""
        # Skip if not in a guild
        if not member.guild:
            return
        
        try:
            # Log to channel if enabled
            if hasattr(self.bot, 'log_channel') and self.bot.log_channel:
                embed = discord.Embed(
                    title="👋 새 멤버 참가",
                    description=f"{member.mention}님이 서버에 참가했습니다.",
                    color=discord.Color.green(),
                    timestamp=member.joined_at or datetime.now()
                )
            
                embed.set_author(
                    name=f"{member.display_name} ({member})",
                    icon_url=member.avatar.url if member.avatar else None
                )
            
                embed.add_field(name="계정 생성일", value=member.created_at.strftime("%Y-%m-%d %H:%M:%S"), inline=True)
                embed.add_field(name="멤버 번호", value=str(len(member.guild.members)), inline=True)
                embed.add_field(name="사용자 ID", value=str(member.id), inline=True)
            
                # Check account age
                account_age = datetime.now(member.created_at.tzinfo) - member.created_at
                if account_age.days < 60:
                    embed.add_field(
                        name="⚠️ 주의", 
                        value=f"계정이 {account_age.days}일 전에 생성되었습니다.", 
                        inline=False
                    )
                
                await self.bot.log_channel.send(embed=embed)
            
        except Exception as e:
            self.logger.error(f"Error logging member join: {e}")

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        """Log when members leave the server."""
        # Skip if not in a guild
        if not member.guild:
            return
        
        try:
            # Log to channel if enabled
            if hasattr(self.bot, 'log_channel') and self.bot.log_channel:
                embed = discord.Embed(
                    title="👋 멤버 퇴장",
                    description=f"{member.mention}님이 서버를 떠났습니다.",
                    color=discord.Color.red(),
                    timestamp=datetime.now()
                )
            
                embed.set_author(
                    name=f"{member.display_name} ({member})",
                    icon_url=member.avatar.url if member.avatar else None
                )
            
                # Calculate how long they were in the server
                if member.joined_at:
                    time_in_server = datetime.now(member.joined_at.tzinfo) - member.joined_at
                    days = time_in_server.days
                    hours, remainder = divmod(time_in_server.seconds, 3600)
                    minutes, _ = divmod(remainder, 60)
                
                    duration_str = f"{days}일 {hours}시간 {minutes}분"
                    embed.add_field(name="서버 체류 시간", value=duration_str, inline=True)
            
                embed.add_field(name="참가일", value=member.joined_at.strftime("%Y-%m-%d %H:%M:%S") if member.joined_at else "알 수 없음", inline=True)
                embed.add_field(name="사용자 ID", value=str(member.id), inline=True)
            
                # Show roles they had
                if member.roles and len(member.roles) > 1:  # Exclude @everyone role
                    roles = [role.mention for role in member.roles[1:]]  # Skip @everyone
                    roles_text = ", ".join(roles[:10])  # Limit to 10 roles
                    if len(member.roles) > 11:
                        roles_text += f" 외 {len(member.roles) - 11}개..."
                    embed.add_field(name="보유 역할", value=roles_text, inline=False)
                
                await self.bot.log_channel.send(embed=embed)
            
        except Exception as e:
            self.logger.error(f"Error logging member remove: {e}")
            
    @commands.command(name="로그검색", aliases=["searchlogs", "findlogs"])
    @require_permission(PermissionLevel.MODERATOR)
    @error_handler
    async def search_logs(self, ctx, user: discord.Member = None, *, content: str = None):
        """
        Search message logs.
        
        Args:
            user (discord.Member, optional): Filter by user
            content (str, optional): Search in message content
        """
        # Validate search parameters
        if not user and not content:
            embed = discord.Embed(
                title="❌ 검색 조건 부족",
                description="유저나 내용 중 하나 이상을 지정해야 합니다.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
            
        # Send initial status
        status_message = await ctx.send(
            embed=discord.Embed(
                title="🔍 로그 검색 중...",
                description="메시지 로그를 검색하고 있습니다. 잠시만 기다려주세요...",
                color=discord.Color.blue()
            )
        )
        
        try:
            # Search logs
            logs = await self.log_model.search_logs(
                user_id=user.id if user else None,
                content_search=content,
                limit=50
            )
            
            if not logs:
                await status_message.edit(
                    embed=discord.Embed(
                        title="❓ 검색 결과 없음",
                        description="검색 조건에 맞는 로그를 찾을 수 없습니다.",
                        color=discord.Color.orange()
                    )
                )
                return
                
            # Create result embed
            embed = discord.Embed(
                title="📋 로그 검색 결과",
                description=f"총 {len(logs)}개의 메시지를 찾았습니다.",
                color=discord.Color.green()
            )
            
            # Add search filters
            filters = []
            if user:
                filters.append(f"유저: {user.mention}")
            if content:
                filters.append(f"내용: '{content}'")
                
            embed.add_field(name="검색 조건", value=", ".join(filters), inline=False)
            
            # Add results (limited to 10 for display)
            for i, log in enumerate(logs[:10]):
                # Format timestamp
                timestamp = log['created_at']
                if isinstance(timestamp, str):
                    timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    
                time_str = timestamp.strftime("%Y-%m-%d %H:%M:%S")
                
                # Format content
                content = log['content']
                if content and len(content) > 100:
                    content = content[:97] + "..."
                elif not content:
                    content = "*내용 없음*"
                    
                # Add field
                embed.add_field(
                    name=f"{i+1}. {log['author_name']} - #{log['channel_name']} - {time_str}",
                    value=content,
                    inline=False
                )
                
            # Add note if there are more results
            if len(logs) > 10:
                embed.set_footer(text=f"표시된 결과: 10/{len(logs)}개")
                
            await status_message.edit(embed=embed)
            
        except Exception as e:
            self.logger.error(f"Error searching logs: {e}")
            await status_message.edit(
                embed=discord.Embed(
                    title="❌ 검색 오류",
                    description=f"로그 검색 중 오류가 발생했습니다: {str(e)}",
                    color=discord.Color.red()
                )
            )
            
    @commands.command(name="로그채널설정", aliases=["setlogchannel"])
    @require_permission(PermissionLevel.ADMIN)
    @error_handler
    async def set_log_channel(self, ctx, channel: discord.TextChannel = None):
        """
        Set the log channel for the bot.
        
        Args:
            channel (discord.TextChannel, optional): The channel to use for logging.
                                                    If not provided, shows the current log channel.
        """
        if not channel:
            # Show current log channel
            if hasattr(self.bot, 'log_channel') and self.bot.log_channel:
                embed = discord.Embed(
                    title="ℹ️ 현재 로그 채널",
                    description=f"현재 로그 채널은 {self.bot.log_channel.mention} 입니다.",
                    color=discord.Color.blue()
                )
            else:
                embed = discord.Embed(
                    title="ℹ️ 로그 채널 없음",
                    description="현재 설정된 로그 채널이 없습니다.",
                    color=discord.Color.orange()
                )
                
            await ctx.send(embed=embed)
            return
            
        # Set new log channel
        self.bot.log_channel = channel
        
        # Update settings (this is temporary, would need to be saved to database or config file)
        # In a real implementation, you would update the database or config file here
        
        embed = discord.Embed(
            title="✅ 로그 채널 설정 완료",
            description=f"로그 채널이 {channel.mention}로 설정되었습니다.",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)
        
        # Send test message to log channel
        test_embed = discord.Embed(
            title="📝 로그 채널 설정됨",
            description=f"이 채널이 봇의 로그 채널로 설정되었습니다.",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        test_embed.add_field(name="설정자", value=ctx.author.mention, inline=True)
        
        await channel.send(embed=test_embed)

async def setup(bot):
    """Add the cog to the bot."""
    await bot.add_cog(LoggingSystem(bot))