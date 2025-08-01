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

# UI 컴포넌트 클래스 (베팅 등에 사용)
class BettingView(discord.ui.View):
    """베팅 UI 컴포넌트"""
    def __init__(self, betting_model, point_model, event_id, options, timeout=600):
        super().__init__(timeout=timeout)
        self.betting_model = betting_model
        self.point_model = point_model
        self.event_id = event_id
        self.options = options
        
        # 각 옵션에 대한 버튼 추가
        for option in options:
            button = discord.ui.Button(
                label=option['name'], 
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
                option,
                title=f"{option['name']}에 베팅"
            )
            await interaction.response.send_modal(modal)
        return callback

class BettingModal(discord.ui.Modal):
    """베팅 금액 입력 모달"""
    def __init__(self, betting_model, point_model, event_id, option, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.betting_model = betting_model
        self.point_model = point_model
        self.event_id = event_id
        self.option = option
        
        # 베팅 금액 입력 필드 추가
        self.amount_input = discord.ui.TextInput(
            label="베팅 금액",
            placeholder="베팅할 포인트 금액을 입력하세요",
            required=True,
            min_length=1,
            max_length=10
        )
        self.add_item(self.amount_input)
    
    async def on_submit(self, interaction):
        """모달 제출 시 처리"""
        # 입력값 검증
        try:
            amount = int(self.amount_input.value)
            if amount <= 0:
                raise ValueError("베팅 금액은 양수여야 합니다.")
        except ValueError as e:
            await interaction.response.send_message(f"❌ 잘못된 입력: {e}", ephemeral=True)
            return
        
        # 사용자 포인트 확인
        user_points = await self.point_model.get_user_points(interaction.user.id)
        if not user_points or user_points['points'] < amount:
            await interaction.response.send_message("❌ 포인트가 부족합니다.", ephemeral=True)
            return
        
        # 베팅 이벤트 상태 확인
        event = await self.betting_model.get_event(self.event_id)
        if not event or event['status'] != 'open':
            await interaction.response.send_message("❌ 이 베팅은 더 이상 참여할 수 없습니다.", ephemeral=True)
            return
        
        # 베팅 처리
        success = await self.betting_model.place_bet(
            user_id=interaction.user.id,
            username=str(interaction.user),
            event_id=self.event_id,
            option_id=self.option['id'],
            amount=amount
        )
        
        if success:
            # 포인트 차감
            await self.point_model.remove_points(
                user_id=interaction.user.id,
                amount=amount,
                reason=f"베팅: {event['title']} - {self.option['name']}"
            )
            
            # 성공 메시지
            embed = discord.Embed(
                title="✅ 베팅 완료",
                description=f"{self.option['name']}에 {amount:,} 포인트를 베팅했습니다.",
                color=discord.Color.green()
            )
            embed.add_field(name="이벤트", value=event['title'], inline=False)
            embed.add_field(name="배당률", value=f"{self.option['odds']}배", inline=True)
            embed.add_field(name="최대 획득 가능", value=f"{int(amount * self.option['odds']):,} 포인트", inline=True)
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message("❌ 베팅 처리 중 오류가 발생했습니다.", ephemeral=True)

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
        
        # 상점 명령어
        self.add_shop_commands()
        
        # 도박 명령어
        self.add_gambling_commands()
        
        # 베팅 명령어
        self.add_betting_commands()
        
        # 나머지 명령어 카테고리는 추후 구현
        
    def add_basic_commands(self):
        """기본 명령어 추가"""
        
        @self.tree.command(name="도움말", description="봇의 명령어 도움말을 표시합니다")
        @app_commands.describe(명령어="도움말을 볼 특정 명령어 (선택사항)")
        async def slash_help(interaction: discord.Interaction, 명령어: str = None):
            """슬래시 명령어 버전의 도움말"""
            await self.send_help_embed(interaction, 명령어)
            
        @self.tree.command(name="핑", description="봇의 지연 시간을 확인합니다")
        async def slash_ping(interaction: discord.Interaction):
            """봇의 지연 시간 확인"""
            await interaction.response.defer()
            
            start_time = datetime.now()
            await interaction.followup.send("핑 측정 중...")
            end_time = datetime.now()
            
            # Calculate latencies
            api_latency = round(self.latency * 1000)
            bot_latency = round((end_time - start_time).total_seconds() * 1000)
            
            embed = discord.Embed(
                title="🏓 퐁!",
                color=discord.Color.green()
            )
            embed.add_field(name="API 지연 시간", value=f"{api_latency}ms", inline=True)
            embed.add_field(name="봇 지연 시간", value=f"{bot_latency}ms", inline=True)
            
            await interaction.edit_original_response(content=None, embed=embed)
            
        @self.tree.command(name="정보", description="봇의 정보를 표시합니다")
        async def slash_info(interaction: discord.Interaction):
            """봇 정보 표시"""
            await self.send_bot_info(interaction)
            
        @self.tree.command(name="상태", description="봇의 현재 상태를 표시합니다")
        async def slash_status(interaction: discord.Interaction):
            """봇 상태 표시"""
            await self.send_status_info(interaction)
            
        @self.tree.command(name="서버정보", description="현재 서버의 정보를 표시합니다")
        async def slash_serverinfo(interaction: discord.Interaction):
            """서버 정보 표시"""
            guild = interaction.guild
            if not guild:
                await interaction.response.send_message("❌ 이 명령어는 서버에서만 사용할 수 있습니다.", ephemeral=True)
                return
                
            embed = discord.Embed(
                title=f"🏰 {guild.name} 정보",
                color=discord.Color.blue(),
                timestamp=datetime.now()
            )
            
            embed.add_field(name="서버 ID", value=guild.id, inline=True)
            embed.add_field(name="멤버 수", value=guild.member_count, inline=True)
            embed.add_field(name="생성일", value=guild.created_at.strftime("%Y년 %m월 %d일"), inline=True)
            embed.add_field(name="채널 수", value=len(guild.channels), inline=True)
            embed.add_field(name="역할 수", value=len(guild.roles), inline=True)
            embed.add_field(name="부스트 레벨", value=guild.premium_tier, inline=True)
            
            if guild.owner:
                embed.add_field(name="서버 소유자", value=guild.owner.mention, inline=True)
            
            if guild.icon:
                embed.set_thumbnail(url=guild.icon.url)
                
            await interaction.response.send_message(embed=embed)
            
        @self.tree.command(name="유저정보", description="사용자 정보를 표시합니다")
        @app_commands.describe(사용자="정보를 볼 사용자 (선택사항, 기본값: 자신)")
        async def slash_userinfo(interaction: discord.Interaction, 사용자: discord.Member = None):
            """사용자 정보 표시"""
            target = 사용자 or interaction.user
            
            embed = discord.Embed(
                title=f"👤 {target.display_name} 정보",
                color=target.color if hasattr(target, 'color') else discord.Color.blue(),
                timestamp=datetime.now()
            )
            
            embed.add_field(name="사용자명", value=f"{target.name}#{target.discriminator}", inline=True)
            embed.add_field(name="ID", value=target.id, inline=True)
            embed.add_field(name="계정 생성일", value=target.created_at.strftime("%Y년 %m월 %d일"), inline=True)
            
            if hasattr(target, 'joined_at') and target.joined_at:
                embed.add_field(name="서버 참가일", value=target.joined_at.strftime("%Y년 %m월 %d일"), inline=True)
            
            if hasattr(target, 'roles') and len(target.roles) > 1:
                roles = [role.mention for role in target.roles[1:]]  # @everyone 제외
                if roles:
                    role_text = ", ".join(roles[:5])
                    if len(roles) > 5:
                        role_text += f" 외 {len(roles) - 5}개"
                    embed.add_field(name="역할", value=role_text, inline=False)
            
            if target.avatar:
                embed.set_thumbnail(url=target.avatar.url)
                
            await interaction.response.send_message(embed=embed)
            
        @self.tree.command(name="동기화", description="[관리자] 슬래시 명령어를 동기화합니다")
        @app_commands.describe(
            범위="동기화 범위 선택",
            강제="기존 명령어를 강제로 덮어쓸지 여부"
        )
        @app_commands.choices(범위=[
            app_commands.Choice(name="현재 서버만", value="guild"),
            app_commands.Choice(name="모든 서버 (글로벌)", value="global"),
            app_commands.Choice(name="현재 서버 초기화", value="clear_guild"),
            app_commands.Choice(name="글로벌 초기화", value="clear_global"),
            app_commands.Choice(name="전체 동기화 (서버+글로벌)", value="full_sync")
        ])
        async def slash_sync(interaction: discord.Interaction, 범위: app_commands.Choice[str], 강제: bool = False):
            """슬래시 명령어 동기화 (관리자 전용)"""
            # 권한 확인
            if not await self.is_admin_user(interaction.user):
                await interaction.response.send_message("❌ 이 명령어는 관리자만 사용할 수 있습니다.", ephemeral=True)
                return
                
            await interaction.response.defer()
            
            try:
                if 범위.value == "guild":
                    # 현재 서버에만 동기화
                    if interaction.guild:
                        if 강제:
                            self.tree.clear_commands(guild=interaction.guild)
                        synced = await self.tree.sync(guild=interaction.guild)
                        status_embed = discord.Embed(
                            title="⏳ 명령어 동기화 중...",
                            description="슬래시 명령어를 동기화하고 있습니다. 잠시 기다려주세요...",
                            color=discord.Color.orange(),
                            timestamp=datetime.now()
                        )
                        status_embed.add_field(name="동기화 범위", value=scope.upper(), inline=True)
                        status_embed.add_field(name="등록된 명령어 수", value=len(self.tree.get_commands()), inline=True)
                        
                        status_message = await ctx.send(embed=status_embed)
                        
                        try:
                            synced_guild = []
                            synced_global = []
                            
                            if scope.lower() == "clear":
                                # 현재 서버의 모든 명령어 삭제
                                self.tree.clear_commands(guild=discord.Object(id=ctx.guild.id))
                                await self.tree.sync(guild=discord.Object(id=ctx.guild.id))
                                
                                # 명령어 다시 추가
                                self.add_slash_commands()
                                
                                # 서버 동기화
                                synced_guild = await self.tree.sync(guild=discord.Object(id=ctx.guild.id))
                                
                                result_embed = discord.Embed(
                                    title="✅ 명령어 초기화 및 동기화 완료",
                                    description="모든 명령어를 삭제하고 다시 동기화했습니다.",
                                    color=discord.Color.green(),
                                    timestamp=datetime.now()
                                )
                                result_embed.add_field(name="서버 동기화", value=f"{len(synced_guild)}개 명령어", inline=True)
                                
                            elif scope.lower() == "guild":
                                # 현재 서버에만 동기화
                                guild = discord.Object(id=ctx.guild.id)
                                synced_guild = await self.tree.sync(guild=guild)
                                
                                result_embed = discord.Embed(
                                    title="✅ 서버 명령어 동기화 완료",
                                    description=f"{ctx.guild.name} 서버에 슬래시 명령어가 동기화되었습니다.",
                                    color=discord.Color.green(),
                                    timestamp=datetime.now()
                                )
                                result_embed.add_field(name="동기화된 명령어", value=f"{len(synced_guild)}개", inline=True)
                                result_embed.set_footer(text="서버 동기화는 즉시 적용됩니다.")
                                
                            elif scope.lower() == "global":
                                # 전역 동기화만
                                synced_global = await self.tree.sync()
                                
                                result_embed = discord.Embed(
                                    title="✅ 전역 명령어 동기화 완료",
                                    description="모든 서버에 슬래시 명령어가 동기화되었습니다.",
                                    color=discord.Color.blue(),
                                    timestamp=datetime.now()
                                )
                                result_embed.add_field(name="동기화된 명령어", value=f"{len(synced_global)}개", inline=True)
                                result_embed.set_footer(text="전역 동기화는 최대 1시간이 걸릴 수 있습니다.")
                                
                            elif scope.lower() == "both":
                                # 서버 + 전역 동기화
                                guild = discord.Object(id=ctx.guild.id)
                                synced_guild = await self.tree.sync(guild=guild)
                                synced_global = await self.tree.sync()
                                
                                result_embed = discord.Embed(
                                    title="✅ 전체 명령어 동기화 완료",
                                    description="서버와 전역 모두에 슬래시 명령어가 동기화되었습니다.",
                                    color=discord.Color.green(),
                                    timestamp=datetime.now()
                                )
                                result_embed.add_field(name="서버 동기화", value=f"{len(synced_guild)}개 명령어", inline=True)
                                result_embed.add_field(name="전역 동기화", value=f"{len(synced_global)}개 명령어", inline=True)
                                result_embed.set_footer(text="서버 동기화는 즉시, 전역 동기화는 최대 1시간이 걸릴 수 있습니다.")
                                
                            else:
                                # 잘못된 범위
                                result_embed = discord.Embed(
                                    title="❌ 잘못된 동기화 범위",
                                    description="올바른 범위를 선택해주세요:",
                                    color=discord.Color.red()
                                )
                                result_embed.add_field(
                                    name="사용 가능한 범위",
                                    value="`guild` - 현재 서버만\n`global` - 전역 동기화\n`both` - 서버 + 전역\n`clear` - 초기화 후 재동기화",
                                    inline=False
                                )
                                await status_message.edit(embed=result_embed)
                                return
                            
                            # 동기화된 명령어 목록 추가
                            if synced_guild or synced_global:
                                commands_list = []
                                all_commands = synced_guild if synced_guild else synced_global
                                
                                for cmd in all_commands[:10]:  # 처음 10개만 표시
                                    commands_list.append(f"• `/{cmd.name}` - {cmd.description[:50]}{'...' if len(cmd.description) > 50 else ''}")
                                
                                if commands_list:
                                    result_embed.add_field(
                                        name=f"동기화된 명령어 목록 {'(처음 10개)' if len(all_commands) > 10 else ''}",
                                        value="\n".join(commands_list),
                                        inline=False
                                    )
                                
                                if len(all_commands) > 10:
                                    result_embed.add_field(
                                        name="추가 정보",
                                        value=f"총 {len(all_commands)}개 명령어가 동기화되었습니다.",
                                        inline=False
                                    )
                            
                            await status_message.edit(embed=result_embed)
                            
                            # 로그 채널에 기록
                            if hasattr(self, 'log_channel') and self.log_channel:
                                log_embed = discord.Embed(
                                    title="🔄 명령어 동기화",
                                    description=f"{ctx.author.mention}님이 슬래시 명령어를 동기화했습니다.",
                                    color=discord.Color.blue(),
                                    timestamp=datetime.now()
                                )
                                log_embed.add_field(name="동기화 범위", value=scope.upper(), inline=True)
                                log_embed.add_field(name="서버", value=ctx.guild.name, inline=True)
                                
                                if synced_guild:
                                    log_embed.add_field(name="서버 동기화", value=f"{len(synced_guild)}개", inline=True)
                                if synced_global:
                                    log_embed.add_field(name="전역 동기화", value=f"{len(synced_global)}개", inline=True)
                                
            # 로그 채널에 기록
                                await self.log_channel.send(embed=log_embed)
                            
                        except Exception as e:
                            error_embed = discord.Embed(
                                title="❌ 동기화 실패",
                                description="명령어 동기화 중 오류가 발생했습니다.",
                                color=discord.Color.red(),
                                timestamp=datetime.now()
                            )
                            error_embed.add_field(name="오류 내용", value=f"```{str(e)[:1000]}```", inline=False)
                            error_embed.add_field(
                                name="해결 방법",
                                value="• 봇에 슬래시 명령어 권한이 있는지 확인\n• 잠시 후 다시 시도\n• 관리자에게 문의",
                                inline=False
                            )
                            
                            await status_message.edit(embed=error_embed)
                            self.logger.error(f"Command sync failed: {e}", exc_info=True)
                    
                    @sync_commands.error
                    async def sync_commands_error(ctx, error):
                        """Handle sync command errors"""
                        if isinstance(error, commands.MissingPermissions):
                            embed = discord.Embed(
                                title="❌ 권한 부족",
                                description="이 명령어는 관리자만 사용할 수 있습니다.",
                                color=discord.Color.red()
                            )
                            await ctx.send(embed=embed)
                        else:
                            embed = discord.Embed(
                                title="❌ 오류 발생",
                                description=f"명령어 실행 중 오류가 발생했습니다: {str(error)}",
                                color=discord.Color.red()
                            )
                            await ctx.send(embed=embed)
                    
                    @self.command(name="명령어목록", aliases=["commands", "cmdlist"])
                    @commands.has_permissions(administrator=True)
                    async def list_commands(ctx):
                        """등록된 슬래시 명령어 목록을 보여줍니다."""
                        try:
                            await ctx.message.delete()
                        except:
                            pass
                        
                        all_commands = self.tree.get_commands()
                        
                        if not all_commands:
                            embed = discord.Embed(
                                title="📋 명령어 목록",
                                description="등록된 슬래시 명령어가 없습니다.",
                                color=discord.Color.orange()
                            )
                            await ctx.send(embed=embed)
                            return
                        
                        # 명령어를 카테고리별로 분류
                        categories = {}
                        for cmd in all_commands:
                            # 명령어 이름으로 카테고리 추정
                            if any(keyword in cmd.name for keyword in ['포인트', 'point']):
                                category = '💰 포인트'
                            elif any(keyword in cmd.name for keyword in ['베팅', 'bet']):
                                category = '🎲 베팅'
                            elif any(keyword in cmd.name for keyword in ['상점', 'shop']):
                                category = '🛒 상점'
                            elif any(keyword in cmd.name for keyword in ['도박', 'gamble', '상자']):
                                category = '🎰 도박'
                            elif any(keyword in cmd.name for keyword in ['삭제', 'delete', '청소', 'purge']):
                                category = '🧹 관리'
                            elif any(keyword in cmd.name for keyword in ['로그', 'log']):
                                category = '📝 로깅'
                            else:
                                category = '🔧 기타'
                            
                            if category not in categories:
                                categories[category] = []
                            categories[category].append(cmd)
                        
            # 임베드 생성
                        embed = discord.Embed(
                            title="📋 등록된 슬래시 명령어 목록",
                            description=f"총 {len(all_commands)}개의 명령어가 등록되어 있습니다.",
                            color=discord.Color.blue(),
                            timestamp=datetime.now()
                        )
                        
                        for category, commands in categories.items():
                            command_list = []
            # 이벤트 정보 추가
                            for cmd in commands:
                                description = cmd.description[:40] + '...' if len(cmd.description) > 40 else cmd.description
                                command_list.append(f"`/{cmd.name}` - {description}")
                            
                            embed.add_field(
                                name=f"{category} ({len(commands)}개)",
                                value="\n".join(command_list),
                                inline=False
                            )
                        
                        embed.set_footer(text="명령어를 사용하려면 Discord에서 '/'를 입력하세요.")
                        await ctx.send(embed=embed)
            
        @self.tree.command(name="베팅하기", description="베팅 이벤트에 포인트를 걸어 베팅합니다")
        @app_commands.describe(
            이벤트_아이디="베팅할 이벤트 ID",
            옵션번호="베팅할 옵션 번호",
            포인트="베팅할 포인트 수량"
        )
        async def slash_place_bet(interaction: discord.Interaction, 이벤트_아이디: str, 옵션번호: int, 포인트: int):
            """베팅하기"""
            # 포인트 검증
            if 포인트 <= 0:
                await interaction.response.send_message("❌ 베팅 포인트는 양수여야 합니다.", ephemeral=True)
                return
                
            # 사용자 포인트 확인
            user_points = await self.point_model.get_user_points(interaction.user.id)
            if not user_points or user_points['points'] < 포인트:
                await interaction.response.send_message("❌ 포인트가 부족합니다.", ephemeral=True)
                return
                
            # 이벤트 존재 확인
            event = await self.betting_model.get_betting_event(이벤트_아이디)
            if not event:
                await interaction.response.send_message(f"❌ ID가 '{이벤트_아이디}'인 베팅 이벤트를 찾을 수 없습니다.", ephemeral=True)
                return
                
            # 이벤트 마감 확인
            if event['end_time'] < datetime.now():
                await interaction.response.send_message("❌ 이 베팅 이벤트는 이미 마감되었습니다.", ephemeral=True)
                return
                
            # 이벤트 결과 확인
            if event['result_option_id'] is not None:
                await interaction.response.send_message("❌ 이 베팅 이벤트는 이미 결과가 발표되었습니다.", ephemeral=True)
                return
                
            # 옵션 존재 확인
            options = await self.betting_model.get_betting_options(이벤트_아이디)
            if not options or 옵션번호 < 1 or 옵션번호 > len(options):
                await interaction.response.send_message(f"❌ 옵션 번호는 1에서 {len(options) if options else 0} 사이여야 합니다.", ephemeral=True)
                return
                
            selected_option = options[옵션번호 - 1]
            
            # 이미 베팅했는지 확인
            existing_bet = await self.betting_model.get_user_bet(이벤트_아이디, interaction.user.id)
            if existing_bet:
                await interaction.response.send_message(f"❌ 이미 이 이벤트에 베팅했습니다. (옵션: {existing_bet['option_text']}, 포인트: {existing_bet['points']})", ephemeral=True)
                return
                
            # 포인트 차감
            success, message = await self.point_model.remove_points(
                user_id=interaction.user.id,
                amount=포인트,
                reason=f"베팅: {event['title']} - {selected_option['option_text']}"
            )
            
            if not success:
                await interaction.response.send_message(f"❌ 포인트 차감 실패: {message}", ephemeral=True)
                return
                
            # 베팅 등록
            bet_id = await self.betting_model.place_bet(
                event_id=이벤트_아이디,
                option_id=selected_option['id'],
                user_id=interaction.user.id,
                username=str(interaction.user),
                points=포인트
            )
            
            if not bet_id:
                # 베팅 실패 시 포인트 환불
                await self.point_model.add_points(
                    user_id=interaction.user.id,
                    username=str(interaction.user),
                    amount=포인트,
                    reason=f"베팅 실패 환불: {event['title']}"
                )
                
                await interaction.response.send_message("❌ 베팅 등록에 실패했습니다. 포인트가 환불되었습니다.", ephemeral=True)
                return
                
            # 성공 메시지
            embed = discord.Embed(
                title="✅ 베팅 완료",
                description=f"**{event['title']}** 이벤트에 베팅했습니다.",
                color=discord.Color.green()
            )
            
            embed.add_field(name="선택 옵션", value=selected_option['option_text'], inline=True)
            embed.add_field(name="베팅 포인트", value=f"{포인트:,} 포인트", inline=True)
            embed.add_field(name="남은 포인트", value=f"{user_points['points'] - 포인트:,} 포인트", inline=True)
            embed.add_field(name="마감 시간", value=event['end_time'].strftime("%Y-%m-%d %H:%M:%S"), inline=True)
            
            await interaction.response.send_message(embed=embed)
            
        @self.tree.command(name="베팅결과", description="[관리자] 베팅 이벤트의 결과를 발표합니다")
        @app_commands.describe(
            이벤트_아이디="결과를 발표할 이벤트 ID",
            당첨옵션="당첨된 옵션 번호"
        )
        async def slash_resolve_betting(interaction: discord.Interaction, 이벤트_아이디: str, 당첨옵션: int):
            """베팅 결과 발표"""
            # 권한 확인
            if not await self.is_admin_user(interaction.user):
                await interaction.response.send_message("❌ 이 명령어는 관리자만 사용할 수 있습니다.", ephemeral=True)
                return
                
            # 이벤트 존재 확인
            event = await self.betting_model.get_betting_event(이벤트_아이디)
            if not event:
                await interaction.response.send_message(f"❌ ID가 '{이벤트_아이디}'인 베팅 이벤트를 찾을 수 없습니다.", ephemeral=True)
                return
                
            # 이벤트 결과 확인
            if event['result_option_id'] is not None:
                await interaction.response.send_message("❌ 이 베팅 이벤트는 이미 결과가 발표되었습니다.", ephemeral=True)
                return
                
            # 옵션 존재 확인
            options = await self.betting_model.get_betting_options(이벤트_아이디)
            if not options or 당첨옵션 < 1 or 당첨옵션 > len(options):
                await interaction.response.send_message(f"❌ 옵션 번호는 1에서 {len(options) if options else 0} 사이여야 합니다.", ephemeral=True)
                return
                
            winning_option = options[당첨옵션 - 1]
            
            # 베팅 결과 처리
            await interaction.response.defer()
            
            result = await self.betting_model.resolve_betting_event(
                event_id=이벤트_아이디,
                winning_option_id=winning_option['id'],
                resolved_by=interaction.user.id
            )
            
            if not result:
                await interaction.followup.send("❌ 베팅 결과 처리에 실패했습니다.")
                return
                
            # 당첨자 보상 지급
            winners = result['winners']
            total_bet_points = result['total_points']
            winning_points = result['winning_points']
            
            # 성공 메시지
            embed = discord.Embed(
                title="🏆 베팅 결과 발표",
                description=f"**{event['title']}** 이벤트의 결과가 발표되었습니다.",
                color=discord.Color.gold()
            )
            
            embed.add_field(name="당첨 옵션", value=winning_option['option_text'], inline=False)
            embed.add_field(name="총 베팅 포인트", value=f"{total_bet_points:,} 포인트", inline=True)
            embed.add_field(name="당첨 옵션 베팅 포인트", value=f"{winning_points:,} 포인트", inline=True)
            embed.add_field(name="당첨자 수", value=f"{len(winners)}명", inline=True)
            
            # 당첨자 목록
            if winners:
                winner_text = ""
                for winner in winners[:10]:  # 최대 10명까지만 표시
                    user_id = winner['user_id']
                    bet_points = winner['points']
                    reward_points = winner['reward']
                    
                    user = interaction.guild.get_member(user_id)
                    user_name = user.mention if user else f"ID: {user_id}"
                    
                    winner_text += f"{user_name}: {bet_points:,} → {reward_points:,} 포인트 (+{reward_points - bet_points:,})\n"
                    
                if len(winners) > 10:
                    winner_text += f"*외 {len(winners) - 10}명...*"
                    
                embed.add_field(name="🏆 당첨자", value=winner_text, inline=False)
            
            await interaction.followup.send(embed=embed)
            
            # 로그 채널에 기록
            if hasattr(self, 'log_channel') and self.log_channel:
                log_embed = discord.Embed(
                    title="🎲 베팅 이벤트 결과",
                    description=f"{interaction.user.mention}님이 베팅 이벤트 결과를 발표했습니다.",
                    color=discord.Color.gold(),
                    timestamp=datetime.now()
                )
                log_embed.add_field(name="이벤트", value=event['title'], inline=True)
                log_embed.add_field(name="이벤트 ID", value=이벤트_아이디, inline=True)
                log_embed.add_field(name="당첨 옵션", value=winning_option['option_text'], inline=True)
                log_embed.add_field(name="당첨자 수", value=f"{len(winners)}명", inline=True)
                log_embed.add_field(name="총 지급 포인트", value=f"{sum(w['reward'] for w in winners):,} 포인트", inline=True)
                
                await self.log_channel.send(embed=log_embed)
    
    def add_gambling_commands(self):
        """도박 명령어 추가"""
        
        # 관리자 명령어
        @self.tree.command(name="룻박스관리", description="[관리자] 룻박스 관리 메뉴를 표시합니다")
        async def slash_lootbox_admin(interaction: discord.Interaction):
            """룻박스 관리 메뉴"""
            # 권한 확인
            if not await self.is_admin_user(interaction.user):
                await interaction.response.send_message("❌ 이 명령어는 관리자만 사용할 수 있습니다.", ephemeral=True)
                return
                
            # 룻박스 정보 가져오기
            lootboxes = await self.gambling_model.get_lootboxes()
            
            # 임베드 생성
            embed = discord.Embed(
                title="🎁 룻박스 관리 메뉴",
                description="룻박스 관리를 위한 명령어 목록입니다.",
                color=discord.Color.blue()
            )
            
            # 명령어 설명
            embed.add_field(
                name="룻박스 추가",
                value="`/박스추가 이름 가격 설명` - 새 룻박스를 추가합니다.",
                inline=False
            )
            
            embed.add_field(
                name="룻박스 제거",
                value="`/박스제거 이름` - 기존 룻박스를 제거합니다.",
                inline=False
            )
            
            embed.add_field(
                name="보상 추가",
                value="`/보상추가 룻박스명 보상유형 보상값 확률 설명` - 룻박스에 보상을 추가합니다.",
                inline=False
            )
            
            embed.add_field(
                name="보상 제거",
                value="`/보상제거 룻박스명 보상ID` - 룻박스에서 보상을 제거합니다.",
                inline=False
            )
            
            # 현재 룻박스 목록
            if lootboxes:
                box_list = "\n".join([f"• {box['name']} - {box['price']:,} 포인트" for box in lootboxes])
                embed.add_field(
                    name="현재 룻박스 목록",
                    value=box_list,
                    inline=False
                )
            else:
                embed.add_field(
                    name="현재 룻박스 목록",
                    value="없음",
                    inline=False
                )
                
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        @self.tree.command(name="박스추가", description="[관리자] 새 룻박스를 추가합니다")
        @app_commands.describe(
            이름="룻박스 이름",
            가격="룻박스 가격 (포인트)",
            설명="룻박스 설명 (선택사항)"
        )
        async def slash_add_lootbox(interaction: discord.Interaction, 이름: str, 가격: int, 설명: str = None):
            """룻박스 추가"""
            # 권한 확인
            if not await self.is_admin_user(interaction.user):
                await interaction.response.send_message("❌ 이 명령어는 관리자만 사용할 수 있습니다.", ephemeral=True)
                return
                
            # 가격 검증
            if 가격 <= 0 or 가격 > 1000000:
                await interaction.response.send_message("❌ 가격은 1에서 1,000,000 사이여야 합니다.", ephemeral=True)
                return
                
            # 이름 중복 확인
            existing_box = await self.gambling_model.get_lootbox_by_name(이름)
            if existing_box:
                await interaction.response.send_message(f"❌ '{이름}' 룻박스가 이미 존재합니다.", ephemeral=True)
                return
                
            # 룻박스 추가
            success = await self.gambling_model.add_lootbox(이름, 가격, 설명)
            
            if success:
                embed = discord.Embed(
                    title="✅ 룻박스 추가 완료",
                    description=f"'{이름}' 룻박스가 추가되었습니다.",
                    color=discord.Color.green()
                )
                embed.add_field(name="가격", value=f"{가격:,} 포인트", inline=True)
                if 설명:
                    embed.add_field(name="설명", value=설명, inline=True)
                    
                # 로그 채널에 기록
                if hasattr(self, 'log_channel') and self.log_channel:
                    log_embed = discord.Embed(
                        title="🎁 룻박스 추가",
                        description=f"{interaction.user.mention}님이 새 룻박스를 추가했습니다.",
                        color=discord.Color.blue(),
                        timestamp=datetime.now()
                    )
                    log_embed.add_field(name="이름", value=이름, inline=True)
                    log_embed.add_field(name="가격", value=f"{가격:,} 포인트", inline=True)
                    if 설명:
                        log_embed.add_field(name="설명", value=설명, inline=False)
                        
                    await self.log_channel.send(embed=log_embed)
            else:
                embed = discord.Embed(
                    title="❌ 룻박스 추가 실패",
                    description="룻박스를 추가하는 데 실패했습니다.",
                    color=discord.Color.red()
                )
                
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        @self.tree.command(name="박스제거", description="[관리자] 기존 룻박스를 제거합니다")
        @app_commands.describe(이름="제거할 룻박스 이름")
        async def slash_remove_lootbox(interaction: discord.Interaction, 이름: str):
            """룻박스 제거"""
            # 권한 확인
            if not await self.is_admin_user(interaction.user):
                await interaction.response.send_message("❌ 이 명령어는 관리자만 사용할 수 있습니다.", ephemeral=True)
                return
                
            # 룻박스 존재 확인
            box = await self.gambling_model.get_lootbox_by_name(이름)
            if not box:
                await interaction.response.send_message(f"❌ '{이름}' 룻박스는 존재하지 않습니다.", ephemeral=True)
                return
                
            # 확인 메시지
            embed = discord.Embed(
                title="⚠️ 룻박스 제거 확인",
                description=f"'{이름}' 룻박스를 정말로 제거하시겠습니까? 이 작업은 되돌릴 수 없습니다.",
                color=discord.Color.orange()
            )
            
            # 확인 버튼 생성
            class ConfirmView(discord.ui.View):
                def __init__(self, timeout=60):
                    super().__init__(timeout=timeout)
                    
                @discord.ui.button(label="제거", style=discord.ButtonStyle.red)
                async def confirm(self, button_interaction: discord.Interaction, button: discord.ui.Button):
                    # 상호작용한 사용자 확인
                    if button_interaction.user.id != interaction.user.id:
                        await button_interaction.response.send_message("❌ 자신의 작업만 확인할 수 있습니다.", ephemeral=True)
                        return
                        
                    # 룻박스 제거
                    success = await self.gambling_model.remove_lootbox(box['id'])
                    
                    if success:
                        result_embed = discord.Embed(
                            title="✅ 룻박스 제거 완료",
                            description=f"'{이름}' 룻박스가 제거되었습니다.",
                            color=discord.Color.green()
                        )
                        
                        # 로그 채널에 기록
                        if hasattr(self, 'log_channel') and self.log_channel:
                            log_embed = discord.Embed(
                                title="🗑️ 룻박스 제거",
                                description=f"{interaction.user.mention}님이 룻박스를 제거했습니다.",
                                color=discord.Color.orange(),
                                timestamp=datetime.now()
                            )
                            log_embed.add_field(name="이름", value=이름, inline=True)
                            log_embed.add_field(name="가격", value=f"{box['price']:,} 포인트", inline=True)
                            
                            await self.log_channel.send(embed=log_embed)
                    else:
                        result_embed = discord.Embed(
                            title="❌ 룻박스 제거 실패",
                            description="룻박스를 제거하는 데 실패했습니다.",
                            color=discord.Color.red()
                        )
                        
                    await button_interaction.response.edit_message(embed=result_embed, view=None)
                
                @discord.ui.button(label="취소", style=discord.ButtonStyle.grey)
                async def cancel(self, button_interaction: discord.Interaction, button: discord.ui.Button):
                    # 상호작용한 사용자 확인
                    if button_interaction.user.id != interaction.user.id:
                        await button_interaction.response.send_message("❌ 자신의 작업만 취소할 수 있습니다.", ephemeral=True)
                        return
                        
                    # 취소 메시지
                    cancel_embed = discord.Embed(
                        title="❌ 룻박스 제거 취소",
                        description="룻박스 제거가 취소되었습니다.",
                        color=discord.Color.grey()
                    )
                    
                    await button_interaction.response.edit_message(embed=cancel_embed, view=None)
            
            # 확인 메시지 전송
            await interaction.response.send_message(embed=embed, view=ConfirmView(), ephemeral=True)
            
        @self.tree.command(name="보상추가", description="[관리자] 룻박스에 보상을 추가합니다")
        @app_commands.describe(
            룻박스명="보상을 추가할 룻박스 이름",
            보상유형="보상 유형 (포인트, 역할, 기타)",
            보상값="보상 값 (포인트: 숫자, 역할: 역할ID, 기타: 텍스트)",
            확률="보상 확률 (0-100)",
            설명="보상 설명 (선택사항)"
        )
        @app_commands.choices(보상유형=[
            app_commands.Choice(name="포인트", value="포인트"),
            app_commands.Choice(name="역할", value="역할"),
            app_commands.Choice(name="기타", value="기타")
        ])
        async def slash_add_reward(
            interaction: discord.Interaction, 
            룻박스명: str, 
            보상유형: app_commands.Choice[str], 
            보상값: str, 
            확률: float, 
            설명: str = None
        ):
            """룻박스 보상 추가"""
            # 권한 확인
            if not await self.is_admin_user(interaction.user):
                await interaction.response.send_message("❌ 이 명령어는 관리자만 사용할 수 있습니다.", ephemeral=True)
                return
                
            # 확률 검증
            if 확률 <= 0 or 확률 > 100:
                await interaction.response.send_message("❌ 확률은 0보다 크고 100 이하여야 합니다.", ephemeral=True)
                return
                
            # 룻박스 존재 확인
            box = await self.gambling_model.get_lootbox_by_name(룻박스명)
            if not box:
                await interaction.response.send_message(f"❌ '{룻박스명}' 룻박스는 존재하지 않습니다.", ephemeral=True)
                return
                
            # 보상 유형 검증
            reward_type = 보상유형.value
            
            # 보상값 검증
            if reward_type == "포인트":
                try:
                    point_amount = int(보상값)
                    if point_amount <= 0:
                        await interaction.response.send_message("❌ 포인트 보상은 양수여야 합니다.", ephemeral=True)
                        return
                except ValueError:
                    await interaction.response.send_message("❌ 포인트 보상은 숫자여야 합니다.", ephemeral=True)
                    return
            elif reward_type == "역할":
                try:
                    role_id = int(보상값)
                    role = interaction.guild.get_role(role_id)
                    if not role:
                        await interaction.response.send_message("❌ 해당 ID의 역할을 찾을 수 없습니다.", ephemeral=True)
                        return
                except ValueError:
                    await interaction.response.send_message("❌ 역할 ID는 숫자여야 합니다.", ephemeral=True)
                    return
                
            # 보상 추가
            success = await self.gambling_model.add_box_reward(
                box_id=box['id'],
                reward_type=reward_type,
                reward_value=보상값,
                probability=확률,
                description=설명
            )
            
            if success:
                embed = discord.Embed(
                    title="✅ 보상 추가 완료",
                    description=f"'{룻박스명}' 룻박스에 보상이 추가되었습니다.",
                    color=discord.Color.green()
                )
                embed.add_field(name="보상 유형", value=reward_type, inline=True)
                embed.add_field(name="보상 값", value=보상값, inline=True)
                embed.add_field(name="확률", value=f"{확률}%", inline=True)
                if 설명:
                    embed.add_field(name="설명", value=설명, inline=False)
                    
                # 로그 채널에 기록
                if hasattr(self, 'log_channel') and self.log_channel:
                    log_embed = discord.Embed(
                        title="🎁 룻박스 보상 추가",
                        description=f"{interaction.user.mention}님이 룻박스에 보상을 추가했습니다.",
                        color=discord.Color.blue(),
                        timestamp=datetime.now()
                    )
                    log_embed.add_field(name="룻박스", value=룻박스명, inline=True)
                    log_embed.add_field(name="보상 유형", value=reward_type, inline=True)
                    log_embed.add_field(name="보상 값", value=보상값, inline=True)
                    log_embed.add_field(name="확률", value=f"{확률}%", inline=True)
                    if 설명:
                        log_embed.add_field(name="설명", value=설명, inline=False)
                        
                    await self.log_channel.send(embed=log_embed)
            else:
                embed = discord.Embed(
                    title="❌ 보상 추가 실패",
                    description="보상을 추가하는 데 실패했습니다.",
                    color=discord.Color.red()
                )
                
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        @self.tree.command(name="보상제거", description="[관리자] 룻박스에서 보상을 제거합니다")
        @app_commands.describe(
            룻박스명="보상을 제거할 룻박스 이름",
            보상_아이디="제거할 보상 ID"
        )
        async def slash_remove_reward(interaction: discord.Interaction, 룻박스명: str, 보상_아이디: int):
            """룻박스 보상 제거"""
            # 권한 확인
            if not await self.is_admin_user(interaction.user):
                await interaction.response.send_message("❌ 이 명령어는 관리자만 사용할 수 있습니다.", ephemeral=True)
                return
                
            # 룻박스 존재 확인
            box = await self.gambling_model.get_lootbox_by_name(룻박스명)
            if not box:
                await interaction.response.send_message(f"❌ '{룻박스명}' 룻박스는 존재하지 않습니다.", ephemeral=True)
                return
                
            # 보상 존재 확인
            reward = await self.gambling_model.get_reward_by_id(보상_아이디)
            if not reward or reward['box_id'] != box['id']:
                await interaction.response.send_message(f"❌ 해당 ID의 보상을 찾을 수 없습니다.", ephemeral=True)
                return
                
            # 보상 제거
            success = await self.gambling_model.remove_box_reward(보상_아이디)
            
            if success:
                embed = discord.Embed(
                    title="✅ 보상 제거 완료",
                    description=f"'{룻박스명}' 룻박스에서 보상이 제거되었습니다.",
                    color=discord.Color.green()
                )
                
                # 로그 채널에 기록
                if hasattr(self, 'log_channel') and self.log_channel:
                    log_embed = discord.Embed(
                        title="🗑️ 룻박스 보상 제거",
                        description=f"{interaction.user.mention}님이 룻박스에서 보상을 제거했습니다.",
                        color=discord.Color.orange(),
                        timestamp=datetime.now()
                    )
                    log_embed.add_field(name="룻박스", value=룻박스명, inline=True)
                    log_embed.add_field(name="보상 ID", value=str(보상_아이디), inline=True)
                    log_embed.add_field(name="보상 유형", value=reward['reward_type'], inline=True)
                    log_embed.add_field(name="보상 값", value=reward['reward_value'], inline=True)
                    
                    await self.log_channel.send(embed=log_embed)
            else:
                embed = discord.Embed(
                    title="❌ 보상 제거 실패",
                    description="보상을 제거하는 데 실패했습니다.",
                    color=discord.Color.red()
                )
                
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        @self.tree.command(name="보상목록", description="[관리자] 룻박스의 보상 목록을 표시합니다")
        @app_commands.describe(룻박스명="보상을 확인할 룻박스 이름")
        async def slash_list_rewards(interaction: discord.Interaction, 룻박스명: str):
            """룻박스 보상 목록"""
            # 권한 확인
            if not await self.is_admin_user(interaction.user):
                await interaction.response.send_message("❌ 이 명령어는 관리자만 사용할 수 있습니다.", ephemeral=True)
                return
                
            # 룻박스 존재 확인
            box = await self.gambling_model.get_lootbox_by_name(룻박스명)
            if not box:
                await interaction.response.send_message(f"❌ '{룻박스명}' 룻박스는 존재하지 않습니다.", ephemeral=True)
                return
                
            # 보상 목록 가져오기
            rewards = await self.gambling_model.get_box_rewards(box['id'])
            
            if not rewards:
                embed = discord.Embed(
                    title=f"🎁 {룻박스명} 보상 목록",
                    description="이 룻박스에는 보상이 없습니다.",
                    color=discord.Color.orange()
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
                
            # 임베드 생성
            embed = discord.Embed(
                title=f"🎁 {룻박스명} 보상 목록",
                description=f"가격: {box['price']:,} 포인트",
                color=discord.Color.blue()
            )
            
            # 총 확률 계산
            total_probability = sum(reward['probability'] for reward in rewards)
            embed.add_field(name="총 확률", value=f"{total_probability}%", inline=True)
            embed.add_field(name="보상 개수", value=str(len(rewards)), inline=True)
            
            # 보상 목록 추가
            for reward in rewards:
                reward_type = reward['reward_type']
                reward_value = reward['reward_value']
                probability = reward['probability']
                description = reward['description'] or "설명 없음"
                
                # 보상 표시 형식 조정
                if reward_type == "포인트" and reward_value.isdigit():
                    display_value = f"{int(reward_value):,} 포인트"
                elif reward_type == "역할":
                    try:
                        role_id = int(reward_value)
                        role = interaction.guild.get_role(role_id)
                        display_value = role.mention if role else f"역할 ID: {reward_value}"
                    except ValueError:
                        display_value = reward_value
                else:
                    display_value = reward_value
                    
                embed.add_field(
                    name=f"ID: {reward['id']} - {reward_type} ({probability}%)",
                    value=f"값: {display_value}\n설명: {description}",
                    inline=False
                )
                
            await interaction.response.send_message(embed=embed, ephemeral=True)
        
        @self.tree.command(name="룻박스", description="구매 가능한 룻박스 목록을 표시합니다")
        async def slash_lootbox(interaction: discord.Interaction):
            """룻박스 목록 표시"""
            # 룻박스 정보 가져오기
            lootboxes = await self.gambling_model.get_lootboxes()
            
            if not lootboxes:
                embed = discord.Embed(
                    title="🎁 구매 가능한 룻박스",
                    description="현재 구매 가능한 룻박스가 없습니다.",
                    color=discord.Color.orange()
                )
                await interaction.response.send_message(embed=embed)
                return
                
            # 임베드 생성
            embed = discord.Embed(
                title="🎁 구매 가능한 룻박스",
                description="포인트로 구매할 수 있는 룻박스 목록입니다.",
                color=discord.Color.blue()
            )
            
            # 룻박스 정보 추가
            for box in lootboxes:
                # 설명 추가
                description = box['description'] or "설명 없음"
                
                # 보상 정보 가져오기
                rewards = await self.gambling_model.get_box_rewards(box['id'])
                reward_text = "없음"
                if rewards:
                    reward_types = {}
                    for reward in rewards:
                        reward_type = reward['reward_type']
                        if reward_type not in reward_types:
                            reward_types[reward_type] = 0
                        reward_types[reward_type] += 1
                    
                    reward_text = ", ".join([f"{count}개의 {reward_type}" for reward_type, count in reward_types.items()])
                
                # 필드 추가
                embed.add_field(
                    name=f"{box['name']} - {box['price']:,} 포인트",
                    value=f"설명: {description}\n보상: {reward_text}\n구매 방법: `/룻박스구매 {box['name']}`",
                    inline=False
                )
                
            await interaction.response.send_message(embed=embed)
            
        @self.tree.command(name="룻박스구매", description="룻박스를 구매합니다")
        @app_commands.describe(룻박스명="구매할 룻박스의 이름")
        async def slash_buy_lootbox(interaction: discord.Interaction, 룻박스명: str):
            """룻박스 구매"""
            # 룻박스 정보 가져오기
            box = await self.gambling_model.get_lootbox_by_name(룻박스명)
            
            if not box:
                await interaction.response.send_message(f"❌ '{룻박스명}' 룻박스는 존재하지 않습니다.", ephemeral=True)
                return
                
            # 사용자 포인트 확인
            user_points = await self.point_model.get_user_points(interaction.user.id)
            if not user_points or user_points['points'] < box['price']:
                await interaction.response.send_message(f"❌ 포인트가 부족합니다. 필요한 포인트: {box['price']:,}", ephemeral=True)
                return
                
            # 구매 확인 메시지
            embed = discord.Embed(
                title="🎁 룻박스 구매 확인",
                description=f"{box['name']} 룻박스를 {box['price']:,} 포인트에 구매하시겠습니까?",
                color=discord.Color.blue()
            )
            embed.add_field(name="현재 포인트", value=f"{user_points['points']:,} 포인트", inline=True)
            embed.add_field(name="구매 후 포인트", value=f"{user_points['points'] - box['price']:,} 포인트", inline=True)
            
            # 확인 버튼 생성
            class ConfirmView(discord.ui.View):
                def __init__(self, timeout=60):
                    super().__init__(timeout=timeout)
                    
                @discord.ui.button(label="구매", style=discord.ButtonStyle.green)
                async def confirm(self, button_interaction: discord.Interaction, button: discord.ui.Button):
                    # 상호작용한 사용자 확인
                    if button_interaction.user.id != interaction.user.id:
                        await button_interaction.response.send_message("❌ 자신의 거래만 확인할 수 있습니다.", ephemeral=True)
                        return
                        
                    # 포인트 차감
                    success, message = await self.point_model.remove_points(
                        user_id=interaction.user.id,
                        amount=box['price'],
                        reason=f"룻박스 구매: {box['name']}"
                    )
                    
                    if not success:
                        await button_interaction.response.send_message(f"❌ 포인트 차감 실패: {message}", ephemeral=True)
                        return
                        
                    # 보상 처리
                    try:
                        # 보상 선택
                        rewards = await self.gambling_model.get_box_rewards(box['id'])
                        if not rewards:
                            # 보상이 없는 경우 포인트 환불
                            await self.point_model.add_points(
                                user_id=interaction.user.id,
                                username=str(interaction.user),
                                amount=box['price'],
                                reason=f"룻박스 보상 없음 환불: {box['name']}"
                            )
                            
                            await button_interaction.response.edit_message(
                                embed=discord.Embed(
                                    title="❌ 룻박스 오류",
                                    description="이 룻박스에는 보상이 없습니다. 포인트가 환불되었습니다.",
                                    color=discord.Color.red()
                                ),
                                view=None
                            )
                            return
                            
                        # 확률에 따라 보상 선택
                        total_probability = sum(reward['probability'] for reward in rewards)
                        if total_probability <= 0:
                            # 확률이 잘못된 경우 포인트 환불
                            await self.point_model.add_points(
                                user_id=interaction.user.id,
                                username=str(interaction.user),
                                amount=box['price'],
                                reason=f"룻박스 확률 오류 환불: {box['name']}"
                            )
                            
                            await button_interaction.response.edit_message(
                                embed=discord.Embed(
                                    title="❌ 룻박스 오류",
                                    description="이 룻박스의 확률 설정에 문제가 있습니다. 포인트가 환불되었습니다.",
                                    color=discord.Color.red()
                                ),
                                view=None
                            )
                            return
                            
                        # 랜덤 값 생성 (0 ~ 총 확률)
                        rand_val = random.uniform(0, total_probability)
                        
                        # 보상 선택
                        selected_reward = None
                        current_sum = 0
                        
                        for reward in rewards:
                            current_sum += reward['probability']
                            if rand_val <= current_sum:
                                selected_reward = reward
                                break
                                
                        if not selected_reward:
                            selected_reward = rewards[-1]
                            
                        # 보상 지급
                        reward_type = selected_reward['reward_type']
                        reward_value = selected_reward['reward_value']
                        reward_description = selected_reward['description'] or "보상"
                        
                        # 보상 처리
                        if reward_type == "포인트":
                            # 포인트 보상
                            try:
                                point_amount = int(reward_value)
                                await self.point_model.add_points(
                                    user_id=interaction.user.id,
                                    username=str(interaction.user),
                                    amount=point_amount,
                                    reason=f"룻박스 보상: {box['name']}"
                                )
                                
                                # 성공 메시지
                                success_embed = discord.Embed(
                                    title="🎉 룻박스 오픈 성공!",
                                    description=f"{box['name']} 룻박스에서 보상을 획득했습니다!",
                                    color=discord.Color.gold()
                                )
                                success_embed.add_field(name="보상 유형", value="포인트", inline=True)
                                success_embed.add_field(name="획득한 포인트", value=f"{point_amount:,} 포인트", inline=True)
                                success_embed.add_field(name="설명", value=reward_description, inline=False)
                                
                                await button_interaction.response.edit_message(embed=success_embed, view=None)
                                
                            except ValueError:
                                # 포인트 값이 잘못된 경우
                                await self.point_model.add_points(
                                    user_id=interaction.user.id,
                                    username=str(interaction.user),
                                    amount=box['price'],
                                    reason=f"룻박스 보상 오류 환불: {box['name']}"
                                )
                                
                                await button_interaction.response.edit_message(
                                    embed=discord.Embed(
                                        title="❌ 룻박스 오류",
                                        description="보상 처리 중 오류가 발생했습니다. 포인트가 환불되었습니다.",
                                        color=discord.Color.red()
                                    ),
                                    view=None
                                )
                                
                        elif reward_type == "역할":
                            # 역할 보상
                            try:
                                role_id = int(reward_value)
                                role = interaction.guild.get_role(role_id)
                                
                                if not role:
                                    # 역할이 존재하지 않는 경우
                                    await self.point_model.add_points(
                                        user_id=interaction.user.id,
                                        username=str(interaction.user),
                                        amount=box['price'],
                                        reason=f"룻박스 역할 없음 환불: {box['name']}"
                                    )
                                    
                                    await button_interaction.response.edit_message(
                                        embed=discord.Embed(
                                            title="❌ 룻박스 오류",
                                            description="보상 역할을 찾을 수 없습니다. 포인트가 환불되었습니다.",
                                            color=discord.Color.red()
                                        ),
                                        view=None
                                    )
                                    return
                                    
                                # 이미 역할을 가지고 있는지 확인
                                if role in interaction.user.roles:
                                    # 이미 가지고 있는 경우 포인트로 보상
                                    compensation = box['price'] // 2
                                    await self.point_model.add_points(
                                        user_id=interaction.user.id,
                                        username=str(interaction.user),
                                        amount=compensation,
                                        reason=f"룻박스 중복 역할 보상: {box['name']}"
                                    )
                                    
                                    success_embed = discord.Embed(
                                        title="🎉 룻박스 오픈 성공!",
                                        description=f"{box['name']} 룻박스에서 이미 가지고 있는 역할이 나왔습니다!",
                                        color=discord.Color.gold()
                                    )
                                    success_embed.add_field(name="보상 유형", value="역할 (중복)", inline=True)
                                    success_embed.add_field(name="역할", value=role.mention, inline=True)
                                    success_embed.add_field(name="보상 포인트", value=f"{compensation:,} 포인트", inline=True)
                                    success_embed.add_field(name="설명", value=reward_description, inline=False)
                                    
                                    await button_interaction.response.edit_message(embed=success_embed, view=None)
                                    return
                                    
                                # 역할 부여
                                await interaction.user.add_roles(role, reason=f"룻박스 보상: {box['name']}")
                                
                                # 성공 메시지
                                success_embed = discord.Embed(
                                    title="🎉 룻박스 오픈 성공!",
                                    description=f"{box['name']} 룻박스에서 역할을 획득했습니다!",
                                    color=discord.Color.gold()
                                )
                                success_embed.add_field(name="보상 유형", value="역할", inline=True)
                                success_embed.add_field(name="획득한 역할", value=role.mention, inline=True)
                                success_embed.add_field(name="설명", value=reward_description, inline=False)
                                
                                await button_interaction.response.edit_message(embed=success_embed, view=None)
                                
                            except (ValueError, discord.Forbidden) as e:
                                # 역할 부여 실패
                                await self.point_model.add_points(
                                    user_id=interaction.user.id,
                                    username=str(interaction.user),
                                    amount=box['price'],
                                    reason=f"룻박스 역할 부여 실패 환불: {box['name']}"
                                )
                                
                                await button_interaction.response.edit_message(
                                    embed=discord.Embed(
                                        title="❌ 룻박스 오류",
                                        description=f"역할 부여 중 오류가 발생했습니다: {str(e)}. 포인트가 환불되었습니다.",
                                        color=discord.Color.red()
                                    ),
                                    view=None
                                )
                                
                        else:
                            # 기타 보상 (텍스트 보상)
                            success_embed = discord.Embed(
                                title="🎉 룻박스 오픈 성공!",
                                description=f"{box['name']} 룻박스에서 보상을 획득했습니다!",
                                color=discord.Color.gold()
                            )
                            success_embed.add_field(name="보상 유형", value=reward_type, inline=True)
                            success_embed.add_field(name="보상 내용", value=reward_value, inline=True)
                            success_embed.add_field(name="설명", value=reward_description, inline=False)
                            
                            await button_interaction.response.edit_message(embed=success_embed, view=None)
                        
                        # 로그 채널에 기록
                        if hasattr(self, 'log_channel') and self.log_channel:
                            log_embed = discord.Embed(
                                title="🎲 룻박스 보상",
                                description=f"{interaction.user.mention}님이 룻박스에서 보상을 획득했습니다.",
                                color=discord.Color.gold(),
                                timestamp=datetime.now()
                            )
                            log_embed.add_field(name="룻박스", value=box['name'], inline=True)
                            log_embed.add_field(name="보상 유형", value=reward_type, inline=True)
                            log_embed.add_field(name="보상 내용", value=reward_value, inline=True)
                            
                            await self.log_channel.send(embed=log_embed)
                            
                        # 도박 기록 저장
                        await self.gambling_model.add_gambling_history(
                            user_id=interaction.user.id,
                            username=str(interaction.user),
                            box_id=box['id'],
                            box_name=box['name'],
                            reward_id=selected_reward['id'],
                            reward_type=reward_type,
                            reward_value=reward_value,
                            cost=box['price']
                        )
                            
                    except Exception as e:
                        # 보상 처리 실패
                        await self.point_model.add_points(
                            user_id=interaction.user.id,
                            username=str(interaction.user),
                            amount=box['price'],
                            reason=f"룻박스 처리 오류 환불: {box['name']}"
                        )
                        
                        await button_interaction.response.edit_message(
                            embed=discord.Embed(
                                title="❌ 룻박스 오류",
                                description=f"보상 처리 중 오류가 발생했습니다: {str(e)}. 포인트가 환불되었습니다.",
                                color=discord.Color.red()
                            ),
                            view=None
                        )
                
                @discord.ui.button(label="취소", style=discord.ButtonStyle.red)
                async def cancel(self, button_interaction: discord.Interaction, button: discord.ui.Button):
                    # 상호작용한 사용자 확인
                    if button_interaction.user.id != interaction.user.id:
                        await button_interaction.response.send_message("❌ 자신의 거래만 취소할 수 있습니다.", ephemeral=True)
                        return
                        
                    # 취소 메시지
                    cancel_embed = discord.Embed(
                        title="❌ 룻박스 구매 취소",
                        description="룻박스 구매가 취소되었습니다.",
                        color=discord.Color.red()
                    )
                    
                    await button_interaction.response.edit_message(embed=cancel_embed, view=None)
            
            # 확인 메시지 전송
            await interaction.response.send_message(embed=embed, view=ConfirmView())
            
        @self.tree.command(name="도박기록", description="자신의 도박 기록을 확인합니다")
        @app_commands.describe(개수="표시할 기록 개수 (기본값: 5)")
        async def slash_gambling_history(interaction: discord.Interaction, 개수: int = 5):
            """도박 기록 확인"""
            # 개수 검증
            if 개수 < 1 or 개수 > 20:
                개수 = 5
                
            # 도박 기록 가져오기
            history = await self.gambling_model.get_user_gambling_history(interaction.user.id, 개수)
            
            if not history:
                embed = discord.Embed(
                    title="🎲 도박 기록",
                    description="아직 도박 기록이 없습니다.",
                    color=discord.Color.orange()
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
                
            # 임베드 생성
            embed = discord.Embed(
                title="🎲 도박 기록",
                description=f"{interaction.user.mention}님의 최근 {len(history)}개 도박 기록입니다.",
                color=discord.Color.blue()
            )
            
            # 총 지출 및 획득 계산
            total_spent = sum(record['cost'] for record in history)
            total_earned = sum(int(record['reward_value']) if record['reward_type'] == '포인트' and record['reward_value'].isdigit() else 0 for record in history)
            
            embed.add_field(name="총 지출", value=f"{total_spent:,} 포인트", inline=True)
            embed.add_field(name="총 획득 (포인트)", value=f"{total_earned:,} 포인트", inline=True)
            embed.add_field(name="수익률", value=f"{(total_earned / total_spent * 100) if total_spent > 0 else 0:.1f}%", inline=True)
            
            # 기록 추가
            for i, record in enumerate(history):
                reward_value = record['reward_value']
                if record['reward_type'] == '포인트' and reward_value.isdigit():
                    reward_display = f"{int(reward_value):,} 포인트"
                else:
                    reward_display = reward_value
                    
                embed.add_field(
                    name=f"{i+1}. {record['box_name']} ({record['created_at'].strftime('%Y-%m-%d %H:%M')})",
                    value=f"비용: {record['cost']:,} 포인트\n보상: {record['reward_type']} - {reward_display}",
                    inline=False
                )
                
            await interaction.response.send_message(embed=embed, ephemeral=True)
    # 기존 add_basic_commands 메서드 안에 추가하거나, 새로운 메서드로 분리하여 추가
    
    def add_sync_commands(self):
        """Add synchronization commands"""
        
        @self.command(name="sync", aliases=["동기화", "명령어동기화"])
        @commands.has_permissions(administrator=True)
        async def sync_commands(ctx, scope: str = "guild"):
            """
            슬래시 명령어를 수동으로 동기화합니다.
            
            Args:
                scope: 동기화 범위 ("guild", "global", "both", "clear")
                      - guild: 현재 서버에만 동기화
                      - global: 전역 동기화 (모든 서버, 최대 1시간 소요)
                      - both: 서버 + 전역 동기화
                      - clear: 서버의 모든 명령어 삭제 후 재동기화
            """
            # 명령어가 실행된 메시지 삭제
            """상점 메뉴 표시"""
            embed = discord.Embed(
                title="🛒 상점",
                description="포인트로 구매할 수 있는 아이템 목록입니다.",
                color=discord.Color.blue()
            )
            
            # 역할 및 채널 정보 가져오기
            roles = await self.shop_model.get_purchasable_roles()
            channels = await self.shop_model.get_purchasable_channels()
            
            # 역할 정보 추가
            if roles:
                role_text = "\n".join([f"• {role['name']} - {role['price']:,} 포인트" for role in roles[:3]])
                if len(roles) > 3:
                    role_text += f"\n*그 외 {len(roles) - 3}개 역할...*"
                embed.add_field(name="구매 가능한 역할", value=role_text, inline=False)
            else:
                embed.add_field(name="구매 가능한 역할", value="현재 구매 가능한 역할이 없습니다.", inline=False)
                
            # 채널 정보 추가
            if channels:
                channel_text = "\n".join([f"• {channel['name']} - {channel['price']:,} 포인트" for channel in channels[:3]])
                if len(channels) > 3:
                    channel_text += f"\n*그 외 {len(channels) - 3}개 채널...*"
                embed.add_field(name="구매 가능한 채널", value=channel_text, inline=False)
            else:
                embed.add_field(name="구매 가능한 채널", value="현재 구매 가능한 채널이 없습니다.", inline=False)
                
            # 명령어 안내
            embed.add_field(
                name="사용 가능한 명령어",
                value="• `/상점역할` - 구매 가능한 역할 목록 보기\n• `/상점채널` - 구매 가능한 채널 목록 보기\n• `/역할구매` - 역할 구매하기\n• `/채널구매` - 채널 접근 권한 구매하기",
                inline=False
            )
            
            await interaction.response.send_message(embed=embed)
            
        @self.tree.command(name="상점역할", description="구매 가능한 역할 목록을 표시합니다")
        async def slash_shop_roles(interaction: discord.Interaction):
            """구매 가능한 역할 목록 표시"""
            # 역할 정보 가져오기
            roles = await self.shop_model.get_purchasable_roles()
            
            if not roles:
                embed = discord.Embed(
                    title="🛒 구매 가능한 역할",
                    description="현재 구매 가능한 역할이 없습니다.",
                    color=discord.Color.orange()
                )
                await interaction.response.send_message(embed=embed)
                return
                
            # 임베드 생성
            embed = discord.Embed(
                title="🛒 구매 가능한 역할",
                description="포인트로 구매할 수 있는 역할 목록입니다.",
                color=discord.Color.blue()
            )
            
            # 역할 정보 추가
            for role_data in roles:
                # 역할 객체 가져오기
                role = interaction.guild.get_role(role_data['role_id'])
                if not role:
                    continue
                    
                # 설명 추가
                description = role_data['description'] or "설명 없음"
                
                # 필드 추가
                embed.add_field(
                    name=f"{role.name} - {role_data['price']:,} 포인트",
                    value=f"설명: {description}\n구매 방법: `/역할구매 {role.name}`",
                    inline=False
                )
                
            await interaction.response.send_message(embed=embed)
            
        @self.tree.command(name="상점채널", description="구매 가능한 채널 목록을 표시합니다")
        async def slash_shop_channels(interaction: discord.Interaction):
            """구매 가능한 채널 목록 표시"""
            # 채널 정보 가져오기
            channels = await self.shop_model.get_purchasable_channels()
            
            if not channels:
                embed = discord.Embed(
                    title="🛒 구매 가능한 채널",
                    description="현재 구매 가능한 채널이 없습니다.",
                    color=discord.Color.orange()
                )
                await interaction.response.send_message(embed=embed)
                return
                
            # 임베드 생성
            embed = discord.Embed(
                title="🛒 구매 가능한 채널",
                description="포인트로 구매할 수 있는 채널 접근 권한 목록입니다.",
                color=discord.Color.blue()
            )
            
            # 채널 정보 추가
            for channel_data in channels:
                # 채널 객체 가져오기
                channel = interaction.guild.get_channel(channel_data['channel_id'])
                if not channel:
                    continue
                    
                # 접근 역할 가져오기
                access_role = interaction.guild.get_role(channel_data['access_role_id'])
                access_role_name = access_role.name if access_role else "알 수 없음"
                
                # 설명 추가
                description = channel_data['description'] or "설명 없음"
                
                # 필드 추가
                embed.add_field(
                    name=f"{channel.name} - {channel_data['price']:,} 포인트",
                    value=f"설명: {description}\n접근 역할: {access_role_name}\n구매 방법: `/채널구매 {channel.name}`",
                    inline=False
                )
                
            await interaction.response.send_message(embed=embed)
            
        @self.tree.command(name="역할구매", description="역할을 구매합니다")
        @app_commands.describe(역할명="구매할 역할의 이름")
        async def slash_buy_role(interaction: discord.Interaction, 역할명: str):
            """역할 구매"""
            # 역할 정보 가져오기
            role_data = await self.shop_model.get_purchasable_role_by_name(역할명)
            
            if not role_data:
                await interaction.response.send_message(f"❌ '{역할명}' 역할은 상점에서 판매하지 않습니다.", ephemeral=True)
                return
                
            # 역할 객체 가져오기
            role = interaction.guild.get_role(role_data['role_id'])
            if not role:
                await interaction.response.send_message("❌ 역할을 찾을 수 없습니다.", ephemeral=True)
                return
                
            # 이미 역할을 가지고 있는지 확인
            if role in interaction.user.roles:
                await interaction.response.send_message(f"❌ 이미 {role.mention} 역할을 가지고 있습니다.", ephemeral=True)
                return
                
            # 사용자 포인트 확인
            user_points = await self.point_model.get_user_points(interaction.user.id)
            if not user_points or user_points['points'] < role_data['price']:
                await interaction.response.send_message(f"❌ 포인트가 부족합니다. 필요한 포인트: {role_data['price']:,}", ephemeral=True)
                return
                
            # 구매 확인 메시지
            embed = discord.Embed(
                title="🛒 역할 구매 확인",
                description=f"{role.mention} 역할을 {role_data['price']:,} 포인트에 구매하시겠습니까?",
                color=discord.Color.blue()
            )
            embed.add_field(name="현재 포인트", value=f"{user_points['points']:,} 포인트", inline=True)
            embed.add_field(name="구매 후 포인트", value=f"{user_points['points'] - role_data['price']:,} 포인트", inline=True)
            
            # 확인 버튼 생성
            class ConfirmView(discord.ui.View):
                def __init__(self, timeout=60):
                    super().__init__(timeout=timeout)
                    
                @discord.ui.button(label="구매", style=discord.ButtonStyle.green)
                async def confirm(self, button_interaction: discord.Interaction, button: discord.ui.Button):
                    # 상호작용한 사용자 확인
                    if button_interaction.user.id != interaction.user.id:
                        await button_interaction.response.send_message("❌ 자신의 거래만 확인할 수 있습니다.", ephemeral=True)
                        return
                        
                    # 포인트 차감
                    success, message = await self.point_model.remove_points(
                        user_id=interaction.user.id,
                        amount=role_data['price'],
                        reason=f"역할 구매: {role.name}"
                    )
                    
                    if not success:
                        await button_interaction.response.send_message(f"❌ 포인트 차감 실패: {message}", ephemeral=True)
                        return
                        
                    # 역할 부여
                    try:
                        await interaction.user.add_roles(role, reason=f"상점에서 구매: {role_data['price']} 포인트")
                        
                        # 성공 메시지
                        success_embed = discord.Embed(
                            title="✅ 역할 구매 완료",
                            description=f"{role.mention} 역할을 성공적으로 구매했습니다!",
                            color=discord.Color.green()
                        )
                        success_embed.add_field(name="지불한 포인트", value=f"{role_data['price']:,} 포인트", inline=True)
                        success_embed.add_field(name="남은 포인트", value=f"{user_points['points'] - role_data['price']:,} 포인트", inline=True)
                        
                        await button_interaction.response.edit_message(embed=success_embed, view=None)
                        
                        # 로그 채널에 기록
                        if hasattr(self, 'log_channel') and self.log_channel:
                            log_embed = discord.Embed(
                                title="💰 역할 구매",
                                description=f"{interaction.user.mention}님이 역할을 구매했습니다.",
                                color=discord.Color.gold(),
                                timestamp=datetime.now()
                            )
                            log_embed.add_field(name="역할", value=role.mention, inline=True)
                            log_embed.add_field(name="가격", value=f"{role_data['price']:,} 포인트", inline=True)
                            
                            await self.log_channel.send(embed=log_embed)
                            
                    except discord.Forbidden:
                        # 포인트 환불
                        await self.point_model.add_points(
                            user_id=interaction.user.id,
                            username=str(interaction.user),
                            amount=role_data['price'],
                            reason=f"역할 구매 실패 환불: {role.name}"
                        )
                        
                        await button_interaction.response.send_message("❌ 역할을 부여할 권한이 없습니다. 포인트가 환불되었습니다.", ephemeral=True)
                    except Exception as e:
                        # 포인트 환불
                        await self.point_model.add_points(
                            user_id=interaction.user.id,
                            username=str(interaction.user),
                            amount=role_data['price'],
                            reason=f"역할 구매 실패 환불: {role.name}"
                        )
                        
                        await button_interaction.response.send_message(f"❌ 역할 부여 중 오류가 발생했습니다: {str(e)}. 포인트가 환불되었습니다.", ephemeral=True)
                
                @discord.ui.button(label="취소", style=discord.ButtonStyle.red)
                async def cancel(self, button_interaction: discord.Interaction, button: discord.ui.Button):
                    # 상호작용한 사용자 확인
                    if button_interaction.user.id != interaction.user.id:
                        await button_interaction.response.send_message("❌ 자신의 거래만 취소할 수 있습니다.", ephemeral=True)
                        return
                        
                    # 취소 메시지
                    cancel_embed = discord.Embed(
                        title="❌ 역할 구매 취소",
                        description="역할 구매가 취소되었습니다.",
                        color=discord.Color.red()
                    )
                    
                    await button_interaction.response.edit_message(embed=cancel_embed, view=None)
            
            # 확인 메시지 전송
            await interaction.response.send_message(embed=embed, view=ConfirmView())
            
        @self.tree.command(name="상점관리", description="[관리자] 상점 관리 메뉴를 표시합니다")
        async def slash_shop_admin(interaction: discord.Interaction):
            """상점 관리 메뉴"""
            # 권한 확인
            if not await PermissionChecker.check_permission(interaction.user, PermissionLevel.ADMIN):
                await interaction.response.send_message("❌ 이 명령어는 관리자만 사용할 수 있습니다.", ephemeral=True)
                return
                
            # 역할 및 채널 정보 가져오기
            roles = await self.shop_model.get_purchasable_roles()
            channels = await self.shop_model.get_purchasable_channels()
            
            # 임베드 생성
            embed = discord.Embed(
                title="🛠️ 상점 관리",
                description="상점 아이템을 관리할 수 있는 메뉴입니다.",
                color=discord.Color.blue()
            )
            
            # 역할 정보 추가
            role_text = "없음"
            if roles:
                role_text = "\n".join([f"• {role['name']} - {role['price']:,} 포인트" for role in roles[:5]])
                if len(roles) > 5:
                    role_text += f"\n*그 외 {len(roles) - 5}개 역할...*"
            embed.add_field(name=f"구매 가능한 역할 ({len(roles)}개)", value=role_text, inline=False)
            
            # 채널 정보 추가
            channel_text = "없음"
            if channels:
                channel_text = "\n".join([f"• {channel['name']} - {channel['price']:,} 포인트" for channel in channels[:5]])
                if len(channels) > 5:
                    channel_text += f"\n*그 외 {len(channels) - 5}개 채널...*"
            embed.add_field(name=f"구매 가능한 채널 ({len(channels)}개)", value=channel_text, inline=False)
            
            # 관리 명령어 안내
            embed.add_field(
                name="관리 명령어",
                value="• `/역할추가` - 구매 가능한 역할 추가\n• `/역할제거` - 구매 가능한 역할 제거\n• `/채널추가` - 구매 가능한 채널 추가\n• `/채널제거` - 구매 가능한 채널 제거",
                inline=False
            )
            
            await interaction.response.send_message(embed=embed)
        
        @self.tree.command(name="채널구매", description="채널 접근 권한을 구매합니다")
        @app_commands.describe(채널명="구매할 채널의 이름")
        async def slash_buy_channel(interaction: discord.Interaction, 채널명: str):
            """채널 접근 권한 구매"""
            # 채널 정보 가져오기
            channel_data = await self.shop_model.get_purchasable_channel_by_name(채널명)
            
            if not channel_data:
                await interaction.response.send_message(f"❌ '{채널명}' 채널은 상점에서 판매하지 않습니다.", ephemeral=True)
                return
                
            # 채널 객체 가져오기
            channel = interaction.guild.get_channel(channel_data['channel_id'])
            if not channel:
                await interaction.response.send_message("❌ 채널을 찾을 수 없습니다.", ephemeral=True)
                return
                
            # 접근 역할 가져오기
            access_role = interaction.guild.get_role(channel_data['access_role_id'])
            if not access_role:
                await interaction.response.send_message("❌ 채널 접근 역할을 찾을 수 없습니다.", ephemeral=True)
                return
                
            # 이미 역할을 가지고 있는지 확인
            if access_role in interaction.user.roles:
                await interaction.response.send_message(f"❌ 이미 {channel.mention} 채널에 접근할 수 있는 {access_role.mention} 역할을 가지고 있습니다.", ephemeral=True)
                return
                
            # 사용자 포인트 확인
            user_points = await self.point_model.get_user_points(interaction.user.id)
            if not user_points or user_points['points'] < channel_data['price']:
                await interaction.response.send_message(f"❌ 포인트가 부족합니다. 필요한 포인트: {channel_data['price']:,}", ephemeral=True)
                return
                
            # 구매 확인 메시지
            embed = discord.Embed(
                title="🛒 채널 접근 권한 구매 확인",
                description=f"{channel.mention} 채널 접근 권한을 {channel_data['price']:,} 포인트에 구매하시겠습니까?",
                color=discord.Color.blue()
            )
            embed.add_field(name="접근 역할", value=access_role.mention, inline=True)
            embed.add_field(name="현재 포인트", value=f"{user_points['points']:,} 포인트", inline=True)
            embed.add_field(name="구매 후 포인트", value=f"{user_points['points'] - channel_data['price']:,} 포인트", inline=True)
            
            # 확인 버튼 생성
            class ConfirmView(discord.ui.View):
                def __init__(self, timeout=60):
                    super().__init__(timeout=timeout)
                    
                @discord.ui.button(label="구매", style=discord.ButtonStyle.green)
                async def confirm(self, button_interaction: discord.Interaction, button: discord.ui.Button):
                    # 상호작용한 사용자 확인
                    if button_interaction.user.id != interaction.user.id:
                        await button_interaction.response.send_message("❌ 자신의 거래만 확인할 수 있습니다.", ephemeral=True)
                        return
                        
                    # 포인트 차감
                    success, message = await self.point_model.remove_points(
                        user_id=interaction.user.id,
                        amount=channel_data['price'],
                        reason=f"채널 접근 권한 구매: {channel.name}"
                    )
                    
                    if not success:
                        await button_interaction.response.send_message(f"❌ 포인트 차감 실패: {message}", ephemeral=True)
                        return
                        
                    # 역할 부여
                    try:
                        await interaction.user.add_roles(access_role, reason=f"채널 접근 권한 구매: {channel_data['price']} 포인트")
                        
                        # 성공 메시지
                        success_embed = discord.Embed(
                            title="✅ 채널 접근 권한 구매 완료",
                            description=f"{channel.mention} 채널 접근 권한을 성공적으로 구매했습니다!",
                            color=discord.Color.green()
                        )
                        success_embed.add_field(name="지불한 포인트", value=f"{channel_data['price']:,} 포인트", inline=True)
                        success_embed.add_field(name="남은 포인트", value=f"{user_points['points'] - channel_data['price']:,} 포인트", inline=True)
                        success_embed.add_field(name="접근 방법", value=f"{channel.mention} 채널로 이동하세요!", inline=False)
                        
                        await button_interaction.response.edit_message(embed=success_embed, view=None)
                        
                        # 로그 채널에 기록
                        if hasattr(self, 'log_channel') and self.log_channel:
                            log_embed = discord.Embed(
                                title="💰 채널 접근 권한 구매",
                                description=f"{interaction.user.mention}님이 채널 접근 권한을 구매했습니다.",
                                color=discord.Color.gold(),
                                timestamp=datetime.now()
                            )
                            log_embed.add_field(name="채널", value=channel.mention, inline=True)
                            log_embed.add_field(name="접근 역할", value=access_role.mention, inline=True)
                            log_embed.add_field(name="가격", value=f"{channel_data['price']:,} 포인트", inline=True)
                            
                            await self.log_channel.send(embed=log_embed)
                            
                    except discord.Forbidden:
                        # 포인트 환불
                        await self.point_model.add_points(
                            user_id=interaction.user.id,
                            username=str(interaction.user),
                            amount=channel_data['price'],
                            reason=f"채널 접근 권한 구매 실패 환불: {channel.name}"
                        )
                        
                        await button_interaction.response.send_message("❌ 역할을 부여할 권한이 없습니다. 포인트가 환불되었습니다.", ephemeral=True)
                    except Exception as e:
                        # 포인트 환불
                        await self.point_model.add_points(
                            user_id=interaction.user.id,
                            username=str(interaction.user),
                            amount=channel_data['price'],
                            reason=f"채널 접근 권한 구매 실패 환불: {channel.name}"
                        )
                        
                        await button_interaction.response.send_message(f"❌ 역할 부여 중 오류가 발생했습니다: {str(e)}. 포인트가 환불되었습니다.", ephemeral=True)
                
                @discord.ui.button(label="취소", style=discord.ButtonStyle.red)
                async def cancel(self, button_interaction: discord.Interaction, button: discord.ui.Button):
                    # 상호작용한 사용자 확인
                    if button_interaction.user.id != interaction.user.id:
                        await button_interaction.response.send_message("❌ 자신의 거래만 취소할 수 있습니다.", ephemeral=True)
                        return
                        
                    # 취소 메시지
                    cancel_embed = discord.Embed(
                        title="❌ 채널 접근 권한 구매 취소",
                        description="채널 접근 권한 구매가 취소되었습니다.",
                        color=discord.Color.red()
                    )
                    
                    await button_interaction.response.edit_message(embed=cancel_embed, view=None)
            
            # 확인 메시지 전송
            await interaction.response.send_message(embed=embed, view=ConfirmView())
    
    def add_permission_commands(self):
        """권한 관리 명령어 추가"""
        
        @self.tree.command(name="권한확인", description="사용자의 권한 레벨을 확인합니다")
        @app_commands.describe(사용자="권한을 확인할 사용자 (선택사항, 기본값: 자신)")
        async def slash_check_permission(interaction: discord.Interaction, 사용자: discord.Member = None):
            """사용자 권한 확인"""
            target = 사용자 or interaction.user
            
            # 권한 레벨 확인
            permission_level = await PermissionChecker.get_user_level(target)
            
            # 권한 설명
            permission_descriptions = {
                PermissionLevel.OWNER: "봇 소유자 - 모든 명령어 사용 가능",
                PermissionLevel.ADMIN: "관리자 - 대부분의 관리 명령어 사용 가능",
                PermissionLevel.MODERATOR: "모더레이터 - 메시지 관리 및 일부 관리 명령어 사용 가능",
                PermissionLevel.TRUSTED: "신뢰 유저 - 일반 유저보다 더 많은 명령어 사용 가능",
                PermissionLevel.MEMBER: "일반 멤버 - 기본 명령어만 사용 가능",
                PermissionLevel.RESTRICTED: "제한된 유저 - 제한된 명령어만 사용 가능"
            }
            
            # 권한 색상
            permission_colors = {
                PermissionLevel.OWNER: discord.Color.gold(),
                PermissionLevel.ADMIN: discord.Color.red(),
                PermissionLevel.MODERATOR: discord.Color.blue(),
                PermissionLevel.TRUSTED: discord.Color.green(),
                PermissionLevel.MEMBER: discord.Color.light_grey(),
                PermissionLevel.RESTRICTED: discord.Color.dark_grey()
            }
            
            # 임베드 생성
            embed = discord.Embed(
                title="🔒 권한 정보",
                color=permission_colors.get(permission_level, discord.Color.default())
            )
            
            embed.add_field(name="사용자", value=target.mention, inline=False)
            embed.add_field(name="권한 레벨", value=permission_level.name, inline=True)
            embed.add_field(name="설명", value=permission_descriptions.get(permission_level, "알 수 없는 권한"), inline=True)
            
            # 역할 정보 추가
            if hasattr(target, 'roles') and len(target.roles) > 1:
                roles = [role.mention for role in target.roles[1:]]  # @everyone 제외
                if roles:
                    role_text = ", ".join(roles[:5])
                    if len(roles) > 5:
                        role_text += f" 외 {len(roles) - 5}개"
                    embed.add_field(name="역할", value=role_text, inline=False)
            
            # 썸네일 설정
            if target.avatar:
                embed.set_thumbnail(url=target.avatar.url)
                
            await interaction.response.send_message(embed=embed)
            
        @self.tree.command(name="역할부여", description="[관리자] 사용자에게 역할을 부여합니다")
        @app_commands.describe(
            사용자="역할을 부여할 사용자",
            역할="부여할 역할",
            사유="역할 부여 사유 (선택사항)"
        )
        async def slash_give_role(interaction: discord.Interaction, 사용자: discord.Member, 역할: discord.Role, 사유: str = "관리자 지정"):
            """역할 부여"""
            # 권한 확인
            if not await PermissionChecker.check_permission(interaction.user, PermissionLevel.ADMIN):
                await interaction.response.send_message("❌ 이 명령어는 관리자만 사용할 수 있습니다.", ephemeral=True)
                return
                
            # 봇 권한 확인
            if not interaction.guild.me.guild_permissions.manage_roles:
                await interaction.response.send_message("❌ 봇이 역할을 관리할 권한이 없습니다.", ephemeral=True)
                return
                
            # 역할 계층 확인
            if 역할.position >= interaction.guild.me.top_role.position:
                await interaction.response.send_message("❌ 봇의 최상위 역할보다 높은 역할은 부여할 수 없습니다.", ephemeral=True)
                return
                
            # 이미 역할을 가지고 있는지 확인
            if 역할 in 사용자.roles:
                await interaction.response.send_message(f"❌ {사용자.mention}님은 이미 {역할.mention} 역할을 가지고 있습니다.", ephemeral=True)
                return
                
            # 역할 부여
            try:
                await 사용자.add_roles(역할, reason=f"{interaction.user}에 의해 부여됨: {사유}")
                
                # 성공 메시지
                embed = discord.Embed(
                    title="✅ 역할 부여 완료",
                    description=f"{사용자.mention}님에게 {역할.mention} 역할을 부여했습니다.",
                    color=discord.Color.green()
                )
                embed.add_field(name="사유", value=사유, inline=False)
                
                await interaction.response.send_message(embed=embed)
                
                # 로그 채널에 기록
                if hasattr(self, 'log_channel') and self.log_channel:
                    log_embed = discord.Embed(
                        title="👑 역할 부여",
                        description=f"{interaction.user.mention}님이 {사용자.mention}님에게 역할을 부여했습니다.",
                        color=discord.Color.blue(),
                        timestamp=datetime.now()
                    )
                    log_embed.add_field(name="역할", value=역할.mention, inline=True)
                    log_embed.add_field(name="사유", value=사유, inline=True)
                    
                    await self.log_channel.send(embed=log_embed)
                    
            except discord.Forbidden:
                await interaction.response.send_message("❌ 역할을 부여할 권한이 없습니다.", ephemeral=True)
            except discord.HTTPException as e:
                await interaction.response.send_message(f"❌ 역할 부여 중 오류가 발생했습니다: {str(e)}", ephemeral=True)
                
        @self.tree.command(name="역할제거", description="[관리자] 사용자의 역할을 제거합니다")
        @app_commands.describe(
            사용자="역할을 제거할 사용자",
            역할="제거할 역할",
            사유="역할 제거 사유 (선택사항)"
        )
        async def slash_remove_role(interaction: discord.Interaction, 사용자: discord.Member, 역할: discord.Role, 사유: str = "관리자 지정"):
            """역할 제거"""
            # 권한 확인
            if not await PermissionChecker.check_permission(interaction.user, PermissionLevel.ADMIN):
                await interaction.response.send_message("❌ 이 명령어는 관리자만 사용할 수 있습니다.", ephemeral=True)
                return
                
            # 봇 권한 확인
            if not interaction.guild.me.guild_permissions.manage_roles:
                await interaction.response.send_message("❌ 봇이 역할을 관리할 권한이 없습니다.", ephemeral=True)
                return
                
            # 역할 계층 확인
            if 역할.position >= interaction.guild.me.top_role.position:
                await interaction.response.send_message("❌ 봇의 최상위 역할보다 높은 역할은 제거할 수 없습니다.", ephemeral=True)
                return
                
            # 역할을 가지고 있는지 확인
            if 역할 not in 사용자.roles:
                await interaction.response.send_message(f"❌ {사용자.mention}님은 {역할.mention} 역할을 가지고 있지 않습니다.", ephemeral=True)
                return
                
            # 역할 제거
            try:
                await 사용자.remove_roles(역할, reason=f"{interaction.user}에 의해 제거됨: {사유}")
                
                # 성공 메시지
                embed = discord.Embed(
                    title="✅ 역할 제거 완료",
                    description=f"{사용자.mention}님에게서 {역할.mention} 역할을 제거했습니다.",
                    color=discord.Color.green()
                )
                embed.add_field(name="사유", value=사유, inline=False)
                
                await interaction.response.send_message(embed=embed)
                
                # 로그 채널에 기록
                if hasattr(self, 'log_channel') and self.log_channel:
                    log_embed = discord.Embed(
                        title="👑 역할 제거",
                        description=f"{interaction.user.mention}님이 {사용자.mention}님에게서 역할을 제거했습니다.",
                        color=discord.Color.orange(),
                        timestamp=datetime.now()
                    )
                    log_embed.add_field(name="역할", value=역할.mention, inline=True)
                    log_embed.add_field(name="사유", value=사유, inline=True)
                    
                    await self.log_channel.send(embed=log_embed)
                    
            except discord.Forbidden:
                await interaction.response.send_message("❌ 역할을 제거할 권한이 없습니다.", ephemeral=True)
            except discord.HTTPException as e:
                await interaction.response.send_message(f"❌ 역할 제거 중 오류가 발생했습니다: {str(e)}", ephemeral=True)
                
        @self.tree.command(name="역할목록", description="서버의 역할 목록을 표시합니다")
        async def slash_list_roles(interaction: discord.Interaction):
            """역할 목록 표시"""
            # 서버 확인
            if not interaction.guild:
                await interaction.response.send_message("❌ 이 명령어는 서버에서만 사용할 수 있습니다.", ephemeral=True)
                return
                
            # 역할 목록 가져오기 (everyone 역할 제외)
            roles = sorted(interaction.guild.roles[1:], key=lambda r: r.position, reverse=True)
            
            if not roles:
                await interaction.response.send_message("서버에 역할이 없습니다.", ephemeral=True)
                return
                
            # 임베드 생성
            embed = discord.Embed(
                title=f"🔰 {interaction.guild.name} 역할 목록",
                description=f"총 {len(roles)}개의 역할이 있습니다.",
                color=discord.Color.blue()
            )
            
            # 역할 정보 추가
            for i, role in enumerate(roles[:25]):  # 최대 25개만 표시
                members_count = len(role.members)
                embed.add_field(
                    name=f"{i+1}. {role.name}",
                    value=f"멤버: {members_count}명 | ID: {role.id} | 색상: {role.color}",
                    inline=False
                )
                
            # 역할이 25개 이상인 경우
            if len(roles) > 25:
                embed.set_footer(text=f"표시된 역할: 25/{len(roles)}개")
                
            await interaction.response.send_message(embed=embed)
    
    def add_logging_commands(self):
        """로깅 시스템 명령어 추가"""
        
        @self.tree.command(name="로그검색", description="로그를 검색합니다")
        @app_commands.describe(
            사용자="검색할 사용자 (선택사항)",
            내용="검색할 내용 (선택사항)"
        )
        async def slash_search_logs(interaction: discord.Interaction, 사용자: discord.Member = None, 내용: str = None):
            """로그 검색"""
            # 권한 확인
            if not await PermissionChecker.check_permission(interaction.user, PermissionLevel.ADMIN):
                await interaction.response.send_message("❌ 이 명령어는 관리자만 사용할 수 있습니다.", ephemeral=True)
                return
                
            # 응답 지연 (검색이 오래 걸릴 수 있음)
            await interaction.response.defer()
            
            # 검색 조건 설정
            search_conditions = {}
            if 사용자:
                search_conditions['user_id'] = 사용자.id
            if 내용:
                search_conditions['content'] = 내용
                
            # 로그 검색 (최대 20개)
            logs = await self.message_log_model.search_logs(search_conditions, limit=20)
            
            if not logs:
                await interaction.followup.send("검색 결과가 없습니다.")
                return
                
            # 결과 임베드 생성
            embed = discord.Embed(
                title=f"📋 로그 검색 결과 (최근 {len(logs)}개)",
                color=discord.Color.blue()
            )
            
            for log in logs:
                # 채널 및 사용자 정보 가져오기
                channel_name = log.get('channel_name', '알 수 없음')
                author_name = log.get('author_name', '알 수 없음')
                content = log.get('content', '*내용 없음*')
                created_at = log.get('created_at', datetime.now())
                
                # 내용이 너무 길면 자르기
                if len(content) > 100:
                    content = content[:97] + "..."
                    
                # 필드 추가
                embed.add_field(
                    name=f"#{channel_name} - {author_name} - {created_at.strftime('%m/%d %H:%M')}",
                    value=content,
                    inline=False
                )
                
            await interaction.followup.send(embed=embed)
            
        @self.tree.command(name="로그채널설정", description="[관리자] 로그 채널을 설정합니다")
        @app_commands.describe(채널="로그를 기록할 채널 (선택하지 않으면 현재 채널)")
        async def slash_set_log_channel(interaction: discord.Interaction, 채널: discord.TextChannel = None):
            """로그 채널 설정"""
            # 권한 확인
            if not await PermissionChecker.check_permission(interaction.user, PermissionLevel.ADMIN):
                await interaction.response.send_message("❌ 이 명령어는 관리자만 사용할 수 있습니다.", ephemeral=True)
                return
                
            # 채널이 지정되지 않은 경우 현재 채널 사용
            target_channel = 채널 or interaction.channel
            
            # 권한 확인
            if not target_channel.permissions_for(interaction.guild.me).send_messages:
                await interaction.response.send_message(f"❌ {target_channel.mention} 채널에 메시지를 보낼 권한이 없습니다.", ephemeral=True)
                return
                
            # 로그 채널 설정
            self.log_channel = target_channel
            
            # 설정 저장 (환경 변수 업데이트는 불가능하므로 메모리에만 저장)
            # 실제 구현에서는 데이터베이스에 저장하는 것이 좋음
            
            # 확인 메시지
            embed = discord.Embed(
                title="✅ 로그 채널 설정 완료",
                description=f"로그 채널이 {target_channel.mention}로 설정되었습니다.",
                color=discord.Color.green()
            )
            await interaction.response.send_message(embed=embed)
            
            # 테스트 메시지
            test_embed = discord.Embed(
                title="📝 로그 채널 테스트",
                description="이 채널이 로그 채널로 설정되었습니다.",
                color=discord.Color.blue(),
                timestamp=datetime.now()
            )
            test_embed.add_field(name="설정자", value=interaction.user.mention, inline=True)
            
            await target_channel.send(embed=test_embed)
    
    def add_message_commands(self):
        """메시지 관리 명령어 추가"""
        
        @self.tree.command(name="예약삭제", description="메시지를 지정된 시간 후에 삭제하도록 예약합니다")
        @app_commands.describe(
            메시지_아이디="삭제할 메시지의 ID",
            지연_시간="삭제까지 대기할 시간 (분 단위, 최대 10080분 = 7일)",
            사유="삭제 사유 (선택사항)"
        )
        async def slash_schedule_deletion(interaction: discord.Interaction, 메시지_아이디: str, 지연_시간: int, 사유: str = "예약 삭제"):
            """메시지 예약 삭제"""
            # 권한 확인
            if not await PermissionChecker.check_permission(interaction.user, PermissionLevel.MODERATOR):
                await interaction.response.send_message("❌ 이 명령어는 관리자 또는 모더레이터만 사용할 수 있습니다.", ephemeral=True)
                return
                
            # 메시지 ID 변환
            try:
                message_id = int(메시지_아이디)
            except ValueError:
                await interaction.response.send_message("❌ 유효한 메시지 ID를 입력해주세요.", ephemeral=True)
                return
                
            # 지연 시간 검증
            if 지연_시간 <= 0 or 지연_시간 > 10080:  # 최대 7일
                await interaction.response.send_message("❌ 삭제 시간은 1분에서 7일(10080분) 사이여야 합니다.", ephemeral=True)
                return
                
            # 메시지 확인
            try:
                message = await interaction.channel.fetch_message(message_id)
            except discord.NotFound:
                await interaction.response.send_message("❌ 메시지를 찾을 수 없습니다.", ephemeral=True)
                return
            except Exception as e:
                await interaction.response.send_message(f"❌ 메시지를 가져오는 중 오류가 발생했습니다: {str(e)}", ephemeral=True)
                return
                
            # 삭제 시간 계산
            delete_at = datetime.now() + timedelta(minutes=지연_시간)
            
            # 예약 삭제 등록
            success = await self.deletion_model.schedule_deletion(
                message_id=message_id,
                channel_id=interaction.channel.id,
                delete_at=delete_at,
                requester_id=interaction.user.id,
                reason=사유
            )
            
            if success:
                # 삭제 시간 포맷팅
                formatted_time = delete_at.strftime("%Y-%m-%d %H:%M:%S")
                
                embed = discord.Embed(
                    title="⏰ 메시지 삭제 예약 완료",
                    description=f"메시지가 {지연_시간}분 후에 삭제되도록 예약되었습니다.",
                    color=discord.Color.yellow()
                )
                embed.add_field(name="메시지 ID", value=message_id, inline=True)
                embed.add_field(name="삭제 예정 시간", value=formatted_time, inline=True)
                embed.add_field(name="사유", value=사유, inline=False)
                
                # 메시지 내용 미리보기 추가
                content_preview = message.content[:100] + "..." if len(message.content) > 100 else message.content
                if content_preview:
                    embed.add_field(name="메시지 내용", value=f"```{content_preview}```", inline=False)
                    
                await interaction.response.send_message(embed=embed)
                
                # 로그 채널에 기록
                if hasattr(self, 'log_channel') and self.log_channel:
                    log_embed = discord.Embed(
                        title="⏰ 메시지 삭제 예약",
                        description=f"{interaction.user.mention}님이 메시지 삭제를 예약했습니다.",
                        color=discord.Color.blue(),
                        timestamp=datetime.now()
                    )
                    log_embed.add_field(name="채널", value=interaction.channel.mention, inline=True)
                    log_embed.add_field(name="메시지 ID", value=message_id, inline=True)
                    log_embed.add_field(name="삭제 예정 시간", value=formatted_time, inline=True)
                    log_embed.add_field(name="사유", value=사유, inline=False)
                    
                    await self.log_channel.send(embed=log_embed)
            else:
                await interaction.response.send_message("❌ 메시지 삭제를 예약하는 데 실패했습니다.", ephemeral=True)
                
        @self.tree.command(name="삭제취소", description="예약된 메시지 삭제를 취소합니다")
        @app_commands.describe(메시지_아이디="삭제 예약을 취소할 메시지의 ID")
        async def slash_cancel_deletion(interaction: discord.Interaction, 메시지_아이디: str):
            """예약 삭제 취소"""
            # 권한 확인
            if not await PermissionChecker.check_permission(interaction.user, PermissionLevel.MODERATOR):
                await interaction.response.send_message("❌ 이 명령어는 관리자 또는 모더레이터만 사용할 수 있습니다.", ephemeral=True)
                return
                
            # 메시지 ID 변환
            try:
                message_id = int(메시지_아이디)
            except ValueError:
                await interaction.response.send_message("❌ 유효한 메시지 ID를 입력해주세요.", ephemeral=True)
                return
                
            # 예약 삭제 취소
            success = await self.deletion_model.remove_scheduled_deletion(message_id)
            
            if success:
                embed = discord.Embed(
                    title="✅ 삭제 예약 취소 완료",
                    description=f"메시지 ID {message_id}의 삭제 예약이 취소되었습니다.",
                    color=discord.Color.green()
                )
                await interaction.response.send_message(embed=embed)
                
                # 로그 채널에 기록
                if hasattr(self, 'log_channel') and self.log_channel:
                    log_embed = discord.Embed(
                        title="❌ 메시지 삭제 예약 취소",
                        description=f"{interaction.user.mention}님이 메시지 삭제 예약을 취소했습니다.",
                        color=discord.Color.orange(),
                        timestamp=datetime.now()
                    )
                    log_embed.add_field(name="메시지 ID", value=message_id, inline=True)
                    
                    await self.log_channel.send(embed=log_embed)
            else:
                embed = discord.Embed(
                    title="❌ 삭제 예약 없음",
                    description=f"메시지 ID {message_id}에 대한 삭제 예약을 찾을 수 없습니다.",
                    color=discord.Color.red()
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                
        @self.tree.command(name="청소", description="채널에서 여러 메시지를 삭제합니다")
        @app_commands.describe(
            개수="삭제할 메시지 수 (기본값: 10, 최대: 100)",
            대상="특정 사용자의 메시지만 삭제 (선택사항)"
        )
        async def slash_purge(interaction: discord.Interaction, 개수: int = 10, 대상: discord.Member = None):
            """메시지 대량 삭제"""
            # 권한 확인
            if not await PermissionChecker.check_permission(interaction.user, PermissionLevel.MODERATOR):
                await interaction.response.send_message("❌ 이 명령어는 관리자 또는 모더레이터만 사용할 수 있습니다.", ephemeral=True)
                return
                
            # 개수 검증
            if 개수 <= 0 or 개수 > 100:
                await interaction.response.send_message("❌ 삭제할 메시지 수는 1-100 사이여야 합니다.", ephemeral=True)
                return
                
            # 권한 확인
            if not interaction.channel.permissions_for(interaction.guild.me).manage_messages:
                await interaction.response.send_message("❌ 봇이 메시지를 관리할 권한이 없습니다.", ephemeral=True)
                return
                
            # 응답 지연 (작업이 오래 걸릴 수 있음)
            await interaction.response.defer(ephemeral=True)
            
            # 삭제 함수 정의
            def check_message(message):
                if 대상:
                    return message.author == 대상
                return True
                
            # 메시지 삭제
            try:
                deleted = await interaction.channel.purge(limit=개수, check=check_message)
                
                # 결과 메시지
                target_text = f"{대상.mention}의 " if 대상 else ""
                embed = discord.Embed(
                    title="✅ 메시지 삭제 완료",
                    description=f"{target_text}메시지 {len(deleted)}개를 삭제했습니다.",
                    color=discord.Color.green()
                )
                
                await interaction.followup.send(embed=embed, ephemeral=True)
                
                # 로그 채널에 기록
                if hasattr(self, 'log_channel') and self.log_channel:
                    log_embed = discord.Embed(
                        title="🧹 메시지 대량 삭제",
                        description=f"{interaction.user.mention}님이 {interaction.channel.mention}에서 메시지를 대량 삭제했습니다.",
                        color=discord.Color.orange(),
                        timestamp=datetime.now()
                    )
                    log_embed.add_field(name="삭제된 메시지 수", value=len(deleted), inline=True)
                    
                    if 대상:
                        log_embed.add_field(name="대상 유저", value=대상.mention, inline=True)
                        
                    await self.log_channel.send(embed=log_embed)
                    
            except discord.Forbidden:
                await interaction.followup.send("❌ 메시지를 삭제할 권한이 없습니다.", ephemeral=True)
            except discord.HTTPException as e:
                await interaction.followup.send(f"❌ 메시지 삭제 중 오류가 발생했습니다: {str(e)}", ephemeral=True)
                
        @self.tree.command(name="유저삭제", description="특정 사용자의 메시지를 삭제합니다")
        @app_commands.describe(
            대상="메시지를 삭제할 사용자",
            개수="검색할 최대 메시지 수 (기본값: 50, 최대: 500)"
        )
        async def slash_delete_user_messages(interaction: discord.Interaction, 대상: discord.Member, 개수: int = 50):
            """특정 유저의 메시지 삭제"""
            # 권한 확인
            if not await PermissionChecker.check_permission(interaction.user, PermissionLevel.MODERATOR):
                await interaction.response.send_message("❌ 이 명령어는 관리자 또는 모더레이터만 사용할 수 있습니다.", ephemeral=True)
                return
                
            # 개수 검증
            if 개수 <= 0 or 개수 > 500:
                await interaction.response.send_message("❌ 검색할 메시지 수는 1-500 사이여야 합니다.", ephemeral=True)
                return
                
            # 권한 확인
            if not interaction.channel.permissions_for(interaction.guild.me).manage_messages:
                await interaction.response.send_message("❌ 봇이 메시지를 관리할 권한이 없습니다.", ephemeral=True)
                return
                
            # 응답 지연 (작업이 오래 걸릴 수 있음)
            await interaction.response.defer()
            
            # 초기 상태 메시지
            status_message = await interaction.followup.send(
                embed=discord.Embed(
                    title="🔍 메시지 검색 중...",
                    description=f"{대상.mention}님의 메시지를 검색하고 있습니다...",
                    color=discord.Color.blue()
                )
            )
            
            # 메시지 삭제
            deleted_count = 0
            
            async for message in interaction.channel.history(limit=개수 * 2):  # 여유롭게 검색
                if message.author == 대상 and deleted_count < 개수:
                    try:
                        await ctx.message.delete()
                    except:
                        pass
                    
                    # 초기 상태 메시지
                        deleted_count += 1
                        
                        # 상태 업데이트 (5개마다)
                        if deleted_count % 5 == 0:
                            await status_message.edit(
                                embed=discord.Embed(
                                    title="🗑️ 메시지 삭제 중...",
                                    description=f"{대상.mention}님의 메시지 {deleted_count}개를 삭제했습니다...",
                                    color=discord.Color.blue()
                                )
                            )
                            
                        # 레이트 리밋 방지
                        await asyncio.sleep(0.5)
                        
                    except Exception as e:
                        self.logger.error(f"Error deleting message: {e}")
                        continue
                        
            # 최종 상태 업데이트
            await status_message.edit(
                embed=discord.Embed(
                    title="✅ 메시지 삭제 완료",
                    description=f"{대상.mention}님의 메시지 {deleted_count}개를 삭제했습니다.",
                    color=discord.Color.green()
                )
            )
            
            # 로그 채널에 기록
            if hasattr(self, 'log_channel') and self.log_channel:
                log_embed = discord.Embed(
                    title="🧹 유저 메시지 삭제",
                    description=f"{interaction.user.mention}님이 {대상.mention}의 메시지를 삭제했습니다.",
                    color=discord.Color.orange(),
                    timestamp=datetime.now()
                )
                log_embed.add_field(name="채널", value=interaction.channel.mention, inline=True)
                log_embed.add_field(name="삭제된 메시지 수", value=deleted_count, inline=True)
                
                await self.log_channel.send(embed=log_embed)
                
        @self.tree.command(name="메시지삭제", description="특정 유형의 메시지를 삭제합니다")
        @app_commands.describe(
            대상="메시지를 삭제할 사용자",
            개수="검색할 최대 메시지 수 (기본값: 100, 최대: 1000)",
            메시지종류="삭제할 메시지 종류 (기본값: 전부)"
        )
        @app_commands.choices(메시지종류=[
            app_commands.Choice(name="전체 메시지", value="전부"),
            app_commands.Choice(name="이미지만", value="이미지만"),
            app_commands.Choice(name="텍스트만", value="메시지만")
        ])
        async def slash_delete_filtered_messages(
            interaction: discord.Interaction, 
            대상: discord.Member, 
            개수: int = 100, 
            메시지종류: app_commands.Choice[str] = None
        ):
            """특정 유형의 메시지 삭제"""
            # 권한 확인
            if not await PermissionChecker.check_permission(interaction.user, PermissionLevel.MODERATOR):
                await interaction.response.send_message("❌ 이 명령어는 관리자 또는 모더레이터만 사용할 수 있습니다.", ephemeral=True)
                return
                
            # 개수 검증
            if 개수 <= 0 or 개수 > 1000:
                await interaction.response.send_message("❌ 검색할 메시지 수는 1-1000 사이여야 합니다.", ephemeral=True)
                return
                
            # 권한 확인
            if not interaction.channel.permissions_for(interaction.guild.me).manage_messages:
                await interaction.response.send_message("❌ 봇이 메시지를 관리할 권한이 없습니다.", ephemeral=True)
                return
                
            # 메시지 종류 설정
            message_type = 메시지종류.value if 메시지종류 else "전부"
            
            # 응답 지연 (작업이 오래 걸릴 수 있음)
            await interaction.response.defer()
            
            # 초기 상태 메시지
            status_message = await interaction.followup.send(
                embed=discord.Embed(
                    title="🔍 메시지 검색 중...",
                    description=f"{대상.mention}님의 {message_type} 메시지를 검색하고 있습니다...",
                    color=discord.Color.blue()
                )
            )
            
            # 이미지 메시지 확인 함수
            def is_image_message(message):
                # 첨부 파일이 있는지 확인
                if message.attachments:
                    for attachment in message.attachments:
                        content_type = getattr(attachment, 'content_type', '')
                        if content_type and content_type.startswith('image/'):
                            return True
                        # content_type이 없는 경우 확장자로 확인
                        filename = attachment.filename.lower()
                        if any(filename.endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp']):
                            return True
                return False
            
            # 메시지 종류에 따른 확인 함수
            def check_message(message):
                # 대상 유저의 메시지인지 확인
                if message.author.id != 대상.id:
                    return False
                    
                # 메시지 종류 확인
                if message_type == "이미지만":
                    return is_image_message(message)
                elif message_type == "메시지만":
                    return not is_image_message(message)
                else:  # "전부"
                    return True
            
            # 메시지 삭제
            deleted_count = 0
            
            async for message in interaction.channel.history(limit=개수 * 2):  # 여유롭게 검색
                if check_message(message) and deleted_count < 개수:
                    try:
                        await message.delete()
                        deleted_count += 1
                        
                        # 상태 업데이트 (5개마다)
                        if deleted_count % 5 == 0:
                            await status_message.edit(
                                embed=discord.Embed(
                                    title="🗑️ 메시지 삭제 중...",
                                    description=f"{대상.mention}님의 {message_type} 메시지 {deleted_count}개를 삭제했습니다...",
                                    color=discord.Color.blue()
                                )
                            )
                            
                        # 레이트 리밋 방지
                        await asyncio.sleep(0.5)
                        
                    except Exception as e:
                        self.logger.error(f"Error deleting message: {e}")
                        continue
                        
            # 최종 상태 업데이트
            await status_message.edit(
                embed=discord.Embed(
                    title="✅ 메시지 삭제 완료",
                    description=f"{대상.mention}님의 {message_type} 메시지 {deleted_count}개를 삭제했습니다.",
                    color=discord.Color.green()
                )
            )
            
            # 로그 채널에 기록
            if hasattr(self, 'log_channel') and self.log_channel:
                log_embed = discord.Embed(
                    title="🧹 유저 메시지 삭제",
                    description=f"{interaction.user.mention}님이 {대상.mention}의 {message_type} 메시지를 삭제했습니다.",
                    color=discord.Color.orange(),
                    timestamp=datetime.now()
                )
                log_embed.add_field(name="채널", value=interaction.channel.mention, inline=True)
                log_embed.add_field(name="삭제된 메시지 수", value=deleted_count, inline=True)
                log_embed.add_field(name="메시지 종류", value=message_type, inline=True)
                
                await self.log_channel.send(embed=log_embed)
    
    def add_points_commands(self):
        """포인트 시스템 명령어 추가"""
        
        @self.tree.command(name="포인트", description="사용자의 포인트를 확인합니다")
        @app_commands.describe(사용자="포인트를 확인할 사용자 (선택사항, 기본값: 자신)")
        async def slash_check_points(interaction: discord.Interaction, 사용자: discord.Member = None):
            """사용자 포인트 확인"""
            target = 사용자 or interaction.user
            
            # Get user points
            user_points = await self.point_model.get_user_points(target.id)
            
            if not user_points:
                embed = discord.Embed(
                    title="📊 포인트 정보",
                    description=f"{target.display_name}님의 포인트 정보가 없습니다.",
                    color=discord.Color.orange()
                )
                await interaction.response.send_message(embed=embed)
                return
                
            # Create embed
            embed = discord.Embed(
                title="📊 포인트 정보",
                color=discord.Color.blue()
            )
            
            embed.add_field(name="유저", value=target.mention, inline=False)
            embed.add_field(name="현재 포인트", value=f"{user_points['points']:,}", inline=True)
            embed.add_field(name="레벨", value=f"{user_points['level']}", inline=True)
            embed.add_field(name="경험치", value=f"{user_points['experience']:,}", inline=True)
            embed.add_field(name="총 획득", value=f"{user_points['total_earned']:,}", inline=True)
            embed.add_field(name="총 사용", value=f"{user_points['total_spent']:,}", inline=True)
            
            # Calculate next level requirements
            current_level = user_points['level']
            next_level = current_level + 1
            exp_needed = (next_level ** 2) * 100
            current_exp = user_points['experience']
            remaining_exp = exp_needed - current_exp
            
            progress = min(current_exp / exp_needed, 1.0) if exp_needed > 0 else 1.0
            progress_bar = self.create_progress_bar(progress)
            
            embed.add_field(
                name=f"레벨 진행도 ({current_level} → {next_level})",
                value=f"{progress_bar} {int(progress * 100)}%\n{current_exp:,} / {exp_needed:,} XP (앞으로 {remaining_exp:,} XP 필요)",
                inline=False
            )
            
            # Set thumbnail
            embed.set_thumbnail(url=target.avatar.url if target.avatar else None)
            
            await interaction.response.send_message(embed=embed)
            
        @self.tree.command(name="포인트추가", description="[관리자] 사용자에게 포인트를 추가합니다")
        @app_commands.describe(
            사용자="포인트를 추가할 사용자",
            금액="추가할 포인트 금액",
            사유="포인트 추가 사유 (선택사항)"
        )
        async def slash_add_points(interaction: discord.Interaction, 사용자: discord.Member, 금액: int, 사유: str = "관리자 지급"):
            """관리자 포인트 추가"""
            # 권한 확인
            if not await self.is_admin_user(interaction.user):
                await interaction.response.send_message("❌ 이 명령어는 관리자만 사용할 수 있습니다.", ephemeral=True)
                return
                
            # Validate amount
            if not InputValidator.validate_amount(금액, 1, 1000000):
                embed = discord.Embed(
                    title="❌ 잘못된 금액",
                    description="포인트는 1에서 1,000,000 사이여야 합니다.",
                    color=discord.Color.red()
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
                
            # Add points
            success = await self.point_model.add_points(
                user_id=사용자.id,
                username=str(사용자),
                amount=금액,
                reason=사유,
                admin_id=interaction.user.id
            )
            
            if success:
                embed = discord.Embed(
                    title="✅ 포인트 추가 완료",
                    description=f"{사용자.mention}님에게 {금액:,} 포인트를 추가했습니다.",
                    color=discord.Color.green()
                )
                embed.add_field(name="사유", value=사유, inline=False)
                
                # Log the transaction
                if hasattr(self, 'log_channel') and self.log_channel:
                    log_embed = discord.Embed(
                        title="💰 포인트 추가",
                        description=f"{사용자.mention}님에게 {금액:,} 포인트가 추가되었습니다.",
                        color=discord.Color.green(),
                        timestamp=datetime.now()
                    )
                    log_embed.add_field(name="관리자", value=interaction.user.mention, inline=True)
                    log_embed.add_field(name="사유", value=사유, inline=True)
                    await self.log_channel.send(embed=log_embed)
            else:
                embed = discord.Embed(
                    title="❌ 오류 발생",
                    description="포인트를 추가하는 데 실패했습니다.",
                    color=discord.Color.red()
                )
                
            await interaction.response.send_message(embed=embed)
            
        @self.tree.command(name="포인트차감", description="[관리자] 사용자의 포인트를 차감합니다")
        @app_commands.describe(
            사용자="포인트를 차감할 사용자",
            금액="차감할 포인트 금액",
            사유="포인트 차감 사유 (선택사항)"
        )
        async def slash_remove_points(interaction: discord.Interaction, 사용자: discord.Member, 금액: int, 사유: str = "관리자 차감"):
            """관리자 포인트 차감"""
            # 권한 확인
            if not await self.is_admin_user(interaction.user):
                await interaction.response.send_message("❌ 이 명령어는 관리자만 사용할 수 있습니다.", ephemeral=True)
                return
                
            # Validate amount
            if not InputValidator.validate_amount(금액, 1, 1000000):
                embed = discord.Embed(
                    title="❌ 잘못된 금액",
                    description="포인트는 1에서 1,000,000 사이여야 합니다.",
                    color=discord.Color.red()
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
                
            # Remove points
            success, message = await self.point_model.remove_points(
                user_id=사용자.id,
                amount=금액,
                reason=사유,
                admin_id=interaction.user.id
            )
            
            if success:
                embed = discord.Embed(
                    title="✅ 포인트 차감 완료",
                    description=f"{사용자.mention}님에게서 {금액:,} 포인트를 차감했습니다.",
                    color=discord.Color.green()
                )
                embed.add_field(name="사유", value=사유, inline=False)
                
                # Log the transaction
                if hasattr(self, 'log_channel') and self.log_channel:
                    log_embed = discord.Embed(
                        title="💸 포인트 차감",
                        description=f"{사용자.mention}님에게서 {금액:,} 포인트가 차감되었습니다.",
                        color=discord.Color.orange(),
                        timestamp=datetime.now()
                    )
                    log_embed.add_field(name="관리자", value=interaction.user.mention, inline=True)
                    log_embed.add_field(name="사유", value=사유, inline=True)
                    await self.log_channel.send(embed=log_embed)
            else:
                embed = discord.Embed(
                    title="❌ 오류 발생",
                    description=f"포인트를 차감하는 데 실패했습니다: {message}",
                    color=discord.Color.red()
                )
                
            await interaction.response.send_message(embed=embed)
            
        @self.tree.command(name="포인트순위", description="포인트 순위를 표시합니다")
        @app_commands.describe(개수="표시할 순위 개수 (기본값: 10)")
        async def slash_leaderboard(interaction: discord.Interaction, 개수: int = 10):
            """포인트 순위 표시"""
            # Validate limit
            if 개수 < 1 or 개수 > 50:
                개수 = 10
                
            # Get leaderboard
            leaderboard_data = await self.point_model.get_leaderboard(개수)
            
            if not leaderboard_data:
                embed = discord.Embed(
                    title="📊 포인트 순위",
                    description="아직 포인트 데이터가 없습니다.",
                    color=discord.Color.orange()
                )
                await interaction.response.send_message(embed=embed)
                return
                
            # Create embed
            embed = discord.Embed(
                title="🏆 포인트 순위",
                color=discord.Color.gold()
            )
            
            # Format leaderboard entries
            for i, entry in enumerate(leaderboard_data):
                medal = "🥇" if i == 0 else "🥈" if i == 1 else "🥉" if i == 2 else f"{i+1}."
                
                try:
                    member = interaction.guild.get_member(entry['user_id'])
                    name = member.mention if member else entry['username']
                except:
                    name = entry['username']
                    
                embed.add_field(
                    name=f"{medal} {name}",
                    value=f"**{entry['points']:,}** 포인트 (레벨 {entry['level']})",
                    inline=False
                )
                
            embed.set_footer(text=f"서버 포인트 순위 • {datetime.now().strftime('%Y-%m-%d %H:%M')}")
            
            await interaction.response.send_message(embed=embed)
            
        @self.tree.command(name="일일보너스", description="일일 보너스 포인트를 받습니다")
        async def slash_daily_bonus(interaction: discord.Interaction):
            """일일 보너스 포인트 수령"""
            user_id = interaction.user.id
            
            # Check cooldown
            last_daily = await self.point_model.get_last_daily(user_id)
            if last_daily:
                now = datetime.now()
                time_diff = now - last_daily
                if time_diff.total_seconds() < 86400:  # 24 hours in seconds
                    next_daily = last_daily + timedelta(days=1)
                    remaining = next_daily - now
                    hours, remainder = divmod(int(remaining.total_seconds()), 3600)
                    minutes, seconds = divmod(remainder, 60)
                    
                    embed = discord.Embed(
                        title="⏰ 쿨다운 중",
                        description=f"일일 보너스는 하루에 한 번만 받을 수 있습니다.",
                        color=discord.Color.orange()
                    )
                    embed.add_field(
                        name="다음 보너스 가능 시간",
                        value=f"{hours}시간 {minutes}분 {seconds}초 후",
                        inline=False
                    )
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                    return
            
            bonus_amount = Settings.POINT_DAILY_BONUS
            
            # Add points
            success = await self.point_model.add_points(
                user_id=user_id,
                username=str(interaction.user),
                amount=bonus_amount,
                reason="일일 보너스"
            )
            
            # Update last daily timestamp
            await self.point_model.update_last_daily(user_id)
            
            if success:
                embed = discord.Embed(
                    title="🎁 일일 보너스 수령 완료!",
                    description=f"{interaction.user.mention}님이 일일 보너스 {bonus_amount:,} 포인트를 받았습니다!",
                    color=discord.Color.green()
                )
                embed.set_footer(text="다음 보너스는 24시간 후에 받을 수 있습니다.")
            else:
                embed = discord.Embed(
                    title="❌ 오류 발생",
                    description="일일 보너스를 받는 데 실패했습니다.",
                    color=discord.Color.red()
                )
                
            await interaction.response.send_message(embed=embed)
    
    # 헬퍼 메소드
    async def send_help_embed(self, interaction, command_name=None):
        """도움말 임베드 생성 및 전송"""
        try:
            if command_name:
                # Show help for specific slash command
                target_cmd = None
                for cmd in self.tree.get_commands():
                    if cmd.name == command_name:
                        target_cmd = cmd
                        break
                
                if not target_cmd:
                    embed = discord.Embed(
                        title="❓ 명령어 없음",
                        description=f"`/{command_name}` 명령어를 찾을 수 없습니다.",
                        color=discord.Color.red()
                    )
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                    return
                    
                embed = discord.Embed(
                    title=f"📚 /{target_cmd.name} 명령어 도움말",
                    description=target_cmd.description or "설명이 없습니다.",
                    color=discord.Color.blue()
                )
                
                # Add parameters if any
                if target_cmd.parameters:
                    param_text = []
                    for param in target_cmd.parameters:
                        param_desc = f"`{param.name}`"
                        if param.description:
                            param_desc += f": {param.description}"
                        if param.required:
                            param_desc = f"**{param_desc}** (필수)"
                        else:
                            param_desc = f"{param_desc} (선택)"
                        param_text.append(param_desc)
                    
                    embed.add_field(
                        name="매개변수",
                        value="\n".join(param_text),
                        inline=False
                    )
                    
                await interaction.response.send_message(embed=embed)
                return
                
            # Show general help
            embed = discord.Embed(
                title="📚 봇 도움말",
                description="모든 명령어는 슬래시 명령어입니다. `/`를 입력하면 자동완성됩니다!",
                color=discord.Color.blue()
            )
            
            # 기본 명령어들
            basic_commands = [
                ("도움말", "이 도움말을 표시합니다"),
                ("핑", "봇의 지연 시간을 확인합니다"),
                ("정보", "봇의 정보를 표시합니다"),
                ("서버정보", "현재 서버의 정보를 표시합니다"),
                ("유저정보", "사용자 정보를 표시합니다")
            ]
            
            basic_text = "\n".join([f"`/{name}` - {desc}" for name, desc in basic_commands])
            embed.add_field(name="🔸 기본 명령어", value=basic_text, inline=False)
            
            # 관리자 명령어
            admin_commands = [
                ("동기화", "슬래시 명령어를 동기화합니다"),
                ("명령어상태", "명령어 등록 상태를 확인합니다")
            ]
            
            admin_text = "\n".join([f"`/{name}` - {desc}" for name, desc in admin_commands])
            embed.add_field(name="🔸 관리자 명령어", value=admin_text, inline=False)
            
            embed.add_field(
                name="💡 사용 팁",
                value="• `/`를 입력하면 모든 명령어가 자동완성됩니다\n• 명령어 매개변수는 자동으로 안내됩니다\n• 특정 명령어 도움말: `/도움말 명령어이름`",
                inline=False
            )
                
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            self.logger.error(f"Help command error: {e}")
            error_embed = discord.Embed(
                title="❌ 도움말 오류",
                description="도움말을 표시하는 중 오류가 발생했습니다.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=error_embed, ephemeral=True)
    
    async def send_bot_info(self, interaction):
        """봇 정보 전송"""
        embed = discord.Embed(
            title="🤖 봇 정보",
            description="다기능 디스코드 봇 - 슬래시 명령어 전용",
            color=discord.Color.blue()
        )
        
        # Add bot stats
        embed.add_field(name="서버 수", value=str(len(self.guilds)), inline=True)
        embed.add_field(name="유저 수", value=str(len(set(self.get_all_members()))), inline=True)
        embed.add_field(name="슬래시 명령어", value=str(len(self.tree.get_commands())), inline=True)
        
        # Add uptime
        if hasattr(self, 'start_time') and self.start_time:
            uptime = datetime.now() - self.start_time
            days, remainder = divmod(int(uptime.total_seconds()), 86400)
            hours, remainder = divmod(remainder, 3600)
            minutes, seconds = divmod(remainder, 60)
            uptime_str = f"{days}일 {hours}시간 {minutes}분 {seconds}초"
            embed.add_field(name="가동 시간", value=uptime_str, inline=False)
            
        # Add version info
        embed.add_field(name="Python 버전", value=f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}", inline=True)
        embed.add_field(name="discord.py 버전", value=discord.__version__, inline=True)
        embed.add_field(name="지연 시간", value=f"{round(self.latency * 1000)}ms", inline=True)
        
        # Set bot avatar as thumbnail
        if self.user and self.user.avatar:
            embed.set_thumbnail(url=self.user.avatar.url)
        
        await interaction.response.send_message(embed=embed)
    
    async def send_status_info(self, interaction):
        """상태 정보 전송"""
        embed = discord.Embed(
            title="🔧 봇 상태",
            color=discord.Color.blue()
        )
        
        # 명령어 정보
        embed.add_field(name="슬래시 명령어", value=str(len(self.tree.get_commands())), inline=True)
        embed.add_field(name="연결된 서버", value=str(len(self.guilds)), inline=True)
        
        # 슬래시 명령어 목록
        slash_commands = [cmd.name for cmd in self.tree.get_commands()]
        if slash_commands:
            slash_list = ", ".join([f"`/{cmd}`" for cmd in slash_commands])
            if len(slash_list) > 1000:
                slash_list = slash_list[:1000] + "..."
            embed.add_field(name="슬래시 명령어 목록", value=slash_list, inline=False)
        
        # 시스템 정보
        embed.add_field(name="메모리 사용량", value=f"{round(os.getpid() / 1024 / 1024, 2)} MB", inline=True)
        
        await interaction.response.send_message(embed=embed)
        
    async def is_admin_user(self, user):
        """사용자가 관리자인지 확인"""
        # 봇 소유자 확인
        if user.id == Settings.BOT_OWNER_ID:
            return True
            
        # 서버 관리자 권한 확인
        if hasattr(user, 'guild_permissions') and user.guild_permissions.administrator:
            return True
            
        # 관리자 역할 확인
        if hasattr(user, 'roles'):
            for role in user.roles:
                if role.id == Settings.ADMIN_ROLE_ID:
                    return True
                    
        return False
        
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
                    # 예약 삭제 체커 시작
                    if hasattr(self, 'deletion_checker') and not self.deletion_checker.is_running():
                        self.deletion_checker.start()
                        self.logger.info("🔄 Background tasks started successfully")
                    
                    self._tasks_started = True
                    
                except Exception as e:
                    self.logger.error(f"❌ Failed to start background tasks: {e}")
            
            self.logger.info("✅ Bot is ready and all systems are operational!")
            
        except Exception as e:
            self.logger.error(f"❌ Error in on_ready: {e}", exc_info=True)
    
    # 두 번째 on_ready 메서드는 완전히 제거하거나 이름을 변경하세요
    # 예를 들어 on_ready_secondary → on_guild_ready 등으로 변경
            
    @deletion_checker.before_loop
    async def before_deletion_checker(self):
        """삭제 확인 태스크 시작 전 준비"""
        await self.wait_until_ready()
    
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
            except Exception as e:
                self.logger.error(f"Error fetching message {message_id}: {e}")
                return
                
            # Delete the message
            try:
                await message.delete()
                self.logger.info(f"Deleted scheduled message {message_id}")
                
                # Remove from database
                await self.deletion_model.remove_scheduled_deletion(message_id)
                
                # Log the deletion
                if hasattr(self, 'log_channel') and self.log_channel:
                    requester = self.get_user(requester_id)
                    requester_name = requester.mention if requester else f"ID: {requester_id}"
                    
                    log_embed = discord.Embed(
                        title="⏰ 예약 삭제 실행",
                        description=f"예약된 메시지가 삭제되었습니다.",
                        color=discord.Color.orange(),
                        timestamp=datetime.now()
                    )
                    log_embed.add_field(name="채널", value=channel.mention, inline=True)
                    log_embed.add_field(name="메시지 ID", value=message_id, inline=True)
                    log_embed.add_field(name="요청자", value=requester_name, inline=True)
                    
                    if reason:
                        log_embed.add_field(name="사유", value=reason, inline=False)
                        
                    await self.log_channel.send(embed=log_embed)
                    
            except discord.Forbidden:
                self.logger.error(f"No permission to delete message {message_id}")
                
            except Exception as e:
                self.logger.error(f"Error deleting message {message_id}: {e}")
                
        except Exception as e:
            self.logger.error(f"Error processing scheduled deletion: {e}")
                # 두 번째 on_ready 메서드 제거 (line 156513-158109 범위)
                # 다음 코드를 완전히 삭제하세요:
                
                # async def on_ready(self):  # <- 이 부분부터
                #     """Called when the bot is ready"""
                #     # ... 모든 내용 ...
                #     # <- 여기까지 삭제
                
                # 첫 번째 on_ready만 유지하고 다음과 같이 수정:
        self.logger.info(f"Logged in as {self.user} (ID: {self.user.id})")
        self.logger.info(f"Connected to {len(self.guilds)} guilds")
        
        # Set up activity status
        activity = discord.Activity(
            type=discord.ActivityType.listening,
            name="/ 슬래시 명령어"
        )
        await self.change_presence(activity=activity)
        
        # Set up log channel
        if Settings.LOG_CHANNEL_ID:
            self.log_channel = self.get_channel(Settings.LOG_CHANNEL_ID)
            if self.log_channel:
                self.logger.info(f"Log channel set to #{self.log_channel.name}")
            else:
                self.logger.warning(f"Log channel with ID {Settings.LOG_CHANNEL_ID} not found")
                
        # Send startup message to log channel
        if self.log_channel:
            embed = discord.Embed(
                title="🤖 봇 온라인",
                description="봇이 성공적으로 시작되었습니다.",
                color=discord.Color.green(),
                timestamp=datetime.now()
            )
            embed.add_field(name="버전", value="2.0.0 (슬래시 전용)", inline=True)
            embed.add_field(name="서버 수", value=str(len(self.guilds)), inline=True)
            embed.add_field(name="슬래시 명령어", value=str(len(self.tree.get_commands())), inline=True)
            
            try:
                await self.log_channel.send(embed=embed)
            except Exception as e:
                self.logger.error(f"Failed to send startup message: {e}")
    
    async def on_message(self, message):
        """Process messages"""
        # 봇 자신의 메시지는 무시
        if message.author == self.user:
            return
            
        # 포인트 시스템 처리
        await self.process_message_points(message)
        
    async def on_message_delete(self, message):
        """메시지 삭제 이벤트 처리"""
        # 봇 자신의 메시지는 무시
        if message.author == self.user:
            return
            
        # 로그 채널이 없으면 무시
        if not hasattr(self, 'log_channel') or not self.log_channel:
            return
            
        # 메시지 내용이 없고 첨부파일도 없으면 무시
        if not message.content and not message.attachments:
            return
            
        # 삭제된 메시지 로깅
        embed = discord.Embed(
            title="🗑️ 메시지 삭제됨",
            description=f"채널: {message.channel.mention}",
            color=discord.Color.red(),
            timestamp=datetime.now()
        )
        
        embed.set_author(
            name=f"{message.author.display_name} ({message.author})",
            icon_url=message.author.avatar.url if message.author.avatar else None
        )
        
        # 메시지 내용 추가
        if message.content:
            # 내용이 너무 길면 자르기
            content = message.content
            if len(content) > 1024:
                content = content[:1021] + "..."
            embed.add_field(name="내용", value=content, inline=False)
            
        # 첨부파일 정보 추가
        if message.attachments:
            files_text = "\n".join([f"[{attachment.filename}]({attachment.proxy_url})" for attachment in message.attachments])
            embed.add_field(name="첨부파일", value=files_text, inline=False)
            
            # 이미지인 경우 썸네일 추가
            for attachment in message.attachments:
                if attachment.content_type and attachment.content_type.startswith('image/'):
                    embed.set_image(url=attachment.proxy_url)
                    break
        
        # 메시지 ID 추가
        embed.add_field(name="메시지 ID", value=message.id, inline=True)
        
        # 로그 채널에 전송
        await self.log_channel.send(embed=embed)
        
        # 데이터베이스에 로깅
        try:
            await self.message_log_model.log_message_deletion(
                message_id=message.id,
                channel_id=message.channel.id,
                channel_name=message.channel.name,
                author_id=message.author.id,
                author_name=str(message.author),
                content=message.content,
                attachments=[{
                    'filename': attachment.filename,
                    'url': attachment.proxy_url,
                    'content_type': attachment.content_type
                } for attachment in message.attachments]
            )
        except Exception as e:
            self.logger.error(f"메시지 삭제 로깅 오류: {e}")
            
    async def on_message_edit(self, before, after):
        """메시지 수정 이벤트 처리"""
        # 봇 자신의 메시지는 무시
        if before.author == self.user:
            return
            
        # 내용이 같으면 무시 (임베드 로딩 등의 이유로 발생하는 이벤트)
        if before.content == after.content:
            return
            
        # 로그 채널이 없으면 무시
        if not hasattr(self, 'log_channel') or not self.log_channel:
            return
            
        # 수정된 메시지 로깅
        embed = discord.Embed(
            title="✏️ 메시지 수정됨",
            description=f"채널: {before.channel.mention} • [메시지로 이동]({after.jump_url})",
            color=discord.Color.gold(),
            timestamp=datetime.now()
        )
        
        embed.set_author(
            name=f"{before.author.display_name} ({before.author})",
            icon_url=before.author.avatar.url if before.author.avatar else None
        )
        
        # 이전 내용
        if before.content:
            # 내용이 너무 길면 자르기
            content = before.content
            if len(content) > 1024:
                content = content[:1021] + "..."
            embed.add_field(name="이전 내용", value=content, inline=False)
        else:
            embed.add_field(name="이전 내용", value="*내용 없음*", inline=False)
            
        # 새 내용
        if after.content:
            # 내용이 너무 길면 자르기
            content = after.content
            if len(content) > 1024:
                content = content[:1021] + "..."
            embed.add_field(name="새 내용", value=content, inline=False)
        else:
            embed.add_field(name="새 내용", value="*내용 없음*", inline=False)
            
        # 메시지 ID 추가
        embed.add_field(name="메시지 ID", value=before.id, inline=True)
        
        # 로그 채널에 전송
        await self.log_channel.send(embed=embed)
        
        # 데이터베이스에 로깅
        try:
            await self.message_log_model.log_message_edit(
                message_id=before.id,
                channel_id=before.channel.id,
                channel_name=before.channel.name,
                author_id=before.author.id,
                author_name=str(before.author),
                before_content=before.content,
                after_content=after.content
            )
        except Exception as e:
            self.logger.error(f"메시지 수정 로깅 오류: {e}")
            
    async def on_member_join(self, member):
        """멤버 입장 이벤트 처리"""
        # 로그 채널이 없으면 무시
        if not hasattr(self, 'log_channel') or not self.log_channel:
            return
            
        # 멤버 입장 로깅
        embed = discord.Embed(
            title="👋 멤버 입장",
            description=f"{member.mention}님이 서버에 입장했습니다.",
            color=discord.Color.green(),
            timestamp=datetime.now()
        )
        
        embed.set_author(
            name=f"{member.name}#{member.discriminator}",
            icon_url=member.avatar.url if member.avatar else None
        )
        
        embed.add_field(name="계정 생성일", value=member.created_at.strftime("%Y-%m-%d %H:%M:%S"), inline=True)
        embed.add_field(name="ID", value=member.id, inline=True)
        
        # 계정 생성 후 경과 시간
        account_age = datetime.now() - member.created_at.replace(tzinfo=None)
        days = account_age.days
        hours, remainder = divmod(account_age.seconds, 3600)
        minutes, _ = divmod(remainder, 60)
        
        age_text = f"{days}일 {hours}시간 {minutes}분"
        embed.add_field(name="계정 나이", value=age_text, inline=True)
        
        # 새 계정 여부 (7일 이내)
        if days < 7:
            embed.add_field(name="⚠️ 주의", value="최근에 생성된 계정입니다.", inline=False)
            
        # 로그 채널에 전송
        await self.log_channel.send(embed=embed)
        
    async def on_member_remove(self, member):
        """멤버 퇴장 이벤트 처리"""
        # 로그 채널이 없으면 무시
        if not hasattr(self, 'log_channel') or not self.log_channel:
            return
            
        # 멤버 퇴장 로깅
        embed = discord.Embed(
            title="👋 멤버 퇴장",
            description=f"{member.mention}님이 서버에서 나갔습니다.",
            color=discord.Color.red(),
            timestamp=datetime.now()
        )
        
        embed.set_author(
            name=f"{member.name}#{member.discriminator}",
            icon_url=member.avatar.url if member.avatar else None
        )
        
        # 서버 참여 기간
        if member.joined_at:
            join_duration = datetime.now() - member.joined_at.replace(tzinfo=None)
            days = join_duration.days
            hours, remainder = divmod(join_duration.seconds, 3600)
            minutes, _ = divmod(remainder, 60)
            
            duration_text = f"{days}일 {hours}시간 {minutes}분"
            embed.add_field(name="서버 참여 기간", value=duration_text, inline=True)
            embed.add_field(name="참여일", value=member.joined_at.strftime("%Y-%m-%d %H:%M:%S"), inline=True)
            
        embed.add_field(name="ID", value=member.id, inline=True)
        
        # 역할 정보
        if len(member.roles) > 1:  # @everyone 제외
            role_names = [role.name for role in member.roles[1:]]
            roles_text = ", ".join(role_names)
            if len(roles_text) > 1024:
                roles_text = roles_text[:1021] + "..."
            embed.add_field(name="역할", value=roles_text, inline=False)
            
        # 로그 채널에 전송
        await self.log_channel.send(embed=embed)
    
    def create_progress_bar(self, progress, length=10):
        """
        Create a text-based progress bar.
        
        Args:
            progress (float): Progress value between 0 and 1
            length (int): Length of the progress bar
            
        Returns:
            str: Text progress bar
        """
        filled = int(progress * length)
        empty = length - filled
        return '█' * filled + '░' * empty
    
    async def process_message_points(self, message):
        """메시지 기반 포인트 적립"""
        # Ignore bot messages
        if message.author.bot:
            return
            
        # Check cooldown
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