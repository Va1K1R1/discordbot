import asyncio
import functools
import logging
from typing import Callable, TypeVar, Any, Optional

logger = logging.getLogger(__name__)

T = TypeVar('T')


def retry_with_backoff(max_retries: int = 3, base_delay: float = 1.0, backoff_factor: float = 2.0):
    """
    재시도 데코레이터: 지수 백오프를 사용하여 함수 호출을 재시도합니다.
    
    Args:
        max_retries: 최대 재시도 횟수
        base_delay: 초기 지연 시간(초)
        backoff_factor: 백오프 계수
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            retries = 0
            delay = base_delay
            
            while True:
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    retries += 1
                    if retries > max_retries:
                        logger.error(f"최대 재시도 횟수({max_retries})를 초과했습니다: {e}")
                        raise
                    
                    wait_time = delay * (backoff_factor ** (retries - 1))
                    logger.warning(f"오류 발생, {wait_time:.2f}초 후 재시도 ({retries}/{max_retries}): {e}")
                    await asyncio.sleep(wait_time)
        
        return wrapper
    
    return decorator


def log_execution_time(func: Callable[..., T]) -> Callable[..., T]:
    """함수 실행 시간을 로깅하는 데코레이터"""
    @functools.wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> T:
        import time
        start_time = time.time()
        
        try:
            result = await func(*args, **kwargs)
            return result
        finally:
            end_time = time.time()
            execution_time = end_time - start_time
            logger.debug(f"{func.__name__} 실행 시간: {execution_time:.4f}초")
    
    return wrapper