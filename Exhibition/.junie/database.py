"""
데이터베이스 연결 및 세션 관리
"""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from config.settings import settings
import logging

logger = logging.getLogger(__name__)

# SQLAlchemy 설정
if settings.database_url.startswith("sqlite"):
    engine = create_engine(
        settings.database_url,
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
        echo=False
    )
else:
    engine = create_engine(
        settings.database_url,
        pool_pre_ping=True,
        pool_recycle=300,
        echo=False
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db() -> Session:
    """데이터베이스 세션 생성"""
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        logger.error(f"데이터베이스 오류: {e}")
        db.rollback()
        raise
    finally:
        db.close()


async def init_database():
    """데이터베이스 초기화"""
    try:
        # 모든 테이블 생성
        Base.metadata.create_all(bind=engine)
        logger.info("데이터베이스 초기화 완료")
    except Exception as e:
        logger.error(f"데이터베이스 초기화 실패: {e}")
        raise


async def close_database():
    """데이터베이스 연결 종료"""
    try:
        engine.dispose()
        logger.info("데이터베이스 연결 종료")
    except Exception as e:
        logger.error(f"데이터베이스 종료 실패: {e}")
