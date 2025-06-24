# 추가 핵심 서비스 파일들 생성

# services/ai_service.py - AI 서비스 구현
ai_service_content = '''"""
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
            prompt += f"\\n추가 컨텍스트: {json.dumps(context, ensure_ascii=False)}"
        
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
'''

# utils/decorators.py - 유틸리티 데코레이터
decorators_content = '''"""
유틸리티 데코레이터
"""

import asyncio
import functools
import time
import logging
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


def retry_with_backoff(max_retries: int = 3, base_delay: float = 1.0):
    """지수 백오프를 사용한 재시도 데코레이터"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            last_exception = None
            
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        delay = base_delay * (2 ** attempt)
                        logger.warning(
                            f"{func.__name__} 실패 (시도 {attempt + 1}/{max_retries}), "
                            f"{delay}초 후 재시도: {e}"
                        )
                        await asyncio.sleep(delay)
                    else:
                        logger.error(f"{func.__name__} 최종 실패: {e}")
            
            raise last_exception
        return wrapper
    return decorator


def rate_limit(calls_per_minute: int):
    """분당 호출 횟수 제한 데코레이터"""
    def decorator(func: Callable) -> Callable:
        calls = []
        
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            now = time.time()
            # 1분 이전 호출 기록 제거
            while calls and calls[0] <= now - 60:
                calls.pop(0)
            
            if len(calls) >= calls_per_minute:
                raise Exception(f"분당 {calls_per_minute}회 호출 제한을 초과했습니다.")
            
            calls.append(now)
            return await func(*args, **kwargs)
        return wrapper
    return decorator


def log_execution_time(func: Callable) -> Callable:
    """실행 시간 로깅 데코레이터"""
    @functools.wraps(func)
    async def wrapper(*args, **kwargs) -> Any:
        start_time = time.time()
        try:
            result = await func(*args, **kwargs)
            execution_time = time.time() - start_time
            logger.info(f"{func.__name__} 실행 완료: {execution_time:.2f}초")
            return result
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"{func.__name__} 실행 실패: {execution_time:.2f}초, 오류: {e}")
            raise
    return wrapper


def require_permissions(*permissions):
    """권한 요구 데코레이터"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(interaction, *args, **kwargs) -> Any:
            # 관리자는 모든 권한 보유
            if interaction.user.guild_permissions.administrator:
                return await func(interaction, *args, **kwargs)
            
            # 필요한 권한 확인
            user_permissions = interaction.user.guild_permissions
            for permission in permissions:
                if not getattr(user_permissions, permission, False):
                    await interaction.response.send_message(
                        f"❌ 이 명령어를 사용하려면 '{permission}' 권한이 필요합니다.",
                        ephemeral=True
                    )
                    return
            
            return await func(interaction, *args, **kwargs)
        return wrapper
    return decorator


def admin_only(func: Callable) -> Callable:
    """관리자 전용 데코레이터"""
    @functools.wraps(func)
    async def wrapper(interaction, *args, **kwargs) -> Any:
        from config.settings import settings
        
        # 설정된 관리자 ID 확인
        if interaction.user.id in settings.admin_user_ids:
            return await func(interaction, *args, **kwargs)
        
        # Discord 관리자 권한 확인
        if interaction.user.guild_permissions.administrator:
            return await func(interaction, *args, **kwargs)
        
        await interaction.response.send_message(
            "❌ 이 명령어는 관리자만 사용할 수 있습니다.",
            ephemeral=True
        )
    return wrapper


def cooldown(seconds: int):
    """쿨다운 데코레이터"""
    def decorator(func: Callable) -> Callable:
        last_used = {}
        
        @functools.wraps(func)
        async def wrapper(interaction, *args, **kwargs) -> Any:
            user_id = interaction.user.id
            now = time.time()
            
            if user_id in last_used:
                time_diff = now - last_used[user_id]
                if time_diff < seconds:
                    remaining = seconds - time_diff
                    await interaction.response.send_message(
                        f"⏰ {remaining:.1f}초 후에 다시 사용할 수 있습니다.",
                        ephemeral=True
                    )
                    return
            
            last_used[user_id] = now
            return await func(interaction, *args, **kwargs)
        return wrapper
    return decorator
'''

# utils/validators.py - 입력 검증 유틸리티
validators_content = '''"""
입력 검증 유틸리티
"""

import re
import logging
from typing import Optional, List

logger = logging.getLogger(__name__)

# Discord 예약어 목록
DISCORD_RESERVED_WORDS = {
    'help', 'info', 'ping', 'admin', 'mod', 'moderator', 'ban', 'kick', 
    'mute', 'unmute', 'warn', 'clear', 'purge', 'role', 'channel',
    'server', 'guild', 'user', 'member', 'everyone', 'here'
}


def validate_command_name(name: str) -> tuple[bool, Optional[str]]:
    """커맨드 이름 유효성 검사"""
    if not name:
        return False, "커맨드 이름이 비어있습니다."
    
    # 길이 검사
    if len(name) < 1 or len(name) > 32:
        return False, "커맨드 이름은 1-32자 사이여야 합니다."
    
    # 문자 규칙 검사 (영문 소문자, 숫자, 언더스코어만 허용)
    if not re.match(r'^[a-z0-9_]+$', name):
        return False, "커맨드 이름은 영문 소문자, 숫자, 언더스코어만 사용할 수 있습니다."
    
    # 숫자로 시작하는지 검사
    if name[0].isdigit():
        return False, "커맨드 이름은 숫자로 시작할 수 없습니다."
    
    # 언더스코어로만 구성되었는지 검사
    if name.replace('_', '') == '':
        return False, "커맨드 이름은 언더스코어로만 구성될 수 없습니다."
    
    # 예약어 검사
    if name.lower() in DISCORD_RESERVED_WORDS:
        return False, f"'{name}'은 Discord 예약어이므로 사용할 수 없습니다."
    
    return True, None


def validate_command_description(description: str) -> tuple[bool, Optional[str]]:
    """커맨드 설명 유효성 검사"""
    if not description:
        return False, "커맨드 설명이 비어있습니다."
    
    if len(description) < 1 or len(description) > 100:
        return False, "커맨드 설명은 1-100자 사이여야 합니다."
    
    # 특수 문자 검사 (기본적인 문장 부호만 허용)
    if re.search(r'[<>@#&]', description):
        return False, "커맨드 설명에 특수 문자 (<, >, @, #, &)는 사용할 수 없습니다."
    
    return True, None


def validate_response_template(template: str) -> tuple[bool, Optional[str]]:
    """응답 템플릿 유효성 검사"""
    if not template:
        return False, "응답 템플릿이 비어있습니다."
    
    if len(template) > 2000:
        return False, "응답 템플릿은 2000자를 초과할 수 없습니다."
    
    # 금지된 멘션 패턴 검사
    forbidden_patterns = [
        r'@everyone',
        r'@here',
        r'<@&\d+>',  # 역할 멘션
    ]
    
    for pattern in forbidden_patterns:
        if re.search(pattern, template, re.IGNORECASE):
            return False, "응답 템플릿에 전체 멘션(@everyone, @here)이나 역할 멘션은 사용할 수 없습니다."
    
    return True, None


def validate_ai_prompt(prompt: str) -> tuple[bool, Optional[str]]:
    """AI 프롬프트 유효성 검사"""
    if not prompt:
        return False, "AI 프롬프트가 비어있습니다."
    
    if len(prompt) > 1000:
        return False, "AI 프롬프트는 1000자를 초과할 수 없습니다."
    
    # 유해한 키워드 검사
    harmful_keywords = [
        'hack', 'exploit', 'ddos', 'dos attack', 'malware', 'virus',
        'password', 'token', 'secret', 'api key', 'private key'
    ]
    
    prompt_lower = prompt.lower()
    for keyword in harmful_keywords:
        if keyword in prompt_lower:
            return False, f"AI 프롬프트에 보안상 위험한 키워드 '{keyword}'가 포함되어 있습니다."
    
    return True, None


def validate_user_input(user_input: str, max_length: int = 500) -> tuple[bool, Optional[str]]:
    """사용자 입력 유효성 검사"""
    if len(user_input) > max_length:
        return False, f"입력은 {max_length}자를 초과할 수 없습니다."
    
    # SQL 인젝션 패턴 검사
    sql_patterns = [
        r'(union|select|insert|update|delete|drop|create|alter|exec|execute)',
        r'(script|javascript|vbscript)',
        r'(<script|</script>|<iframe|</iframe>)'
    ]
    
    input_lower = user_input.lower()
    for pattern in sql_patterns:
        if re.search(pattern, input_lower):
            return False, "입력에 허용되지 않는 패턴이 포함되어 있습니다."
    
    return True, None


def sanitize_input(text: str) -> str:
    """입력 텍스트 정화"""
    if not text:
        return ""
    
    # HTML 태그 제거
    text = re.sub(r'<[^>]*>', '', text)
    
    # 연속된 공백을 하나로 변경
    text = re.sub(r'\s+', ' ', text)
    
    # 앞뒤 공백 제거
    text = text.strip()
    
    return text


def validate_role_names(role_names: List[str]) -> tuple[bool, Optional[str]]:
    """역할 이름 목록 유효성 검사"""
    if not role_names:
        return True, None  # 빈 목록은 허용
    
    for role_name in role_names:
        if not role_name or not role_name.strip():
            return False, "빈 역할 이름은 허용되지 않습니다."
        
        if len(role_name) > 100:
            return False, f"역할 이름 '{role_name}'이 너무 깁니다 (최대 100자)."
        
        # 특수 문자 검사
        if re.search(r'[<>@#&]', role_name):
            return False, f"역할 이름 '{role_name}'에 허용되지 않는 특수 문자가 포함되어 있습니다."
    
    return True, None


def validate_guild_id(guild_id: str) -> tuple[bool, Optional[str]]:
    """길드 ID 유효성 검사"""
    if not guild_id:
        return False, "길드 ID가 비어있습니다."
    
    # Discord 길드 ID는 일반적으로 18-19자리 숫자
    if not guild_id.isdigit() or len(guild_id) < 17 or len(guild_id) > 20:
        return False, "올바르지 않은 길드 ID 형식입니다."
    
    return True, None


def is_safe_content(content: str) -> bool:
    """콘텐츠 안전성 기본 검사"""
    # 기본적인 안전성 검사
    unsafe_patterns = [
        r'(http|https|ftp)://\S+',  # URL
        r'discord\.gg/\S+',         # Discord 초대 링크
        r'@everyone|@here',         # 전체 멘션
    ]
    
    for pattern in unsafe_patterns:
        if re.search(pattern, content, re.IGNORECASE):
            return False
    
    return True
'''

# 파일 저장
with open("src/services/ai_service.py", "w", encoding="utf-8") as f:
    f.write(ai_service_content)

with open("src/utils/decorators.py", "w", encoding="utf-8") as f:
    f.write(decorators_content)

with open("src/utils/validators.py", "w", encoding="utf-8") as f:
    f.write(validators_content)

print("추가 핵심 서비스 파일들이 생성되었습니다.")
print("- src/services/ai_service.py")
print("- src/utils/decorators.py") 
print("- src/utils/validators.py")