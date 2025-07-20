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
    chunk_based_summary = Column(Text)  # RAG chunking 기반 요약
    keywords = Column(Text)  # JSON string
    url = Column(String)
    space_key = Column(String)  # Confluence Space Key
    modified_date = Column(String)
    created_date = Column(String)
    created_by = Column(String)  # 생성자
    modified_by = Column(String)  # 최종 수정자
    
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

class Person(Base):
    __tablename__ = 'persons'
    
    person_id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    email = Column(String)
    department = Column(String)
    role = Column(String)
    mentioned_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class PersonPageRelation(Base):
    __tablename__ = 'person_page_relations'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    person_id = Column(Integer, ForeignKey('persons.person_id'))
    page_id = Column(String, ForeignKey('pages.page_id'))
    relation_type = Column(String, nullable=False)  # creator, modifier, mentioned
    confidence_score = Column(Float, default=1.0)
    mentioned_context = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 관계 설정
    person = relationship("Person")
    page = relationship("Page")

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
    chunk_based_summary: Optional[str] = None
    keywords: List[str]
    url: str
    space_key: Optional[str] = None
    created_date: Optional[str] = None
    modified_date: Optional[str] = None
    created_by: Optional[str] = None
    modified_by: Optional[str] = None

class MindmapNode(BaseModel):
    id: str
    title: str
    keywords: List[str]
    url: str
    summary: str
    space_key: Optional[str] = None
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

# 인물 관련 Pydantic 모델들
class PersonInfo(BaseModel):
    person_id: int
    name: str
    email: Optional[str] = None
    department: Optional[str] = None
    role: Optional[str] = None
    mentioned_count: int = 0
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

class PersonPageRelationInfo(BaseModel):
    id: int
    person_id: int
    page_id: str
    relation_type: str
    confidence_score: float
    mentioned_context: Optional[str] = None
    created_at: Optional[str] = None

class ExtractedPerson(BaseModel):
    name: str
    department: Optional[str] = None
    role: Optional[str] = None
    email: Optional[str] = None
    mentioned_context: Optional[str] = None
    confidence: float = 0.0

class PersonExtractionResult(BaseModel):
    persons: List[ExtractedPerson]

class UserMindmapNode(BaseModel):
    id: str
    title: str
    relation_to_user: str  # creator, modifier, mentioned
    user_context: Optional[str] = None
    keywords: List[str]
    url: str
    summary: str
    size: int

class UserMindmapData(BaseModel):
    center_user: str
    relation_types: List[str]
    nodes: List[UserMindmapNode]
    links: List[MindmapLink]

class UserStats(BaseModel):
    name: str
    email: Optional[str] = None
    department: Optional[str] = None
    role: Optional[str] = None
    created_pages: int = 0
    modified_pages: int = 0
    mentioned_pages: int = 0
    total_relations: int = 0