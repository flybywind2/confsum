# Confluence Auto-Summarization System
## Technical Requirements Document (TRD)

### 1. 시스템 아키텍처

#### 1.1 전체 구조
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Confluence    │    │    FastAPI      │    │     SQLite      │
│   Data Center   │◄──►│   Application   │◄──►│    Database     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │
                              ▼
                       ┌─────────────────┐
                       │   LLM Service   │
                       │ (Ollama/OpenAI) │
                       └─────────────────┘
```

#### 1.2 레이어 구조
- **Presentation Layer**: FastAPI 엔드포인트, 정적 파일 서빙
- **Business Logic Layer**: 페이지 처리, 마인드맵 생성
- **Data Access Layer**: SQLAlchemy ORM, 데이터베이스 연결
- **External Integration Layer**: Confluence API, LLM 서비스

### 2. 데이터베이스 설계

#### 2.1 테이블 스키마
```sql
CREATE TABLE pages (
    page_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    content TEXT,
    summary TEXT,
    keywords TEXT,  -- JSON 배열 형태로 저장
    url TEXT,
    modified_date TEXT,
    created_date TEXT,
    INDEX idx_modified_date (modified_date),
    INDEX idx_keywords (keywords)
);

CREATE TABLE page_relationships (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_page_id TEXT,
    target_page_id TEXT,
    weight REAL,
    common_keywords TEXT,  -- JSON 배열
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (source_page_id) REFERENCES pages(page_id),
    FOREIGN KEY (target_page_id) REFERENCES pages(page_id)
);
```

#### 2.2 데이터 모델 (SQLAlchemy)
```python
from sqlalchemy import Column, String, Text, DateTime, Float, Integer, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import json

Base = declarative_base()

class Page(Base):
    __tablename__ = 'pages'
    
    page_id = Column(String, primary_key=True)
    title = Column(String, nullable=False)
    content = Column(Text)
    summary = Column(Text)
    keywords = Column(Text)  # JSON string
    url = Column(String)
    modified_date = Column(String)
    created_date = Column(String)
    
    @property
    def keywords_list(self):
        return json.loads(self.keywords) if self.keywords else []

class PageRelationship(Base):
    __tablename__ = 'page_relationships'
    
    id = Column(Integer, primary_key=True)
    source_page_id = Column(String, ForeignKey('pages.page_id'))
    target_page_id = Column(String, ForeignKey('pages.page_id'))
    weight = Column(Float)
    common_keywords = Column(Text)  # JSON string
    created_at = Column(DateTime)
```

### 3. API 설계

#### 3.1 엔드포인트 상세 명세
```python
# 메인 웹 UI
GET /
- Description: 메인 제어 화면 HTML 페이지 제공
- Response: HTML 파일

# Confluence 연결 테스트
POST /test-connection
- Description: Confluence 서버 연결 및 인증 테스트
- Request Body: {"url": "string", "username": "string", "password": "string"}
- Response: {"status": "success/failed", "message": "string", "user_info": "object"}

# 페이지 처리
POST /process-pages/{parent_page_id}
- Description: 부모 페이지 하위의 모든 페이지를 처리
- Parameters: parent_page_id (str)
- Request Body: {"confluence_url": "string", "username": "string", "password": "string"}
- Response: {"status": "processing", "task_id": "uuid", "total_pages": "int"}

# 처리 상태 확인
GET /status/{page_id}
- Description: 특정 페이지의 처리 상태 확인
- Parameters: page_id (str)
- Response: {"status": "completed", "processed_at": "datetime", "progress": "object"}

# 페이지 요약 조회
GET /summary/{page_id}
- Description: 페이지 요약 정보 조회
- Parameters: page_id (str)
- Response: {"summary": "text", "keywords": ["keyword1", "keyword2"]}

# 마인드맵 데이터 조회
GET /mindmap/{parent_page_id}
- Description: 키워드 기반 마인드맵 데이터 조회
- Parameters: parent_page_id (str)
- Query Parameters: 
  - threshold (float): 연결 강도 임계값 (default: 0.3)
  - max_depth (int): 최대 깊이 (default: 3)
- Response: MindmapData 구조

# 마인드맵 화면
GET /mindmap
- Description: 마인드맵 HTML 페이지 제공
- Response: HTML 파일
```

#### 3.2 데이터 전송 객체 (DTO)
```python
from pydantic import BaseModel
from typing import List, Optional

class ConfluenceConnection(BaseModel):
    url: str
    username: str
    password: str

class ConnectionTestResult(BaseModel):
    status: str
    message: str
    user_info: Optional[dict] = None

class ProcessRequest(BaseModel):
    confluence_url: str
    username: str
    password: str

class ProcessResponse(BaseModel):
    status: str
    task_id: str
    total_pages: int

class ProcessStatus(BaseModel):
    status: str
    processed_at: Optional[str] = None
    progress: Optional[dict] = None

class PageSummary(BaseModel):
    page_id: str
    title: str
    summary: str
    keywords: List[str]
    url: str

class MindmapNode(BaseModel):
    id: str
    title: str
    keywords: List[str]
    url: str
    summary: str
    size: int  # 노드 크기 (중심성 기반)

class MindmapLink(BaseModel):
    source: str
    target: str
    weight: float
    common_keywords: List[str]

class MindmapData(BaseModel):
    nodes: List[MindmapNode]
    links: List[MindmapLink]
    center_node: str
```

### 4. 외부 서비스 연동

#### 4.1 Confluence API 클라이언트
```python
class ConfluenceClient:
    def __init__(self, base_url: str, username: str, password: str):
        self.base_url = base_url
        self.auth = (username, password)
    
    def get_page_children(self, page_id: str, limit: int = 50) -> List[dict]:
        """페이지 하위 페이지 목록 조회"""
        
    def get_page_content(self, page_id: str) -> dict:
        """페이지 상세 정보 조회"""
        
    def get_page_history(self, page_id: str) -> dict:
        """페이지 수정 이력 조회"""
```

#### 4.2 LLM 서비스 인터페이스
```python
from abc import ABC, abstractmethod

class LLMService(ABC):
    @abstractmethod
    def summarize(self, content: str) -> str:
        pass
    
    @abstractmethod
    def extract_keywords(self, content: str) -> List[str]:
        pass

class OllamaService(LLMService):
    def __init__(self, base_url: str, model_name: str):
        self.base_url = base_url
        self.model_name = model_name
    
    def summarize(self, content: str) -> str:
        # Ollama API 호출 구현
        pass

class OpenAIService(LLMService):
    def __init__(self, api_key: str, model_name: str = "gpt-3.5-turbo"):
        self.api_key = api_key
        self.model_name = model_name
    
    def summarize(self, content: str) -> str:
        # OpenAI API 호출 구현 (langchain-openai 사용)
        pass
```

### 5. 마인드맵 알고리즘

#### 5.1 키워드 유사도 계산
```python
from typing import Set, List
from collections import Counter
import math

def calculate_keyword_similarity(keywords1: List[str], keywords2: List[str]) -> float:
    """키워드 간 유사도 계산 (Jaccard 유사도)"""
    set1 = set(keywords1)
    set2 = set(keywords2)
    
    intersection = len(set1.intersection(set2))
    union = len(set1.union(set2))
    
    return intersection / union if union > 0 else 0.0

def calculate_tfidf_similarity(pages: List[Page]) -> dict:
    """TF-IDF 기반 페이지 간 유사도 계산"""
    # TF-IDF 벡터 계산
    # 코사인 유사도 계산
    pass
```

#### 5.2 노드 중심성 계산
```python
def calculate_centrality(relationships: List[PageRelationship]) -> dict:
    """페이지 중심성 계산 (PageRank 알고리즘)"""
    # 그래프 생성
    # PageRank 알고리즘 적용
    # 중심성 점수 반환
    pass
```

### 6. 프론트엔드 구현

#### 6.1 메인 제어 화면 (HTML + JavaScript)
```html
<!-- templates/index.html -->
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Confluence Auto-Summarization</title>
    <link rel="stylesheet" href="/static/style.css">
</head>
<body>
    <div class="container">
        <h1>Confluence Auto-Summarization System</h1>
        
        <!-- 연결 설정 섹션 -->
        <div class="section">
            <h2>Confluence 연결 설정</h2>
            <form id="connectionForm">
                <input type="url" id="confluenceUrl" placeholder="Confluence URL" required>
                <input type="text" id="username" placeholder="사용자 ID" required>
                <input type="password" id="password" placeholder="비밀번호" required>
                <button type="button" id="testConnection">연결 테스트</button>
            </form>
            <div id="connectionStatus"></div>
        </div>
        
        <!-- 페이지 처리 섹션 -->
        <div class="section">
            <h2>페이지 처리</h2>
            <form id="processForm">
                <input type="text" id="pageId" placeholder="부모 페이지 ID" required>
                <button type="submit" id="processPages" disabled>처리 시작</button>
            </form>
            <div id="processStatus"></div>
        </div>
        
        <!-- 결과 표시 섹션 -->
        <div class="section">
            <h2>처리 결과</h2>
            <div id="results"></div>
            <button id="viewMindmap" disabled>마인드맵 보기</button>
        </div>
    </div>
    
    <script src="/static/main.js"></script>
</body>
</html>
```

```javascript
// static/main.js
class ConfluenceController {
    constructor() {
        this.connectionStatus = false;
        this.currentTaskId = null;
        this.init();
    }
    
    init() {
        this.bindEvents();
    }
    
    bindEvents() {
        document.getElementById('testConnection').addEventListener('click', () => this.testConnection());
        document.getElementById('processForm').addEventListener('submit', (e) => this.processPages(e));
        document.getElementById('viewMindmap').addEventListener('click', () => this.viewMindmap());
    }
    
    async testConnection() {
        const url = document.getElementById('confluenceUrl').value;
        const username = document.getElementById('username').value;
        const password = document.getElementById('password').value;
        
        try {
            const response = await fetch('/test-connection', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({url, username, password})
            });
            
            const result = await response.json();
            this.updateConnectionStatus(result);
        } catch (error) {
            this.updateConnectionStatus({status: 'failed', message: error.message});
        }
    }
    
    async processPages(event) {
        event.preventDefault();
        
        const pageId = document.getElementById('pageId').value;
        const url = document.getElementById('confluenceUrl').value;
        const username = document.getElementById('username').value;
        const password = document.getElementById('password').value;
        
        try {
            const response = await fetch(`/process-pages/${pageId}`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({confluence_url: url, username, password})
            });
            
            const result = await response.json();
            this.currentTaskId = result.task_id;
            this.startStatusPolling();
        } catch (error) {
            this.updateProcessStatus({status: 'failed', message: error.message});
        }
    }
    
    updateConnectionStatus(result) {
        const statusDiv = document.getElementById('connectionStatus');
        statusDiv.className = result.status === 'success' ? 'success' : 'error';
        statusDiv.textContent = result.message;
        
        this.connectionStatus = result.status === 'success';
        document.getElementById('processPages').disabled = !this.connectionStatus;
    }
    
    startStatusPolling() {
        // 상태 폴링 구현
    }
    
    viewMindmap() {
        const pageId = document.getElementById('pageId').value;
        window.open(`/mindmap?parent_id=${pageId}`, '_blank');
    }
}

// 페이지 로드 시 초기화
document.addEventListener('DOMContentLoaded', () => {
    new ConfluenceController();
});
```

#### 6.2 마인드맵 시각화 (D3.js)
```javascript
class MindmapVisualization {
    constructor(containerId, data) {
        this.container = d3.select(containerId);
        this.data = data;
        this.init();
    }
    
    init() {
        // SVG 초기화
        // 노드 및 링크 렌더링
        // 상호작용 이벤트 설정
    }
    
    updateFilter(keywords) {
        // 키워드 필터링
        // 노드 및 링크 업데이트
    }
    
    highlightPath(nodeId) {
        // 선택된 노드와 연결된 경로 강조
    }
}
```

### 7. 성능 최적화

#### 7.1 데이터베이스 최적화
- 인덱스 설정: page_id, modified_date, keywords
- 연결 풀 설정: SQLAlchemy 연결 풀 크기 조정
- 쿼리 최적화: N+1 문제 방지를 위한 eager loading

#### 7.2 캐싱 전략
```python
from functools import lru_cache
import redis

class CacheService:
    def __init__(self, redis_url: str):
        self.redis = redis.from_url(redis_url)
    
    @lru_cache(maxsize=1000)
    def get_mindmap_data(self, parent_page_id: str) -> dict:
        """마인드맵 데이터 캐싱"""
        pass
    
    def invalidate_cache(self, page_id: str):
        """페이지 업데이트 시 캐시 무효화"""
        pass
```

### 8. 보안 고려사항

#### 8.1 인증 및 권한 관리
- Confluence 계정 정보 안전한 저장 (환경 변수)
- API 키 암호화 저장
- 세션 관리 및 토큰 기반 인증

#### 8.2 입력 검증
- SQL 인젝션 방지: SQLAlchemy ORM 사용
- XSS 방지: 입력 데이터 이스케이프 처리
- 파라미터 검증: Pydantic 모델 활용

### 9. 배포 및 운영

#### 9.1 Docker 설정
```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### 9.2 환경 설정
```bash
# .env 파일
CONFLUENCE_URL=https://your-confluence.com
CONFLUENCE_USER=your-username
CONFLUENCE_PASSWORD=your-password
OLLAMA_URL=http://localhost:11434
OPENAI_API_KEY=your-openai-key
DATABASE_PATH=./data/pages.db
```

### 10. 모니터링 및 로깅

#### 10.1 로깅 설정
```python
import logging
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)
```

#### 10.2 메트릭 수집
- 페이지 처리 시간 측정
- LLM 호출 성공/실패 률
- 데이터베이스 쿼리 성능 모니터링