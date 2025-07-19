import os
from typing import Optional

class Config:
    # 기본 설정
    DATABASE_PATH = os.getenv("DATABASE_PATH", "./data/pages.db")
    
    # Confluence 설정 (환경 변수 또는 동적 설정)
    CONFLUENCE_URL: Optional[str] = os.getenv("CONFLUENCE_URL")
    CONFLUENCE_USER: Optional[str] = os.getenv("CONFLUENCE_USER")
    CONFLUENCE_PASSWORD: Optional[str] = os.getenv("CONFLUENCE_PASSWORD")
    
    # LLM 설정
    OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
    OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemma3:4b")
    
    # OpenAI 설정 (선택사항)
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
    
    # 마인드맵 설정
    MINDMAP_THRESHOLD = float(os.getenv("MINDMAP_THRESHOLD", "0.3"))
    MINDMAP_MAX_DEPTH = int(os.getenv("MINDMAP_MAX_DEPTH", "3"))
    
    # 프롬프트 설정
    SUMMARY_PROMPT = """
    다음 Confluence 페이지 내용을 한국어로 요약해주세요. 요약은 3-5문장으로 작성하고, 핵심 내용을 포함해야 합니다.
    
    페이지 내용:
    {content}
    
    요약:
    """
    
    KEYWORDS_PROMPT = """
    다음 Confluence 페이지 내용에서 주요 키워드를 추출해주세요. 키워드는 5-10개로 제한하고, 쉼표로 구분해주세요.
    
    페이지 내용:
    {content}
    
    키워드:
    """

config = Config()