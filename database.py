import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from models import Base, Page, PageRelationship
from config import config
from typing import List, Optional

class DatabaseManager:
    def __init__(self):
        # 데이터베이스 디렉토리 생성
        db_dir = os.path.dirname(config.DATABASE_PATH)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir)
        
        # SQLite 데이터베이스 연결
        self.engine = create_engine(f"sqlite:///{config.DATABASE_PATH}")
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        
        # 테이블 생성
        Base.metadata.create_all(bind=self.engine)
    
    def get_session(self) -> Session:
        """데이터베이스 세션 반환"""
        return self.SessionLocal()
    
    def create_page(self, page_data: dict) -> Page:
        """페이지 생성"""
        session = self.get_session()
        try:
            page = Page(**page_data)
            session.add(page)
            session.commit()
            session.refresh(page)
            return page
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
    
    def get_page(self, page_id: str) -> Optional[Page]:
        """페이지 조회"""
        session = self.get_session()
        try:
            return session.query(Page).filter(Page.page_id == page_id).first()
        finally:
            session.close()
    
    def get_pages_by_parent(self, parent_id: str) -> List[Page]:
        """부모 페이지와 관련된 페이지 조회 (키워드 유사성 기반)"""
        session = self.get_session()
        try:
            # 부모 페이지 조회
            parent_page = session.query(Page).filter(Page.page_id == parent_id).first()
            if not parent_page:
                return []
            
            parent_keywords = parent_page.keywords_list
            if not parent_keywords:
                # 키워드가 없으면 최근 페이지 10개 반환
                return session.query(Page).limit(10).all()
            
            # 모든 페이지 조회
            all_pages = session.query(Page).all()
            related_pages = []
            
            for page in all_pages:
                if page.page_id == parent_id:
                    continue  # 부모 페이지 자체는 제외
                
                page_keywords = page.keywords_list
                if not page_keywords:
                    continue
                
                # 키워드 유사성 계산 (Jaccard 유사도)
                common_keywords = set(parent_keywords) & set(page_keywords)
                union_keywords = set(parent_keywords) | set(page_keywords)
                
                if union_keywords:
                    similarity = len(common_keywords) / len(union_keywords)
                    if similarity > 0.1:  # 10% 이상 유사한 페이지만 포함
                        related_pages.append((page, similarity))
            
            # 유사도 순으로 정렬하여 상위 20개 반환
            related_pages.sort(key=lambda x: x[1], reverse=True)
            return [page for page, similarity in related_pages[:20]]
            
        finally:
            session.close()
    
    def update_page(self, page_id: str, updates: dict) -> Optional[Page]:
        """페이지 업데이트"""
        session = self.get_session()
        try:
            page = session.query(Page).filter(Page.page_id == page_id).first()
            if page:
                for key, value in updates.items():
                    setattr(page, key, value)
                session.commit()
                session.refresh(page)
                return page
            return None
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
    
    def delete_page(self, page_id: str) -> bool:
        """페이지 삭제"""
        session = self.get_session()
        try:
            page = session.query(Page).filter(Page.page_id == page_id).first()
            if page:
                session.delete(page)
                session.commit()
                return True
            return False
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
    
    def create_relationship(self, source_id: str, target_id: str, weight: float, common_keywords: List[str]) -> PageRelationship:
        """페이지 관계 생성"""
        session = self.get_session()
        try:
            relationship = PageRelationship(
                source_page_id=source_id,
                target_page_id=target_id,
                weight=weight
            )
            relationship.common_keywords_list = common_keywords
            session.add(relationship)
            session.commit()
            session.refresh(relationship)
            return relationship
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
    
    def get_relationships(self, page_id: str) -> List[PageRelationship]:
        """페이지 관계 조회"""
        session = self.get_session()
        try:
            return session.query(PageRelationship).filter(
                (PageRelationship.source_page_id == page_id) |
                (PageRelationship.target_page_id == page_id)
            ).all()
        finally:
            session.close()
    
    def page_exists(self, page_id: str) -> bool:
        """페이지 존재 여부 확인"""
        session = self.get_session()
        try:
            return session.query(Page).filter(Page.page_id == page_id).count() > 0
        finally:
            session.close()
    
    def get_page_modified_date(self, page_id: str) -> Optional[str]:
        """페이지 수정일 조회"""
        session = self.get_session()
        try:
            page = session.query(Page).filter(Page.page_id == page_id).first()
            return page.modified_date if page else None
        finally:
            session.close()
    
    def get_all_pages(self, offset: int = 0, limit: int = 20) -> List[Page]:
        """모든 페이지 조회 (페이징)"""
        session = self.get_session()
        try:
            return session.query(Page).offset(offset).limit(limit).all()
        finally:
            session.close()
    
    def count_pages(self) -> int:
        """총 페이지 수 조회"""
        session = self.get_session()
        try:
            return session.query(Page).count()
        finally:
            session.close()
    
    def search_pages(self, query: str = None, keywords: List[str] = None, offset: int = 0, limit: int = 20) -> List[Page]:
        """페이지 검색"""
        session = self.get_session()
        try:
            query_obj = session.query(Page)
            
            # 텍스트 검색
            if query:
                query_obj = query_obj.filter(
                    (Page.title.contains(query)) |
                    (Page.content.contains(query)) |
                    (Page.summary.contains(query))
                )
            
            # 키워드 검색
            if keywords:
                for keyword in keywords:
                    query_obj = query_obj.filter(Page.keywords.contains(keyword))
            
            return query_obj.offset(offset).limit(limit).all()
        finally:
            session.close()
    
    def count_search_pages(self, query: str = None, keywords: List[str] = None) -> int:
        """검색 결과 수 조회"""
        session = self.get_session()
        try:
            query_obj = session.query(Page)
            
            # 텍스트 검색
            if query:
                query_obj = query_obj.filter(
                    (Page.title.contains(query)) |
                    (Page.content.contains(query)) |
                    (Page.summary.contains(query))
                )
            
            # 키워드 검색
            if keywords:
                for keyword in keywords:
                    query_obj = query_obj.filter(Page.keywords.contains(keyword))
            
            return query_obj.count()
        finally:
            session.close()
    
    def get_recent_pages(self, limit: int = 10) -> List[Page]:
        """최근 수정된 페이지 조회"""
        session = self.get_session()
        try:
            return session.query(Page).order_by(Page.modified_date.desc()).limit(limit).all()
        finally:
            session.close()
    
    def get_pages_with_most_keywords(self, limit: int = 10) -> List[Page]:
        """키워드가 많은 페이지 조회"""
        session = self.get_session()
        try:
            # 키워드 개수가 많은 순으로 정렬 (JSON 길이 기준)
            return session.query(Page).filter(Page.keywords.isnot(None)).order_by(
                Page.keywords.desc()
            ).limit(limit).all()
        finally:
            session.close()
    
    def get_all_keywords(self) -> List[str]:
        """모든 키워드 목록 조회 (중복 제거 및 빈도순 정렬)"""
        session = self.get_session()
        try:
            pages = session.query(Page).filter(Page.keywords.isnot(None)).all()
            keyword_count = {}
            
            # 모든 키워드 수집 및 빈도 계산
            for page in pages:
                for keyword in page.keywords_list:
                    if keyword and keyword.strip():
                        keyword_clean = keyword.strip()
                        keyword_count[keyword_clean] = keyword_count.get(keyword_clean, 0) + 1
            
            # 빈도순으로 정렬하여 키워드만 반환
            sorted_keywords = sorted(keyword_count.items(), key=lambda x: x[1], reverse=True)
            return [keyword for keyword, count in sorted_keywords]
        finally:
            session.close()
    
    def get_pages_by_keyword(self, keyword: str, limit: int = 100) -> List[Page]:
        """특정 키워드를 포함한 페이지 조회"""
        session = self.get_session()
        try:
            return session.query(Page).filter(
                Page.keywords.contains(keyword)
            ).limit(limit).all()
        finally:
            session.close()

# 싱글톤 인스턴스
db_manager = DatabaseManager()