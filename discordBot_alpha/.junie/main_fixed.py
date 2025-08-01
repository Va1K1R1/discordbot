import discord
from discord.ext import commands, tasks
from discord import app_commands
import asyncio
import logging
import os
import sys
import json
import random
import re
from datetime import datetime, timedelta

# 유틸리티 및 설정 임포트
from config.settings import Settings
from config.database import DatabaseManager
from utils.permissions import PermissionLevel, PermissionChecker
from utils.decorators import error_handler
from utils.helpers import MessageFormatter, InputValidator

# 데이터베이스 모델 임포트
from database.models import UserPointsModel, MessageLogModel, ScheduledDeletionModel
from database.shop_models import ShopModel
from database.gambling_models import GamblingModel
from database.betting_models import BettingModel


class BettingView(discord.ui.View):
    """베팅 옵션을 선택하기 위한 UI 뷰"""
    
    def __init__(self, betting_model, point_model, event_id, options, timeout=600):
        super().__init__(timeout=timeout)
        self.betting_model = betting_model
        self.point_model = point_model
        self.event_id = event_id
        self.options = options
        
        # 각 옵션에 대한 버튼 추가
        for i, option in enumerate(options, 1):
            button = discord.ui.Button(
                label=f"{i}. {option['option_text']}", 
                style=discord.ButtonStyle.primary,
                custom_id=f"bet_{event_id}_{option['id']}"
            )
            button.callback = self.make_callback(option)
            self.add_item(button)
    
    def make_callback(self, option):
        """각 버튼에 대한 콜백 함수 생성"""
        async def callback(interaction):
            # 베팅 모달 표시
            modal = BettingModal(
                self.betting_model,
                self.point_model,
                self.event_id,
                option
            )
            await interaction.response.send_modal(modal)
        return callback

class BettingModal(discord.ui.Modal):
    """베팅 금액을 입력받기 위한 모달"""
    
    def __init__(self, betting_model, point_model, event_id, option, *args, **kwargs):
        super().__init__(title=f"베팅: {option['option_text']}", *args, **kwargs)
        self.betting_model = betting_model
        self.point_model = point_model
        self.event_id = event_id
        self.option = option
        
        # 포인트 입력 필드 추가
        self.points_input = discord.ui.TextInput(
            label="베팅할 포인트 수량",
            placeholder="숫자만 입력하세요",
            min_length=1,
            max_length=10,
            required=True,
            style=discord.TextStyle.short
        )
        self.add_item(self.points_input)
    
    async def on_submit(self, interaction):
        """모달 제출 시 처리"""
        try:
            # 입력값 검증
            points_str = self.points_input.value.strip()
            if not points_str.isdigit():
                await interaction.response.send_message("❌ 포인트는 숫자만 입력해주세요.", ephemeral=True)
                return
                
            points = int(points_str)
            if points <= 0:
                await interaction.response.send_message("❌ 포인트는 양수여야 합니다.", ephemeral=True)
                return
                
            # 사용자 포인트 확인
            user_points = await self.point_model.get_user_points(interaction.user.id)
            if not user_points or user_points['points'] < points:
                await interaction.response.send_message("❌ 포인트가 부족합니다.", ephemeral=True)
                return
                
            # 이미 베팅했는지 확인
            existing_bet = await self.betting_model.get_user_bet(self.event_id, interaction.user.id)
            if existing_bet:
                await interaction.response.send_message(f"❌ 이미 이 이벤트에 베팅했습니다. (옵션: {existing_bet['option_text']}, 포인트: {existing_bet['points']})", ephemeral=True)
                return
                
            # 베팅 처리
            success = await self.betting_model.place_bet(
                event_id=self.event_id,
                option_id=self.option['id'],
                user_id=interaction.user.id,
                username=str(interaction.user),
                points=points
            )
            
            if success:
                # 포인트 차감
                await self.point_model.remove_points(
                    user_id=interaction.user.id,
                    amount=points,
                    reason=f"베팅: {self.option['option_text']}"
                )
                
                # 성공 메시지
                embed = discord.Embed(
                    title="✅ 베팅 완료",
                    description=f"**{self.option['option_text']}**에 **{points:,}** 포인트를 베팅했습니다.",
                    color=discord.Color.green()
                )
                embed.add_field(name="이벤트 ID", value=self.event_id, inline=True)
                embed.add_field(name="남은 포인트", value=f"{user_points['points'] - points:,}", inline=True)
                
                await interaction.response.send_message(embed=embed, ephemeral=True)
            else:
                await interaction.response.send_message("❌ 베팅 처리 중 오류가 발생했습니다.", ephemeral=True)
                
        except Exception as e:
            await interaction.response.send_message(f"❌ 오류 발생: {e}", ephemeral=True)

class DiscordBot(commands.Bot):
    """
    Main bot class for the Discord bot.
    Handles initialization, event handling, and command processing.
    """
    
    def __init__(self):
        # Set up intents (permissions)
        intents = discord.Intents.all()
        
        # Initialize the bot
        super().__init__(
            command_prefix="!",  # 사용되지 않을 프리픽스
            intents=intents,
            help_command=None  # Disable default help command
        )
        
        # Initialize database manager
        self.db = DatabaseManager()
        
        # Set up logger
        self.logger = logging.getLogger('discord_bot')
        
        # Initialize log channel (will be set in on_ready)
        self.log_channel = None
        
        # 시작 시간 설정
        self.start_time = datetime.now()
        
        # 데이터베이스 모델 초기화
        self.point_model = UserPointsModel(self.db)
        self.message_log_model = MessageLogModel(self.db)
        self.deletion_model = ScheduledDeletionModel(self.db)
        self.shop_model = ShopModel(self.db)
        self.gambling_model = GamblingModel(self.db)
        self.betting_model = BettingModel(self.db)
        
        # 메시지 쿨다운 관리
        self.message_cooldowns = {}
        
        # 슬래시 명령어 등록
        self.add_slash_commands()
        
    def add_slash_commands(self):
        """슬래시 명령어들을 추가"""
        
        # 기본 명령어
        self.add_basic_commands()
        
        # 포인트 시스템 명령어
        self.add_points_commands()
        
        # 메시지 관리 명령어
        self.add_message_commands()
        
        # 로깅 시스템 명령어
        self.add_logging_commands()
        
        # 권한 관리 명령어
        self.add_permission_commands()
        
        # 상점 명령어 - 아직 구현되지 않음
        # self.add_shop_commands()
        
        # 도박 명령어
        self.add_gambling_commands()
        
        # 베팅 명령어 - 아직 구현되지 않음
        # self.add_betting_commands()
        
        # 나머지 명령어 카테고리는 추후 구현
        
    # 이벤트 핸들러
    async def setup_hook(self):
        """
        Called when the bot is starting up.
        Only handles database initialization.
        """
        self.logger.info("🚀 Bot setup_hook started...")
        
        # Initialize database only
        try:
            await self.db.initialize()
            self.logger.info("✅ Database initialized successfully")
        except Exception as e:
            self.logger.error(f"❌ Failed to initialize database: {e}")
            # Don't pass here, let the error propagate if it's critical
        
        self.logger.info("✅ Setup hook completed")
    
    async def on_ready(self):
        """Called when the bot is ready and connected to Discord"""
        try:
            # 기본 정보 출력
            self.logger.info(f"🤖 Logged in as {self.user.name}#{self.user.discriminator} (ID: {self.user.id})")
            self.logger.info(f"🌐 Connected to {len(self.guilds)} guilds")
            
            # 중복 실행 방지
            if hasattr(self, '_ready_executed'):
                self.logger.info("⚠️ on_ready already executed, skipping...")
                return
            self._ready_executed = True
            
            # 로그 채널 설정
            if not self.log_channel:
                for guild in self.guilds:
                    log_channel = discord.utils.get(guild.channels, name="log")
                    if log_channel:
                        self.log_channel = log_channel
                        self.logger.info(f"📝 Log channel set to #{log_channel.name}")
                        break
            
            # 슬래시 명령어 동기화 (한 번만 실행)
            if not hasattr(self, '_commands_synced') or not self._commands_synced:
                try:
                    # 등록된 명령어 로깅
                    all_commands = self.tree.get_commands()
                    self.logger.info(f"📋 Total slash commands registered: {len(all_commands)}")
                    
                    for cmd in all_commands:
                        self.logger.info(f"  ✓ /{cmd.name} - {cmd.description}")
                    
                    # 길드별 동기화
                    for guild in self.guilds:
                        try:
                            synced_guild = await self.tree.sync(guild=discord.Object(id=guild.id))
                            self.logger.info(f"✅ Synced {len(synced_guild)} slash commands to guild {guild.name} ({guild.id})")
                        except Exception as e:
                            self.logger.error(f"❌ Failed to sync commands to guild {guild.name}: {e}")
                    
                    self._commands_synced = True
                # Log the sync status
                    self.logger.info("🎉 Command synchronization completed successfully")
                    
                except Exception as e:
                    self.logger.error(f"❌ Command sync error: {e}", exc_info=True)
            
            # 백그라운드 작업 시작 (한 번만 실행)
            if not hasattr(self, '_tasks_started') or not self._tasks_started:
                try:
                    # 예약 삭제 체커 시작 - 이 부분 주석 처리
                    # if hasattr(self, 'deletion_checker') and not self.deletion_checker.is_running():
                    #     self.deletion_checker.start()
                    #     self.logger.info("🔄 Background tasks started successfully")
                    
                    self._tasks_started = True
                    
                except Exception as e:
                    self.logger.error(f"❌ Failed to start background tasks: {e}")
            
            self.logger.info("✅ Bot is ready and all systems are operational!")
            
        except Exception as e:
            self.logger.error(f"❌ Error in on_ready: {e}", exc_info=True)
    
    # 두 번째 on_ready 메서드는 완전히 제거하거나 이름을 변경하세요
    # 예를 들어 on_ready_secondary → on_guild_ready 등으로 변경
            
    # @deletion_checker.before_loop 부분 주석 처리
    # async def before_deletion_checker(self):
    #     """삭제 확인 태스크 시작 전 준비"""
    #     await self.wait_until_ready()
    
    async def process_scheduled_deletion(self, deletion):
        """예약된 삭제 처리"""
        try:
            message_id = deletion['message_id']
            channel_id = deletion['channel_id']
            requester_id = deletion['requester_id']
            reason = deletion['reason']
            
            # Get the channel
            channel = self.get_channel(channel_id)
            if not channel:
                self.logger.warning(f"Channel {channel_id} not found for scheduled deletion {message_id}")
                await self.deletion_model.remove_scheduled_deletion(message_id)
                return
                
            # Get the message
            try:
                message = await channel.fetch_message(message_id)
            except discord.NotFound:
                self.logger.warning(f"Message {message_id} not found for scheduled deletion")
                await self.deletion_model.remove_scheduled_deletion(message_id)
                return
                
            # Delete the message
            try:
                await message.delete()
                self.logger.info(f"✅ Scheduled deletion executed for message {message_id}")
                
                # Remove from database
                await self.deletion_model.remove_scheduled_deletion(message_id)
                
                # Log the deletion
                if self.log_channel:
                    requester = self.get_user(requester_id)
                    requester_name = requester.display_name if requester else f"Unknown User ({requester_id})"
                    
                    embed = discord.Embed(
                        title="🗑️ 예약 삭제 실행",
                        description=f"메시지가 예약된 시간에 삭제되었습니다.",
                        color=discord.Color.orange(),
                        timestamp=datetime.now()
                    )
                    embed.add_field(name="채널", value=f"<#{channel_id}>", inline=True)
                    embed.add_field(name="메시지 ID", value=message_id, inline=True)
                    embed.add_field(name="삭제자", value=requester_name, inline=True)
                    embed.add_field(name="사유", value=reason, inline=False)
                    
                    await self.log_channel.send(embed=embed)
                    
            except discord.Forbidden:
                self.logger.error(f"❌ No permission to delete message {message_id}")
                await self.deletion_model.remove_scheduled_deletion(message_id)
            except Exception as e:
                self.logger.error(f"❌ Error deleting message {message_id}: {e}")
                
        except Exception as e:
            self.logger.error(f"❌ Error processing scheduled deletion: {e}")

    # 이 메서드는 원래 @tasks.loop(minutes=1)로 데코레이트 되어야 하지만 현재는 주석 처리
    # async def check_scheduled_deletions(self):
    #     """예약된 삭제 작업 확인"""
    #     try:
    #         # Get all scheduled deletions that are due
    #         current_time = datetime.now()
    #         deletions = await self.deletion_model.get_due_deletions(current_time)
    #         
    #         if deletions:
    #             self.logger.info(f"Found {len(deletions)} scheduled deletions to process")
    #             
    #             for deletion in deletions:
    #                 await self.process_scheduled_deletion(deletion)
    #                 
    #     except Exception as e:
    #         self.logger.error(f"❌ Error checking scheduled deletions: {e}")

async def main():
    """Main entry point for the bot."""
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s:%(levelname)s:%(name)s: %(message)s',
        handlers=[
            logging.StreamHandler()
        ]
    )
    
    # Validate settings
    try:
        Settings.validate_settings()
    except ValueError as e:
        logging.error(f"Settings validation failed: {e}")
        return
        
    # Create and run bot
    bot = DiscordBot()
    
    try:
        await bot.start(Settings.DISCORD_TOKEN)
    except discord.errors.LoginFailure:
        logging.error("Invalid Discord token. Please check your .env file.")
    except Exception as e:
        logging.error(f"Error starting bot: {e}")
    finally:
        await bot.close()

if __name__ == "__main__":
    # Run the bot
    asyncio.run(main())