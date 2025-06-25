import pymysql
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import OperationalError
from src.config.settings import settings

logger = logging.getLogger(__name__)

# 데이터베이스 엔진 및 세션 설정
engine = None
SessionLocal = None
Base = declarative_base()

def init_database():
    """데이터베이스 초기화 (동기 함수)"""
    global engine, SessionLocal
    
    try:
        logger.info("데이터베이스 초기화 중...")
        
        # MySQL 데이터베이스 생성 (존재하지 않는 경우)
        create_database_if_not_exists()
        
        # SQLAlchemy 엔진 생성
        database_url = (
            f"mysql+pymysql://{settings.mysql_user}:{settings.mysql_password}"
            f"@{settings.mysql_host}:{settings.mysql_port}/{settings.mysql_database}"
            f"?charset=utf8mb4"
        )
        
        logger.info(f"MySQL 데이터베이스 URL: {database_url}")
        
        engine = create_engine(
            database_url,
            echo=False,
            pool_recycle=3600,
            pool_pre_ping=True
        )
        
        # 연결 테스트
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("MySQL 데이터베이스 연결 성공")
        
        # 세션 팩토리 생성
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        
        # 기존 테이블 확인
        from sqlalchemy import inspect
        inspector = inspect(engine)
        existing_tables = inspector.get_table_names()
        logger.info(f"기존 테이블: {existing_tables}")
        
        # 테이블 생성
        Base.metadata.create_all(bind=engine)
        
        # 생성된 테이블 확인
        inspector = inspect(engine)
        created_tables = inspector.get_table_names()
        logger.info(f"데이터베이스 테이블 생성 완료")
        logger.info(f"생성된 테이블: {created_tables}")
        
        return True
        
    except Exception as e:
        logger.error(f"데이터베이스 초기화 실패: {e}")
        raise

def create_database_if_not_exists():
    """데이터베이스가 존재하지 않으면 생성"""
    try:
        # MySQL 서버에 연결 (데이터베이스 지정하지 않음)
        connection = pymysql.connect(
            host=settings.mysql_host,
            port=settings.mysql_port,
            user=settings.mysql_user,
            password=settings.mysql_password,
            charset='utf8mb4'
        )
        
        with connection.cursor() as cursor:
            # 데이터베이스 존재 확인
            cursor.execute(f"SHOW DATABASES LIKE '{settings.mysql_database}'")
            result = cursor.fetchone()
            
            if result:
                logger.info(f"데이터베이스 '{settings.mysql_database}' 이미 존재")
            else:
                # 데이터베이스 생성
                cursor.execute(f"CREATE DATABASE {settings.mysql_database} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
                logger.info(f"데이터베이스 '{settings.mysql_database}' 생성 완료")
        
        connection.close()
        
    except Exception as e:
        logger.error(f"데이터베이스 생성 실패: {e}")
        raise

def get_db():
    """데이터베이스 세션 제공 함수"""
    if SessionLocal is None:
        raise RuntimeError("데이터베이스가 초기화되지 않았습니다. init_database()를 먼저 호출하세요.")
    
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_engine():
    """데이터베이스 엔진 반환"""
    if engine is None:
        raise RuntimeError("데이터베이스가 초기화되지 않았습니다. init_database()를 먼저 호출하세요.")
    return engine