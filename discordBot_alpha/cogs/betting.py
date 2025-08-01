import discord
from discord.ext import commands
import asyncio
from datetime import datetime, timedelta
import logging
import re

from utils.permissions import PermissionLevel, PermissionChecker
from utils.decorators import require_permission, error_handler, cooldown
from utils.helpers import MessageFormatter, InputValidator
from database.models import UserPointsModel
from database.betting_models import BettingModel
from config.settings import Settings

class BettingView(discord.ui.View):
    """
    View for betting on options.
    """
    def __init__(self, betting_model, point_model, event_id, options, timeout=600):
        super().__init__(timeout=timeout)
        self.betting_model = betting_model
        self.point_model = point_model
        self.event_id = event_id
        self.options = options
        
        # Add buttons for each option
        for option in options:
            button = discord.ui.Button(
                label=option['name'],
                custom_id=f"bet_{option['id']}",
                style=discord.ButtonStyle.primary
            )
            button.callback = self.make_callback(option)
            self.add_item(button)
            
    def make_callback(self, option):
        """Create a callback for a betting option button."""
        async def callback(interaction):
            # Create a modal for entering bet amount
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
    """
    Modal for entering bet amount.
    """
    def __init__(self, betting_model, point_model, event_id, option, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.betting_model = betting_model
        self.point_model = point_model
        self.event_id = event_id
        self.option = option
        
        self.amount_input = discord.ui.TextInput(
            label="베팅 금액 (5,000 ~ 100,000)",
            placeholder="베팅할 포인트 금액을 입력하세요",
            min_length=1,
            max_length=10,
            required=True
        )
        self.add_item(self.amount_input)
        
    async def on_submit(self, interaction):
        """Handle modal submission."""
        # Parse the amount
        try:
            # Remove commas and non-numeric characters
            amount_str = re.sub(r'[^0-9]', '', self.amount_input.value)
            amount = int(amount_str)
            
            # Validate amount
            if amount < 5000:
                await interaction.response.send_message("❌ 최소 베팅 금액은 5,000 포인트입니다.", ephemeral=True)
                return
                
            if amount > 100000:
                await interaction.response.send_message("❌ 최대 베팅 금액은 100,000 포인트입니다.", ephemeral=True)
                return
                
            # Check if user has enough points
            user_points = await self.point_model.get_user_points(interaction.user.id)
            
            if not user_points or user_points['points'] < amount:
                await interaction.response.send_message(
                    f"❌ 포인트가 부족합니다. 현재 보유 포인트: {user_points['points'] if user_points else 0:,}",
                    ephemeral=True
                )
                return
                
            # Remove points from user
            success, message = await self.point_model.remove_points(
                user_id=interaction.user.id,
                amount=amount,
                reason=f"베팅: {self.option['name']}"
            )
            
            if not success:
                await interaction.response.send_message(f"❌ 포인트 차감 중 오류가 발생했습니다: {message}", ephemeral=True)
                return
                
            # Place the bet
            success, message, bet_id = await self.betting_model.place_bet(
                user_id=interaction.user.id,
                event_id=self.event_id,
                option_id=self.option['id'],
                amount=amount
            )
            
            if success:
                # Calculate potential winnings
                potential_winnings = int(amount * self.option['odds'])
                
                embed = discord.Embed(
                    title="✅ 베팅 완료",
                    description=f"{interaction.user.mention}님이 **{self.option['name']}**에 **{amount:,}** 포인트를 베팅했습니다!",
                    color=discord.Color.green()
                )
                embed.add_field(name="배당률", value=f"{self.option['odds']:.2f}x", inline=True)
                embed.add_field(name="예상 획득 포인트", value=f"{potential_winnings:,}", inline=True)
                
                await interaction.response.send_message(embed=embed)
            else:
                # Refund points
                await self.point_model.add_points(
                    user_id=interaction.user.id,
                    username=str(interaction.user),
                    amount=amount,
                    reason="베팅 실패 환불"
                )
                
                await interaction.response.send_message(f"❌ 베팅 중 오류가 발생했습니다: {message}", ephemeral=True)
                
        except ValueError:
            await interaction.response.send_message("❌ 유효한 금액을 입력해주세요.", ephemeral=True)

class Betting(commands.Cog):
    """
    Betting system for the bot.
    Allows users to bet on events and win points.
    """
    
    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger('discord_bot.betting')
        self.point_model = UserPointsModel(bot.db)
        self.betting_model = BettingModel(bot.db)
        self.formatter = MessageFormatter()
        
    @commands.group(name="배팅", aliases=["bet"], invoke_without_command=True)
    @error_handler
    async def betting(self, ctx):
        """배팅 명령어 그룹"""
        events = await self.betting_model.get_active_betting_events(ctx.guild.id)
        
        if not events:
            embed = discord.Embed(
                title="🎲 배팅",
                description="현재 진행 중인 배팅 이벤트가 없습니다.",
                color=discord.Color.orange()
            )
            await ctx.send(embed=embed)
            return
            
        embed = discord.Embed(
            title="🎲 배팅",
            description="현재 진행 중인 배팅 이벤트 목록입니다.",
            color=discord.Color.blue()
        )
        
        for event in events:
            embed.add_field(
                name=event['title'],
                value=f"ID: {event['id']}\n{event['description'] or '설명 없음'}\n"
                      f"생성일: {event['created_at'].strftime('%Y-%m-%d %H:%M')}",
                inline=False
            )
            
        embed.set_footer(text=f"배팅에 참여하려면 '{ctx.prefix}배팅 참여 [이벤트ID]' 명령어를 사용하세요.")
        
        await ctx.send(embed=embed)
        
    @betting.command(name="참여", aliases=["join"])
    @error_handler
    async def join_betting(self, ctx, event_id: int):
        """
        배팅 이벤트에 참여합니다.
        
        Args:
            event_id (int): 참여할 이벤트 ID
        """
        # Get the event
        event = await self.betting_model.get_betting_event(event_id)
        
        if not event:
            await ctx.send("❌ 해당 ID의 배팅 이벤트를 찾을 수 없습니다.")
            return
            
        if event['status'] != 'OPEN':
            await ctx.send("❌ 이 배팅 이벤트는 더 이상 참여할 수 없습니다.")
            return
            
        # Get the options
        options = await self.betting_model.get_betting_options(event_id)
        
        if not options:
            await ctx.send("❌ 이 배팅 이벤트에는 옵션이 없습니다.")
            return
            
        # Create embed with event details
        embed = discord.Embed(
            title=f"🎲 {event['title']}",
            description=event['description'] or "설명 없음",
            color=discord.Color.blue()
        )
        
        # Add options
        for option in options:
            embed.add_field(
                name=f"{option['name']} (배당률: {option['odds']:.2f}x)",
                value=option['description'] or "설명 없음",
                inline=False
            )
            
        embed.set_footer(text="아래 버튼을 클릭하여 베팅하세요. 최소 5,000 포인트, 최대 100,000 포인트까지 베팅 가능합니다.")
        
        # Create view with betting options
        view = BettingView(self.betting_model, self.point_model, event_id, options)
        
        await ctx.send(embed=embed, view=view)
        
    @betting.command(name="내역", aliases=["mybets"])
    @error_handler
    async def my_bets(self, ctx, status: str = None):
        """
        내 베팅 내역을 확인합니다.
        
        Args:
            status (str, optional): 필터링할 상태 (ACTIVE, WON, LOST, REFUNDED)
        """
        # Validate status
        valid_statuses = ['ACTIVE', 'WON', 'LOST', 'REFUNDED']
        if status and status.upper() not in valid_statuses:
            await ctx.send(f"❌ 유효한 상태가 아닙니다. 가능한 값: {', '.join(valid_statuses)}")
            return
            
        status = status.upper() if status else None
        
        # Get user bets
        bets = await self.betting_model.get_user_bets(ctx.author.id, status)
        
        if not bets:
            embed = discord.Embed(
                title="📜 내 베팅 내역",
                description=f"베팅 내역이 없습니다{f' (상태: {status})' if status else ''}.",
                color=discord.Color.orange()
            )
            await ctx.send(embed=embed)
            return
            
        embed = discord.Embed(
            title="📜 내 베팅 내역",
            description=f"{ctx.author.mention}님의 베팅 내역입니다{f' (상태: {status})' if status else ''}.",
            color=discord.Color.blue()
        )
        
        for bet in bets:
            status_emoji = {
                'ACTIVE': '⏳',
                'WON': '🏆',
                'LOST': '❌',
                'REFUNDED': '💰'
            }.get(bet['status'], '❓')
            
            field_value = (
                f"이벤트: {bet['event_title']}\n"
                f"옵션: {bet['option_name']} (배당률: {bet['odds']:.2f}x)\n"
                f"베팅 금액: {bet['amount']:,} 포인트\n"
                f"예상 획득: {bet['potential_winnings']:,} 포인트\n"
                f"상태: {status_emoji} {bet['status']}"
            )
            
            if bet['settled_at']:
                field_value += f"\n정산일: {bet['settled_at'].strftime('%Y-%m-%d %H:%M')}"
                
            embed.add_field(
                name=f"베팅 #{bet['id']} ({bet['placed_at'].strftime('%Y-%m-%d %H:%M')})",
                value=field_value,
                inline=False
            )
            
        await ctx.send(embed=embed)
        
    @commands.command(name="배팅판", aliases=["createbet"])
    @require_permission(PermissionLevel.ADMIN)
    @error_handler
    async def create_bet(self, ctx, *, teams_info: str):
        """
        새 배팅 이벤트를 생성합니다.
        
        Args:
            teams_info (str): 팀 정보 (형식: "팀개수 & 팀명: 1팀: a팀, 2팀: b팀, 3팀: c팀 등...")
        """
        # Parse teams info
        try:
            # Extract team names
            teams = []
            
            # Check if the format is correct
            if "팀개수 & 팀명:" not in teams_info:
                await ctx.send("❌ 올바른 형식이 아닙니다. 예시: `팀개수 & 팀명: 1팀: a팀, 2팀: b팀`")
                return
                
            # Extract the part after "팀개수 & 팀명:"
            teams_part = teams_info.split("팀개수 & 팀명:")[1].strip()
            
            # Split by comma and extract team names
            team_entries = teams_part.split(",")
            for entry in team_entries:
                entry = entry.strip()
                if ":" in entry:
                    team_name = entry.split(":", 1)[1].strip()
                    teams.append(team_name)
                    
            if not teams:
                await ctx.send("❌ 팀 정보를 추출할 수 없습니다.")
                return
                
            # Create a new betting event
            event_title = f"내전 배팅: {' vs '.join(teams)}"
            event_description = f"팀: {', '.join(teams)}\n배팅 가능 시간: 경기 시작 전까지"
            
            event_id = await self.betting_model.create_betting_event(
                guild_id=ctx.guild.id,
                creator_id=ctx.author.id,
                title=event_title,
                description=event_description
            )
            
            if not event_id:
                await ctx.send("❌ 배팅 이벤트 생성 중 오류가 발생했습니다.")
                return
                
            # Add options for each team
            options = []
            for i, team in enumerate(teams):
                option_id = await self.betting_model.add_betting_option(
                    event_id=event_id,
                    name=team,
                    description=f"{team} 승리",
                    odds=2.0  # Default odds
                )
                
                if option_id:
                    options.append({
                        'id': option_id,
                        'name': team,
                        'odds': 2.0
                    })
                    
            if not options:
                # Cancel the event if no options were added
                await self.betting_model.cancel_betting_event(event_id)
                await ctx.send("❌ 배팅 옵션 추가 중 오류가 발생했습니다.")
                return
                
            # Create embed with event details
            embed = discord.Embed(
                title=f"🎲 {event_title}",
                description=event_description,
                color=discord.Color.blue()
            )
            
            # Add options
            for option in options:
                embed.add_field(
                    name=f"{option['name']} (배당률: {option['odds']:.2f}x)",
                    value="승리 시 베팅 금액의 2배를 획득합니다.",
                    inline=False
                )
                
            embed.add_field(
                name="베팅 방법",
                value=f"`{ctx.prefix}배팅 참여 {event_id}` 명령어로 베팅에 참여하세요.",
                inline=False
            )
            
            embed.set_footer(text=f"이벤트 ID: {event_id} | 최소 5,000 포인트, 최대 100,000 포인트까지 베팅 가능합니다.")
            
            # Send the embed
            await ctx.send(embed=embed)
            
            # Create a view with betting options
            view = BettingView(self.betting_model, self.point_model, event_id, options)
            
            await ctx.send("아래 버튼을 클릭하여 바로 베팅할 수 있습니다:", view=view)
            
        except Exception as e:
            self.logger.error(f"Error creating betting event: {e}")
            await ctx.send(f"❌ 배팅 이벤트 생성 중 오류가 발생했습니다: {e}")
            
    @betting.group(name="관리", aliases=["admin"], invoke_without_command=True)
    @require_permission(PermissionLevel.ADMIN)
    @error_handler
    async def betting_admin(self, ctx):
        """배팅 관리 명령어 그룹"""
        embed = discord.Embed(
            title="🛠️ 배팅 관리",
            description="배팅 관리 명령어 목록입니다.",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="배팅 이벤트 관리",
            value=(
                f"`{ctx.prefix}배팅판 \"팀개수 & 팀명: 1팀: a팀, 2팀: b팀\"` - 새 배팅 이벤트를 생성합니다.\n"
                f"`{ctx.prefix}배팅 관리 마감 [이벤트ID]` - 배팅을 마감합니다.\n"
                f"`{ctx.prefix}배팅 관리 정산 [이벤트ID] [당첨옵션ID]` - 배팅을 정산합니다.\n"
                f"`{ctx.prefix}배팅 관리 취소 [이벤트ID]` - 배팅을 취소하고 환불합니다."
            ),
            inline=False
        )
        
        await ctx.send(embed=embed)
        
    @betting_admin.command(name="마감", aliases=["lock"])
    @require_permission(PermissionLevel.ADMIN)
    @error_handler
    async def lock_betting(self, ctx, event_id: int):
        """
        배팅을 마감합니다.
        
        Args:
            event_id (int): 마감할 이벤트 ID
        """
        # Get the event
        event = await self.betting_model.get_betting_event(event_id)
        
        if not event:
            await ctx.send("❌ 해당 ID의 배팅 이벤트를 찾을 수 없습니다.")
            return
            
        if event['status'] != 'OPEN':
            await ctx.send("❌ 이 배팅 이벤트는 이미 마감되었거나 정산되었습니다.")
            return
            
        # Lock the event
        success = await self.betting_model.lock_betting_event(event_id)
        
        if success:
            embed = discord.Embed(
                title="🔒 배팅 마감",
                description=f"'{event['title']}' 배팅이 마감되었습니다.",
                color=discord.Color.orange()
            )
            
            # Get all bets for this event
            bets = await self.betting_model.get_event_bets(event_id)
            
            if bets:
                total_bets = len(bets)
                total_amount = sum(bet['amount'] for bet in bets)
                
                embed.add_field(name="총 베팅 수", value=str(total_bets), inline=True)
                embed.add_field(name="총 베팅 금액", value=f"{total_amount:,} 포인트", inline=True)
                
            await ctx.send(embed=embed)
            
            # Announce in the channel
            announce_embed = discord.Embed(
                title="🔒 배팅 마감",
                description=f"'{event['title']}' 배팅이 마감되었습니다.",
                color=discord.Color.orange(),
                timestamp=datetime.now()
            )
            
            await ctx.send(embed=announce_embed)
        else:
            await ctx.send("❌ 배팅 마감 중 오류가 발생했습니다.")
            
    @betting_admin.command(name="정산", aliases=["settle"])
    @require_permission(PermissionLevel.ADMIN)
    @error_handler
    async def settle_betting(self, ctx, event_id: int, winning_option_id: int):
        """
        배팅을 정산합니다.
        
        Args:
            event_id (int): 정산할 이벤트 ID
            winning_option_id (int): 당첨된 옵션 ID
        """
        # Get the event
        event = await self.betting_model.get_betting_event(event_id)
        
        if not event:
            await ctx.send("❌ 해당 ID의 배팅 이벤트를 찾을 수 없습니다.")
            return
            
        if event['status'] == 'SETTLED':
            await ctx.send("❌ 이 배팅 이벤트는 이미 정산되었습니다.")
            return
            
        if event['status'] == 'CANCELLED':
            await ctx.send("❌ 이 배팅 이벤트는 취소되었습니다.")
            return
            
        # Get the winning option
        winning_option = await self.betting_model.get_betting_option(winning_option_id)
        
        if not winning_option or winning_option['event_id'] != event_id:
            await ctx.send("❌ 유효하지 않은 당첨 옵션입니다.")
            return
            
        # Settle the event
        success = await self.betting_model.settle_betting_event(event_id, winning_option_id)
        
        if success:
            # Get winning bets
            winning_bets = await self.betting_model.get_winning_bets(event_id, winning_option_id)
            
            # Award points to winners
            for bet in winning_bets:
                await self.point_model.add_points(
                    user_id=bet['user_id'],
                    username=bet['username'],
                    amount=bet['potential_winnings'],
                    reason=f"배팅 당첨: {event['title']} - {winning_option['name']}"
                )
                
            # Create embed
            embed = discord.Embed(
                title="🏆 배팅 정산 완료",
                description=f"'{event['title']}' 배팅이 정산되었습니다.",
                color=discord.Color.green()
            )
            
            embed.add_field(name="당첨 옵션", value=winning_option['name'], inline=True)
            embed.add_field(name="당첨자 수", value=str(len(winning_bets)), inline=True)
            
            if winning_bets:
                total_winnings = sum(bet['potential_winnings'] for bet in winning_bets)
                embed.add_field(name="총 지급 포인트", value=f"{total_winnings:,}", inline=True)
                
            await ctx.send(embed=embed)
            
            # Announce in the channel
            announce_embed = discord.Embed(
                title="🏆 배팅 결과 발표",
                description=f"'{event['title']}' 배팅의 결과가 발표되었습니다!",
                color=discord.Color.gold(),
                timestamp=datetime.now()
            )
            
            announce_embed.add_field(name="당첨 옵션", value=f"**{winning_option['name']}**", inline=False)
            
            if winning_bets:
                # List top winners (up to 5)
                top_winners = sorted(winning_bets, key=lambda x: x['potential_winnings'], reverse=True)[:5]
                
                winners_text = ""
                for i, bet in enumerate(top_winners):
                    user = ctx.guild.get_member(bet['user_id'])
                    user_mention = user.mention if user else f"ID: {bet['user_id']}"
                    winners_text += f"{i+1}. {user_mention} - {bet['potential_winnings']:,} 포인트\n"
                    
                if winners_text:
                    announce_embed.add_field(name="🏅 상위 당첨자", value=winners_text, inline=False)
                    
            await ctx.send(embed=announce_embed)
        else:
            await ctx.send("❌ 배팅 정산 중 오류가 발생했습니다.")
            
    @betting_admin.command(name="취소", aliases=["cancel"])
    @require_permission(PermissionLevel.ADMIN)
    @error_handler
    async def cancel_betting(self, ctx, event_id: int):
        """
        배팅을 취소하고 환불합니다.
        
        Args:
            event_id (int): 취소할 이벤트 ID
        """
        # Get the event
        event = await self.betting_model.get_betting_event(event_id)
        
        if not event:
            await ctx.send("❌ 해당 ID의 배팅 이벤트를 찾을 수 없습니다.")
            return
            
        if event['status'] == 'SETTLED':
            await ctx.send("❌ 이 배팅 이벤트는 이미 정산되었습니다.")
            return
            
        if event['status'] == 'CANCELLED':
            await ctx.send("❌ 이 배팅 이벤트는 이미 취소되었습니다.")
            return
            
        # Cancel the event
        success = await self.betting_model.cancel_betting_event(event_id)
        
        if success:
            # Get all bets for this event
            bets = await self.betting_model.get_event_bets(event_id)
            
            # Refund points to all bettors
            for bet in bets:
                if bet['status'] == 'REFUNDED':
                    await self.point_model.add_points(
                        user_id=bet['user_id'],
                        username=bet['username'],
                        amount=bet['amount'],
                        reason=f"배팅 취소 환불: {event['title']}"
                    )
                    
            # Create embed
            embed = discord.Embed(
                title="🚫 배팅 취소",
                description=f"'{event['title']}' 배팅이 취소되었습니다.",
                color=discord.Color.red()
            )
            
            embed.add_field(name="환불된 베팅 수", value=str(len(bets)), inline=True)
            
            if bets:
                total_refund = sum(bet['amount'] for bet in bets)
                embed.add_field(name="총 환불 포인트", value=f"{total_refund:,}", inline=True)
                
            await ctx.send(embed=embed)
            
            # Announce in the channel
            announce_embed = discord.Embed(
                title="🚫 배팅 취소",
                description=f"'{event['title']}' 배팅이 취소되었습니다. 모든 베팅 금액이 환불됩니다.",
                color=discord.Color.red(),
                timestamp=datetime.now()
            )
            
            await ctx.send(embed=announce_embed)
        else:
            await ctx.send("❌ 배팅 취소 중 오류가 발생했습니다.")
            
    @betting_admin.command(name="목록", aliases=["list"])
    @require_permission(PermissionLevel.ADMIN)
    @error_handler
    async def list_betting_events(self, ctx):
        """모든 배팅 이벤트 목록을 표시합니다."""
        # Get all events for this guild
        query = """
            SELECT * FROM betting_events 
            WHERE guild_id = %s
            ORDER BY created_at DESC
            LIMIT 10
        """
        events = await self.betting_model.execute_query(query, (ctx.guild.id,))
        
        if not events:
            await ctx.send("❌ 배팅 이벤트가 없습니다.")
            return
            
        embed = discord.Embed(
            title="📋 배팅 이벤트 목록",
            description=f"최근 {len(events)}개의 배팅 이벤트입니다.",
            color=discord.Color.blue()
        )
        
        for event in events:
            status_emoji = {
                'OPEN': '🟢',
                'LOCKED': '🔒',
                'SETTLED': '✅',
                'CANCELLED': '❌'
            }.get(event['status'], '❓')
            
            field_value = (
                f"상태: {status_emoji} {event['status']}\n"
                f"생성일: {event['created_at'].strftime('%Y-%m-%d %H:%M')}\n"
            )
            
            if event['locked_at']:
                field_value += f"마감일: {event['locked_at'].strftime('%Y-%m-%d %H:%M')}\n"
                
            if event['settled_at']:
                field_value += f"정산일: {event['settled_at'].strftime('%Y-%m-%d %H:%M')}\n"
                
            embed.add_field(
                name=f"ID: {event['id']} - {event['title']}",
                value=field_value,
                inline=False
            )
            
        await ctx.send(embed=embed)
        
    @betting_admin.command(name="정보", aliases=["info"])
    @require_permission(PermissionLevel.ADMIN)
    @error_handler
    async def betting_info(self, ctx, event_id: int):
        """
        배팅 이벤트 정보를 표시합니다.
        
        Args:
            event_id (int): 이벤트 ID
        """
        # Get the event
        event = await self.betting_model.get_betting_event(event_id)
        
        if not event:
            await ctx.send("❌ 해당 ID의 배팅 이벤트를 찾을 수 없습니다.")
            return
            
        # Get options
        options = await self.betting_model.get_betting_options(event_id)
        
        # Get bets
        bets = await self.betting_model.get_event_bets(event_id)
        
        # Create embed
        embed = discord.Embed(
            title=f"🎲 {event['title']}",
            description=event['description'] or "설명 없음",
            color=discord.Color.blue()
        )
        
        # Add event details
        status_emoji = {
            'OPEN': '🟢',
            'LOCKED': '🔒',
            'SETTLED': '✅',
            'CANCELLED': '❌'
        }.get(event['status'], '❓')
        
        embed.add_field(name="상태", value=f"{status_emoji} {event['status']}", inline=True)
        embed.add_field(name="생성일", value=event['created_at'].strftime('%Y-%m-%d %H:%M'), inline=True)
        
        if event['locked_at']:
            embed.add_field(name="마감일", value=event['locked_at'].strftime('%Y-%m-%d %H:%M'), inline=True)
            
        if event['settled_at']:
            embed.add_field(name="정산일", value=event['settled_at'].strftime('%Y-%m-%d %H:%M'), inline=True)
            
        # Add options
        if options:
            options_text = ""
            for option in options:
                option_bets = [bet for bet in bets if bet['option_id'] == option['id']]
                total_bet = sum(bet['amount'] for bet in option_bets)
                bettors_count = len(option_bets)
                
                if event['winning_option_id'] == option['id']:
                    options_text += f"🏆 **{option['name']}** (배당률: {option['odds']:.2f}x)\n"
                else:
                    options_text += f"• **{option['name']}** (배당률: {option['odds']:.2f}x)\n"
                    
                options_text += f"  베팅 수: {bettors_count}, 총액: {total_bet:,} 포인트\n"
                
            embed.add_field(name="옵션", value=options_text or "옵션 없음", inline=False)
            
        # Add bet summary
        if bets:
            total_bets = len(bets)
            total_amount = sum(bet['amount'] for bet in bets)
            
            embed.add_field(name="총 베팅 수", value=str(total_bets), inline=True)
            embed.add_field(name="총 베팅 금액", value=f"{total_amount:,} 포인트", inline=True)
            
        await ctx.send(embed=embed)

async def setup(bot):
    """Add the cog to the bot."""
    await bot.add_cog(Betting(bot))