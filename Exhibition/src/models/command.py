from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
from src.models.database import Base


class Command(Base):
    __tablename__ = "commands"
    
    id = Column(Integer, primary_key=True, index=True)
    guild_id = Column(String(20), index=True, nullable=False)  # Discord ID는 최대 20자
    name = Column(String(32), unique=True, index=True, nullable=False)  # 슬래시 커맨드 이름 제한
    description = Column(String(100), nullable=False)  # Discord 설명 제한
    response_template = Column(Text, nullable=False)
    
    # AI 관련 설정
    use_ai = Column(Boolean, default=False)
    ai_prompt = Column(Text)
    ai_system_message = Column(Text)
    
    # 권한 관련
    required_permissions = Column(Text)  # JSON 형태로 저장
    allowed_roles = Column(Text)  # JSON 형태로 저장
    
    # 메타데이터
    created_by = Column(String(20), nullable=False)  # Discord User ID
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 사용 통계
    is_active = Column(Boolean, default=True)
    usage_count = Column(Integer, default=0)
    last_used = Column(DateTime)
    
    def get_required_permissions(self):
        """필수 권한 목록 반환"""
        import json
        if self.required_permissions:
            try:
                return json.loads(self.required_permissions)
            except json.JSONDecodeError:
                return []
        return []
    
    def set_required_permissions(self, permissions):
        """필수 권한 목록 설정"""
        import json
        if permissions:
            self.required_permissions = json.dumps(permissions)
        else:
            self.required_permissions = None
    
    def get_allowed_roles(self):
        """허용된 역할 목록 반환"""
        import json
        if self.allowed_roles:
            try:
                return json.loads(self.allowed_roles)
            except json.JSONDecodeError:
                return []
        return []
    
    def set_allowed_roles(self, roles):
        """허용된 역할 목록 설정"""
        import json
        if roles:
            self.allowed_roles = json.dumps(roles)
        else:
            self.allowed_roles = None
    
    def increment_usage(self):
        """사용 횟수 증가"""
        self.usage_count += 1
        self.last_used = datetime.utcnow()