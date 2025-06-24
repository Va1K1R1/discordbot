from sqlalchemy import Column, Integer, String, DateTime, Float, Text
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
from src.models.database import Base


class ConversationHistory(Base):
    __tablename__ = "conversation_history"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(20), index=True, nullable=False)  # Discord User ID
    guild_id = Column(String(20), index=True, nullable=False)  # Discord Guild ID
    channel_id = Column(String(20), nullable=False)  # Discord Channel ID
    message = Column(Text, nullable=False)
    response = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow)
    command_used = Column(String(32))  # 사용된 커맨드명
    
    # AI 관련 메타데이터
    tokens_used = Column(Integer)
    processing_time = Column(Float)
    intent = Column(String(50))  # 감지된 의도
    entities = Column(Text)  # JSON 형태로 저장된 엔터티