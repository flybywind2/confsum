# Confluence Auto-Summarization System
## Product Requirements Document (PRD)

### 1. 프로젝트 개요
**목적**: Confluence Data Center API를 활용하여 페이지 계층 구조를 자동으로 수집하고, LLM을 통해 요약과 키워드를 추출하여 SQLite 데이터베이스에 저장하는 FastAPI 시스템

### 2. 기능 요구사항

#### 2.1 Confluence API 연동
- **인증 방식**: Basic Auth (ID/Password)
- **핵심 기능**:
  - 부모 페이지 ID를 입력받아 하위 페이지 재귀 조회
  - 페이지 메타데이터 및 콘텐츠 수집
  - 수정 날짜 기반 변경 감지

#### 2.2 LLM 서비스
- **지원 모델**:
  - Ollama (로컬 LLM - 우선순위)
  - OpenAI API (백업 옵션)
  - LangChain을 통한 프롬프트 관리
- **처리 기능**:
  - 페이지 콘텐츠 요약 생성
  - 주요 키워드 추출
  - 한국어 최적화

#### 2.3 데이터베이스
- **타입**: SQLite
- **스키마**:
  ```sql
  pages (
    page_id TEXT PRIMARY KEY,
    title TEXT,
    content TEXT,
    summary TEXT,
    keywords TEXT,
    url TEXT,
    modified_date TEXT,
    created_date TEXT
  )
  ```

#### 2.4 API 엔드포인트
- `POST /test-connection` - Confluence 서버 연결 테스트
- `POST /process-pages/{parent_page_id}` - 부모 페이지 하위 페이지 처리
- `GET /status/{page_id}` - 특정 페이지 처리 상태 확인
- `GET /summary/{page_id}` - 페이지 요약 조회
- `GET /mindmap/{parent_page_id}` - 키워드 기반 마인드맵 데이터 조회
- `GET /` - 메인 웹 UI 페이지

#### 2.5 웹 기반 제어 화면
- **목적**: 사용자 친화적인 웹 인터페이스 제공
- **기능**:
  - Confluence 서버 연결 설정 (URL, ID, Password)
  - 연결 상태 확인 및 테스트
  - 페이지 ID 입력 및 처리 실행
  - 실시간 처리 상태 모니터링
  - 처리 결과 확인 및 로그 표시
- **화면 구성**:
  - 연결 설정 섹션
  - 페이지 처리 실행 섹션
  - 상태 모니터링 섹션
  - 결과 표시 섹션

#### 2.6 키워드 기반 마인드맵 화면
- **목적**: 페이지 간 관계를 키워드를 통해 시각화
- **기능**:
  - 부모 페이지를 중심으로 하위 페이지들의 관계 표시
  - 공통 키워드를 가진 페이지들 간의 연결 시각화
  - 인터랙티브한 노드 클릭으로 페이지 상세 정보 표시
  - 키워드 필터링을 통한 관련 페이지 그룹화
- **데이터 구조**:
  ```json
  {
    "nodes": [
      {
        "id": "page_id",
        "title": "페이지 제목",
        "keywords": ["키워드1", "키워드2"],
        "url": "페이지 URL",
        "summary": "요약"
      }
    ],
    "links": [
      {
        "source": "source_page_id",
        "target": "target_page_id",
        "weight": 0.8,
        "common_keywords": ["공통키워드"]
      }
    ]
  }
  ```

### 3. 기술 스택
- **Backend**: FastAPI
- **Database**: SQLite + SQLAlchemy
- **LLM**: Ollama, OpenAI (langchain-openai)
- **API Client**: requests
- **Frontend**: HTML/CSS/JavaScript (D3.js 또는 Vis.js for 마인드맵)
- **Dependencies**: uvicorn, pydantic

### 4. 시스템 요구사항
- **환경 변수**:
  - CONFLUENCE_URL (Confluence 서버 URL)
  - CONFLUENCE_USER (사용자 ID)
  - CONFLUENCE_PASSWORD (비밀번호)
  - OLLAMA_URL (Ollama 서버 URL)
  - OPENAI_API_KEY (OpenAI API 키, 선택사항)
  - DATABASE_PATH (SQLite 파일 경로)

### 5. 처리 로직
1. 부모 페이지 ID 수신
2. Confluence API를 통해 하위 페이지 목록 조회
3. 각 페이지의 수정 날짜를 DB와 비교
4. 변경된 페이지만 LLM으로 처리
5. 요약 및 키워드 추출 결과를 DB에 저장

### 6. 프로젝트 구조
```
confauto/
├── main.py                 # FastAPI 애플리케이션
├── models.py               # SQLAlchemy 모델
├── confluence_api.py       # Confluence API 클라이언트
├── llm_service.py          # LLM 서비스
├── database.py             # 데이터베이스 연결
├── mindmap_service.py      # 마인드맵 데이터 생성 서비스
├── config.py               # 설정 관리
├── requirements.txt        # 의존성 패키지
├── templates/              # HTML 템플릿
│   ├── index.html          # 메인 제어 화면
│   └── mindmap.html        # 마인드맵 화면
├── static/                 # 정적 파일 (CSS, JS)
│   ├── main.js             # 메인 화면 로직
│   ├── mindmap.js          # 마인드맵 로직
│   └── style.css           # 스타일시트
└── PRD.md                  # 제품 요구사항 문서
```

### 7. 마인드맵 알고리즘
- **키워드 유사도 계산**: 
  - 페이지 간 공통 키워드 수 기반
  - TF-IDF 또는 코사인 유사도 활용
- **노드 연결 기준**:
  - 공통 키워드 2개 이상: 강한 연결
  - 공통 키워드 1개: 약한 연결
- **시각화**:
  - 중심성 기반 노드 크기 조정
  - 유사도 기반 링크 두께 조정

### 8. 성능 고려사항
- 대용량 페이지 처리를 위한 배치 처리
- LLM 호출 최적화 (변경된 페이지만 처리)
- 데이터베이스 인덱싱 (page_id, modified_date)
- 마인드맵 데이터 캐싱 (키워드 기반 관계 계산 결과)
- 에러 처리 및 재시도 로직