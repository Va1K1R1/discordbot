from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
from src.models.database import Base


class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    discord_id = Column(String(20), unique=True, index=True, nullable=False)  # Discord User ID
    username = Column(String(32), nullable=False)  # Discord 사용자명 제한
    created_at = Column(DateTime, default=datetime.utcnow)
    last_active = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 사용자 설정
    preferences = Column(Text)  # JSON 형태로 저장
    
    # 권한 관련
    is_admin = Column(Boolean, default=False)
    is_banned = Column(Boolean, default=False)
    
    # 사용 통계
    command_count = Column(Integer, default=0)
    message_count = Column(Integer, default=0)