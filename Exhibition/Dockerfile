FROM python:3.12-slim

WORKDIR /app

# 시스템 의존성 설치 (MySQL 클라이언트 포함)
RUN apt-get update && apt-get install -y \
    gcc \
    default-libmysqlclient-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Python 의존성 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션 코드 복사
COPY src/ ./src/
COPY .env .env

# 필요한 디렉토리 생성
RUN mkdir -p logs data

# Python 경로에 현재 디렉토리 추가 (중요!)
ENV PYTHONPATH=/app

# 헬스체크 수정 (HTTP 요청 제거)
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -c "import sys; sys.exit(0)" || exit 1

# 비루트 사용자 생성
RUN useradd --create-home --shell /bin/bash app \
    && chown -R app:app /app
USER app

# 실행 (Python 모듈로 실행)
CMD ["python", "-m", "src.main"]