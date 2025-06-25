# test_bot.py
import discord
import asyncio
import logging

# 로깅 설정
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger()

# 인텐트 설정
intents = discord.Intents.default()
intents.message_content = True

# 클라이언트 생성
client = discord.Client(intents=intents)

@client.event
async def on_connect():
    print("🔌 CONNECT 이벤트 발생!")

@client.event
async def on_ready():
    print("✅ READY 이벤트 발생!")
    print(f"봇 이름: {client.user.name}")
    print(f"봇 ID: {client.user.id}")
    print(f"서버 수: {len(client.guilds)}")
    
    # 연결된 서버 목록 출력
    for guild in client.guilds:
        print(f" - {guild.name} (ID: {guild.id})")

# 봇 실행
async def main():
    print("🚀 봇 시작 중...")
    try:
        await client.start("REDACTED_DISCORD_TOKEN")
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
    finally:
        print("종료 처리 중...")
        await client.close()

# 실행
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("사용자에 의한 중단")