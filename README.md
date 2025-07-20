# Confluence Auto-Summarization System

Confluence Data Center API를 사용하여 페이지 계층 구조를 자동으로 수집하고, LLM을 통해 요약과 키워드를 추출하며, 인물 정보를 추출하여 SQLite 데이터베이스에 저장하는 FastAPI 기반 웹 애플리케이션입니다.

## 주요 기능

### 📄 문서 처리
- **Confluence 연동**: Basic Auth를 통한 Confluence Data Center 연결
- **자동 요약**: Ollama 또는 OpenAI를 통한 페이지 내용 요약
- **키워드 추출**: 페이지별 주요 키워드 자동 추출
- **인물 정보 추출**: LLM 기반 페이지 내 인물 정보 자동 추출
- **변경 감지**: 수정 날짜 기반 변경 감지 및 처리

### 🎯 시각화 및 분석
- **키워드 마인드맵**: 키워드 기반 페이지 관계 시각화
- **전체 마인드맵**: 모든 페이지 간의 관계 네트워크
- **사용자별 마인드맵**: 특정 사용자와 연관된 문서/키워드 관계 시각화
- **인터랙티브 UI**: D3.js 기반의 드래그, 줌, 필터링 지원

### 🔧 관리 기능
- **데이터 조회**: 페이지, 키워드, 사용자 통계 및 검색
- **일괄 작업**: 선택된 페이지들의 일괄 재생성/삭제
- **모달 페이지 뷰어**: 페이지 상세 정보 확인
- **내보내기**: CSV/JSON 형태로 데이터 다운로드

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
OLLAMA_MODEL=gemma3:4b

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

# 모델 다운로드 (권장: gemma3:4b)
ollama pull gemma3:4b
```

### 6. 애플리케이션 실행
```bash
python main.py
```

또는 uvicorn을 직접 사용:
```bash
uvicorn main:app --host 0.0.0.0 --port 8002 --reload
```

## 사용 방법

### 1. 웹 인터페이스 접속
브라우저에서 `http://localhost:8002`으로 접속

### 2. Confluence 연결 설정
- **Confluence URL**: `https://your-confluence.com`
- **사용자 ID**: Confluence 사용자 ID
- **비밀번호**: Confluence 비밀번호
- **연결 테스트** 버튼 클릭

### 3. 페이지 처리
- **부모 페이지 ID**: 처리할 부모 페이지 ID 입력
- **처리 시작** 버튼 클릭
- 진행 상황을 실시간으로 확인

### 4. 결과 확인 및 활용
- **데이터 조회**: 처리된 페이지들을 검색하고 관리
- **키워드 마인드맵**: 특정 키워드 중심의 관계 시각화
- **사용자별 마인드맵**: 특정 사용자와 연관된 문서/키워드 관계 확인
- **일괄 작업**: 여러 페이지를 선택하여 재생성 또는 삭제

## API 엔드포인트

### 메인 엔드포인트
- `GET /` - 메인 웹 UI
- `GET /data` - 데이터 조회 인터페이스
- `GET /user-mindmap` - 사용자별 마인드맵 인터페이스
- `POST /test-connection` - Confluence 연결 테스트
- `POST /process-pages/{parent_page_id}` - 페이지 처리 시작

### 데이터 조회
- `GET /pages` - 페이지 목록 조회 (페이징, 검색, 필터링 지원)
- `GET /pages/stats` - 페이지 통계 정보
- `GET /pages/{page_id}` - 특정 페이지 조회
- `GET /pages/{page_id}/content` - 페이지 상세 내용
- `POST /pages/{page_id}/regenerate` - 페이지 재생성
- `DELETE /pages/{page_id}` - 페이지 삭제

### 사용자 관련
- `GET /api/users` - 사용자 목록 조회
- `GET /api/users/{user_name}/stats` - 특정 사용자 통계

### 마인드맵
- `GET /mindmap` - 키워드 마인드맵 화면
- `GET /mindmap/{parent_page_id}` - 특정 페이지 기반 마인드맵
- `GET /mindmap-all` - 전체 페이지 마인드맵
- `GET /mindmap-keyword` - 키워드 기반 마인드맵
- `GET /mindmap/user/{user_name}` - 사용자별 마인드맵

### 키워드
- `GET /keywords` - 전체 키워드 목록

## 프로젝트 구조

```
confauto/
├── main.py                 # FastAPI 애플리케이션
├── models.py               # 데이터베이스 모델 (Page, Person, Relations 등)
├── database.py             # 데이터베이스 연결 관리
├── database_optimized.py   # 최적화된 데이터베이스 매니저
├── confluence_api.py       # Confluence API 클라이언트
├── llm_service.py          # LLM 서비스 (Ollama/OpenAI)
├── mindmap_service.py      # 마인드맵 데이터 생성
├── content_utils.py        # 콘텐츠 처리 유틸리티
├── exceptions.py           # 커스텀 예외 클래스
├── exception_handlers.py   # 예외 처리 핸들러
├── logging_config.py       # 로깅 설정
├── config.py               # 설정 관리
├── requirements.txt        # 의존성 패키지
├── templates/              # HTML 템플릿
│   ├── index.html          # 메인 화면
│   ├── data.html           # 데이터 조회 화면
│   ├── mindmap.html        # 키워드 마인드맵 화면
│   └── user_mindmap.html   # 사용자별 마인드맵 화면
├── static/                 # 정적 파일
│   ├── main.js             # 메인 화면 로직
│   ├── data.js             # 데이터 조회 로직
│   ├── mindmap_simple.js   # 마인드맵 로직
│   ├── utils.js            # 공통 유틸리티
│   └── style.css           # 스타일시트
├── data/                   # 데이터베이스 파일
├── logs/                   # 로그 파일
├── PRD.md                  # 제품 요구사항 문서
├── TRD.md                  # 기술 요구사항 문서
└── README.md               # 사용 가이드
```

## 주요 기능 상세

### 🎯 사용자별 마인드맵
- **사용자 중심 시각화**: 선택된 사용자를 중심으로 연관 문서와 키워드를 표시
- **관계 유형 필터링**: 생성자, 수정자, 언급됨 등의 관계 유형별 필터링
- **사용자 통계**: 각 사용자별 생성/수정/언급된 페이지 수 표시
- **인터랙티브 네트워크**: D3.js 기반의 동적 네트워크 시각화

### 📊 데이터 관리
- **고급 검색**: 제목, 내용, 키워드 기반 검색
- **일괄 작업**: 여러 페이지 선택 후 일괄 재생성/삭제
- **페이지 상세 뷰어**: 모달을 통한 페이지 전체 내용 확인
- **데이터 내보내기**: CSV/JSON 형태로 검색 결과 다운로드

### 🔍 LLM 기반 인물 추출
- **정규식 + LLM 조합**: 후보 이름 추출 후 LLM으로 검증
- **한국어/영어 이름 패턴**: 다양한 이름 형식 지원
- **중복 방지**: 동일 인물의 중복 저장 방지
- **관계 추적**: 인물과 페이지 간의 다양한 관계 유형 추적

### 🎨 시각화 기능
- **다중 마인드맵 모드**: 키워드, 전체, 사용자별 마인드맵
- **노드 타입별 색상**: 사용자, 문서, 키워드별 구분된 색상
- **관계 강도 표시**: 연결선 두께로 관계 강도 표현
- **범례 및 필터**: 직관적인 범례와 다양한 필터링 옵션

## 마인드맵 기능

### 키워드 기반 관계 시각화
- 페이지 간 공통 키워드를 기반으로 관계 계산
- Jaccard 유사도를 사용한 연결 강도 측정
- 중심성 기반 노드 크기 조정

### 인터랙티브 기능
- 드래그 앤 드롭으로 노드 이동
- 줌 인/아웃 및 팬 기능
- 노드 클릭 시 상세 정보 모달 표시
- 키워드 필터링
- 연결 강도 임계값 조정
- 관계 유형별 필터링

## 문제 해결

### 1. Confluence 연결 실패
- URL 형식 확인 (`https://` 포함)
- 사용자 권한 확인
- 네트워크 연결 상태 확인

### 2. LLM 서비스 오류
- Ollama 서버 실행 상태 확인: `ollama serve`
- 모델 다운로드 확인: `ollama pull gemma3:4b`
- OpenAI API 키 유효성 확인

### 3. 데이터베이스 오류
- 데이터베이스 디렉토리 권한 확인
- 디스크 공간 확인
- 외래키 제약 조건 오류 시 관련 데이터 정리

### 4. 포트 충돌
- 기본 포트 8002 사용 중인 경우 main.py에서 포트 변경
- `netstat -ano | findstr :8002`로 포트 사용 확인

## 개발 정보

### 기술 스택
- **Backend**: FastAPI, SQLAlchemy, Pydantic
- **Frontend**: HTML/CSS/JavaScript, D3.js
- **Database**: SQLite
- **LLM**: Ollama (gemma3:4b), OpenAI
- **Visualization**: D3.js v7

### 주요 의존성
- `fastapi`: 웹 프레임워크
- `uvicorn`: ASGI 서버
- `sqlalchemy`: ORM
- `requests`: HTTP 클라이언트
- `ollama`: Ollama 클라이언트
- `langchain-openai`: OpenAI 통합
- `python-dotenv`: 환경변수 관리

### 최신 업데이트
- **v2.0.0**: 사용자별 마인드맵 기능 추가
- **v1.5.0**: 일괄 작업 기능 및 데이터 관리 UI 개선
- **v1.4.0**: LLM 기반 인물 정보 추출 기능
- **v1.3.0**: 다중 마인드맵 모드 지원
- **v1.2.0**: 고급 검색 및 필터링 기능

## 라이선스

이 프로젝트는 MIT 라이선스를 따릅니다.

## 기여

버그 리포트, 기능 요청, 풀 리퀘스트를 환영합니다.

## 지원

문제가 발생하면 GitHub Issues를 통해 문의해주세요.

---

## 📋 체크리스트

### 초기 설정
- [ ] Python 3.9+ 설치 확인
- [ ] 가상환경 생성 및 활성화
- [ ] 의존성 패키지 설치
- [ ] Ollama 설치 및 모델 다운로드
- [ ] Confluence 접근 권한 확인

### 기본 사용
- [ ] 서버 시작 (port 8002)
- [ ] Confluence 연결 테스트
- [ ] 페이지 처리 실행
- [ ] 데이터 조회 화면 확인
- [ ] 마인드맵 기능 테스트

### 고급 기능
- [ ] 사용자별 마인드맵 생성
- [ ] 일괄 작업 기능 테스트
- [ ] 데이터 내보내기 기능
- [ ] 검색 및 필터링 기능
- [ ] 페이지 상세 뷰어 확인