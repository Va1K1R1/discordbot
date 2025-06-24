import discord
from discord import app_commands
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional, Tuple
import logging
import json

from src.models.database import get_db
from src.models.command import Command
from src.services.ai_service import ai_service
from src.utils.validators import validate_command_name, validate_command_description
from src.exceptions.custom_exceptions import (
    CommandNotFoundError,
    CommandAlreadyExistsError,
    ValidationError,
    DatabaseError
)

logger = logging.getLogger(__name__)


class CommandService:
    """커맨드 관리 서비스"""
    
    @staticmethod
    async def create_command(
        guild_id: str,
        name: str,
        description: str,
        response_template: str,
        created_by: str,
        use_ai: bool = False,
        ai_prompt: Optional[str] = None,
        ai_system_message: Optional[str] = None,
        allowed_roles: Optional[List[str]] = None
    ) -> Command:
        """
        새 커맨드 생성
        
        Args:
            guild_id: 길드 ID
            name: 커맨드 이름
            description: 커맨드 설명
            response_template: 응답 템플릿
            created_by: 생성자 ID
            use_ai: AI 사용 여부
            ai_prompt: AI 프롬프트
            ai_system_message: AI 시스템 메시지
            allowed_roles: 허용된 역할 목록
            
        Returns:
            생성된 커맨드 객체
            
        Raises:
            ValidationError: 유효성 검사 실패 시
            CommandAlreadyExistsError: 커맨드가 이미 존재할 경우
            DatabaseError: 데이터베이스 오류 발생 시
        """
        # 유효성 검사
        is_valid, error_message = validate_command_name(name)
        if not is_valid:
            raise ValidationError(error_message)
        
        is_valid, error_message = validate_command_description(description)
        if not is_valid:
            raise ValidationError(error_message)
        
        try:
            db = next(get_db())
            
            # 커맨드 중복 확인
            existing_command = db.query(Command).filter(
                Command.guild_id == guild_id,
                Command.name == name
            ).first()
            
            if existing_command:
                raise CommandAlreadyExistsError(name)
            
            # 새 커맨드 생성
            new_command = Command(
                guild_id=guild_id,
                name=name,
                description=description,
                response_template=response_template,
                created_by=created_by,
                use_ai=use_ai,
                ai_prompt=ai_prompt,
                ai_system_message=ai_system_message
            )
            
            # 허용된 역할 설정
            if allowed_roles:
                new_command.set_allowed_roles(allowed_roles)
            
            db.add(new_command)
            db.commit()
            db.refresh(new_command)
            
            logger.info(f"커맨드 생성 성공: {name} (길드: {guild_id})")
            return new_command
            
        except Exception as e:
            logger.error(f"커맨드 생성 실패: {e}")
            if isinstance(e, (ValidationError, CommandAlreadyExistsError)):
                raise
            raise DatabaseError(f"커맨드 생성 중 오류 발생: {str(e)}")
    
    @staticmethod
    async def get_command(guild_id: str, name: str) -> Command:
        """
        커맨드 조회
        
        Args:
            guild_id: 길드 ID
            name: 커맨드 이름
            
        Returns:
            커맨드 객체
            
        Raises:
            CommandNotFoundError: 커맨드를 찾을 수 없을 경우
            DatabaseError: 데이터베이스 오류 발생 시
        """
        try:
            db = next(get_db())
            
            command = db.query(Command).filter(
                Command.guild_id == guild_id,
                Command.name == name,
                Command.is_active == True
            ).first()
            
            if not command:
                raise CommandNotFoundError(name)
            
            return command
            
        except Exception as e:
            logger.error(f"커맨드 조회 실패: {e}")
            if isinstance(e, CommandNotFoundError):
                raise
            raise DatabaseError(f"커맨드 조회 중 오류 발생: {str(e)}")
    
    @staticmethod
    async def get_all_commands(guild_id: str) -> List[Command]:
        """
        모든 커맨드 조회
        
        Args:
            guild_id: 길드 ID
            
        Returns:
            커맨드 객체 목록
            
        Raises:
            DatabaseError: 데이터베이스 오류 발생 시
        """
        try:
            db = next(get_db())
            
            commands = db.query(Command).filter(
                Command.guild_id == guild_id,
                Command.is_active == True
            ).all()
            
            return commands
            
        except Exception as e:
            logger.error(f"모든 커맨드 조회 실패: {e}")
            raise DatabaseError(f"커맨드 목록 조회 중 오류 발생: {str(e)}")
    
    @staticmethod
    async def update_command(
        guild_id: str,
        name: str,
        description: Optional[str] = None,
        response_template: Optional[str] = None,
        use_ai: Optional[bool] = None,
        ai_prompt: Optional[str] = None,
        ai_system_message: Optional[str] = None,
        allowed_roles: Optional[List[str]] = None
    ) -> Command:
        """
        커맨드 업데이트
        
        Args:
            guild_id: 길드 ID
            name: 커맨드 이름
            description: 커맨드 설명
            response_template: 응답 템플릿
            use_ai: AI 사용 여부
            ai_prompt: AI 프롬프트
            ai_system_message: AI 시스템 메시지
            allowed_roles: 허용된 역할 목록
            
        Returns:
            업데이트된 커맨드 객체
            
        Raises:
            CommandNotFoundError: 커맨드를 찾을 수 없을 경우
            ValidationError: 유효성 검사 실패 시
            DatabaseError: 데이터베이스 오류 발생 시
        """
        try:
            db = next(get_db())
            
            # 커맨드 조회
            command = db.query(Command).filter(
                Command.guild_id == guild_id,
                Command.name == name,
                Command.is_active == True
            ).first()
            
            if not command:
                raise CommandNotFoundError(name)
            
            # 설명 업데이트
            if description is not None:
                is_valid, error_message = validate_command_description(description)
                if not is_valid:
                    raise ValidationError(error_message)
                command.description = description
            
            # 응답 템플릿 업데이트
            if response_template is not None:
                command.response_template = response_template
            
            # AI 관련 필드 업데이트
            if use_ai is not None:
                command.use_ai = use_ai
            
            if ai_prompt is not None:
                command.ai_prompt = ai_prompt
            
            if ai_system_message is not None:
                command.ai_system_message = ai_system_message
            
            # 허용된 역할 업데이트
            if allowed_roles is not None:
                command.set_allowed_roles(allowed_roles)
            
            db.commit()
            db.refresh(command)
            
            logger.info(f"커맨드 업데이트 성공: {name} (길드: {guild_id})")
            return command
            
        except Exception as e:
            logger.error(f"커맨드 업데이트 실패: {e}")
            if isinstance(e, (CommandNotFoundError, ValidationError)):
                raise
            raise DatabaseError(f"커맨드 업데이트 중 오류 발생: {str(e)}")
    
    @staticmethod
    async def delete_command(guild_id: str, name: str) -> bool:
        """
        커맨드 삭제 (비활성화)
        
        Args:
            guild_id: 길드 ID
            name: 커맨드 이름
            
        Returns:
            삭제 성공 여부
            
        Raises:
            CommandNotFoundError: 커맨드를 찾을 수 없을 경우
            DatabaseError: 데이터베이스 오류 발생 시
        """
        try:
            db = next(get_db())
            
            # 커맨드 조회
            command = db.query(Command).filter(
                Command.guild_id == guild_id,
                Command.name == name,
                Command.is_active == True
            ).first()
            
            if not command:
                raise CommandNotFoundError(name)
            
            # 비활성화 처리
            command.is_active = False
            
            db.commit()
            
            logger.info(f"커맨드 삭제 성공: {name} (길드: {guild_id})")
            return True
            
        except Exception as e:
            logger.error(f"커맨드 삭제 실패: {e}")
            if isinstance(e, CommandNotFoundError):
                raise
            raise DatabaseError(f"커맨드 삭제 중 오류 발생: {str(e)}")
    
    @staticmethod
    async def generate_command_from_description(
        guild_id: str,
        user_description: str,
        created_by: str
    ) -> Command:
        """
        사용자 설명으로부터 커맨드 생성
        
        Args:
            guild_id: 길드 ID
            user_description: 사용자 설명
            created_by: 생성자 ID
            
        Returns:
            생성된 커맨드 객체
            
        Raises:
            ValidationError: 유효성 검사 실패 시
            CommandAlreadyExistsError: 커맨드가 이미 존재할 경우
            DatabaseError: 데이터베이스 오류 발생 시
        """
        try:
            # AI로 커맨드 메타데이터 생성
            metadata = await ai_service.generate_command_metadata(user_description)
            
            # 커맨드 생성
            command = await CommandService.create_command(
                guild_id=guild_id,
                name=metadata.get("name", ""),
                description=metadata.get("description", ""),
                response_template=metadata.get("response_template", ""),
                created_by=created_by,
                use_ai=True,
                ai_prompt=user_description
            )
            
            return command
            
        except Exception as e:
            logger.error(f"AI 기반 커맨드 생성 실패: {e}")
            if isinstance(e, (ValidationError, CommandAlreadyExistsError)):
                raise
            raise DatabaseError(f"AI 기반 커맨드 생성 중 오류 발생: {str(e)}")


# 전역 커맨드 서비스 인스턴스
command_service = CommandService()