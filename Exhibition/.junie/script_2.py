# 환경 변수 예시 파일 생성
env_example_content = '''# Discord Bot 설정
DISCORD_TOKEN=your_discord_bot_token_here
DISCORD_GUILD_ID=your_test_guild_id_here

# OpenAI API 설정
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4
OPENAI_MAX_TOKENS=1000
OPENAI_TEMPERATURE=0.7

# 데이터베이스 설정
DATABASE_URL=sqlite:///./bot_database.db
# 프로덕션 환경에서는 PostgreSQL 사용
# DATABASE_URL=postgresql://user:password@localhost:5432/botdb

# Redis 캐시 (선택사항)
REDIS_URL=redis://localhost:6379/0

# 로깅 설정
LOG_LEVEL=INFO
LOG_FILE=logs/bot.log

# 보안 설정
ADMIN_USER_IDS=123456789012345678,987654321098765432
ALLOWED_GUILD_IDS=111111111111111111,222222222222222222
MAX_COMMAND_LENGTH=2000

# API 제한
MAX_REQUESTS_PER_MINUTE=60
MAX_AI_REQUESTS_PER_USER_PER_HOUR=20

# 기능 토글
ENABLE_NATURAL_LANGUAGE_PROCESSING=true
ENABLE_COMMAND_GENERATION=true
ENABLE_AI_RESPONSES=true
ENABLE_CONVERSATION_MEMORY=true

# 모니터링 (선택사항)
SENTRY_DSN=your_sentry_dsn_here
PROMETHEUS_PORT=8000
'''

gitignore_content = '''# Byte-compiled / optimized / DLL files
__pycache__/
*.py[cod]
*$py.class

# C extensions
*.so

# Distribution / packaging
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
share/python-wheels/
*.egg-info/
.installed.cfg
*.egg
MANIFEST

# PyInstaller
*.manifest
*.spec

# Installer logs
pip-log.txt
pip-delete-this-directory.txt

# Unit test / coverage reports
htmlcov/
.tox/
.nox/
.coverage
.coverage.*
.cache
nosetests.xml
coverage.xml
*.cover
*.py,cover
.hypothesis/
.pytest_cache/
cover/

# Translations
*.mo
*.pot

# Django stuff:
*.log
local_settings.py
db.sqlite3
db.sqlite3-journal

# Flask stuff:
instance/
.webassets-cache

# Scrapy stuff:
.scrapy

# Sphinx documentation
docs/_build/

# PyBuilder
.pybuilder/
target/

# Jupyter Notebook
.ipynb_checkpoints

# IPython
profile_default/
ipython_config.py

# pyenv
.python-version

# pipenv
Pipfile.lock

# poetry
poetry.lock

# pdm
.pdm.toml

# PEP 582
__pypackages__/

# Celery stuff
celerybeat-schedule
celerybeat.pid

# SageMath parsed files
*.sage.py

# Environments
.env
.venv
env/
venv/
ENV/
env.bak/
venv.bak/

# Spyder project settings
.spyderproject
.spyproject

# Rope project settings
.ropeproject

# mkdocs documentation
/site

# mypy
.mypy_cache/
.dmypy.json
dmypy.json

# Pyre type checker
.pyre/

# pytype static type analyzer
.pytype/

# Cython debug symbols
cython_debug/

# PyCharm
.idea/

# VS Code
.vscode/

# OS generated files
.DS_Store
.DS_Store?
._*
.Spotlight-V100
.Trashes
ehthumbs.db
Thumbs.db

# Discord Bot specific
logs/
*.db
data/
backups/

# Docker
.dockerignore
'''

# 파일 저장
with open(".env.example", "w", encoding="utf-8") as f:
    f.write(env_example_content)

with open(".gitignore", "w", encoding="utf-8") as f:
    f.write(gitignore_content)

print(".env.example과 .gitignore 파일이 생성되었습니다.")