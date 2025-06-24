"""
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
