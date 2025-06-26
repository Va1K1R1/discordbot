import asyncio
import json
import logging
import time
from typing import Dict, List, Optional, Any, Tuple

from openai import OpenAI
from src.config.settings import settings
from src.exceptions.custom_exceptions import AIServiceError
from src.utils.decorators import retry_with_backoff

logger = logging.getLogger(__name__)


class AIService:
    def __init__(self):
        self.client = OpenAI(api_key=settings.openai_api_key)
        self.model = settings.openai_model
        self.max_tokens = settings.openai_max_tokens
        self.temperature = settings.openai_temperature

    @retry_with_backoff(max_retries=3)
    async def generate_response(
        self, 
        prompt: str, 
        system_message: Optional[str] = None,
        context: Optional[List[Dict]] = None
    ) -> Tuple[str, Dict]:
        """AI 응답 생성"""
        try:
            messages = []

            # 시스템 메시지 추가
            if system_message:
                messages.append({"role": "system", "content": system_message})

            # 대화 컨텍스트 추가
            if context:
                messages.extend(context)

            # 사용자 메시지 추가
            messages.append({"role": "user", "content": prompt})

            response = await asyncio.to_thread(
                self.client.chat.completions.create,
                model=self.model,
                messages=messages,
                max_tokens=self.max_tokens,
                temperature=self.temperature
            )

            content = response.choices[0].message.content
            metadata = {
                "tokens_used": response.usage.total_tokens,
                "model": self.model,
                "finish_reason": response.choices[0].finish_reason
            }

            return content, metadata

        except Exception as e:
            logger.error(f"AI 응답 생성 실패: {e}")
            raise

    async def analyze_intent(self, message: str) -> Dict[str, Any]:
        """사용자 메시지의 의도 분석"""
        system_message = """
        Analyze the user's message and return the following information in JSON format:
        {
            "intent": "command_creation | information_request | general_conversation | help_request",
            "confidence": 0.0-1.0,
            "entities": {
                "command_name": "extracted command name",
                "action": "action to perform",
                "parameters": ["parameter1", "parameter2"]
            }
        }
        """

        try:
            response, _ = await self.generate_response(
                message, 
                system_message=system_message
            )
            return json.loads(response)
        except Exception as e:
            logger.error(f"Intent analysis failed: {e}")
            return {"intent": "general_conversation", "confidence": 0.5, "entities": {}}

    async def generate_command_metadata(
        self, 
        user_description: str
    ) -> Dict[str, str]:
        """사용자 설명으로부터 커맨드 메타데이터 생성"""
        system_message = """
        Based on the user's request, generate Discord slash command metadata.
        Respond in the following JSON format:
        {
            "name": "command_name",
            "description": "command description (under 100 characters)",
            "response_template": "response template (use {variable} format for variables)",
            "parameters": ["param1", "param2"]
        }

        Command name rules:
        - Use only lowercase letters, numbers, and underscores
        - Must be 1-32 characters long
        - Follow Discord slash command naming conventions
        """

        try:
            response, _ = await self.generate_response(
                user_description,
                system_message=system_message
            )
            return json.loads(response)
        except Exception as e:
            logger.error(f"Command metadata generation failed: {e}")
            raise

    async def enhance_response(
        self, 
        base_template: str, 
        user_input: str,
        context: Optional[Dict] = None
    ) -> str:
        """응답 템플릿을 AI로 향상시킴"""
        try:
            system_message = """
            You are enhancing a Discord bot response template.
            Make the response more engaging and personalized while keeping the core functionality.
            Keep the response under 2000 characters for Discord limits.
            """
            
            enhanced_prompt = f"""
            Base template: {base_template}
            User input: {user_input}
            Context: {context or {}}
            
            Please enhance this response to be more engaging and personalized.
            """
            
            response, _ = await self.generate_response(
                enhanced_prompt,
                system_message=system_message
            )
            
            return response
            
        except Exception as e:
            logger.error(f"Response enhancement failed: {e}")
            # 실패 시 기본 템플릿 반환
            return base_template


# 전역 AI 서비스 인스턴스
ai_service = AIService()