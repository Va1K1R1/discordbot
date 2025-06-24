import discord
from discord import app_commands
from discord.ext import commands
import logging
from typing import Optional, Dict, Any, List
import time
from datetime import datetime

from src.models.database import get_db
from src.models.conversation import ConversationHistory
from src.services.ai_service import ai_service
from src.utils.helpers import create_embed, truncate_text
from src.utils.validators import validate_user_input, sanitize_user_input
from src.exceptions.custom_exceptions import AIServiceError

logger = logging.getLogger(__name__)


class AIChatCog(commands.Cog):
    """AI 채팅 명령어"""
    
    def __init__(self, bot):
        self.bot = bot
        self.conversation_contexts = {}  # 사용자별 대화 컨텍스트 저장
    
    @app_commands.command(name="질문", description="AI에게 질문하고 답변을 받습니다")
    @app_commands.describe(question="AI에게 물어볼 질문")
    async def ask(self, interaction: discord.Interaction, question: str):
        """AI에게 질문"""
        try:
            # 입력 유효성 검사
            is_valid, error_message = validate_user_input(question)
            if not is_valid:
                await interaction.response.send_message(
                    f"❌ 입력 오류: {error_message}",
                    ephemeral=True
                )
                return
            
            # 입력 정제
            question = sanitize_user_input(question)
            
            # 응답 지연 표시
            await interaction.response.defer()
            
            # 처리 시간 측정 시작
            start_time = time.time()
            
            # AI 응답 생성
            system_message = """
            당신은 Discord 봇에 내장된 AI 비서입니다.
            사용자의 질문에 친절하고 도움이 되는 방식으로 답변해주세요.
            답변은 간결하고 명확하게 작성하되, 필요한 정보는 충분히 제공해주세요.
            """
            
            response_content, metadata = await ai_service.generate_response(
                prompt=question,
                system_message=system_message
            )
            
            # 처리 시간 계산
            processing_time = time.time() - start_time
            
            # 의도 분석
            intent_data = await ai_service.analyze_intent(question)
            
            # 대화 기록 저장
            db = next(get_db())
            conversation = ConversationHistory(
                user_id=str(interaction.user.id),
                guild_id=str(interaction.guild.id),
                channel_id=str(interaction.channel.id),
                message=question,
                response=response_content,
                tokens_used=metadata.get("tokens_used", 0),
                processing_time=processing_time,
                intent=intent_data.get("intent", "일반 대화"),
                entities=str(intent_data.get("entities", {}))
            )
            db.add(conversation)
            db.commit()
            
            # 응답 전송
            await interaction.followup.send(truncate_text(response_content, 2000))
            
        except Exception as e:
            logger.error(f"AI 질문 처리 실패: {e}")
            await interaction.followup.send(
                "❌ 질문 처리 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.",
                ephemeral=True
            )
    
    @app_commands.command(name="대화", description="AI와 대화를 시작하거나 계속합니다")
    @app_commands.describe(message="AI에게 보낼 메시지")
    async def chat(self, interaction: discord.Interaction, message: str):
        """AI와 대화"""
        try:
            # 입력 유효성 검사
            is_valid, error_message = validate_user_input(message)
            if not is_valid:
                await interaction.response.send_message(
                    f"❌ 입력 오류: {error_message}",
                    ephemeral=True
                )
                return
            
            # 입력 정제
            message = sanitize_user_input(message)
            
            # 응답 지연 표시
            await interaction.response.defer()
            
            # 처리 시간 측정 시작
            start_time = time.time()
            
            # 사용자 컨텍스트 가져오기 또는 생성
            user_id = str(interaction.user.id)
            if user_id not in self.conversation_contexts:
                self.conversation_contexts[user_id] = []
            
            # 시스템 메시지 설정
            system_message = """
            당신은 Discord 봇에 내장된 AI 비서입니다.
            사용자와 자연스러운 대화를 이어나가세요.
            이전 대화 내용을 기억하고 맥락에 맞게 응답해주세요.
            답변은 친절하고 도움이 되게 작성하되, 간결하게 유지해주세요.
            """
            
            # 사용자 메시지 추가
            self.conversation_contexts[user_id].append({
                "role": "user",
                "content": message
            })
            
            # 컨텍스트 크기 제한 (최근 10개 메시지만 유지)
            if len(self.conversation_contexts[user_id]) > 10:
                self.conversation_contexts[user_id] = self.conversation_contexts[user_id][-10:]
            
            # AI 응답 생성
            response_content, metadata = await ai_service.generate_response(
                prompt="",  # 컨텍스트에 이미 메시지가 포함되어 있으므로 빈 문자열 전달
                system_message=system_message,
                context=self.conversation_contexts[user_id]
            )
            
            # AI 응답 컨텍스트에 추가
            self.conversation_contexts[user_id].append({
                "role": "assistant",
                "content": response_content
            })
            
            # 처리 시간 계산
            processing_time = time.time() - start_time
            
            # 대화 기록 저장
            db = next(get_db())
            conversation = ConversationHistory(
                user_id=user_id,
                guild_id=str(interaction.guild.id),
                channel_id=str(interaction.channel.id),
                message=message,
                response=response_content,
                tokens_used=metadata.get("tokens_used", 0),
                processing_time=processing_time,
                intent="대화",
                entities="{}"
            )
            db.add(conversation)
            db.commit()
            
            # 응답 전송
            await interaction.followup.send(truncate_text(response_content, 2000))
            
        except Exception as e:
            logger.error(f"AI 대화 처리 실패: {e}")
            await interaction.followup.send(
                "❌ 대화 처리 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.",
                ephemeral=True
            )
    
    @app_commands.command(name="대화초기화", description="현재 진행 중인 AI 대화를 초기화합니다")
    async def reset_chat(self, interaction: discord.Interaction):
        """대화 컨텍스트 초기화"""
        user_id = str(interaction.user.id)
        
        if user_id in self.conversation_contexts:
            del self.conversation_contexts[user_id]
            await interaction.response.send_message(
                "✅ 대화가 초기화되었습니다. 새로운 대화를 시작할 수 있습니다.",
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                "ℹ️ 진행 중인 대화가 없습니다.",
                ephemeral=True
            )
    
    @app_commands.command(name="대화기록", description="최근 AI 대화 기록을 확인합니다")
    async def chat_history(self, interaction: discord.Interaction):
        """대화 기록 조회"""
        try:
            await interaction.response.defer(ephemeral=True)
            
            # 데이터베이스에서 최근 대화 기록 조회
            db = next(get_db())
            history = db.query(ConversationHistory).filter(
                ConversationHistory.user_id == str(interaction.user.id)
            ).order_by(ConversationHistory.timestamp.desc()).limit(5).all()
            
            if not history:
                await interaction.followup.send(
                    "아직 대화 기록이 없습니다.",
                    ephemeral=True
                )
                return
            
            # 임베드 생성
            embed = create_embed(
                title="🗨️ 최근 대화 기록",
                description=f"{interaction.user.mention}님의 최근 5개 대화 기록입니다.",
                color=discord.Color.blue().value
            )
            
            # 대화 기록 추가
            for i, conv in enumerate(history):
                # 날짜 형식 변환
                date_str = conv.timestamp.strftime("%Y-%m-%d %H:%M")
                
                # 질문과 응답 요약
                question = truncate_text(conv.message, 100)
                answer = truncate_text(conv.response, 100)
                
                embed.add_field(
                    name=f"{date_str}",
                    value=f"**Q:** {question}\n**A:** {answer}",
                    inline=False
                )
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"대화 기록 조회 실패: {e}")
            await interaction.followup.send(
                "❌ 대화 기록을 가져오는 중 오류가 발생했습니다.",
                ephemeral=True
            )


async def setup(bot):
    await bot.add_cog(AIChatCog(bot))
    logger.info("AIChatCog 로드 완료")