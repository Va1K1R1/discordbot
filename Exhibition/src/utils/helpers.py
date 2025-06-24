import discord
import json
import re
from typing import Dict, List, Any, Optional, Union
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


def format_discord_message(message: str, **kwargs) -> str:
    """
    Discord 메시지 형식화
    
    Args:
        message: 형식화할 메시지
        **kwargs: 메시지에 삽입할 변수
        
    Returns:
        형식화된 메시지
    """
    try:
        return message.format(**kwargs)
    except KeyError as e:
        logger.warning(f"메시지 형식화 중 누락된 키: {e}")
        return message
    except Exception as e:
        logger.error(f"메시지 형식화 오류: {e}")
        return message


def create_embed(
    title: str,
    description: Optional[str] = None,
    color: int = 0x3498db,
    fields: Optional[List[Dict[str, str]]] = None,
    footer: Optional[str] = None,
    thumbnail: Optional[str] = None,
    image: Optional[str] = None
) -> discord.Embed:
    """
    Discord 임베드 생성
    
    Args:
        title: 임베드 제목
        description: 임베드 설명
        color: 임베드 색상 (16진수)
        fields: 필드 목록 [{"name": "필드명", "value": "필드값", "inline": True/False}]
        footer: 푸터 텍스트
        thumbnail: 썸네일 URL
        image: 이미지 URL
        
    Returns:
        Discord 임베드 객체
    """
    embed = discord.Embed(
        title=title,
        description=description,
        color=color,
        timestamp=datetime.utcnow()
    )
    
    if fields:
        for field in fields:
            embed.add_field(
                name=field.get("name", ""),
                value=field.get("value", ""),
                inline=field.get("inline", False)
            )
    
    if footer:
        embed.set_footer(text=footer)
    
    if thumbnail:
        embed.set_thumbnail(url=thumbnail)
    
    if image:
        embed.set_image(url=image)
    
    return embed


def parse_json_safely(json_str: str) -> Dict[str, Any]:
    """
    안전하게 JSON 파싱
    
    Args:
        json_str: 파싱할 JSON 문자열
        
    Returns:
        파싱된 JSON 객체 또는 빈 딕셔너리
    """
    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        logger.error(f"JSON 파싱 오류: {e}")
        return {}


def truncate_text(text: str, max_length: int = 2000, suffix: str = "...") -> str:
    """
    텍스트 길이 제한
    
    Args:
        text: 제한할 텍스트
        max_length: 최대 길이
        suffix: 잘린 경우 추가할 접미사
        
    Returns:
        제한된 텍스트
    """
    if len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix


def extract_mentions(content: str) -> List[int]:
    """
    메시지에서 멘션된 사용자 ID 추출
    
    Args:
        content: 메시지 내용
        
    Returns:
        멘션된 사용자 ID 목록
    """
    # Discord 멘션 패턴: <@USER_ID> 또는 <@!USER_ID>
    mention_pattern = r'<@!?(\d+)>'
    mentions = re.findall(mention_pattern, content)
    
    return [int(user_id) for user_id in mentions]


def format_time_difference(time1: datetime, time2: Optional[datetime] = None) -> str:
    """
    두 시간 사이의 차이를 사람이 읽기 쉬운 형태로 변환
    
    Args:
        time1: 첫 번째 시간
        time2: 두 번째 시간 (기본값: 현재 시간)
        
    Returns:
        형식화된 시간 차이 문자열
    """
    if time2 is None:
        time2 = datetime.utcnow()
    
    diff = abs(time2 - time1)
    
    if diff < timedelta(minutes=1):
        return f"{diff.seconds}초 전"
    elif diff < timedelta(hours=1):
        return f"{diff.seconds // 60}분 전"
    elif diff < timedelta(days=1):
        return f"{diff.seconds // 3600}시간 전"
    elif diff < timedelta(days=30):
        return f"{diff.days}일 전"
    elif diff < timedelta(days=365):
        return f"{diff.days // 30}개월 전"
    else:
        return f"{diff.days // 365}년 전"