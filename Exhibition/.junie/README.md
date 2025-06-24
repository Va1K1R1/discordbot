# AI Discord Bot 프로젝트

> 자연어 이해와 동적 커맨드 생성을 결합한 AI 기반 Discord 봇

## 🚀 주요 기능

- **🧠 자연어 처리**: OpenAI GPT-4를 활용한 의도 분석 및 자연스러운 대화
- **⚡ 동적 커맨드 생성**: 사용자 대화만으로 새로운 슬래시 커맨드 실시간 생성
- **🔐 권한 관리**: 역할 기반 접근 제어 (RBAC) 시스템
- **💾 지능형 저장**: SQLAlchemy ORM을 통한 효율적인 데이터 관리
- **📊 모니터링**: 상세한 로깅 및 사용 통계

## 🏗 기술 스택

### 백엔드
- **Python 3.8+** - 메인 개발 언어
- **discord.py 2.0+** - Discord API 래퍼
- **OpenAI API** - GPT-4 자연어 처리
- **SQLAlchemy** - ORM 및 데이터베이스 관리
- **PostgreSQL/SQLite** - 데이터베이스
- **Redis** - 캐싱 (선택사항)

### 개발 도구
- **IntelliJ IDEA** - 통합 개발 환경
- **pytest** - 테스트 프레임워크
- **Black + isort** - 코드 포맷팅
- **mypy** - 타입 검사

### 배포 및 운영
- **Docker** - 컨테이너화
- **GitHub Actions** - CI/CD
- **Prometheus/Grafana** - 모니터링 (선택사항)

## 📦 설치 및 실행

### 1. 사전 요구사항

- Python 3.8 이상
- Discord 개발자 계정
- OpenAI API 키

### 2. 환경 설정

```bash
# 저장소 클론
git clone https://github.com/yourusername/ai-discord-bot.git
cd ai-discord-bot

# 가상 환경 생성 및 활성화
python -m venv venv
source venv/bin/activate  # Linux/macOS
# 또는
venv\Scripts\activate     # Windows

# 의존성 설치
pip install -r requirements.txt
```

### 3. 환경 변수 설정

`.env` 파일을 생성하고 다음 내용을 입력:

```env
# Discord Bot 설정
DISCORD_TOKEN=your_discord_bot_token
DISCORD_GUILD_ID=your_test_guild_id

# OpenAI API 설정
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=gpt-4

# 데이터베이스 설정
DATABASE_URL=sqlite:///./bot_database.db

# 보안 설정
ADMIN_USER_IDS=123456789,987654321
```

### 4. 봇 실행

```bash
python src/main.py
```

## 🤖 Discord 봇 설정

### 1. Discord Developer Portal 설정

1. [Discord Developer Portal](https://discord.com/developers/applications)에서 새 애플리케이션 생성
2. Bot 탭에서 봇 생성 및 토큰 복사
3. 다음 권한 활성화:
   - Send Messages
   - Use Slash Commands
   - Manage Messages
   - Embed Links
   - Read Message History

### 2. 봇 초대

다음 URL로 봇을 서버에 초대:
```
https://discord.com/api/oauth2/authorize?client_id=YOUR_CLIENT_ID&permissions=2147483648&scope=bot%20applications.commands
```

## 💬 사용법

### 기본 명령어

- `/추가` - 새로운 커맨드 생성 (관리자 전용)
- `/커맨드목록` - 서버의 모든 커맨드 확인
- `/도움말` - 봇 사용법 안내

### 자연어로 커맨드 생성

1. **자연어로 요청**: "공지사항을 올리는 커맨드를 만들어줘"
2. **AI 분석**: 봇이 의도를 분석하고 커맨드 생성 제안
3. **즉시 생성**: 확인 후 슬래시 커맨드로 자동 등록
4. **바로 사용**: 생성된 커맨드 즉시 사용 가능

### 예시 워크플로우

```
사용자: "날씨 정보를 알려주는 커맨드 만들어줘"
봇: 🤖 커맨드 생성을 감지했습니다. 생성하시겠습니까?
[생성하기] 버튼 클릭
→ /날씨 커맨드 자동 생성 및 등록
사용자: "/날씨 서울"
봇: "서울의 현재 날씨는..."
```

## 🏗 프로젝트 구조

```
ai-discord-bot/
├── src/
│   ├── main.py                 # 메인 봇 실행 파일
│   ├── config/
│   │   ├── settings.py         # 설정 관리
│   │   └── logging_config.py   # 로깅 설정
│   ├── models/
│   │   ├── database.py         # 데이터베이스 연결
│   │   ├── command.py          # 커맨드 모델
│   │   └── conversation.py     # 대화 기록 모델
│   ├── commands/
│   │   ├── admin.py            # 관리자 명령어
│   │   ├── dynamic.py          # 동적 커맨드 관리
│   │   └── ai_chat.py          # AI 채팅 명령어
│   ├── services/
│   │   ├── ai_service.py       # OpenAI API 연동
│   │   ├── command_service.py  # 커맨드 관리 서비스
│   │   └── permission_service.py # 권한 관리
│   └── utils/
│       ├── decorators.py       # 유틸리티 데코레이터
│       └── validators.py       # 입력 검증
├── tests/                      # 테스트 파일
├── docs/                       # 문서
├── requirements.txt            # 의존성 목록
├── docker-compose.yml          # Docker 설정
└── README.md                   # 프로젝트 문서
```

## 🔧 개발 환경 설정

### IntelliJ IDEA

상세한 IntelliJ IDEA 설정은 [IntelliJ 설정 가이드](IntelliJ-설정-가이드.md)를 참조하세요.

### 테스트 실행

```bash
# 전체 테스트
pytest

# 커버리지 포함
pytest --cov=src

# 특정 테스트 파일
pytest tests/test_ai_service.py
```

### 코드 포맷팅

```bash
# 코드 포맷팅
black src/
isort src/

# 타입 검사
mypy src/

# 린팅
flake8 src/
```

## 🐳 Docker 배포

### 개발 환경

```bash
docker-compose up -d
```

### 프로덕션 배포

```bash
# 이미지 빌드
docker build -t ai-discord-bot .

# 컨테이너 실행
docker run -d --name bot --env-file .env ai-discord-bot
```

## 📊 모니터링 및 로그

### 로그 확인

```bash
# 실시간 로그
tail -f logs/bot.log

# 최근 로그
tail -100 logs/bot.log
```

### 로그 레벨

- **DEBUG**: 상세한 디버그 정보
- **INFO**: 일반적인 정보 메시지
- **WARNING**: 경고 메시지
- **ERROR**: 오류 메시지
- **CRITICAL**: 치명적인 오류

## 🚨 문제 해결

### 자주 발생하는 문제

#### 1. 토큰 오류
```
discord.errors.LoginFailure: Improper token has been passed.
```
**해결방법**: `.env` 파일의 `DISCORD_TOKEN` 확인

#### 2. 권한 오류
```
discord.errors.Forbidden: 403 Forbidden
```
**해결방법**: 봇 권한 설정 확인 및 서버 역할 확인

#### 3. OpenAI API 오류
```
openai.error.RateLimitError
```
**해결방법**: API 사용량 확인 및 요청 제한 설정

### 디버그 모드 실행

```bash
LOG_LEVEL=DEBUG python src/main.py
```

## 🤝 기여하기

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### 코딩 스타일

- [Black](https://black.readthedocs.io/) 코드 포맷터 사용
- [isort](https://pycqa.github.io/isort/) import 정렬
- [mypy](https://mypy.readthedocs.io/) 타입 힌팅
- 함수와 클래스에 docstring 작성

## 📄 라이선스

이 프로젝트는 MIT 라이선스 하에 있습니다. 자세한 내용은 [LICENSE](LICENSE) 파일을 참조하세요.

## 📞 지원

- **이슈 리포트**: [GitHub Issues](https://github.com/yourusername/ai-discord-bot/issues)
- **문서**: [프로젝트 위키](https://github.com/yourusername/ai-discord-bot/wiki)
- **디스코드**: [개발자 서버](https://discord.gg/yourinvite)

## 📋 로드맵

- [x] 기본 Discord 봇 설정
- [x] AI 자연어 처리 통합
- [x] 동적 커맨드 생성 시스템
- [x] 권한 관리 시스템
- [ ] 웹 대시보드 구현
- [ ] 플러그인 시스템 개발
- [ ] 다국어 지원
- [ ] 음성 명령 지원

## 🙏 감사의 말

이 프로젝트는 다음 오픈소스 프로젝트들의 도움을 받았습니다:

- [discord.py](https://github.com/Rapptz/discord.py) - Discord API 래퍼
- [OpenAI API](https://openai.com/api/) - AI 자연어 처리
- [SQLAlchemy](https://www.sqlalchemy.org/) - Python ORM
- [FastAPI](https://fastapi.tiangolo.com/) - 웹 API 프레임워크

---

⭐ 이 프로젝트가 도움이 되었다면 스타를 눌러주세요!