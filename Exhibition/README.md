# AI Discord 봇

이 프로젝트는 OpenAI API를 활용한 지능형 Discord 봇으로, 동적 명령어 생성 및 AI 기반 대화 기능을 제공합니다.

## 주요 기능

- AI 기반 대화 및 질문 응답
- 동적 커스텀 명령어 생성 및 관리
- 사용자 권한 관리
- 대화 기록 저장 및 분석

## 시작하기

### 필수 요구사항

- Python 3.8 이상
- Discord 봇 토큰
- OpenAI API 키

### 설치 방법

1. 저장소 클론:
   ```bash
   git clone https://github.com/yourusername/ai-discord-bot.git
   cd ai-discord-bot
   ```

2. 가상 환경 생성 및 활성화:
   ```bash
   python -m venv venv
   # Windows
   venv\Scripts\activate
   # macOS/Linux
   source venv/bin/activate
   ```

3. 의존성 설치:
   ```bash
   pip install -r requirements.txt
   ```

4. 환경 변수 설정:
   `.env.example` 파일을 `.env`로 복사하고 필요한 값을 설정합니다.
   ```bash
   cp .env.example .env
   # 편집기로 .env 파일 열기
   ```

### 실행 방법

#### 로컬 실행

```bash
python src/main.py
```

#### Docker 실행

```bash
docker-compose up -d
```

## 명령어 사용법

### 기본 명령어

- `/질문 [질문내용]` - AI에게 질문하고 답변 받기
- `/대화 [메시지]` - AI와 대화 시작 또는 계속하기
- `/대화초기화` - 현재 진행 중인 대화 초기화
- `/대화기록` - 최근 대화 기록 확인

### 관리자 명령어

- `/추가` - 새로운 커스텀 명령어 추가
- `/명령어삭제 [명령어이름]` - 커스텀 명령어 삭제
- `/역할설정 [명령어이름] [역할목록]` - 명령어에 허용된 역할 설정
- `/명령어정보 [명령어이름]` - 명령어 상세 정보 확인
- `/커맨드목록` - 서버의 모든 커스텀 명령어 목록 확인
- `/상태` - 봇 상태 정보 확인

## 프로젝트 구조

```
ai-discord-bot/
├── src/                    # 소스 코드
│   ├── commands/           # 명령어 처리
│   ├── config/             # 설정 관리
│   ├── models/             # 데이터 모델
│   ├── services/           # 서비스 로직
│   ├── utils/              # 유틸리티 함수
│   └── exceptions/         # 예외 처리
├── tests/                  # 테스트 코드
├── logs/                   # 로그 파일
├── docs/                   # 문서
├── .env.example            # 환경 변수 예시
├── requirements.txt        # 의존성 목록
├── Dockerfile              # Docker 이미지 정의
└── docker-compose.yml      # Docker 서비스 구성
```

## 테스트

```bash
pytest
```

## 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다.