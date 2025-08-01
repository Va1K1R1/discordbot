import discord
from discord import app_commands
from discord.ext import commands
import psutil
import platform
from datetime import datetime
from utils.helpers import MessageFormatter

class BaseCog(commands.Cog):
    """기본 명령어들을 제공하는 Cog"""
    
    def __init__(self, bot):
        self.bot = bot
        self.formatter = MessageFormatter()

    @app_commands.command(name="ping", description="봇의 응답 시간을 확인합니다")
    async def ping(self, interaction: discord.Interaction):
        latency = round(self.bot.latency * 1000)
        embed = discord.Embed(
            title="🏓 Pong!",
            description=f"응답 시간: {latency}ms",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="help", description="봇의 명령어 도움말을 표시합니다")
    async def help_command(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="📚 봇 명령어 도움말",
            description="사용 가능한 명령어들",
            color=discord.Color.blue()
        )
        embed.add_field(name="기본", value="`/ping`, `/help`, `/info`", inline=False)
        embed.add_field(name="포인트", value="`/포인트`, `/랭킹`, `/일일보상`", inline=False)
        embed.add_field(name="관리", value="`/삭제`, `/청소`, `/뮤트`", inline=False)
        embed.add_field(name="상점", value="`/상점`, `/역할구매`, `/채널구매`", inline=False)
        embed.add_field(name="도박", value="`/룰렛`, `/뽑기함구매`", inline=False)
        embed.add_field(name="베팅", value="`/베팅`, `/베팅참여`", inline=False)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="info", description="봇 정보를 표시합니다")
    async def info(self, interaction: discord.Interaction):
        # 시스템 정보 수집
        process = psutil.Process()
        memory_info = process.memory_info()
        memory_mb = memory_info.rss / 1024 / 1024
        
        # 봇 가동 시간 계산 (간단한 버전)
        uptime = "온라인"
        
        embed = discord.Embed(
            title="🤖 봇 정보",
            color=discord.Color.purple(),
            timestamp=datetime.now()
        )
        embed.add_field(name="서버 수", value=len(self.bot.guilds), inline=True)
        embed.add_field(name="사용자 수", value=len(self.bot.users), inline=True)
        embed.add_field(name="가동 시간", value=uptime, inline=True)
        embed.add_field(name="메모리 사용량", value=f"{memory_mb:.1f} MB", inline=True)
        embed.add_field(name="플랫폼", value=platform.system(), inline=True)
        embed.add_field(name="Python 버전", value=platform.python_version(), inline=True)
        
        if self.bot.user.avatar:
            embed.set_thumbnail(url=self.bot.user.avatar.url)
            
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(BaseCog(bot))