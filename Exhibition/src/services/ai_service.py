from openai import OpenAI
import asyncio
import json
from typing import Dict, List, Optional, Tuple, Any
from src.config.settings import settings
from src.utils.decorators import retry_with_backoff
import logging

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
        사용자의 메시지를 분석하여 다음 정보를 JSON 형태로 반환해주세요:
        {
            "intent": "커맨드 생성 | 정보 요청 | 일반 대화 | 도움말 요청",
            "confidence": 0.0-1.0,
            "entities": {
                "command_name": "추출된 커맨드 이름",
                "action": "수행할 작업",
                "parameters": ["매개변수1", "매개변수2"]
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
            logger.error(f"의도 분석 실패: {e}")
            return {"intent": "일반 대화", "confidence": 0.5, "entities": {}}

    async def generate_command_metadata(
        self, 
        user_description: str
    ) -> Dict[str, str]:
        """사용자 설명으로부터 커맨드 메타데이터 생성"""
        system_message = """
        사용자가 요청한 기능을 바탕으로 Discord 슬래시 커맨드의 메타데이터를 생성해주세요.
        다음 JSON 형태로 응답해주세요:
        {
            "name": "커맨드_이름",
            "description": "커맨드 설명 (100자 이내)",
            "response_template": "응답 템플릿 (변수는 {variable} 형태)",
            "parameters": ["param1", "param2"]
        }

        커맨드 이름은 영문 소문자, 숫자, 언더스코어만 사용하고, 
        Discord 규칙에 맞게 1-32자로 제한해주세요.
        """

        try:
            response, _ = await self.generate_response(
                user_description,
                system_message=system_message
            )
            return json.loads(response)
        except Exception as e:
            logger.error(f"커맨드 메타데이터 생성 실패: {e}")
            raise

    async def enhance_response(
        self, 
        base_template: str, 
        user_input: str,
        context: Optional[Dict] = None
    ) -> str:
        """기본 템플릿을 AI로 향상시킨 응답 생성"""
        system_message = f"""
        다음 템플릿을 기반으로 사용자의 입력에 맞는 자연스럽고 도움이 되는 응답을 생성해주세요:

        템플릿: {base_template}

        응답은 친근하고 도움이 되는 톤으로 작성하며, 
        사용자의 구체적인 요청에 맞게 개인화해주세요.
        """

        prompt = f"사용자 입력: {user_input}"
        if context:
            prompt += f"\n추가 컨텍스트: {json.dumps(context, ensure_ascii=False)}"

        try:
            response, _ = await self.generate_response(
                prompt,
                system_message=system_message
            )
            return response
        except Exception as e:
            logger.error(f"응답 향상 실패: {e}")
            return base_template  # 실패 시 기본 템플릿 반환


# 전역 AI 서비스 인스턴스
ai_service = AIService()
