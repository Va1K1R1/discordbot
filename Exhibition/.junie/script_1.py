# requirements.txt 파일 생성
requirements_content = '''# Discord Bot 라이브러리
discord.py==2.3.2

# AI 및 NLP 라이브러리
openai==0.28.1
langchain==0.0.350
langchain-openai==0.0.2

# 데이터베이스 관련
SQLAlchemy==2.0.23
alembic==1.13.1
psycopg2-binary==2.9.9

# 설정 및 환경 변수
pydantic==2.5.2
python-dotenv==1.0.0

# 웹 요청
aiohttp==3.9.1
httpx==0.25.2

# 유틸리티
python-dateutil==2.8.2
pytz==2023.3

# 로깅 및 모니터링
structlog==23.2.0

# 캐싱
redis==5.0.1
aioredis==2.0.1

# 타입 힌팅
typing-extensions==4.8.0
'''

requirements_dev_content = '''# 개발 도구
pytest==7.4.3
pytest-asyncio==0.21.1
pytest-cov==4.1.0
pytest-mock==3.12.0

# 코드 품질
black==23.11.0
isort==5.12.0
mypy==1.7.1
flake8==6.1.0

# 개발 서버
watchdog==3.0.0

# 문서화
mkdocs==1.5.3
mkdocs-material==9.4.8

# 보안 검사
bandit==1.7.5
safety==2.3.5

# 성능 프로파일링
py-spy==0.3.14
memory-profiler==0.61.0
'''

# 파일 저장
with open("requirements.txt", "w", encoding="utf-8") as f:
    f.write(requirements_content)

with open("requirements-dev.txt", "w", encoding="utf-8") as f:
    f.write(requirements_dev_content)

print("requirements.txt와 requirements-dev.txt 파일이 생성되었습니다.")