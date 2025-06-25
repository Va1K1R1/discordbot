# MySQL 최적화된 안전한 DB 세션 관리

import logging
from contextlib import contextmanager
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError, IntegrityError, OperationalError
from src.models.database import get_db
from src.models.command import Command
from src.exceptions.custom_exceptions import (
    CommandNotFoundError,
    CommandAlreadyExistsError,
    DatabaseError
)

logger = logging.getLogger(__name__)

class CommandService:
    """MySQL 최적화된 안전한 명령어 서비스"""
    
    @contextmanager
    def get_db_session(self):
        """MySQL용 안전한 DB 세션 컨텍스트 매니저"""
        db = next(get_db())
        try:
            yield db
            db.commit()  # MySQL 트랜잭션 커밋
        except IntegrityError as e:
            db.rollback()
            logger.error(f"MySQL 무결성 제약 위반: {e}")
            if "Duplicate entry" in str(e):
                raise CommandAlreadyExistsError("명령어가 이미 존재합니다.")
            raise DatabaseError(f"데이터 무결성 오류: {str(e)}")
        except OperationalError as e:
            db.rollback()
            logger.error(f"MySQL 연결 오류: {e}")
            raise DatabaseError(f"데이터베이스 연결 오류: {str(e)}")
        except SQLAlchemyError as e:
            db.rollback()
            logger.error(f"MySQL DB 오류: {e}")
            raise DatabaseError(f"데이터베이스 오류: {str(e)}")
        except Exception as e:
            db.rollback()
            logger.error(f"예상치 못한 오류: {e}")
            raise
        finally:
            db.close()  # 🔥 MySQL 연결 해제 - 중요!
    
    async def create_command(
        self,
        guild_id: str,
        name: str,
        description: str,
        response_template: str,
        created_by: int,
        use_ai: bool = False,
        allowed_roles: Optional[List[str]] = None
    ) -> Command:
        """MySQL 최적화된 안전한 명령어 생성"""
        try:
            with self.get_db_session() as db:
                # MySQL 중복 확인 (UNIQUE 제약 활용)
                existing = db.query(Command).filter(
                    Command.guild_id == guild_id,
                    Command.name == name
                ).first()
                
                if existing:
                    raise CommandAlreadyExistsError(f"명령어 '{name}'이 이미 존재합니다.")
                
                # 새 명령어 생성
                new_command = Command(
                    guild_id=guild_id,
                    name=name,
                    description=description,
                    response_template=response_template,
                    created_by=created_by,
                    use_ai=use_ai
                )
                
                # 허용된 역할 설정
                if allowed_roles:
                    new_command.set_allowed_roles(allowed_roles)
                
                db.add(new_command)
                db.flush()  # MySQL AUTO_INCREMENT ID 생성
                
                logger.info(f"MySQL: 명령어 생성 성공 - {name} (Guild: {guild_id}, ID: {new_command.id})")
                return new_command
                
        except (CommandAlreadyExistsError, DatabaseError):
            raise
        except Exception as e:
            logger.error(f"MySQL: 명령어 생성 실패 - {e}")
            raise DatabaseError(f"명령어 생성 오류: {str(e)}")
    
    async def get_command(self, guild_id: str, name: str) -> Command:
        """MySQL 최적화된 명령어 조회"""
        try:
            with self.get_db_session() as db:
                # MySQL 인덱스 활용한 효율적 조회
                command = db.query(Command).filter(
                    Command.guild_id == guild_id,
                    Command.name == name,
                    Command.is_active == True  # 활성화된 명령어만
                ).first()
                
                if not command:
                    raise CommandNotFoundError(f"명령어 '{name}'을 찾을 수 없습니다.")
                
                # 사용 횟수 증가 (별도 트랜잭션)
                self._increment_usage_async(command.id)
                
                return command
                
        except CommandNotFoundError:
            raise
        except Exception as e:
            logger.error(f"MySQL: 명령어 조회 실패 - {e}")
            raise DatabaseError(f"명령어 조회 오류: {str(e)}")
    
    def _increment_usage_async(self, command_id: int):
        """MySQL 비동기 사용 횟수 증가 (성능 최적화)"""
        try:
            with self.get_db_session() as db:
                # 직접 UPDATE 쿼리로 성능 최적화
                db.execute(
                    "UPDATE commands SET usage_count = usage_count + 1, "
                    "last_used = NOW() WHERE id = :id",
                    {"id": command_id}
                )
        except Exception as e:
            logger.warning(f"MySQL: 사용 횟수 업데이트 실패 - {e}")
            # 사용 횟수 업데이트 실패는 치명적이지 않음
    
    async def get_all_commands(self, guild_id: str) -> List[Command]:
        """MySQL 최적화된 명령어 목록 조회"""
        try:
            with self.get_db_session() as db:
                commands = db.query(Command).filter(
                    Command.guild_id == guild_id,
                    Command.is_active == True
                ).order_by(Command.created_at.desc()).all()
                
                logger.info(f"MySQL: 길드 {guild_id}의 명령어 {len(commands)}개 조회")
                return commands
                
        except Exception as e:
            logger.error(f"MySQL: 명령어 목록 조회 실패 - {e}")
            raise DatabaseError(f"명령어 목록 조회 오류: {str(e)}")
    
    async def update_command(
        self,
        guild_id: str,
        name: str,
        **updates
    ) -> Command:
        """MySQL 최적화된 명령어 업데이트"""
        try:
            with self.get_db_session() as db:
                command = db.query(Command).filter(
                    Command.guild_id == guild_id,
                    Command.name == name
                ).with_for_update().first()  # MySQL 행 잠금
                
                if not command:
                    raise CommandNotFoundError(f"명령어 '{name}'을 찾을 수 없습니다.")
                
                # 업데이트 적용
                for key, value in updates.items():
                    if key == 'allowed_roles' and value is not None:
                        command.set_allowed_roles(value)
                    elif hasattr(command, key):
                        setattr(command, key, value)
                
                # MySQL updated_at 자동 갱신
                from datetime import datetime
                command.updated_at = datetime.utcnow()
                
                logger.info(f"MySQL: 명령어 업데이트 성공 - {name} (Guild: {guild_id})")
                return command
                
        except CommandNotFoundError:
            raise
        except Exception as e:
            logger.error(f"MySQL: 명령어 업데이트 실패 - {e}")
            raise DatabaseError(f"명령어 업데이트 오류: {str(e)}")
    
    async def delete_command(self, guild_id: str, name: str) -> bool:
        """MySQL 최적화된 명령어 삭제 (소프트 삭제)"""
        try:
            with self.get_db_session() as db:
                command = db.query(Command).filter(
                    Command.guild_id == guild_id,
                    Command.name == name
                ).first()
                
                if not command:
                    raise CommandNotFoundError(f"명령어 '{name}'을 찾을 수 없습니다.")
                
                # 소프트 삭제 (데이터 보존)
                command.is_active = False
                from datetime import datetime
                command.updated_at = datetime.utcnow()
                
                logger.info(f"MySQL: 명령어 소프트 삭제 성공 - {name} (Guild: {guild_id})")
                return True
                
        except CommandNotFoundError:
            raise
        except Exception as e:
            logger.error(f"MySQL: 명령어 삭제 실패 - {e}")
            raise DatabaseError(f"명령어 삭제 오류: {str(e)}")

# 전역 서비스 인스턴스
command_service = CommandService()