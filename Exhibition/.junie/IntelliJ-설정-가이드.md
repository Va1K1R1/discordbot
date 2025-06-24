# IntelliJ IDEA 설정 가이드

## 목차
1. [초기 설정](#초기-설정)
2. [Python 인터프리터 구성](#python-인터프리터-구성)
3. [프로젝트 구조 설정](#프로젝트-구조-설정)
4. [플러그인 설치 및 설정](#플러그인-설치-및-설정)
5. [코딩 스타일 설정](#코딩-스타일-설정)
6. [실행 및 디버그 구성](#실행-및-디버그-구성)
7. [Git 통합 설정](#git-통합-설정)
8. [데이터베이스 도구 설정](#데이터베이스-도구-설정)

## 초기 설정

### 1. IntelliJ IDEA 다운로드 및 설치

#### Community Edition (무료)
- [JetBrains 공식 사이트](https://www.jetbrains.com/idea/download/)에서 다운로드
- Python 플러그인 별도 설치 필요

#### Ultimate Edition (유료)
- Python 지원 내장
- 데이터베이스 도구, 웹 개발 도구 포함
- 학생 무료 라이선스 제공

### 2. 첫 실행 설정

1. **테마 선택**: Darcula (다크 테마) 또는 IntelliJ Light 선택
2. **플러그인 설치**: Python 플러그인 활성화 (Community Edition)
3. **키맵 설정**: Default 또는 선호하는 키맵 선택

## Python 인터프리터 구성

### 1. 프로젝트 열기

```
File → Open → ai-discord-bot 폴더 선택
```

### 2. Python 인터프리터 설정

#### 자동 감지 (권장)
1. IntelliJ가 가상환경을 자동으로 감지하면 알림 표시
2. "Configure Python Interpreter" 클릭
3. 감지된 가상환경 선택

#### 수동 설정
```
File → Project Structure → Project Settings → Project
```

**Windows:**
```
프로젝트경로\venv\Scripts\python.exe
```

**macOS/Linux:**
```
프로젝트경로/venv/bin/python
```

### 3. Python SDK 추가 (필요 시)

```
File → Project Structure → Platform Settings → SDKs → + → Python SDK
```

## 프로젝트 구조 설정

### 1. 소스 루트 설정

```
File → Project Structure → Project Settings → Modules
```

1. **src 폴더**: Sources Root로 마크
2. **tests 폴더**: Test Sources Root로 마크
3. **docs 폴더**: Excluded로 마크 (선택사항)

### 2. Content Root 설정

- 프로젝트 루트가 Content Root로 자동 설정
- 필요 시 추가 Content Root 지정 가능

### 3. 라이브러리 경로 설정

- 가상환경의 site-packages가 자동으로 추가됨
- 외부 라이브러리 경로 수동 추가 가능

## 플러그인 설치 및 설정

### 1. 필수 플러그인

```
File → Settings → Plugins
```

#### Python 개발 필수
- **Python** (Community Edition용)
- **.env files support**: 환경 변수 파일 지원
- **Requirements**: requirements.txt 관리

#### Git 및 버전 관리
- **Git Integration** (기본 내장)
- **GitToolBox**: Git 기능 강화
- **GitHub**: GitHub 통합

#### 데이터베이스
- **Database Tools and SQL** (Ultimate Edition 내장)
- **PostgreSQL**: PostgreSQL 지원 강화

### 2. 권장 플러그인

#### 코딩 도구
- **Rainbow Brackets**: 브래킷 색상 구분
- **Key Promoter X**: 단축키 학습 도구
- **String Manipulation**: 문자열 조작 도구
- **JSON Parser**: JSON 파싱 및 포맷팅

#### 문서화
- **Markdown**: 마크다운 파일 지원
- **PlantUML Integration**: UML 다이어그램

#### 기타 유틸리티
- **RestfulTool**: API 테스트 도구
- **SonarLint**: 코드 품질 검사
- **CodeGlance**: 미니맵 표시

### 3. 플러그인 설정

#### .env files support 설정
```
File → Settings → Languages & Frameworks → Environment Variables Files
```
- 프로젝트 루트의 `.env` 파일 자동 인식
- 환경 변수 자동 완성 활성화

## 코딩 스타일 설정

### 1. Python 코딩 스타일

```
File → Settings → Editor → Code Style → Python
```

#### 기본 설정
- **Indentation**: 4 spaces
- **Tab size**: 4
- **Continuation indent**: 4

#### 길이 제한
- **Right margin**: 88 (Black 스타일)
- **Hard wrap at**: 88

#### Import 스타일
```
File → Settings → Editor → Code Style → Python → Imports
```
- **Sort imports**: 활성화
- **From imports**: Use separate imports

### 2. 자동 포맷팅 설정

#### Black Formatter 설정
```
File → Settings → Tools → External Tools → +
```

**Black 설정:**
- **Name**: Black
- **Program**: `venv/Scripts/black.exe` (Windows) 또는 `venv/bin/black` (macOS/Linux)
- **Arguments**: `$FilePath$`
- **Working directory**: `$ProjectFileDir$`

#### isort 설정
```
File → Settings → Tools → External Tools → +
```

**isort 설정:**
- **Name**: isort
- **Program**: `venv/Scripts/isort.exe` (Windows) 또는 `venv/bin/isort` (macOS/Linux)
- **Arguments**: `$FilePath$`

### 3. 자동 저장 시 포맷팅

```
File → Settings → Tools → Actions on Save
```
- **Reformat code**: 활성화
- **Optimize imports**: 활성화

## 실행 및 디버그 구성

### 1. 메인 애플리케이션 실행 구성

```
Run → Edit Configurations → + → Python
```

**Discord Bot 구성:**
- **Name**: Discord Bot
- **Script path**: `src/main.py`
- **Parameters**: (비워둠)
- **Working directory**: `$PROJECT_DIR$`
- **Environment variables**: 
  ```
  DISCORD_TOKEN=your_token_here
  OPENAI_API_KEY=your_api_key_here
  DATABASE_URL=sqlite:///./bot_database.db
  ```

### 2. 테스트 실행 구성

```
Run → Edit Configurations → + → Python tests → pytest
```

**테스트 구성:**
- **Name**: All Tests
- **Target**: Custom
- **Custom**: `tests/`
- **Working directory**: `$PROJECT_DIR$`

### 3. 디버그 설정

#### 중단점 (Breakpoint) 설정
- 코드 라인 번호 왼쪽 클릭
- 조건부 중단점: 중단점 우클릭 → Condition

#### 디버그 실행
- **F9**: 중단점 토글
- **F8**: Step Over
- **F7**: Step Into
- **Shift+F8**: Step Out
- **F9**: Resume

### 4. 환경별 실행 구성

#### 개발 환경
```
DISCORD_GUILD_ID=your_test_guild_id
LOG_LEVEL=DEBUG
```

#### 프로덕션 환경
```
LOG_LEVEL=INFO
DATABASE_URL=postgresql://...
```

## Git 통합 설정

### 1. Git 저장소 연결

```
VCS → Git → Clone
```
또는 기존 프로젝트에서:
```
VCS → Import into Version Control → Create Git Repository
```

### 2. GitHub 계정 연결

```
File → Settings → Version Control → Git → GitHub
```
- **Add Account**: GitHub 계정 추가
- **Token**: Personal Access Token 사용 권장

### 3. Git 설정

```
File → Settings → Version Control → Git
```
- **Path to Git executable**: Git 설치 경로
- **Use credential helper**: 활성화

### 4. 커밋 및 푸시 설정

#### 커밋 템플릿 설정
```
File → Settings → Version Control → Git
```
**Commit Message Template:**
```
[타입] 제목

상세 설명

- 변경사항 1
- 변경사항 2

Closes #이슈번호
```

#### 자동 검사 설정
```
File → Settings → Version Control → Git
```
- **Perform code analysis**: 활성화
- **Check TODO**: 활성화
- **Run Git hooks**: 활성화

## 데이터베이스 도구 설정

### 1. 데이터베이스 연결

```
View → Tool Windows → Database
```

#### SQLite 연결
1. **+ → Data Source → SQLite**
2. **File**: `bot_database.db`
3. **Test Connection**: 연결 테스트

#### PostgreSQL 연결 (프로덕션)
1. **+ → Data Source → PostgreSQL**
2. **Host**: localhost
3. **Port**: 5432
4. **Database**: bot_db
5. **User/Password**: 설정값 입력

### 2. SQL 스크립트 실행

#### 쿼리 콘솔 열기
```
Database Tool Window → 데이터베이스 우클릭 → New → Query Console
```

#### 즐겨찾기 쿼리 저장
```
Ctrl+Shift+F → Add to Favorites
```

### 3. 테이블 스키마 시각화

```
Database Tool Window → 테이블 → Diagrams → Show Visualization
```

## 개발 워크플로우 최적화

### 1. 라이브 템플릿 설정

```
File → Settings → Editor → Live Templates
```

**Python 템플릿 예시:**
```python
# 로거 설정
logger = logging.getLogger(__name__)

# 비동기 함수
async def $NAME$($PARAMS$):
    """$DESC$"""
    $END$
```

### 2. 키보드 단축키 사용자 정의

```
File → Settings → Keymap
```

**추천 단축키:**
- **Ctrl+Shift+F10**: 현재 파일 실행
- **Ctrl+Shift+F9**: 디버그 모드 실행
- **Ctrl+Alt+L**: 코드 포맷팅
- **Ctrl+Alt+O**: Import 최적화

### 3. 프로젝트 템플릿 생성

```
File → Export Settings
```
- 설정을 템플릿으로 저장
- 새 프로젝트에서 Import Settings로 적용

## 문제 해결

### 1. 일반적인 문제

#### Python 인터프리터 인식 안됨
1. 가상환경 재생성
2. 캐시 무효화: `File → Invalidate Caches and Restart`
3. 인터프리터 수동 설정

#### 모듈 임포트 오류
1. Sources Root 설정 확인
2. `__init__.py` 파일 존재 확인
3. PYTHONPATH 설정 확인

### 2. 성능 최적화

#### 메모리 설정 조정
```
Help → Edit Custom VM Options
```
```
-Xmx4g
-XX:ReservedCodeCacheSize=512m
```

#### 인덱싱 최적화
```
File → Settings → Advanced Settings
```
- **Shared project indexes**: 활성화
- **Exclude from indexing**: logs, data 폴더 제외

이 가이드를 따라 설정하면 IntelliJ IDEA에서 효율적으로 Discord 봇을 개발할 수 있습니다.