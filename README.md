# Confluence Auto-Summarization System

Confluence Data Center API를 사용하여 페이지 계층 구조를 자동으로 수집하고, LLM을 통해 요약과 키워드를 추출하여 SQLite 데이터베이스에 저장하는 FastAPI 기반 웹 애플리케이션입니다.

## 주요 기능

- **Confluence 연동**: Basic Auth를 통한 Confluence Data Center 연결
- **자동 요약**: Ollama 또는 OpenAI를 통한 페이지 내용 요약
- **키워드 추출**: 페이지별 주요 키워드 자동 추출
- **변경 감지**: 수정 날짜 기반 변경 감지 및 처리
- **마인드맵 시각화**: 키워드 기반 페이지 관계 시각화
- **웹 UI**: 직관적인 웹 인터페이스

## 시스템 요구사항

- Python 3.9 이상
- Confluence Data Center 접근 권한
- Ollama 서버 (권장) 또는 OpenAI API 키

## 설치 및 실행

### 1. 저장소 클론
```bash
git clone <repository-url>
cd confauto
```

### 2. 가상환경 생성 및 활성화
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

### 3. 의존성 설치
```bash
pip install -r requirements.txt
```

### 4. 환경 변수 설정 (선택사항)
`.env` 파일을 생성하여 기본 설정을 구성할 수 있습니다:
```bash
# 데이터베이스 경로
DATABASE_PATH=./data/pages.db

# Ollama 설정
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=llama2

# OpenAI 설정 (선택사항)
OPENAI_API_KEY=your-openai-api-key
OPENAI_MODEL=gpt-3.5-turbo

# 마인드맵 설정
MINDMAP_THRESHOLD=0.3
MINDMAP_MAX_DEPTH=3
```

### 5. Ollama 설정 (권장)
```bash
# Ollama 설치 (macOS/Linux)
curl -fsSL https://ollama.ai/install.sh | sh

# 모델 다운로드
ollama pull llama2
```

### 6. 애플리케이션 실행
```bash
python main.py
```

또는 uvicorn을 직접 사용:
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

## 사용 방법

### 1. 웹 인터페이스 접속
브라우저에서 `http://localhost:8000`으로 접속

### 2. Confluence 연결 설정
- **Confluence URL**: `https://your-confluence.com`
- **사용자 ID**: Confluence 사용자 ID
- **비밀번호**: Confluence 비밀번호
- **연결 테스트** 버튼 클릭

### 3. 페이지 처리
- **부모 페이지 ID**: 처리할 부모 페이지 ID 입력
- **처리 시작** 버튼 클릭
- 진행 상황을 실시간으로 확인

### 4. 결과 확인
- 처리 완료 후 **마인드맵 보기** 버튼 클릭
- 키워드 기반 페이지 관계 시각화 확인

## API 엔드포인트

### 메인 엔드포인트
- `GET /` - 메인 웹 UI
- `POST /test-connection` - Confluence 연결 테스트
- `POST /process-pages/{parent_page_id}` - 페이지 처리 시작

### 상태 및 결과 조회
- `GET /status/{task_id}` - 처리 상태 확인
- `GET /summary/{page_id}` - 페이지 요약 조회
- `GET /mindmap/{parent_page_id}` - 마인드맵 데이터 조회

### 마인드맵
- `GET /mindmap` - 마인드맵 시각화 화면

## 프로젝트 구조

```
confauto/
├── main.py                 # FastAPI 애플리케이션
├── models.py               # 데이터베이스 모델
├── database.py             # 데이터베이스 연결 관리
├── confluence_api.py       # Confluence API 클라이언트
├── llm_service.py          # LLM 서비스 (Ollama/OpenAI)
├── mindmap_service.py      # 마인드맵 데이터 생성
├── config.py               # 설정 관리
├── requirements.txt        # 의존성 패키지
├── templates/              # HTML 템플릿
│   ├── index.html          # 메인 화면
│   └── mindmap.html        # 마인드맵 화면
├── static/                 # 정적 파일
│   ├── main.js             # 메인 화면 로직
│   ├── mindmap.js          # 마인드맵 로직
│   └── style.css           # 스타일시트
├── data/                   # 데이터베이스 파일
├── PRD.md                  # 제품 요구사항 문서
├── TRD.md                  # 기술 요구사항 문서
└── README.md               # 사용 가이드
```

## 마인드맵 기능

### 키워드 기반 관계 시각화
- 페이지 간 공통 키워드를 기반으로 관계 계산
- Jaccard 유사도를 사용한 연결 강도 측정
- 중심성 기반 노드 크기 조정

### 인터랙티브 기능
- 드래그 앤 드롭으로 노드 이동
- 줌 인/아웃 및 팬 기능
- 노드 클릭 시 상세 정보 표시
- 키워드 필터링
- 연결 강도 임계값 조정

## 문제 해결

### 1. Confluence 연결 실패
- URL 형식 확인 (`https://` 포함)
- 사용자 권한 확인
- 네트워크 연결 상태 확인

### 2. LLM 서비스 오류
- Ollama 서버 실행 상태 확인
- 모델 다운로드 확인
- OpenAI API 키 유효성 확인

### 3. 데이터베이스 오류
- 데이터베이스 디렉토리 권한 확인
- 디스크 공간 확인

## 개발 정보

### 기술 스택
- **Backend**: FastAPI, SQLAlchemy, Pydantic
- **Frontend**: HTML/CSS/JavaScript, D3.js
- **Database**: SQLite
- **LLM**: Ollama, OpenAI (langchain-openai)

### 주요 의존성
- `fastapi`: 웹 프레임워크
- `uvicorn`: ASGI 서버
- `sqlalchemy`: ORM
- `requests`: HTTP 클라이언트
- `ollama`: Ollama 클라이언트
- `langchain-openai`: OpenAI 통합

## 라이선스

이 프로젝트는 MIT 라이선스를 따릅니다.

## 기여

버그 리포트, 기능 요청, 풀 리퀘스트를 환영합니다.

## 지원

문제가 발생하면 GitHub Issues를 통해 문의해주세요.