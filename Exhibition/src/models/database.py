from sqlalchemy import create_engine, text, inspect
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import OperationalError
import logging
from src.config.settings import settings

logger = logging.getLogger(__name__)

# MySQL 데이터베이스 엔진 생성 (연결 풀 설정 추가)
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,  # 연결 상태 확인
    pool_recycle=3600,   # 1시간마다 연결 재생성
    echo=False,          # SQL 쿼리 로깅 (개발 시에만 True)
    connect_args={
        "charset": "utf8mb4",
        "autocommit": False
    }
)

# 세션 팩토리 생성
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base 클래스 생성
Base = declarative_base()


def get_db():
    """데이터베이스 세션 생성"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_database():
    """데이터베이스 초기화"""
    try:
        # 데이터베이스 연결 테스트
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1"))
            logger.info("MySQL 데이터베이스 연결 성공")
        
        # 기존 테이블 확인
        inspector = inspect(engine)
        existing_tables = inspector.get_table_names()
        logger.info(f"기존 테이블: {existing_tables}")
        
        # 테이블 생성
        Base.metadata.create_all(bind=engine)
        logger.info("데이터베이스 테이블 생성 완료")
        
        # 생성된 테이블 확인
        inspector = inspect(engine)
        created_tables = inspector.get_table_names()
        logger.info(f"생성된 테이블: {created_tables}")
        
        return True
        
    except OperationalError as e:
        logger.error(f"MySQL 데이터베이스 연결 실패: {e}")
        logger.error("MySQL 서버가 실행 중인지, 데이터베이스가 존재하는지 확인하세요.")
        return False
    except Exception as e:
        logger.error(f"데이터베이스 초기화 실패: {e}")
        return False


def create_database_if_not_exists():
    """데이터베이스가 없으면 생성"""
    try:
        # 데이터베이스 없이 연결 (mysql 기본 데이터베이스 사용)
        temp_url = f"mysql+pymysql://{settings.mysql_user}:{settings.mysql_password}@{settings.mysql_host}:{settings.mysql_port}/mysql?charset=utf8mb4"
        temp_engine = create_engine(temp_url)
        
        with temp_engine.connect() as connection:
            # 데이터베이스 존재 확인
            result = connection.execute(text(f"SHOW DATABASES LIKE '{settings.mysql_database}'"))
            if not result.fetchone():
                # 데이터베이스 생성
                connection.execute(text(f"CREATE DATABASE {settings.mysql_database} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"))
                connection.commit()
                logger.info(f"데이터베이스 '{settings.mysql_database}' 생성 완료")
            else:
                logger.info(f"데이터베이스 '{settings.mysql_database}' 이미 존재")
        
        temp_engine.dispose()
        return True
        
    except Exception as e:
        logger.error(f"데이터베이스 생성 실패: {e}")
        return False