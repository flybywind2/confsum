from sqlalchemy import Column, String, Text, DateTime, Float, Integer, ForeignKey, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from datetime import datetime
import json
from typing import List, Optional
from pydantic import BaseModel

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
    def keywords_list(self) -> List[str]:
        return json.loads(self.keywords) if self.keywords else []
    
    @keywords_list.setter
    def keywords_list(self, value: List[str]):
        self.keywords = json.dumps(value, ensure_ascii=False)

class PageRelationship(Base):
    __tablename__ = 'page_relationships'
    
    id = Column(Integer, primary_key=True)
    source_page_id = Column(String, ForeignKey('pages.page_id'))
    target_page_id = Column(String, ForeignKey('pages.page_id'))
    weight = Column(Float)
    common_keywords = Column(Text)  # JSON string
    created_at = Column(DateTime, default=datetime.utcnow)
    
    @property
    def common_keywords_list(self) -> List[str]:
        return json.loads(self.common_keywords) if self.common_keywords else []
    
    @common_keywords_list.setter
    def common_keywords_list(self, value: List[str]):
        self.common_keywords = json.dumps(value, ensure_ascii=False)

# Pydantic 모델 (API 응답용)
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

class PageListResponse(BaseModel):
    pages: List[PageSummary]
    total: int
    page: int
    per_page: int

class PageSearchRequest(BaseModel):
    query: Optional[str] = None
    keywords: Optional[List[str]] = None
    page: int = 1
    per_page: int = 20