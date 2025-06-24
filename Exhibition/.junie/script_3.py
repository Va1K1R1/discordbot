# Docker 관련 파일 생성
dockerfile_content = '''FROM python:3.9-slim

# 작업 디렉토리 설정
WORKDIR /app

# 시스템 의존성 설치
RUN apt-get update && apt-get install -y \\
    gcc \\
    g++ \\
    git \\
    && rm -rf /var/lib/apt/lists/*

# Python 의존성 설치
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \\
    pip install --no-cache-dir -r requirements.txt

# 애플리케이션 코드 복사
COPY src/ ./src/
COPY .env .env

# 필요한 디렉토리 생성
RUN mkdir -p logs data

# 비root 사용자 생성
RUN useradd -m -u 1000 botuser && \\
    chown -R botuser:botuser /app
USER botuser

# 헬스체크
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \\
    CMD python -c "import requests; requests.get('http://localhost:8000/health')" || exit 1

# 포트 노출 (모니터링용)
EXPOSE 8000

# 실행
CMD ["python", "src/main.py"]
'''

docker_compose_content = '''version: '3.8'

services:
  discord-bot:
    build: .
    container_name: ai-discord-bot
    restart: unless-stopped
    environment:
      - DATABASE_URL=postgresql://bot_user:bot_password@postgres:5432/bot_db
      - REDIS_URL=redis://redis:6379/0
    volumes:
      - ./logs:/app/logs
      - ./data:/app/data
    depends_on:
      - postgres
      - redis
    networks:
      - bot-network
    labels:
      - "com.example.description=AI Discord Bot"
      - "com.example.version=1.0.0"

  postgres:
    image: postgres:13-alpine
    container_name: bot-postgres
    restart: unless-stopped
    environment:
      POSTGRES_DB: bot_db
      POSTGRES_USER: bot_user
      POSTGRES_PASSWORD: bot_password
      POSTGRES_INITDB_ARGS: "--encoding=UTF-8"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./init.sql:/docker-entrypoint-initdb.d/init.sql
    ports:
      - "5432:5432"
    networks:
      - bot-network
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U bot_user -d bot_db"]
      interval: 30s
      timeout: 10s
      retries: 3

  redis:
    image: redis:6-alpine
    container_name: bot-redis
    restart: unless-stopped
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data
    ports:
      - "6379:6379"
    networks:
      - bot-network
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 30s
      timeout: 10s
      retries: 3

  nginx:
    image: nginx:alpine
    container_name: bot-nginx
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - discord-bot
    networks:
      - bot-network

volumes:
  postgres_data:
  redis_data:

networks:
  bot-network:
    driver: bridge
'''

# GitHub Actions 워크플로우
github_actions_content = '''name: CI/CD Pipeline

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

env:
  PYTHON_VERSION: 3.9

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: [3.8, 3.9, 3.10]

    services:
      postgres:
        image: postgres:13
        env:
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: test_db
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432

      redis:
        image: redis:6
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 6379:6379

    steps:
    - uses: actions/checkout@v4
    
    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v4
      with:
        python-version: ${{ matrix.python-version }}
    
    - name: Cache pip packages
      uses: actions/cache@v3
      with:
        path: ~/.cache/pip
        key: ${{ runner.os }}-pip-${{ hashFiles('**/requirements*.txt') }}
        restore-keys: |
          ${{ runner.os }}-pip-
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install -r requirements-dev.txt
    
    - name: Run linting
      run: |
        black --check src/
        isort --check-only src/
        mypy src/
        flake8 src/
    
    - name: Run security checks
      run: |
        bandit -r src/
        safety check
    
    - name: Run tests
      env:
        DATABASE_URL: postgresql://postgres:postgres@localhost:5432/test_db
        REDIS_URL: redis://localhost:6379/0
        OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
      run: |
        pytest tests/ --cov=src --cov-report=xml --cov-report=html
    
    - name: Upload coverage to Codecov
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
        flags: unittests
        name: codecov-umbrella

  build:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Set up Docker Buildx
      uses: docker/setup-buildx-action@v3
    
    - name: Login to DockerHub
      uses: docker/login-action@v3
      with:
        username: ${{ secrets.DOCKERHUB_USERNAME }}
        password: ${{ secrets.DOCKERHUB_TOKEN }}
    
    - name: Build and push Docker image
      uses: docker/build-push-action@v5
      with:
        context: .
        push: true
        tags: |
          yourusername/ai-discord-bot:latest
          yourusername/ai-discord-bot:${{ github.sha }}
        cache-from: type=gha
        cache-to: type=gha,mode=max

  deploy:
    needs: [test, build]
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Deploy to production
      run: |
        echo "Production deployment would go here"
        # 실제 배포 스크립트를 여기에 추가
'''

# 파일 저장
with open("Dockerfile", "w", encoding="utf-8") as f:
    f.write(dockerfile_content)

with open("docker-compose.yml", "w", encoding="utf-8") as f:
    f.write(docker_compose_content)

# GitHub Actions 디렉토리 생성
import os
os.makedirs(".github/workflows", exist_ok=True)

with open(".github/workflows/ci.yml", "w", encoding="utf-8") as f:
    f.write(github_actions_content)

print("Docker 및 CI/CD 파일들이 생성되었습니다.")