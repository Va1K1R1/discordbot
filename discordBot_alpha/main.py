from typing import Literal, Optional
import discord
from discord.ext import commands, tasks
from discord.ext.commands import Greedy, Context
import asyncio
import logging
import os
import sys
import psutil
import platform
from datetime import datetime, timedelta

# 유틸리티 및 설정 임포트
from config.settings import Settings
from config.database import DatabaseManager
from utils.permissions import PermissionLevel, PermissionChecker
from utils.decorators import error_handler
from utils.helpers import MessageFormatter, InputValidator

# 데이터베이스 모델 임포트
from database.models import UserPointsModel, MessageLogModel, ScheduledDeletionModel, ServerSettingsModel
from database.shop_models import ShopModel
from database.gambling_models import GamblingModel
from database.betting_models import BettingModel

class DiscordBot(commands.Bot):
    """
    Main Discord bot class that handles events and commands.
    """
    def __init__(self):
        # Set up intents (permissions for the bot)
        intents = discord.Intents.all()

        # Initialize the bot with command prefix and intents
        super().__init__(
            command_prefix=Settings.COMMAND_PREFIX,
            intents=intents,
            help_command=None  # Disable default help command
        )

        # Set up logging
        self.logger = logging.getLogger('discord_bot')

        # Initialize database manager
        self.db = DatabaseManager()

        # Initialize models - 실제 초기화는 setup_hook에서 진행
        self.point_model = None
        self.message_log_model = None
        self.scheduled_deletion_model = None
        self.server_settings_model = None
        self.shop_model = None
        self.gambling_model = None
        self.betting_model = None

        # Cooldown tracking
        self.message_cooldowns = {}

        # Log channel reference
        self.log_channel = None

        # Memory usage tracking
        self.process = psutil.Process(os.getpid())
        self.start_memory = self.get_memory_usage()
        self.peak_memory = self.start_memory
        self.last_memory_check = datetime.now()

        # 동기화 상태 추적
        self._synced = False
        
        # 모델 초기화 완료 상태 추적
        self._models_initialized = False

    def get_memory_usage(self):
        """Get current memory usage in MB"""
        try:
            # Get memory info for the current process
            memory_info = self.process.memory_info()
            # Return RSS (Resident Set Size) in MB
            return memory_info.rss / (1024 * 1024)
        except Exception as e:
            self.logger.error(f"Error getting memory usage: {e}")
            return 0

    @tasks.loop(minutes=5)
    async def memory_monitor(self):
        """Monitor memory usage and log warnings if it exceeds limits"""
        try:
            current_memory = self.get_memory_usage()

            # Update peak memory
            if current_memory > self.peak_memory:
                self.peak_memory = current_memory

            # Log memory usage periodically
            self.logger.info(f"Memory usage: {current_memory:.2f} MB (Peak: {self.peak_memory:.2f} MB)")

            # Check if memory limit is exceeded
            if Settings.MEMORY_LIMIT_MB > 0 and current_memory > Settings.MEMORY_LIMIT_MB:
                self.logger.warning(
                    f"Memory usage ({current_memory:.2f} MB) exceeds limit ({Settings.MEMORY_LIMIT_MB} MB). "
                    f"Consider enabling LIGHTWEIGHT_MODE or increasing MEMORY_LIMIT_MB."
                )

                # If running on Raspberry Pi with limited memory, take action
                if Settings.IS_RASPBERRY_PI and current_memory > Settings.MEMORY_LIMIT_MB * 1.2:
                    self.logger.warning("Memory usage critically high on Raspberry Pi. Attempting to reduce memory usage.")
                    # Force garbage collection
                    import gc
                    gc.collect()
                    # Clear caches
                    self.message_cooldowns.clear()
                    if hasattr(self.db, 'query_cache'):
                        self.db.query_cache.clear()

        except Exception as e:
            self.logger.error(f"Error in memory monitor: {e}")

    @memory_monitor.before_loop
    async def before_memory_monitor(self):
        """Wait for the bot to be ready before starting memory monitoring"""
        await self.wait_until_ready()

    async def setup_hook(self):
        """
        Called when the bot is starting up.
        Sets up the database connection and loads extensions.
        """
        self.logger.info("🚀 Bot is starting up...")

        # Initialize database
        try:
            await self.initialize_database()
        except Exception as e:
            self.logger.error(f"Failed to initialize database: {e}")
            raise

        # Initialize models
        await self.initialize_models()

        # Load all cogs
        await self.load_extensions()

        # Start background tasks
        self.check_scheduled_deletions.start()

        self.logger.info("✅ Setup hook completed successfully")

    async def initialize_database(self):
        """
        Initialize the database connection and run migrations.
        """
        self.logger.info("🗄️ Initializing database...")
        await self.db.initialize()
        await self.db.run_migrations()
        await self.db.check_and_update_schema()
        self.logger.info("✅ Database initialization complete.")

    async def initialize_models(self):
        """
        Initialize all database models.
        """
        self.logger.info("🔧 Initializing models...")
        
        self.point_model = UserPointsModel(self.db)
        self.message_log_model = MessageLogModel(self.db)
        self.scheduled_deletion_model = ScheduledDeletionModel(self.db)
        self.server_settings_model = ServerSettingsModel(self.db)
        self.shop_model = ShopModel(self.db)
        self.gambling_model = GamblingModel(self.db)
        self.betting_model = BettingModel(self.db)
        
        self._models_initialized = True
        self.logger.info("✅ Models initialization complete.")

    async def load_extensions(self):
        """
        Load cog extensions based on settings.
        """
        self.logger.info("📦 Loading extensions...")

        # Get enabled cogs from settings
        enabled_cogs = Settings.ENABLED_COGS

        # Map cog short names to full module paths
        cog_mapping = {
            'base': 'cogs.base',  # 기본 명령어 추가
            'permissions': 'cogs.permissions',
            'points': 'cogs.points',
            'message_manager': 'cogs.message_manager',
            'logging_system': 'cogs.logging_system',
            'shop': 'cogs.shop',
            'gambling': 'cogs.gambling',
            'betting': 'cogs.betting'
        }

        # Always load essential cogs
        essential_cogs = ['base', 'permissions']  # base cog도 필수로 추가
        for cog in essential_cogs:
            if cog not in enabled_cogs:
                self.logger.warning(f"Essential cog '{cog}' was not in ENABLED_COGS, adding it")
                enabled_cogs.append(cog)

        # Load each enabled cog
        loaded_count = 0
        for cog_name, cog_path in cog_mapping.items():
            if cog_name in enabled_cogs or Settings.LIGHTWEIGHT_MODE == False:
                try:
                    await self.load_extension(cog_path)
                    self.logger.info(f"✅ Loaded extension: {cog_path}")
                    loaded_count += 1
                except Exception as e:
                    self.logger.error(f"❌ Failed to load extension {cog_path}: {e}")
            else:
                self.logger.info(f"⏭️ Skipping disabled extension: {cog_path}")

        self.logger.info(f"📦 Loaded {loaded_count} extensions")

        # Apply memory usage monitoring if enabled
        if Settings.MEMORY_LIMIT_MB > 0:
            self.memory_monitor.start()

    async def force_sync_commands(self):
        """
        강제로 모든 슬래시 명령어를 동기화합니다.
        """
        if self._synced:
            self.logger.info("⏭️ Commands already synced, skipping...")
            return

        self.logger.info("🔄 Starting forced command synchronization...")

        try:
            # 모든 길드에 대해 명령어 동기화
            synced_commands = []

            # 글로벌 명령어 동기화 (선택사항)
            try:
                global_synced = await self.tree.sync()
                self.logger.info(f"🌍 Synced {len(global_synced)} global commands")
                synced_commands.extend(global_synced)
            except Exception as e:
                self.logger.error(f"❌ Failed to sync global commands: {e}")

            # 각 길드별 명령어 동기화
            guild_sync_count = 0
            for guild in self.guilds:
                try:
                    guild_synced = await self.tree.sync(guild=guild)
                    self.logger.info(f"🏰 Synced {len(guild_synced)} commands to guild: {guild.name} ({guild.id})")
                    synced_commands.extend(guild_synced)
                    guild_sync_count += 1
                except Exception as e:
                    self.logger.error(f"❌ Failed to sync commands to guild {guild.name}: {e}")

            # 동기화 완료 로그
            total_synced = len(synced_commands)
            self.logger.info(f"✅ Command synchronization completed!")
            self.logger.info(f"📊 Total commands synced: {total_synced}")
            self.logger.info(f"🏰 Guilds synchronized: {guild_sync_count}/{len(self.guilds)}")

            # 동기화된 명령어 목록 로그
            if synced_commands:
                self.logger.info("📋 Synchronized commands:")
                for cmd in synced_commands:
                    self.logger.info(f"  ✓ /{cmd.name} - {cmd.description}")

            self._synced = True

            # 로그 채널에 동기화 완료 메시지 전송
            if self.log_channel:
                embed = discord.Embed(
                    title="🔄 명령어 동기화 완료",
                    description=f"총 {total_synced}개의 슬래시 명령어가 동기화되었습니다.",
                    color=discord.Color.green(),
                    timestamp=datetime.now()
                )
                embed.add_field(name="동기화된 길드", value=f"{guild_sync_count}/{len(self.guilds)}", inline=True)
                embed.add_field(name="동기화 시간", value=datetime.now().strftime("%Y-%m-%d %H:%M:%S"), inline=True)

                try:
                    await self.log_channel.send(embed=embed)
                except Exception as e:
                    self.logger.error(f"Failed to send sync notification to log channel: {e}")

        except Exception as e:
            self.logger.error(f"❌ Critical error during command synchronization: {e}", exc_info=True)
            raise

    @tasks.loop(seconds=Settings.BACKGROUND_TASK_INTERVAL)
    async def check_scheduled_deletions(self):
        """
        Check for scheduled message deletions and execute them.
        """
        # 모델이 초기화되지 않았으면 대기
        if not self._models_initialized or not self.scheduled_deletion_model:
            return
            
        try:
            # Get pending deletions
            pending_deletions = await self.scheduled_deletion_model.get_pending_deletions()

            if not pending_deletions:
                return

            self.logger.info(f"Found {len(pending_deletions)} pending message deletions.")

            # Process each deletion
            for deletion in pending_deletions:
                try:
                    # Get the channel
                    channel = self.get_channel(deletion['channel_id'])
                    if not channel:
                        self.logger.warning(f"Channel {deletion['channel_id']} not found for scheduled deletion.")
                        continue

                    # Get the message
                    try:
                        message = await channel.fetch_message(deletion['message_id'])
                    except discord.NotFound:
                        self.logger.info(f"Message {deletion['message_id']} already deleted.")
                        await self.scheduled_deletion_model.remove_scheduled_deletion(deletion['message_id'])
                        continue

                    # Delete the message
                    await message.delete()
                    self.logger.info(f"Deleted scheduled message {deletion['message_id']}.")

                    # Remove from database
                    await self.scheduled_deletion_model.remove_scheduled_deletion(deletion['message_id'])

                    # Log the deletion
                    if self.log_channel:
                        embed = MessageFormatter.create_embed(
                            title="🗑️ 예약 삭제 실행",
                            description=f"메시지가 예약된 시간에 삭제되었습니다.",
                            color=discord.Color.orange()
                        )
                        embed.add_field(name="채널", value=f"<#{deletion['channel_id']}>", inline=True)
                        embed.add_field(name="삭제자", value=f"<@{deletion['requester_id']}>", inline=True)

                        await self.log_channel.send(embed=embed)

                except Exception as e:
                    self.logger.error(f"Error processing scheduled deletion: {e}")

        except Exception as e:
            self.logger.error(f"Error checking scheduled deletions: {e}")

    @check_scheduled_deletions.before_loop
    async def before_check_scheduled_deletions(self):
        """
        Wait for the bot to be ready before starting the scheduled deletion check.
        """
        await self.wait_until_ready()

    async def on_ready(self):
        """
        Called when the bot is ready and connected to Discord.
        """
        self.logger.info(f"🤖 Logged in as {self.user.name} ({self.user.id})")
        self.logger.info(f"🌐 Connected to {len(self.guilds)} guilds")

        # Set up log channel
        if Settings.LOG_CHANNEL_ID:
            self.log_channel = self.get_channel(Settings.LOG_CHANNEL_ID)
            if not self.log_channel:
                self.logger.warning(f"⚠️ Log channel with ID {Settings.LOG_CHANNEL_ID} not found.")
            else:
                self.logger.info(f"📝 Log channel set to: #{self.log_channel.name}")

        # 강제 명령어 동기화 실행
        try:
            await self.force_sync_commands()
        except Exception as e:
            self.logger.error(f"❌ Failed to sync commands: {e}")

        # Set bot status
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.listening,
                name=f"{Settings.COMMAND_PREFIX}help | 슬래시 명령어 지원"
            )
        )

        self.logger.info("🎉 Bot is ready and all systems operational!")

        # 준비 완료 메시지를 로그 채널에 전송
        if self.log_channel:
            embed = discord.Embed(
                title="🚀 봇 시작 완료",
                description="디스코드 봇이 성공적으로 시작되었습니다!",
                color=discord.Color.green(),
                timestamp=datetime.now()
            )
            embed.add_field(name="서버 수", value=len(self.guilds), inline=True)
            embed.add_field(name="사용자 수", value=len(self.users), inline=True)
            embed.add_field(name="메모리 사용량", value=f"{self.get_memory_usage():.2f} MB", inline=True)
            embed.set_thumbnail(url=self.user.avatar.url if self.user.avatar else None)

            try:
                await self.log_channel.send(embed=embed)
            except Exception as e:
                self.logger.error(f"Failed to send ready notification: {e}")

    async def on_message(self, message):
        """
        Called when a message is sent in a channel the bot can see.
        """
        # Ignore messages from bots
        if message.author.bot:
            return

        # Process commands
        await self.process_commands(message)

        # 모델이 초기화되지 않았으면 로깅과 포인트 부여를 건너뜀
        if not self._models_initialized:
            return

        # Log the message
        try:
            if self.message_log_model:
                # Extract attachments
                attachments = []
                if message.attachments:
                    for attachment in message.attachments:
                        attachments.append({
                            'filename': attachment.filename,
                            'url': attachment.url,
                            'size': attachment.size
                        })

                # Extract embeds
                embeds = []
                if message.embeds:
                    for embed in message.embeds:
                        embeds.append({
                            'title': embed.title,
                            'description': embed.description,
                            'color': embed.color.value if embed.color else None
                        })

                # Log the message
                await self.message_log_model.log_message(
                    message_id=message.id,
                    channel_id=message.channel.id,
                    channel_name=message.channel.name,
                    author_id=message.author.id,
                    author_name=str(message.author),
                    content=message.content,
                    guild_id=message.guild.id if message.guild else None,
                    attachments=attachments,
                    embeds=embeds
                )
        except Exception as e:
            self.logger.error(f"Error logging message: {e}")

        # Award points for messages
        await self.award_message_points(message)

    async def award_message_points(self, message):
        """
        Award points to users for sending messages.
        """
        # 모델이 초기화되지 않았으면 건너뜀
        if not self._models_initialized or not self.point_model:
            return

        user_id = message.author.id
        current_time = datetime.now()

        if user_id in self.message_cooldowns:
            time_diff = current_time - self.message_cooldowns[user_id]
            if time_diff.total_seconds() < Settings.POINT_MESSAGE_COOLDOWN:
                return

        # Update cooldown
        self.message_cooldowns[user_id] = current_time

        # Award points
        try:
            await self.point_model.add_points(
                user_id=user_id,
                username=str(message.author),
                amount=Settings.POINT_MESSAGE_REWARD,
                reason="메시지 작성"
            )

            # Update experience and check for level up
            level_up_info = await self.point_model.update_experience(
                user_id=user_id,
                username=str(message.author),
                exp_amount=Settings.POINT_MESSAGE_REWARD * 2  # Experience is 2x points
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
            self.logger.error(f"Error awarding points: {e}")

    async def on_command_error(self, ctx, error):
        """
        Global error handler for command errors.
        """
        if isinstance(error, commands.CommandNotFound):
            return

        if isinstance(error, commands.MissingRequiredArgument):
            embed = discord.Embed(
                title="❓ 인수 부족",
                description=f"필수 인수가 누락되었습니다: {error.param.name}",
                color=discord.Color.yellow()
            )
            embed.add_field(
                name="사용법",
                value=f"`{ctx.prefix}{ctx.command.qualified_name} {ctx.command.signature}`",
                inline=False
            )
            await ctx.send(embed=embed)
            return

        if isinstance(error, commands.BadArgument):
            embed = discord.Embed(
                title="❓ 잘못된 인수",
                description=str(error),
                color=discord.Color.yellow()
            )
            embed.add_field(
                name="사용법",
                value=f"`{ctx.prefix}{ctx.command.qualified_name} {ctx.command.signature}`",
                inline=False
            )
            await ctx.send(embed=embed)
            return

        if isinstance(error, commands.CommandOnCooldown):
            embed = discord.Embed(
                title="⏰ 쿨다운",
                description=f"이 명령어는 {error.retry_after:.1f}초 후에 다시 사용할 수 있습니다.",
                color=discord.Color.orange()
            )
            await ctx.send(embed=embed)
            return

        # Log other errors
        self.logger.error(f"Command error in {ctx.command}: {error}", exc_info=error)

        # Send error message
        embed = discord.Embed(
            title="🔧 오류 발생",
            description="명령어 실행 중 오류가 발생했습니다.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)

    @commands.command(name="sync")
    @commands.is_owner()
    @commands.guild_only()
    async def sync_cmd(
        self,
        ctx: Context,
        targets: Greedy[discord.Object],     # 여러 길드 ID 지원
        spec: Optional[Literal["~", "*", "^"]] = None
    ) -> None:
        """
        Slash command sync utility. 오너만 사용 가능.
        [옵션]
        - !sync : 글로벌 커맨드 동기화
        - !sync ~ : 현 길드만 동기화
        - !sync * : 글로벌 커맨드를 현길드에 복사 후 동기화
        - !sync ^ : 현 길드 커맨드 리셋/초기화
        - !sync [guildid1] [guildid2] ... : 여러 길드 동기화
        """
        tree = ctx.bot.tree

        # 1) 옵션 없이 → 글로벌 동기화
        if not targets:
            if spec == "~":                               # 현 길드만
                synced = await tree.sync(guild=ctx.guild)
            elif spec == "*":                             # 글로벌→현길드 복사 후 동기화
                tree.copy_global_to(guild=ctx.guild)
                synced = await tree.sync(guild=ctx.guild)
            elif spec == "^":                             # 현 길드 커맨드 초기화
                tree.clear_commands(guild=ctx.guild)
                await tree.sync(guild=ctx.guild)
                synced = []
            else:                                         # 완전 글로벌
                synced = await tree.sync()

            await ctx.send(f"✅ {len(synced)}개 명령 동기화 완료.")
            return

        # 2) 길드 ID 목록 제공 시 각 길드 동기화
        success = 0
        for gid in targets:
            try:
                await tree.sync(guild=discord.Object(id=int(gid.id)))
            except discord.HTTPException:
                pass
            else:
                success += 1
        await ctx.send(f"✅ {success}/{len(targets)}개 길드 동기화 완료.")

async def main():
    """Main entry point for the bot."""
    # Set up logging
    log_level = getattr(logging, Settings.LOG_LEVEL.upper(), logging.INFO)
    log_format = '%(asctime)s:%(levelname)s:%(name)s: %(message)s'

    # Configure log handlers based on settings
    handlers = [logging.StreamHandler()]

    # Add file handler if enabled
    if Settings.LOG_TO_FILE:
        # Ensure logs directory exists
        os.makedirs('logs', exist_ok=True)

        # Add file handler
        handlers.append(logging.FileHandler('logs/discord_bot.log', encoding='utf-8'))

        print(f"Logging to file: logs/discord_bot.log")
    else:
        print("File logging disabled")

    # Apply logging configuration
    logging.basicConfig(
        level=log_level,
        format=log_format,
        handlers=handlers
    )

    logger = logging.getLogger('discord_bot')

    # Log system information
    logger.info(f"🖥️ Starting Discord Bot on {platform.system()} {platform.release()}")

    if Settings.IS_RASPBERRY_PI:
        # Get Raspberry Pi model
        try:
            with open('/sys/firmware/devicetree/base/model', 'r') as f:
                pi_model = f.read().strip()
            logger.info(f"🥧 Running on {pi_model}")
        except:
            logger.info("🥧 Running on Raspberry Pi (unknown model)")

        # Log memory information
        mem = psutil.virtual_memory()
        logger.info(f"💾 System memory: {mem.total / (1024*1024):.1f} MB total, {mem.available / (1024*1024):.1f} MB available")

    # Apply Raspberry Pi optimizations if detected
    Settings.auto_configure_for_raspberry_pi()

    # Validate settings
    try:
        Settings.validate_settings()
    except ValueError as e:
        logger.error(f"❌ Settings validation failed: {e}")
        return

    # Create and run bot
    bot = DiscordBot()

    try:
        logger.info("🚀 Starting bot...")
        await bot.start(Settings.DISCORD_TOKEN)
    except discord.errors.LoginFailure:
        logger.error("❌ Invalid Discord token. Please check your .env file.")
    except Exception as e:
        logger.error(f"❌ Error starting bot: {e}")
    finally:
        await bot.close()

if __name__ == "__main__":
    # Run the bot
    asyncio.run(main())