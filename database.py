import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from models import Base, Page, PageRelationship, Person, PersonPageRelation
from config import config
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)

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
        
        # 새로운 컬럼들이 존재하는지 확인하고 없으면 추가
        self._ensure_columns_exist()
    
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
        """페이지 삭제 (관련된 모든 참조 포함)"""
        session = self.get_session()
        try:
            page = session.query(Page).filter(Page.page_id == page_id).first()
            if not page:
                logger.warning(f"삭제할 페이지를 찾을 수 없음: {page_id}")
                return False
            
            # 1. PersonPageRelation 테이블에서 관련 관계 삭제
            person_relations = session.query(PersonPageRelation).filter(
                PersonPageRelation.page_id == page_id
            ).all()
            for relation in person_relations:
                session.delete(relation)
            logger.info(f"PersonPageRelation 삭제됨: {len(person_relations)}개")
            
            # 2. PageRelationship 테이블에서 관련 관계 삭제
            page_relationships = session.query(PageRelationship).filter(
                (PageRelationship.source_id == page_id) | 
                (PageRelationship.target_id == page_id)
            ).all()
            for relationship in page_relationships:
                session.delete(relationship)
            logger.info(f"PageRelationship 삭제됨: {len(page_relationships)}개")
            
            # 3. PageKeyword 테이블에서 관련 키워드 관계 삭제
            page_keywords = session.query(PageKeyword).filter(
                PageKeyword.page_id == page_id
            ).all()
            for page_keyword in page_keywords:
                session.delete(page_keyword)
            logger.info(f"PageKeyword 삭제됨: {len(page_keywords)}개")
            
            # 4. 마지막으로 페이지 자체 삭제
            session.delete(page)
            session.commit()
            logger.info(f"페이지 삭제 완료: {page_id}")
            return True
            
        except Exception as e:
            session.rollback()
            logger.error(f"페이지 삭제 실패", extra={"page_id": page_id, "error": str(e)})
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
    
    def _ensure_columns_exist(self):
        """필요한 컬럼들이 존재하는지 확인하고 없으면 추가"""
        session = self.get_session()
        try:
            # 기존 테이블의 컬럼 정보 확인
            result = session.execute(text("PRAGMA table_info(pages)"))
            columns = [row[1] for row in result.fetchall()]
            
            # chunk_based_summary 컬럼 추가
            if 'chunk_based_summary' not in columns:
                logger.info("chunk_based_summary 컬럼 추가 중...")
                session.execute(text("ALTER TABLE pages ADD COLUMN chunk_based_summary TEXT"))
                session.commit()
                logger.info("chunk_based_summary 컬럼 추가 완료")
            
            # created_by 컬럼 추가
            if 'created_by' not in columns:
                logger.info("created_by 컬럼 추가 중...")
                session.execute(text("ALTER TABLE pages ADD COLUMN created_by TEXT"))
                session.commit()
                logger.info("created_by 컬럼 추가 완료")
            
            # modified_by 컬럼 추가
            if 'modified_by' not in columns:
                logger.info("modified_by 컬럼 추가 중...")
                session.execute(text("ALTER TABLE pages ADD COLUMN modified_by TEXT"))
                session.commit()
                logger.info("modified_by 컬럼 추가 완료")
                
        except Exception as e:
            logger.error(f"컬럼 추가 중 오류 발생: {str(e)}")
            session.rollback()
        finally:
            session.close()
    
    # Person 관련 메서드들
    def create_person(self, person_data: dict) -> Person:
        """인물 생성"""
        session = self.get_session()
        try:
            person = Person(**person_data)
            session.add(person)
            session.commit()
            session.refresh(person)
            return person
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
    
    def get_person_by_name(self, name: str) -> Optional[Person]:
        """이름으로 인물 조회"""
        session = self.get_session()
        try:
            return session.query(Person).filter(Person.name == name).first()
        finally:
            session.close()
    
    def update_person(self, person_id: int, person_data: dict) -> Person:
        """인물 정보 업데이트"""
        session = self.get_session()
        try:
            person = session.query(Person).filter(Person.person_id == person_id).first()
            if person:
                for key, value in person_data.items():
                    if hasattr(person, key):
                        setattr(person, key, value)
                session.commit()
                session.refresh(person)
            return person
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
    
    def create_person_page_relation(self, relation_data: dict) -> PersonPageRelation:
        """인물-페이지 관계 생성"""
        session = self.get_session()
        try:
            relation = PersonPageRelation(**relation_data)
            session.add(relation)
            session.commit()
            session.refresh(relation)
            return relation
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
    
    def get_person_relations(self, person_id: int) -> List[PersonPageRelation]:
        """특정 인물의 모든 페이지 관계 조회"""
        session = self.get_session()
        try:
            return session.query(PersonPageRelation).filter(
                PersonPageRelation.person_id == person_id
            ).all()
        finally:
            session.close()
    
    def get_page_relations(self, page_id: str) -> List[PersonPageRelation]:
        """특정 페이지의 모든 인물 관계 조회"""
        session = self.get_session()
        try:
            return session.query(PersonPageRelation).filter(
                PersonPageRelation.page_id == page_id
            ).all()
        finally:
            session.close()
    
    def get_all_persons(self) -> List[Person]:
        """모든 인물 조회"""
        session = self.get_session()
        try:
            return session.query(Person).order_by(Person.mentioned_count.desc()).all()
        finally:
            session.close()
    
    def get_person_by_relation_type(self, relation_type: str) -> List[Person]:
        """관계 유형별 인물 조회"""
        session = self.get_session()
        try:
            return session.query(Person).join(PersonPageRelation).filter(
                PersonPageRelation.relation_type == relation_type
            ).distinct().all()
        finally:
            session.close()
    
    def find_or_create_person(self, name: str, email: str = None, department: str = None, role: str = None) -> Person:
        """인물 찾기 또는 생성 (중복 방지)"""
        session = self.get_session()
        try:
            # 이름으로 먼저 찾기
            person = session.query(Person).filter(Person.name == name).first()
            
            if person:
                # 기존 인물 정보 업데이트
                updated = False
                if email and not person.email:
                    person.email = email
                    updated = True
                if department and not person.department:
                    person.department = department
                    updated = True
                if role and not person.role:
                    person.role = role
                    updated = True
                
                if updated:
                    session.commit()
                    session.refresh(person)
                
                return person
            else:
                # 새 인물 생성
                person_data = {
                    'name': name,
                    'email': email,
                    'department': department,
                    'role': role,
                    'mentioned_count': 0
                }
                person = Person(**person_data)
                session.add(person)
                session.commit()
                session.refresh(person)
                return person
                
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
    
    def relation_exists(self, person_id: int, page_id: str, relation_type: str) -> bool:
        """인물-페이지 관계가 이미 존재하는지 확인"""
        session = self.get_session()
        try:
            relation = session.query(PersonPageRelation).filter(
                PersonPageRelation.person_id == person_id,
                PersonPageRelation.page_id == page_id,
                PersonPageRelation.relation_type == relation_type
            ).first()
            return relation is not None
        finally:
            session.close()

# 싱글톤 인스턴스
db_manager = DatabaseManager()