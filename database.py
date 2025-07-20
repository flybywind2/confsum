"""
성능 최적화된 데이터베이스 관리자
배치 처리, 연결 풀링, 인덱스 최적화 등을 포함
"""
import os
import json
from contextlib import contextmanager
from typing import List, Optional, Dict, Any, Tuple, Generator
from sqlalchemy import (
    create_engine, text, Index, func, and_, or_,
    event, pool
)
from sqlalchemy.orm import sessionmaker, Session, selectinload, joinedload
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.pool import StaticPool

from models import Base, Page, PageRelationship, Person, PersonPageRelation
from config import config
from logging_config import get_logger
from exceptions import DatabaseError, raise_database_error

logger = get_logger("database")


class OptimizedDatabaseManager:
    """성능 최적화된 데이터베이스 매니저"""
    
    def __init__(self):
        self.engine = None
        self.SessionLocal = None
        self._setup_database()
        self._setup_indexes()
        self._setup_event_listeners()
        
    def _setup_database(self):
        """데이터베이스 설정 및 연결"""
        try:
            # 데이터베이스 디렉토리 생성
            db_dir = os.path.dirname(config.DATABASE_PATH)
            if db_dir and not os.path.exists(db_dir):
                os.makedirs(db_dir)
            
            # SQLite 최적화 설정
            sqlite_url = f"sqlite:///{config.DATABASE_PATH}"
            
            # 성능 최적화를 위한 엔진 설정
            self.engine = create_engine(
                sqlite_url,
                poolclass=StaticPool,
                pool_pre_ping=True,
                pool_recycle=300,
                connect_args={
                    "check_same_thread": False,
                    "timeout": 30,
                    # SQLite 성능 최적화 설정
                    "isolation_level": None,  # autocommit 모드
                },
                echo=config.DEBUG if hasattr(config, 'DEBUG') else False
            )
            
            # 세션 팩토리 생성
            self.SessionLocal = sessionmaker(
                autocommit=False,
                autoflush=False,
                bind=self.engine,
                expire_on_commit=False  # 성능 향상을 위해
            )
            
            # 테이블 생성
            Base.metadata.create_all(bind=self.engine)
            
            logger.info("데이터베이스 초기화 완료", extra_data={"db_path": config.DATABASE_PATH})
            
        except Exception as e:
            logger.error("데이터베이스 초기화 실패", extra_data={"error": str(e)})
            raise DatabaseError(f"데이터베이스 초기화 실패: {str(e)}")
    
    def _setup_indexes(self):
        """성능 최적화를 위한 인덱스 생성"""
        try:
            with self.get_session() as session:
                # SQLite 성능 최적화 설정
                session.execute(text("PRAGMA journal_mode=WAL"))  # Write-Ahead Logging
                session.execute(text("PRAGMA synchronous=NORMAL"))  # 성능과 안정성 균형
                session.execute(text("PRAGMA cache_size=10000"))  # 캐시 크기 증가
                session.execute(text("PRAGMA temp_store=memory"))  # 임시 저장소를 메모리에
                session.execute(text("PRAGMA mmap_size=268435456"))  # 256MB 메모리 맵
                
                # space_key 컬럼이 없는 경우 추가
                try:
                    session.execute(text("SELECT space_key FROM pages LIMIT 1"))
                except Exception:
                    logger.info("space_key 컬럼을 추가합니다...")
                    session.execute(text("ALTER TABLE pages ADD COLUMN space_key VARCHAR"))
                    session.commit()
                    logger.info("space_key 컬럼 추가 완료")
                
                # 추가 인덱스가 필요한 경우 여기에 추가
                # 예: session.execute(text("CREATE INDEX IF NOT EXISTS idx_custom ON pages(column)"))
                
                session.commit()
                
            logger.info("데이터베이스 인덱스 및 최적화 설정 완료")
            
        except Exception as e:
            logger.error("인덱스 설정 실패", extra_data={"error": str(e)})
    
    def _setup_event_listeners(self):
        """SQLAlchemy 이벤트 리스너 설정"""
        @event.listens_for(self.engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            """연결 시 SQLite PRAGMA 설정"""
            cursor = dbapi_connection.cursor()
            # 외래 키 제약 조건 활성화
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()
    
    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """컨텍스트 매니저를 사용한 안전한 세션 관리"""
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error("데이터베이스 트랜잭션 실패", extra_data={"error": str(e)})
            raise DatabaseError(f"데이터베이스 작업 실패: {str(e)}")
        finally:
            session.close()
    
    def create_page(self, page_data: dict) -> Page:
        """페이지 생성 (최적화)"""
        with self.get_session() as session:
            try:
                page = Page(**page_data)
                session.add(page)
                session.flush()  # ID 생성을 위해
                session.refresh(page)
                
                logger.debug(
                    "페이지 생성 완료",
                    extra_data={
                        "page_id": page.page_id,
                        "title": page.title
                    }
                )
                
                return page
                
            except SQLAlchemyError as e:
                logger.error(
                    "페이지 생성 실패",
                    extra_data={
                        "page_data": page_data,
                        "error": str(e)
                    }
                )
                raise DatabaseError(f"페이지 생성 실패: {str(e)}")
    
    def create_pages_batch(self, pages_data: List[dict]) -> List[Page]:
        """페이지 배치 생성 (성능 최적화)"""
        if not pages_data:
            return []
        
        with self.get_session() as session:
            try:
                pages = [Page(**data) for data in pages_data]
                session.add_all(pages)
                session.flush()
                
                for page in pages:
                    session.refresh(page)
                
                logger.info(
                    "페이지 배치 생성 완료",
                    extra_data={"count": len(pages)}
                )
                
                return pages
                
            except SQLAlchemyError as e:
                logger.error(
                    "페이지 배치 생성 실패",
                    extra_data={
                        "count": len(pages_data),
                        "error": str(e)
                    }
                )
                raise DatabaseError(f"페이지 배치 생성 실패: {str(e)}")
    
    def get_page(self, page_id: str) -> Optional[Page]:
        """페이지 조회 (최적화)"""
        with self.get_session() as session:
            try:
                page = session.query(Page).filter(Page.page_id == page_id).first()
                
                if page:
                    # 관련 데이터를 미리 로드
                    session.refresh(page)
                
                return page
                
            except SQLAlchemyError as e:
                logger.error(
                    "페이지 조회 실패",
                    extra_data={
                        "page_id": page_id,
                        "error": str(e)
                    }
                )
                return None
    
    def get_pages_batch(self, page_ids: List[str]) -> List[Page]:
        """페이지 배치 조회 (N+1 문제 해결)"""
        if not page_ids:
            return []
        
        with self.get_session() as session:
            try:
                pages = session.query(Page).filter(
                    Page.page_id.in_(page_ids)
                ).all()
                
                logger.debug(
                    "페이지 배치 조회 완료",
                    extra_data={
                        "requested": len(page_ids),
                        "found": len(pages)
                    }
                )
                
                return pages
                
            except SQLAlchemyError as e:
                logger.error(
                    "페이지 배치 조회 실패",
                    extra_data={
                        "page_ids": page_ids,
                        "error": str(e)
                    }
                )
                return []
    
    def update_page(self, page_id: str, updates: dict) -> bool:
        """페이지 업데이트 (최적화)"""
        with self.get_session() as session:
            try:
                result = session.query(Page).filter(
                    Page.page_id == page_id
                ).update(updates)
                
                success = result > 0
                
                if success:
                    logger.debug(
                        "페이지 업데이트 완료",
                        extra_data={
                            "page_id": page_id,
                            "updates": list(updates.keys())
                        }
                    )
                else:
                    logger.warning(
                        "페이지 업데이트 실패 - 페이지 없음",
                        extra_data={"page_id": page_id}
                    )
                
                return success
                
            except SQLAlchemyError as e:
                logger.error(
                    "페이지 업데이트 실패",
                    extra_data={
                        "page_id": page_id,
                        "updates": updates,
                        "error": str(e)
                    }
                )
                return False
    
    def update_pages_batch(self, updates: List[Tuple[str, dict]]) -> int:
        """페이지 배치 업데이트"""
        if not updates:
            return 0
        
        with self.get_session() as session:
            try:
                updated_count = 0
                
                for page_id, update_data in updates:
                    result = session.query(Page).filter(
                        Page.page_id == page_id
                    ).update(update_data)
                    updated_count += result
                
                logger.info(
                    "페이지 배치 업데이트 완료",
                    extra_data={
                        "requested": len(updates),
                        "updated": updated_count
                    }
                )
                
                return updated_count
                
            except SQLAlchemyError as e:
                logger.error(
                    "페이지 배치 업데이트 실패",
                    extra_data={
                        "count": len(updates),
                        "error": str(e)
                    }
                )
                return 0
    
    def get_all_pages(self, offset: int = 0, limit: int = 100) -> List[Page]:
        """모든 페이지 조회 (페이징)"""
        with self.get_session() as session:
            try:
                pages = session.query(Page).offset(offset).limit(limit).all()
                
                logger.debug(
                    "페이지 목록 조회 완료",
                    extra_data={
                        "offset": offset,
                        "limit": limit,
                        "count": len(pages)
                    }
                )
                
                return pages
                
            except SQLAlchemyError as e:
                logger.error(
                    "페이지 목록 조회 실패",
                    extra_data={"error": str(e)}
                )
                return []
    
    def search_pages(self, query: str = None, keywords: List[str] = None, 
                    offset: int = 0, limit: int = 20) -> List[Page]:
        """페이지 검색 (최적화)"""
        with self.get_session() as session:
            try:
                q = session.query(Page)
                
                # 텍스트 검색
                if query:
                    search_term = f"%{query}%"
                    q = q.filter(or_(
                        Page.title.like(search_term),
                        Page.summary.like(search_term),
                        Page.content.like(search_term)
                    ))
                
                # 키워드 검색
                if keywords:
                    for keyword in keywords:
                        keyword_term = f"%{keyword}%"
                        q = q.filter(Page.keywords.like(keyword_term))
                
                pages = q.offset(offset).limit(limit).all()
                
                logger.debug(
                    "페이지 검색 완료",
                    extra_data={
                        "query": query,
                        "keywords": keywords,
                        "found": len(pages)
                    }
                )
                
                return pages
                
            except SQLAlchemyError as e:
                logger.error(
                    "페이지 검색 실패",
                    extra_data={
                        "query": query,
                        "keywords": keywords,
                        "error": str(e)
                    }
                )
                return []
    
    def count_pages(self) -> int:
        """총 페이지 수 조회"""
        with self.get_session() as session:
            try:
                count = session.query(func.count(Page.page_id)).scalar()
                return count or 0
            except SQLAlchemyError as e:
                logger.error("페이지 수 조회 실패", extra_data={"error": str(e)})
                return 0
    
    def count_search_pages(self, query: str = None, keywords: List[str] = None) -> int:
        """검색 결과 페이지 수 조회"""
        with self.get_session() as session:
            try:
                q = session.query(func.count(Page.page_id))
                
                if query:
                    search_term = f"%{query}%"
                    q = q.filter(or_(
                        Page.title.like(search_term),
                        Page.summary.like(search_term),
                        Page.content.like(search_term)
                    ))
                
                if keywords:
                    for keyword in keywords:
                        keyword_term = f"%{keyword}%"
                        q = q.filter(Page.keywords.like(keyword_term))
                
                count = q.scalar()
                return count or 0
                
            except SQLAlchemyError as e:
                logger.error(
                    "검색 페이지 수 조회 실패",
                    extra_data={"error": str(e)}
                )
                return 0
    
    def get_recent_pages(self, limit: int = 10) -> List[Page]:
        """최근 수정된 페이지 조회"""
        with self.get_session() as session:
            try:
                pages = session.query(Page).order_by(
                    Page.modified_date.desc()
                ).limit(limit).all()
                
                return pages
                
            except SQLAlchemyError as e:
                logger.error(
                    "최근 페이지 조회 실패",
                    extra_data={"error": str(e)}
                )
                return []
    
    def get_all_keywords(self) -> List[str]:
        """모든 키워드 목록 조회 (최적화)"""
        with self.get_session() as session:
            try:
                # 모든 페이지의 키워드를 한 번에 가져와서 처리
                results = session.query(Page.keywords).filter(
                    Page.keywords.isnot(None)
                ).all()
                
                all_keywords = set()
                for (keywords_json,) in results:
                    try:
                        keywords = json.loads(keywords_json)
                        if isinstance(keywords, list):
                            all_keywords.update(keywords)
                    except (json.JSONDecodeError, TypeError):
                        continue
                
                return sorted(list(all_keywords))
                
            except SQLAlchemyError as e:
                logger.error(
                    "키워드 목록 조회 실패",
                    extra_data={"error": str(e)}
                )
                return []
    
    def page_exists(self, page_id: str) -> bool:
        """페이지 존재 여부 확인 (최적화)"""
        with self.get_session() as session:
            try:
                exists = session.query(
                    session.query(Page).filter(Page.page_id == page_id).exists()
                ).scalar()
                return bool(exists)
                
            except SQLAlchemyError as e:
                logger.error(
                    "페이지 존재 확인 실패",
                    extra_data={
                        "page_id": page_id,
                        "error": str(e)
                    }
                )
                return False
    
    def get_page_modified_date(self, page_id: str) -> Optional[str]:
        """페이지 수정일 조회 (최적화)"""
        with self.get_session() as session:
            try:
                result = session.query(Page.modified_date).filter(
                    Page.page_id == page_id
                ).first()
                
                return result[0] if result else None
                
            except SQLAlchemyError as e:
                logger.error(
                    "페이지 수정일 조회 실패",
                    extra_data={
                        "page_id": page_id,
                        "error": str(e)
                    }
                )
                return None
    
    def delete_page(self, page_id: str) -> bool:
        """페이지 삭제"""
        with self.get_session() as session:
            try:
                # 먼저 관련 관계 삭제
                session.query(PageRelationship).filter(
                    or_(
                        PageRelationship.source_page_id == page_id,
                        PageRelationship.target_page_id == page_id
                    )
                ).delete(synchronize_session=False)
                
                # 페이지 삭제
                result = session.query(Page).filter(
                    Page.page_id == page_id
                ).delete(synchronize_session=False)
                
                success = result > 0
                
                if success:
                    logger.info(
                        "페이지 삭제 완료",
                        extra_data={"page_id": page_id}
                    )
                
                return success
                
            except SQLAlchemyError as e:
                logger.error(
                    "페이지 삭제 실패",
                    extra_data={
                        "page_id": page_id,
                        "error": str(e)
                    }
                )
                return False
    
    def vacuum_database(self):
        """데이터베이스 최적화 (VACUUM)"""
        try:
            with self.engine.connect() as connection:
                connection.execute(text("VACUUM"))
                connection.execute(text("ANALYZE"))
            
            logger.info("데이터베이스 VACUUM 완료")
            
        except Exception as e:
            logger.error(
                "데이터베이스 VACUUM 실패",
                extra_data={"error": str(e)}
            )
    
    def get_database_stats(self) -> Dict[str, Any]:
        """데이터베이스 통계 정보 조회"""
        with self.get_session() as session:
            try:
                stats = {
                    "total_pages": session.query(func.count(Page.page_id)).scalar() or 0,
                    "total_relationships": session.query(func.count(PageRelationship.id)).scalar() or 0,
                }
                
                # 데이터베이스 파일 크기
                if os.path.exists(config.DATABASE_PATH):
                    stats["db_size_mb"] = round(
                        os.path.getsize(config.DATABASE_PATH) / (1024 * 1024), 2
                    )
                
                return stats
                
            except SQLAlchemyError as e:
                logger.error(
                    "데이터베이스 통계 조회 실패",
                    extra_data={"error": str(e)}
                )
                return {}
    
    def close(self):
        """데이터베이스 연결 종료"""
        if self.engine:
            self.engine.dispose()
            logger.info("데이터베이스 연결 종료")
    
    # Person 관련 메서드들
    def get_all_persons(self) -> List[Person]:
        """모든 인물 조회"""
        with self.get_session() as session:
            try:
                return session.query(Person).order_by(Person.mentioned_count.desc()).all()
            except SQLAlchemyError as e:
                logger.error("모든 인물 조회 실패", extra_data={"error": str(e)})
                raise_database_error("인물 목록 조회 실패", {"error": str(e)})
    
    def get_person_by_name(self, name: str) -> Optional[Person]:
        """이름으로 인물 조회"""
        with self.get_session() as session:
            try:
                return session.query(Person).filter(Person.name == name).first()
            except SQLAlchemyError as e:
                logger.error("인물 이름 조회 실패", extra_data={"name": name, "error": str(e)})
                return None
    
    def find_or_create_person(self, name: str, email: str = None, department: str = None, role: str = None) -> Person:
        """인물 찾기 또는 생성 (중복 방지)"""
        with self.get_session() as session:
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
                    
            except SQLAlchemyError as e:
                logger.error("인물 찾기/생성 실패", extra_data={"name": name, "error": str(e)})
                raise_database_error("인물 처리 실패", {"name": name, "error": str(e)})
    
    def update_person(self, person_id: int, person_data: dict) -> bool:
        """인물 정보 업데이트"""
        with self.get_session() as session:
            try:
                person = session.query(Person).filter(Person.person_id == person_id).first()
                if person:
                    for key, value in person_data.items():
                        if hasattr(person, key):
                            setattr(person, key, value)
                    session.commit()
                    return True
                return False
            except SQLAlchemyError as e:
                logger.error("인물 업데이트 실패", extra_data={"person_id": person_id, "error": str(e)})
                return False
    
    def get_person_relations(self, person_id: int) -> List[PersonPageRelation]:
        """특정 인물의 모든 페이지 관계 조회"""
        with self.get_session() as session:
            try:
                return session.query(PersonPageRelation).filter(
                    PersonPageRelation.person_id == person_id
                ).all()
            except SQLAlchemyError as e:
                logger.error("인물 관계 조회 실패", extra_data={"person_id": person_id, "error": str(e)})
                return []
    
    def create_person_page_relation(self, relation_data: dict) -> Optional[PersonPageRelation]:
        """인물-페이지 관계 생성"""
        with self.get_session() as session:
            try:
                relation = PersonPageRelation(**relation_data)
                session.add(relation)
                session.commit()
                session.refresh(relation)
                return relation
            except SQLAlchemyError as e:
                logger.error("인물-페이지 관계 생성 실패", extra_data={"relation_data": relation_data, "error": str(e)})
                return None
    
    def relation_exists(self, person_id: int, page_id: str, relation_type: str) -> bool:
        """인물-페이지 관계가 이미 존재하는지 확인"""
        with self.get_session() as session:
            try:
                relation = session.query(PersonPageRelation).filter(
                    PersonPageRelation.person_id == person_id,
                    PersonPageRelation.page_id == page_id,
                    PersonPageRelation.relation_type == relation_type
                ).first()
                return relation is not None
            except SQLAlchemyError as e:
                logger.error("관계 존재 확인 실패", extra_data={"person_id": person_id, "page_id": page_id, "relation_type": relation_type, "error": str(e)})
                return False
    
    # Space 관련 메서드들
    def get_all_spaces(self) -> List[dict]:
        """모든 Space 목록 조회"""
        with self.get_session() as session:
            try:
                spaces = session.query(Page.space_key)\
                    .filter(Page.space_key.isnot(None))\
                    .distinct()\
                    .all()
                
                space_list = []
                for space in spaces:
                    space_key = space[0]
                    page_count = session.query(Page).filter(Page.space_key == space_key).count()
                    space_list.append({
                        "space_key": space_key,
                        "page_count": page_count
                    })
                
                return sorted(space_list, key=lambda x: x['page_count'], reverse=True)
            except SQLAlchemyError as e:
                logger.error("Space 목록 조회 실패", extra_data={"error": str(e)})
                return []
    
    def get_pages_by_space(self, space_key: str, page: int = 1, per_page: int = 20) -> dict:
        """특정 Space의 페이지들 조회"""
        with self.get_session() as session:
            try:
                query = session.query(Page).filter(Page.space_key == space_key)
                total = query.count()
                
                pages = query.offset((page - 1) * per_page).limit(per_page).all()
                
                return {
                    "pages": [self._page_to_summary(p) for p in pages],
                    "total": total,
                    "page": page,
                    "per_page": per_page,
                    "space_key": space_key
                }
            except SQLAlchemyError as e:
                logger.error("Space별 페이지 조회 실패", extra_data={"space_key": space_key, "error": str(e)})
                return {"pages": [], "total": 0, "page": page, "per_page": per_page, "space_key": space_key}
    
    def get_space_stats(self, space_key: str) -> dict:
        """특정 Space의 통계 정보"""
        with self.get_session() as session:
            try:
                total_pages = session.query(Page).filter(Page.space_key == space_key).count()
                
                # 최근 수정된 페이지
                recent_pages = session.query(Page)\
                    .filter(Page.space_key == space_key)\
                    .filter(Page.modified_date.isnot(None))\
                    .count()
                
                # 키워드 개수 계산
                pages_with_keywords = session.query(Page)\
                    .filter(Page.space_key == space_key)\
                    .filter(Page.keywords.isnot(None))\
                    .all()
                
                unique_keywords = set()
                for page in pages_with_keywords:
                    if page.keywords:
                        try:
                            keywords = json.loads(page.keywords)
                            unique_keywords.update(keywords)
                        except:
                            pass
                
                return {
                    "space_key": space_key,
                    "total_pages": total_pages,
                    "recent_pages": recent_pages,
                    "total_unique_keywords": len(unique_keywords),
                    "top_keywords": list(unique_keywords)[:10]  # 상위 10개만
                }
            except SQLAlchemyError as e:
                logger.error("Space 통계 조회 실패", extra_data={"space_key": space_key, "error": str(e)})
                return {"space_key": space_key, "total_pages": 0, "recent_pages": 0, "total_unique_keywords": 0, "top_keywords": []}
    
    def create_relationship(self, source_page_id: str, target_page_id: str, weight: float, common_keywords: List[str]) -> Optional[PageRelationship]:
        """페이지 간 관계 생성"""
        with self.get_session() as session:
            try:
                # 이미 존재하는 관계인지 확인
                existing_relationship = session.query(PageRelationship).filter(
                    or_(
                        and_(
                            PageRelationship.source_page_id == source_page_id,
                            PageRelationship.target_page_id == target_page_id
                        ),
                        and_(
                            PageRelationship.source_page_id == target_page_id,
                            PageRelationship.target_page_id == source_page_id
                        )
                    )
                ).first()
                
                if existing_relationship:
                    # 기존 관계 업데이트
                    existing_relationship.weight = max(existing_relationship.weight, weight)
                    if common_keywords:
                        existing_relationship.common_keywords = json.dumps(common_keywords, ensure_ascii=False)
                    session.commit()
                    return existing_relationship
                else:
                    # 새 관계 생성
                    relationship_data = {
                        'source_page_id': source_page_id,
                        'target_page_id': target_page_id,
                        'weight': weight,
                        'common_keywords': json.dumps(common_keywords, ensure_ascii=False) if common_keywords else None
                    }
                    relationship = PageRelationship(**relationship_data)
                    session.add(relationship)
                    session.flush()
                    session.refresh(relationship)
                    
                    logger.debug(
                        "페이지 관계 생성 완료",
                        extra_data={
                            "source_page_id": source_page_id,
                            "target_page_id": target_page_id,
                            "weight": weight
                        }
                    )
                    
                    return relationship
                    
            except SQLAlchemyError as e:
                logger.error(
                    "페이지 관계 생성 실패",
                    extra_data={
                        "source_page_id": source_page_id,
                        "target_page_id": target_page_id,
                        "error": str(e)
                    }
                )
                return None
    
    def get_page_relationships(self, page_id: str) -> List[PageRelationship]:
        """특정 페이지의 모든 관계 조회"""
        with self.get_session() as session:
            try:
                relationships = session.query(PageRelationship).filter(
                    or_(
                        PageRelationship.source_page_id == page_id,
                        PageRelationship.target_page_id == page_id
                    )
                ).all()
                
                return relationships
                
            except SQLAlchemyError as e:
                logger.error(
                    "페이지 관계 조회 실패",
                    extra_data={
                        "page_id": page_id,
                        "error": str(e)
                    }
                )
                return []
    
    def _page_to_summary(self, page: Page) -> dict:
        """Page 객체를 요약 dict로 변환"""
        return {
            "page_id": page.page_id,
            "title": page.title,
            "summary": page.summary or "",
            "chunk_based_summary": page.chunk_based_summary or "",
            "keywords": page.keywords_list,
            "url": page.url or "",
            "space_key": page.space_key,
            "modified_date": page.modified_date,
            "created_date": page.created_date,
            "created_by": page.created_by,
            "modified_by": page.modified_by
        }


# 전역 데이터베이스 매니저 인스턴스
optimized_db_manager = OptimizedDatabaseManager()