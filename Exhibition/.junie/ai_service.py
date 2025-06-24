"""
OpenAI API 연동 서비스
"""

import asyncio
import json
import time
from typing import Dict, List, Optional, Tuple, Any
import openai
from config.settings import settings
from utils.decorators import retry_with_backoff
import logging

logger = logging.getLogger(__name__)


class AIService:
    """OpenAI API 서비스"""

    def __init__(self):
        openai.api_key = settings.openai_api_key
        self.model = settings.openai_model
        self.max_tokens = settings.openai_max_tokens
        self.temperature = settings.openai_temperature

        # 요청 제한 관리
        self.request_count = {}
        self.last_reset = time.time()

    def _check_rate_limit(self, user_id: str) -> bool:
        """사용자별 요청 제한 확인"""
        now = time.time()

        # 1시간마다 리셋
        if now - self.last_reset > 3600:
            self.request_count.clear()
            self.last_reset = now

        user_requests = self.request_count.get(user_id, 0)
        return user_requests < settings.max_ai_requests_per_user_per_hour

    def _increment_usage(self, user_id: str):
        """사용량 카운트 증가"""
        self.request_count[user_id] = self.request_count.get(user_id, 0) + 1

    @retry_with_backoff(max_retries=3)
    async def generate_response(
        self, 
        prompt: str, 
        system_message: Optional[str] = None,
        context: Optional[List[Dict]] = None,
        user_id: Optional[str] = None
    ) -> Tuple[str, Dict]:
        """AI 응답 생성"""

        # 요청 제한 확인
        if user_id and not self._check_rate_limit(user_id):
            raise Exception("시간당 요청 제한을 초과했습니다.")

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

            # OpenAI API 호출
            response = await openai.ChatCompletion.acreate(
                model=self.model,
                messages=messages,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                timeout=30
            )

            content = response.choices[0].message.content
            metadata = {
                "tokens_used": response.usage.total_tokens,
                "model": self.model,
                "finish_reason": response.choices[0].finish_reason,
                "timestamp": time.time()
            }

            # 사용량 증가
            if user_id:
                self._increment_usage(user_id)

            logger.info(f"AI 응답 생성 완료 - 토큰 사용: {metadata['tokens_used']}")
            return content, metadata

        except openai.error.RateLimitError:
            logger.warning("OpenAI API 요청 제한 도달")
            raise Exception("API 요청 제한에 도달했습니다. 잠시 후 다시 시도해주세요.")

        except openai.error.InvalidRequestError as e:
            logger.error(f"잘못된 요청: {e}")
            raise Exception("요청이 잘못되었습니다. 입력을 확인해주세요.")

        except Exception as e:
            logger.error(f"AI 응답 생성 실패: {e}")
            raise

    async def analyze_intent(self, message: str, user_id: str) -> Dict[str, Any]:
        """사용자 메시지의 의도 분석"""
        system_message = """
        사용자의 메시지를 분석하여 다음 정보를 JSON 형태로 반환해주세요:
        {
            "intent": "커맨드_생성 | 정보_요청 | 일반_대화 | 도움말_요청 | 관리_명령",
            "confidence": 0.0-1.0,
            "entities": {
                "command_name": "추출된 커맨드 이름 (있다면)",
                "action": "수행할 작업",
                "parameters": ["매개변수1", "매개변수2"],
                "topic": "주제나 도메인"
            },
            "sentiment": "positive | neutral | negative",
            "urgency": "low | medium | high"
        }

        의도 분류 기준:
        - 커맨드_생성: "만들어줘", "생성해줘", "추가해줘" 등의 표현이 포함된 경우
        - 정보_요청: 질문이나 정보를 묻는 경우
        - 일반_대화: 단순한 대화나 인사
        - 도움말_요청: 도움이나 사용법을 묻는 경우
        - 관리_명령: 관리자 기능과 관련된 요청
        """

        try:
            response, _ = await self.generate_response(
                message, 
                system_message=system_message,
                user_id=user_id
            )
            return json.loads(response)
        except json.JSONDecodeError:
            logger.warning("의도 분석 결과 JSON 파싱 실패")
            return {
                "intent": "일반_대화", 
                "confidence": 0.5, 
                "entities": {},
                "sentiment": "neutral",
                "urgency": "low"
            }
        except Exception as e:
            logger.error(f"의도 분석 실패: {e}")
            return {
                "intent": "일반_대화", 
                "confidence": 0.3, 
                "entities": {},
                "sentiment": "neutral",
                "urgency": "low"
            }

    async def generate_command_metadata(
        self, 
        user_description: str,
        user_id: str
    ) -> Dict[str, str]:
        """사용자 설명으로부터 커맨드 메타데이터 생성"""
        system_message = """
        사용자가 요청한 기능을 바탕으로 Discord 슬래시 커맨드의 메타데이터를 생성해주세요.
        다음 JSON 형태로 정확히 응답해주세요:

        {
            "name": "커맨드_이름",
            "description": "커맨드 설명 (100자 이내)",
            "response_template": "응답 템플릿 (변수는 {variable} 형태로 사용)",
            "parameters": ["param1", "param2"],
            "category": "일반|관리|정보|유틸리티",
            "usage_example": "/커맨드_이름 예시"
        }

        중요한 규칙:
        1. 커맨드 이름은 영문 소문자, 숫자, 언더스코어만 사용
        2. 1-32자 제한
        3. Discord 예약어 피하기 (help, info 등)
        4. 응답 템플릿에는 {user}, {input} 같은 변수 활용
        5. 한국어 설명은 명확하고 간결하게
        """

        try:
            response, _ = await self.generate_response(
                user_description,
                system_message=system_message,
                user_id=user_id
            )
            metadata = json.loads(response)

            # 기본값 설정
            if "category" not in metadata:
                metadata["category"] = "일반"
            if "usage_example" not in metadata:
                metadata["usage_example"] = f"/{metadata.get('name', 'example')}"

            return metadata

        except json.JSONDecodeError:
            logger.error("커맨드 메타데이터 JSON 파싱 실패")
            raise Exception("커맨드 메타데이터 생성에 실패했습니다.")
        except Exception as e:
            logger.error(f"커맨드 메타데이터 생성 실패: {e}")
            raise

    async def enhance_response(
        self, 
        base_template: str, 
        user_input: str,
        context: Optional[Dict] = None,
        user_id: Optional[str] = None
    ) -> str:
        """기본 템플릿을 AI로 향상시킨 응답 생성"""
        system_message = f"""
        다음 템플릿을 기반으로 사용자의 입력에 맞는 자연스럽고 도움이 되는 응답을 생성해주세요:

        템플릿: {base_template}

        응답 가이드라인:
        1. 친근하고 도움이 되는 톤으로 작성
        2. 사용자의 구체적인 요청에 맞게 개인화
        3. 이모지를 적절히 사용하여 친근함 표현
        4. 정보가 부족하면 추가 질문 유도
        5. 최대 500자 이내로 작성

        컨텍스트가 제공되면 이를 활용하여 더 정확한 응답을 생성해주세요.
        """

        prompt = f"사용자 입력: {user_input}"
        if context:
            prompt += f"\n추가 컨텍스트: {json.dumps(context, ensure_ascii=False)}"

        try:
            response, _ = await self.generate_response(
                prompt,
                system_message=system_message,
                user_id=user_id
            )
            return response
        except Exception as e:
            logger.error(f"응답 향상 실패: {e}")
            # 실패 시 기본 템플릿에 사용자 정보만 치환하여 반환
            return base_template.format(
                user=context.get("user", "사용자") if context else "사용자",
                input=user_input
            )

    async def moderate_content(self, content: str) -> Dict[str, Any]:
        """콘텐츠 조절 (유해성 검사)"""
        try:
            response = await openai.Moderation.acreate(input=content)
            result = response.results[0]

            return {
                "flagged": result.flagged,
                "categories": result.categories,
                "category_scores": result.category_scores
            }
        except Exception as e:
            logger.error(f"콘텐츠 조절 실패: {e}")
            return {"flagged": False, "categories": {}, "category_scores": {}}


# 전역 AI 서비스 인스턴스
ai_service = AIService()
