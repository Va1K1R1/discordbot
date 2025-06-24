FROM python:3.9-slim

# 작업 디렉토리 설정
WORKDIR /app

# 시스템 의존성 설치
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    git \
    && rm -rf /var/lib/apt/lists/*

# Python 의존성 설치
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 애플리케이션 코드 복사
COPY src/ ./src/
COPY .env .env

# 필요한 디렉토리 생성
RUN mkdir -p logs data

# 비root 사용자 생성
RUN useradd -m -u 1000 botuser && \
    chown -R botuser:botuser /app
USER botuser

# 헬스체크
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health')" || exit 1

# 포트 노출 (모니터링용)
EXPOSE 8000

# 실행
CMD ["python", "src/main.py"]
