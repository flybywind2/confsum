from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi import Request
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
import asyncio
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional

# 로컬 모듈 imports
from models import (
    ConfluenceConnection, ConnectionTestResult, ProcessRequest, 
    ProcessResponse, ProcessStatus, PageSummary, MindmapData,
    PageListResponse, PageSearchRequest, PersonPageRelation
)
from confluence_api import ConfluenceClient
from llm_service import llm_service
from database import optimized_db_manager as db_manager
from mindmap_service import mindmap_service
from config import config

# 새로운 모듈들
from logging_config import setup_logging, get_logger
from exceptions import (
    ConfluenceAutoBaseException, ConfluenceConnectionError, 
    ConfluenceAPIError, raise_confluence_connection_error,
    raise_not_found_error, raise_page_processing_error
)
from exception_handlers import (
    confluence_auto_exception_handler, custom_http_exception_handler,
    custom_validation_exception_handler, generic_exception_handler
)
from content_utils import ContentAnalyzer, ContentAnalysisResult, analyze_page_content, extract_fallback_keywords, clean_keywords

# 로깅 시스템 초기화
setup_logging()
logger = get_logger("main")

# FastAPI 애플리케이션 초기화
app = FastAPI(
    title="Confluence Auto-Summarization System",
    description="Confluence 페이지 자동 요약 및 키워드 추출 시스템",
    version="1.0.0"
)

# 예외 핸들러 등록
app.add_exception_handler(ConfluenceAutoBaseException, confluence_auto_exception_handler)
app.add_exception_handler(StarletteHTTPException, custom_http_exception_handler)
app.add_exception_handler(RequestValidationError, custom_validation_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)

# 정적 파일 및 템플릿 설정
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# 백그라운드 태스크 상태 관리
task_status: Dict[str, Dict[str, Any]] = {}

# localStorage 사용으로 서버 측 세션 저장소 제거됨

@app.get("/", response_class=HTMLResponse)
async def main_page(request: Request):
    """메인 제어 화면"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/test-connection", response_model=ConnectionTestResult)
async def test_connection(connection: ConfluenceConnection):
    """Confluence 연결 테스트"""
    connection_logger = logger.with_context(
        operation="test_connection",
        confluence_url=connection.url,
        username=connection.username
    )
    
    try:
        connection_logger.info("Confluence 연결 테스트 시작")
        
        client = ConfluenceClient(
            connection.url,
            connection.username,
            connection.password
        )
        
        result = client.test_connection()
        
        connection_logger.info(
            "Confluence 연결 테스트 완료",
            extra_data={"status": result["status"]}
        )
        
        return ConnectionTestResult(
            status=result["status"],
            message=result["message"],
            user_info=result.get("user_info")
        )
        
    except Exception as e:
        connection_logger.error(
            "Confluence 연결 테스트 실패",
            extra_data={"error": str(e)}
        )
        raise_confluence_connection_error(
            "Confluence 연결에 실패했습니다",
            {"original_error": str(e), "url": connection.url}
        )

@app.post("/process-pages/{parent_page_id}", response_model=ProcessResponse)
async def process_pages(
    parent_page_id: str, 
    request_data: ProcessRequest,
    background_tasks: BackgroundTasks
):
    """페이지 처리 시작"""
    task_id = str(uuid.uuid4())
    
    # 연결 정보 확인
    if not request_data.confluence_url or not request_data.username or not request_data.password:
        raise HTTPException(
            status_code=400, 
            detail="Confluence 연결 정보가 필요합니다. URL, 사용자명, 패스워드를 모두 제공해주세요."
        )
    
    confluence_url = request_data.confluence_url
    username = request_data.username
    password = request_data.password
    
    # 태스크 상태 초기화
    task_status[task_id] = {
        "status": "processing",
        "progress": {"total": 0, "completed": 0},
        "started_at": datetime.now().isoformat(),
        "page_id": parent_page_id
    }
    
    # 백그라운드 태스크 시작
    background_tasks.add_task(
        process_pages_background,
        task_id,
        parent_page_id,
        confluence_url,
        username,
        password
    )
    
    return ProcessResponse(
        status="processing",
        task_id=task_id,
        total_pages=0  # 백그라운드에서 업데이트
    )

async def process_pages_background(
    task_id: str,
    parent_page_id: str,
    confluence_url: str,
    username: str,
    password: str
):
    """백그라운드 페이지 처리"""
    try:
        # Confluence 클라이언트 생성
        client = ConfluenceClient(confluence_url, username, password)
        
        # 부모 페이지 및 모든 하위 페이지 조회
        logger.info(f"페이지 수집 시작: {parent_page_id}")
        
        # 부모 페이지 조회
        logger.info(f"부모 페이지 조회 시작: {parent_page_id}")
        parent_page = client.get_page_content(parent_page_id)
        if not parent_page:
            raise Exception(f"부모 페이지를 찾을 수 없습니다: {parent_page_id}")
        
        logger.info(f"부모 페이지 조회 완료: {parent_page.get('title', 'Unknown')}")
        
        # 모든 하위 페이지 조회
        logger.info("하위 페이지 조회 시작")
        all_pages = client.get_all_descendants(parent_page_id)
        all_pages.insert(0, parent_page)  # 부모 페이지 포함
        
        logger.info(f"전체 페이지 수집 완료: {len(all_pages)}개")
        
        # 진행 상태 업데이트
        task_status[task_id]["progress"]["total"] = len(all_pages)
        
        logger.info(f"총 {len(all_pages)}개 페이지 처리 시작")
        
        processed_pages = []
        
        for i, page_data in enumerate(all_pages):
            try:
                page_id = page_data.get('id')
                title = page_data.get('title', 'Untitled')
                
                logger.info(f"페이지 처리 중: {title} ({page_id})")
                
                # 페이지 수정 날짜 확인
                current_modified = page_data.get('version', {}).get('when', '')
                existing_modified = db_manager.get_page_modified_date(page_id)
                
                # 변경되지 않은 페이지는 건너뛰기
                if existing_modified == current_modified:
                    logger.info(f"페이지 건너뛰기 (변경 없음): {title}")
                    task_status[task_id]["progress"]["completed"] += 1
                    continue
                
                # 페이지 콘텐츠 추출 (전체 BODY 내용)
                logger.info(f"콘텐츠 추출 시작: {title}")
                content = client.extract_text_from_content(page_data.get('body', {}))
                
                logger.info(f"추출된 전체 BODY 콘텐츠 길이: {len(content) if content else 0}자")
                
                # 콘텐츠 분석
                content_analyzer = ContentAnalyzer()
                analysis_result = content_analyzer.analyze_content(content, title)
                
                logger.info(f"콘텐츠 분석 완료: {analysis_result.content_type}, 특수키워드: {analysis_result.special_keywords}")
                
                # 콘텐츠가 없는 경우 대체 처리
                if not content or len(content.strip()) < 10:
                    logger.warning(f"콘텐츠가 부족합니다 ({title}): {len(content) if content else 0}자")
                    # 페이지 제목을 기본 요약으로 사용
                    summary = f"페이지 제목: {title}"
                    chunk_based_summary = summary  # 짧은 콘텐츠는 동일한 요약 사용
                    keywords = ["내용없음"]
                    if title:
                        keywords.append(title)
                    # 특수 키워드를 우선적으로 추가 (중복 제거)
                    for special_kw in analysis_result.special_keywords:
                        if special_kw not in keywords:
                            keywords.insert(0, special_kw)  # 앞쪽에 추가
                    
                    # 데이터베이스에 최소한의 정보라도 저장
                    content = summary
                
                # LLM 처리
                elif llm_service:
                    try:
                        logger.info(f"LLM 처리 시작: {title} ({len(content)}자)")
                        
                        # 콘텐츠가 짧으면 간단 처리
                        if len(content.strip()) < 100:
                            summary = content.strip()
                            chunk_based_summary = summary  # 짧은 콘텐츠는 동일한 요약 사용
                            # 간단한 키워드 추출
                            keywords = extract_fallback_keywords(content, max_keywords=5)
                            
                            # 키워드가 부족하거나 내용이 매우 짧으면 "내용없음" 추가
                            if len(content.strip()) < 10 or len(keywords) < 2:
                                if "내용없음" not in keywords:
                                    keywords.insert(0, "내용없음")
                            
                            # 특수 키워드 추가 (HTML, 이미지 등)
                            keywords.extend(analysis_result.special_keywords)
                        else:
                            # 두 가지 요약을 모두 생성
                            logger.info(f"일반 요약 생성 시작: {title}")
                            summary = llm_service.summarize(content)
                            raw_keywords = llm_service.extract_keywords(content)
                            
                            # RAG chunking 기반 요약도 생성
                            chunk_based_summary = None
                            if config.RAG_ENABLED and len(content) > config.RAG_CHUNK_SIZE:
                                logger.info(f"RAG chunking 기반 요약 생성 시작: {title}")
                                try:
                                    chunk_based_summary = llm_service.chunk_based_summarize(content, title)
                                    logger.info(f"RAG chunking 요약 완료: {title}")
                                except Exception as e:
                                    logger.warning(f"RAG chunking 요약 실패, 일반 요약 사용: {title} - {str(e)}")
                                    chunk_based_summary = summary
                            else:
                                # 짧은 콘텐츠는 일반 요약을 chunk 기반 요약으로도 사용
                                chunk_based_summary = summary
                            
                            # 키워드 결과 검증 및 정리
                            keywords = clean_keywords(raw_keywords)
                            
                            # 키워드가 부족하면 폴백 처리
                            if len(keywords) < 2:
                                fallback_keywords = extract_fallback_keywords(content)
                                keywords.extend(fallback_keywords)
                            
                            # 특수 키워드를 우선적으로 추가 (중복 제거)
                            for special_kw in analysis_result.special_keywords:
                                if special_kw not in keywords:
                                    keywords.insert(0, special_kw)  # 앞쪽에 추가
                            keywords = keywords[:10]  # 최대 10개로 제한
                        
                        logger.info(f"LLM 처리 완료: {title}, 요약 길이: {len(summary)}, 키워드 수: {len(keywords)}")
                        
                    except Exception as e:
                        logger.warning(f"LLM 처리 실패 ({title}): {str(e)}")
                        # 폴백: 간단한 요약
                        sentences = content.split('.')[:3]
                        summary = '. '.join(sentences).strip()
                        if not summary:
                            summary = content[:200] + "..." if len(content) > 200 else content
                        
                        chunk_based_summary = summary  # 폴백 시에도 동일한 요약 사용
                        
                        # 간단한 키워드 추출
                        keywords = extract_fallback_keywords(content)
                        
                        # 내용이 짧거나 키워드가 부족하면 "내용없음" 추가
                        if len(content.strip()) < 10 or len(keywords) < 2:
                            if "내용없음" not in keywords:
                                keywords.insert(0, "내용없음")
                        
                        # 특수 키워드를 우선적으로 추가 (중복 제거)
                        for special_kw in analysis_result.special_keywords:
                            if special_kw not in keywords:
                                keywords.insert(0, special_kw)  # 앞쪽에 추가
                
                else:
                    logger.warning(f"LLM 서비스가 없습니다. 기본 처리: {title}")
                    # LLM 없이 기본 처리
                    sentences = content.split('.')[:3]
                    summary = '. '.join(sentences).strip()
                    if not summary:
                        summary = content[:300] + "..." if len(content) > 300 else content
                    
                    chunk_based_summary = summary  # LLM 없이는 동일한 요약 사용
                    
                    # 기본 키워드 추출
                    keywords = extract_fallback_keywords(content)
                    
                    # 내용이 짧거나 키워드가 부족하면 "내용없음" 추가
                    if len(content.strip()) < 10 or len(keywords) < 2:
                        if "내용없음" not in keywords:
                            keywords.insert(0, "내용없음")
                    
                    # 특수 키워드를 우선적으로 추가 (중복 제거)
                    for special_kw in analysis_result.special_keywords:
                        if special_kw not in keywords:
                            keywords.insert(0, special_kw)  # 앞쪽에 추가
                
                # 페이지 URL 생성
                space_key = page_data.get('space', {}).get('key', '')
                page_url = client.get_page_url(page_id, space_key)
                
                # 생성자와 수정자 정보 추출
                created_by = page_data.get('history', {}).get('createdBy', {}).get('displayName', '')
                # 최종 수정자는 version 정보에서 가져오기 (더 정확함)
                modified_by = page_data.get('version', {}).get('by', {}).get('displayName', '')
                # 만약 version에 없으면 history에서 시도
                if not modified_by:
                    modified_by = page_data.get('history', {}).get('lastUpdated', {}).get('by', {}).get('displayName', '')
                
                # 데이터베이스에 저장 (전체 BODY 내용 포함)
                page_db_data = {
                    'page_id': page_id,
                    'title': title,
                    'content': content,  # 전체 BODY 내용 저장
                    'summary': summary,
                    'chunk_based_summary': chunk_based_summary,  # RAG chunking 기반 요약
                    'url': page_url,
                    'space_key': space_key,  # Space Key 추가
                    'modified_date': current_modified,
                    'created_date': page_data.get('history', {}).get('createdDate', ''),
                    'created_by': created_by,
                    'modified_by': modified_by
                }
                
                logger.info(f"DB 저장 예정 콘텐츠 길이: {len(content) if content else 0}자")
                
                if db_manager.page_exists(page_id):
                    db_manager.update_page(page_id, page_db_data)
                else:
                    # 키워드 리스트를 JSON 문자열로 변환
                    page_obj = db_manager.create_page(page_db_data)
                    page_obj.keywords_list = keywords
                    db_manager.update_page(page_id, {'keywords': page_obj.keywords})
                
                # 인물 정보 추출 및 저장
                if llm_service and content and len(content.strip()) > 100:
                    try:
                        logger.info(f"인물 정보 추출 시작: {title}")
                        person_extraction = llm_service.extract_persons(content, title)
                        
                        # 생성자/수정자 관계 저장
                        if created_by:
                            creator_person = db_manager.find_or_create_person(created_by)
                            # 생성자 관계 저장
                            relation_data = {
                                'person_id': creator_person.person_id,
                                'page_id': page_id,
                                'relation_type': 'creator',
                                'confidence_score': 1.0,
                                'mentioned_context': f'페이지 생성자'
                            }
                            # 중복 체크
                            if not db_manager.relation_exists(creator_person.person_id, page_id, 'creator'):
                                db_manager.create_person_page_relation(relation_data)
                        
                        if modified_by and modified_by != created_by:
                            modifier_person = db_manager.find_or_create_person(modified_by)
                            # 수정자 관계 저장
                            relation_data = {
                                'person_id': modifier_person.person_id,
                                'page_id': page_id,
                                'relation_type': 'modifier',
                                'confidence_score': 1.0,
                                'mentioned_context': f'페이지 최종 수정자'
                            }
                            # 중복 체크
                            if not db_manager.relation_exists(modifier_person.person_id, page_id, 'modifier'):
                                db_manager.create_person_page_relation(relation_data)
                        
                        # LLM 추출 인물들 저장
                        for extracted_person in person_extraction.persons:
                            try:
                                # 인물 찾기 또는 생성
                                person = db_manager.find_or_create_person(
                                    name=extracted_person.name,
                                    email=extracted_person.email,
                                    department=extracted_person.department,
                                    role=extracted_person.role
                                )
                                
                                # 언급 횟수 증가
                                person.mentioned_count += 1
                                db_manager.update_person(person.person_id, {'mentioned_count': person.mentioned_count})
                                
                                # 언급 관계 저장
                                relation_data = {
                                    'person_id': person.person_id,
                                    'page_id': page_id,
                                    'relation_type': 'mentioned',
                                    'confidence_score': extracted_person.confidence,
                                    'mentioned_context': extracted_person.mentioned_context
                                }
                                
                                # 중복 체크 (같은 페이지에서 같은 사람의 언급 관계)
                                if not db_manager.relation_exists(person.person_id, page_id, 'mentioned'):
                                    db_manager.create_person_page_relation(relation_data)
                                    logger.info(f"인물 관계 저장: {person.name} -> {title}")
                                
                            except Exception as e:
                                logger.warning(f"인물 관계 저장 실패 ({extracted_person.name}): {str(e)}")
                        
                        logger.info(f"인물 정보 추출 완료: {title}, {len(person_extraction.persons)}명 발견")
                        
                    except Exception as e:
                        logger.warning(f"인물 정보 추출 실패 ({title}): {str(e)}")
                
                processed_pages.append(db_manager.get_page(page_id))
                
                # 진행 상태 업데이트
                task_status[task_id]["progress"]["completed"] += 1
                
                logger.info(f"페이지 처리 완료: {title}")
                
            except Exception as e:
                logger.error(f"페이지 처리 오류: {str(e)}")
                task_status[task_id]["progress"]["completed"] += 1
                continue
        
        # 마인드맵 관계 업데이트
        if processed_pages:
            mindmap_service.update_relationships(processed_pages)
        
        # 태스크 완료
        task_status[task_id]["status"] = "completed"
        task_status[task_id]["completed_at"] = datetime.now().isoformat()
        
        logger.info(f"페이지 처리 완료: {len(processed_pages)}개 페이지")
        
    except Exception as e:
        logger.error(f"백그라운드 처리 오류: {str(e)}")
        task_status[task_id]["status"] = "failed"
        task_status[task_id]["error"] = str(e)
        task_status[task_id]["completed_at"] = datetime.now().isoformat()

@app.get("/status/{task_id}", response_model=ProcessStatus)
async def get_status(task_id: str):
    """태스크 상태 확인"""
    if task_id not in task_status:
        raise HTTPException(status_code=404, detail="태스크를 찾을 수 없습니다")
    
    status = task_status[task_id]
    return ProcessStatus(
        status=status["status"],
        processed_at=status.get("completed_at"),
        progress=status.get("progress")
    )

@app.get("/summary/{page_id}", response_model=PageSummary)
async def get_summary(page_id: str):
    """페이지 요약 조회"""
    page = db_manager.get_page(page_id)
    if not page:
        raise HTTPException(status_code=404, detail="페이지를 찾을 수 없습니다")
    
    return PageSummary(
        page_id=page.page_id,
        title=page.title,
        summary=page.summary or "",
        chunk_based_summary=page.chunk_based_summary or "",
        keywords=page.keywords_list,
        url=page.url or ""
    )

@app.get("/mindmap/{parent_page_id}", response_model=MindmapData)
async def get_mindmap(
    parent_page_id: str,
    threshold: float = 0.3,
    max_depth: int = 3
):
    """특정 페이지 마인드맵 데이터 조회"""
    try:
        logger.info(f"특정 페이지 마인드맵 요청: parent_id={parent_page_id}, threshold={threshold}")
        
        mindmap_data = mindmap_service.generate_mindmap_data(
            parent_page_id, threshold, max_depth
        )
        
        logger.info(f"마인드맵 생성 완료: 노드 {len(mindmap_data.nodes)}개, 링크 {len(mindmap_data.links)}개")
        return mindmap_data
    except ValueError as e:
        logger.error(f"페이지 찾기 실패: {parent_page_id} - {str(e)}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"마인드맵 생성 오류 (parent_id={parent_page_id}): {str(e)}")
        raise HTTPException(status_code=500, detail="마인드맵 생성 중 오류 발생")

@app.get("/mindmap-all", response_model=MindmapData)
async def get_all_mindmap(
    threshold: float = 0.3,
    limit: int = 100
):
    """전체 페이지 마인드맵 데이터 조회"""
    try:
        mindmap_data = mindmap_service.generate_all_pages_mindmap(threshold, limit)
        return mindmap_data
    except Exception as e:
        logger.error(f"전체 마인드맵 생성 오류: {str(e)}")
        raise HTTPException(status_code=500, detail="전체 마인드맵 생성 중 오류 발생")

@app.get("/mindmap-keyword", response_model=MindmapData)
async def get_keyword_mindmap(
    keyword: str,
    threshold: float = 0.3,
    limit: int = 100
):
    """키워드 기반 마인드맵 데이터 조회"""
    try:
        mindmap_data = mindmap_service.generate_keyword_mindmap(keyword, threshold, limit)
        return mindmap_data
    except Exception as e:
        logger.error(f"키워드 마인드맵 생성 오류: {str(e)}")
        raise HTTPException(status_code=500, detail="키워드 마인드맵 생성 중 오류 발생")

@app.get("/mindmap-all-keywords", response_model=MindmapData)
async def get_all_keywords_mindmap(
    threshold: float = 0.3,
    limit: int = 200
):
    """전체 키워드 네트워크 마인드맵 데이터 조회"""
    try:
        mindmap_data = mindmap_service.generate_all_keywords_mindmap(threshold, limit)
        return mindmap_data
    except Exception as e:
        logger.error(f"전체 키워드 마인드맵 생성 오류: {str(e)}")
        raise HTTPException(status_code=500, detail="전체 키워드 마인드맵 생성 중 오류 발생")

@app.get("/keywords", response_model=List[str])
async def get_all_keywords():
    """모든 키워드 목록 조회"""
    try:
        keywords = db_manager.get_all_keywords()
        return keywords
    except Exception as e:
        logger.error(f"키워드 목록 조회 오류: {str(e)}")
        raise HTTPException(status_code=500, detail="키워드 목록 조회 중 오류 발생")

@app.get("/mindmap", response_class=HTMLResponse)
async def mindmap_page(request: Request):
    """마인드맵 화면"""
    return templates.TemplateResponse("mindmap.html", {"request": request})

@app.get("/user-mindmap", response_class=HTMLResponse)
async def user_mindmap_page(request: Request):
    """사용자별 마인드맵 페이지"""
    return templates.TemplateResponse("user_mindmap.html", {"request": request})

@app.get("/data", response_class=HTMLResponse)
async def data_page(request: Request):
    """데이터 조회 화면"""
    return templates.TemplateResponse("data.html", {"request": request})

@app.get("/spaces", response_class=HTMLResponse)
async def spaces_page(request: Request):
    """Space 관리 화면"""
    return templates.TemplateResponse("spaces.html", {"request": request})

@app.get("/pages", response_model=PageListResponse)
async def get_pages(page: int = 1, per_page: int = 20):
    """모든 페이지 조회 (페이징)"""
    if per_page > 100:
        per_page = 100  # 최대 100개로 제한
    
    offset = (page - 1) * per_page
    pages = db_manager.get_all_pages(offset=offset, limit=per_page)
    total = db_manager.count_pages()
    
    page_summaries = []
    for p in pages:
        page_summaries.append(PageSummary(
            page_id=p.page_id,
            title=p.title,
            summary=p.summary or "",
            chunk_based_summary=p.chunk_based_summary or "",
            keywords=p.keywords_list,
            url=p.url or ""
        ))
    
    return PageListResponse(
        pages=page_summaries,
        total=total,
        page=page,
        per_page=per_page
    )

@app.post("/pages/search", response_model=PageListResponse)
async def search_pages(search_request: PageSearchRequest):
    """페이지 검색"""
    if search_request.per_page > 100:
        search_request.per_page = 100  # 최대 100개로 제한
    
    offset = (search_request.page - 1) * search_request.per_page
    
    pages = db_manager.search_pages(
        query=search_request.query,
        keywords=search_request.keywords,
        offset=offset,
        limit=search_request.per_page
    )
    
    total = db_manager.count_search_pages(
        query=search_request.query,
        keywords=search_request.keywords
    )
    
    page_summaries = []
    for p in pages:
        page_summaries.append(PageSummary(
            page_id=p.page_id,
            title=p.title,
            summary=p.summary or "",
            chunk_based_summary=p.chunk_based_summary or "",
            keywords=p.keywords_list,
            url=p.url or ""
        ))
    
    return PageListResponse(
        pages=page_summaries,
        total=total,
        page=search_request.page,
        per_page=search_request.per_page
    )

@app.get("/pages/recent", response_model=List[PageSummary])
async def get_recent_pages(limit: int = 10):
    """최근 수정된 페이지 조회"""
    if limit > 50:
        limit = 50  # 최대 50개로 제한
    
    pages = db_manager.get_recent_pages(limit=limit)
    
    page_summaries = []
    for p in pages:
        page_summaries.append(PageSummary(
            page_id=p.page_id,
            title=p.title,
            summary=p.summary or "",
            chunk_based_summary=p.chunk_based_summary or "",
            keywords=p.keywords_list,
            url=p.url or ""
        ))
    
    return page_summaries

@app.get("/pages/stats")
async def get_pages_stats():
    """페이지 통계 정보"""
    total_pages = db_manager.count_pages()
    recent_pages = db_manager.get_recent_pages(limit=5)
    
    # 키워드 통계
    all_keywords = []
    for page in db_manager.get_all_pages(limit=1000):  # 최대 1000개만 분석
        all_keywords.extend(page.keywords_list)
    
    from collections import Counter
    keyword_counts = Counter(all_keywords)
    top_keywords = keyword_counts.most_common(10)
    
    return {
        "total_pages": total_pages,
        "recent_pages": len(recent_pages),
        "top_keywords": [{"keyword": k, "count": c} for k, c in top_keywords],
        "total_unique_keywords": len(keyword_counts)
    }

@app.get("/pages/{page_id}/content")
async def get_page_content(page_id: str):
    """페이지 상세 내용 조회 (BODY 포함)"""
    page = db_manager.get_page(page_id)
    if not page:
        raise HTTPException(status_code=404, detail="페이지를 찾을 수 없습니다.")
    
    return {
        "page_id": page.page_id,
        "title": page.title,
        "content": page.content or "",
        "summary": page.summary or "",
        "chunk_based_summary": page.chunk_based_summary or "",
        "keywords": page.keywords_list,
        "url": page.url or "",
        "modified_date": page.modified_date,
        "created_date": page.created_date
    }

@app.post("/pages/{page_id}/regenerate")
async def regenerate_page_summary(page_id: str, use_chunking: bool = None):
    """페이지 요약 및 키워드 재생성"""
    try:
        page = db_manager.get_page(page_id)
        if not page:
            raise HTTPException(status_code=404, detail="페이지를 찾을 수 없습니다.")
        
        # 콘텐츠가 없으면 재생성 불가
        if not page.content or len(page.content.strip()) < 10:
            raise HTTPException(status_code=400, detail="페이지 콘텐츠가 없어 재생성할 수 없습니다.")
        
        # LLM 서비스 확인
        if not llm_service:
            raise HTTPException(status_code=503, detail="LLM 서비스를 사용할 수 없습니다.")
        
        logger.info(f"페이지 요약/키워드 재생성 시작: {page.title} ({page_id})")
        
        # 콘텐츠 분석
        content_analyzer = ContentAnalyzer()
        analysis_result = content_analyzer.analyze_content(page.content, page.title)
        
        logger.info(f"콘텐츠 분석 완료: {analysis_result.content_type}, 특수키워드: {analysis_result.special_keywords}")
        
        # LLM으로 요약 및 키워드 재생성 (두 가지 요약 모두 생성)
        try:
            # 일반 요약 생성
            logger.info(f"일반 요약 재생성: {page.title}")
            new_summary = llm_service.summarize(page.content)
            raw_keywords = llm_service.extract_keywords(page.content)
            
            # RAG chunking 기반 요약 생성
            new_chunk_based_summary = None
            enable_chunking = use_chunking if use_chunking is not None else config.RAG_ENABLED
            
            if enable_chunking and len(page.content) > config.RAG_CHUNK_SIZE:
                logger.info(f"RAG chunking 기반 요약 재생성: {page.title}")
                try:
                    new_chunk_based_summary = llm_service.chunk_based_summarize(page.content, page.title, use_chunking=True)
                except Exception as e:
                    logger.warning(f"RAG chunking 재생성 실패, 일반 요약 사용: {page.title} - {str(e)}")
                    new_chunk_based_summary = new_summary
            else:
                # 짧은 콘텐츠는 일반 요약을 chunk 기반 요약으로도 사용
                new_chunk_based_summary = new_summary
            
            # 키워드 결과 검증 및 정리
            new_keywords = clean_keywords(raw_keywords)
            
            # 키워드가 비어있거나 너무 적으면 폴백 처리
            if len(new_keywords) < 2:
                logger.warning("LLM 키워드 추출 결과가 부적절함, 폴백 처리")
                fallback_keywords = extract_fallback_keywords(page.content)
                new_keywords.extend(fallback_keywords)
            
            # 내용이 짧거나 키워드가 여전히 부족하면 "내용없음" 추가
            if len(page.content.strip()) < 10 or len(new_keywords) < 2:
                if "내용없음" not in new_keywords:
                    new_keywords.insert(0, "내용없음")
            
            # 특수 키워드를 우선적으로 추가 (중복 제거)
            for special_kw in analysis_result.special_keywords:
                if special_kw not in new_keywords:
                    new_keywords.insert(0, special_kw)  # 앞쪽에 추가
            
            # 최대 10개로 제한
            new_keywords = new_keywords[:10]
            
            logger.info(f"재생성 완료 - 요약: {len(new_summary)}자, 키워드: {len(new_keywords)}개")
            
        except Exception as e:
            logger.warning(f"LLM 처리 실패, 폴백 처리: {str(e)}")
            # 폴백: 간단한 요약
            sentences = page.content.split('.')[:3]
            new_summary = '. '.join(sentences).strip()
            if not new_summary:
                new_summary = page.content[:200] + "..." if len(page.content) > 200 else page.content
            
            new_chunk_based_summary = new_summary  # 폴백 시에도 동일한 요약 사용
            
            # 간단한 키워드 추출
            new_keywords = extract_fallback_keywords(page.content)
            
            # 내용이 짧거나 키워드가 부족하면 "내용없음" 추가
            if len(page.content.strip()) < 10 or len(new_keywords) < 2:
                if "내용없음" not in new_keywords:
                    new_keywords.insert(0, "내용없음")
            
            # 특수 키워드를 우선적으로 추가 (중복 제거)
            for special_kw in analysis_result.special_keywords:
                if special_kw not in new_keywords:
                    new_keywords.insert(0, special_kw)  # 앞쪽에 추가
        
        # 데이터베이스 업데이트
        update_data = {
            'summary': new_summary,
            'chunk_based_summary': new_chunk_based_summary,
            'keywords': page.keywords  # 임시로 기존 값 유지
        }
        
        # 키워드 리스트를 JSON 문자열로 변환
        page.keywords_list = new_keywords
        update_data['keywords'] = page.keywords
        
        success = db_manager.update_page(page_id, update_data)
        
        if not success:
            raise HTTPException(status_code=500, detail="데이터베이스 업데이트 실패")
        
        logger.info(f"페이지 재생성 완료: {page.title}")
        
        return {
            "message": "요약 및 키워드가 재생성되었습니다.",
            "page_id": page_id,
            "summary": new_summary,
            "chunk_based_summary": new_chunk_based_summary,
            "keywords": new_keywords
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"페이지 재생성 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=f"재생성 중 오류 발생: {str(e)}")

@app.post("/pages/{page_id}/chunk-analyze")
async def analyze_page_chunks(page_id: str):
    """페이지 RAG chunking 분석"""
    try:
        page = db_manager.get_page(page_id)
        if not page:
            raise HTTPException(status_code=404, detail="페이지를 찾을 수 없습니다.")
        
        if not page.content or len(page.content.strip()) < 10:
            raise HTTPException(status_code=400, detail="페이지 콘텐츠가 없어 chunking 분석을 할 수 없습니다.")
        
        # HierarchicalChunker 초기화
        from rag_chunking import HierarchicalChunker
        chunker = HierarchicalChunker(
            chunk_size=config.RAG_CHUNK_SIZE,
            max_chunk_size=config.RAG_MAX_CHUNK_SIZE,
            overlap_tokens=config.RAG_OVERLAP_TOKENS
        )
        
        # 콘텐츠를 chunk로 분할
        chunks = chunker.chunk_content(page.content, page.title)
        
        # chunk 정보를 반환용으로 변환
        chunk_info = []
        for i, chunk in enumerate(chunks):
            chunk_info.append({
                "chunk_id": chunk.chunk_id,
                "chunk_index": i,
                "chunk_type": chunk.chunk_type.value,
                "token_count": chunk.token_count,
                "char_count": chunk.char_count,
                "content_preview": chunk.content[:200] + "..." if len(chunk.content) > 200 else chunk.content,
                "quality_score": chunk.metadata.get("quality_score", 0),
                "overlap_start": chunk.overlap_start,
                "overlap_end": chunk.overlap_end
            })
        
        return {
            "page_id": page_id,
            "page_title": page.title,
            "total_chunks": len(chunks),
            "total_tokens": sum(chunk.token_count for chunk in chunks),
            "chunks": chunk_info,
            "chunking_settings": {
                "chunk_size": config.RAG_CHUNK_SIZE,
                "max_chunk_size": config.RAG_MAX_CHUNK_SIZE,
                "overlap_tokens": config.RAG_OVERLAP_TOKENS
            }
        }
        
    except Exception as e:
        logger.error(f"페이지 chunking 분석 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Chunking 분석 중 오류 발생: {str(e)}")

@app.delete("/pages/{page_id}")
async def delete_page(page_id: str):
    """페이지 삭제"""
    success = db_manager.delete_page(page_id)
    if success:
        return {"message": "페이지가 삭제되었습니다.", "page_id": page_id}
    else:
        raise HTTPException(status_code=404, detail="페이지를 찾을 수 없습니다.")

# 사용자별 마인드맵 API 엔드포인트들
@app.get("/api/users")
async def get_all_users():
    """모든 사용자 목록 조회"""
    try:
        persons = db_manager.get_all_persons()
        users = []
        
        for person in persons:
            # 사용자별 통계 계산
            relations = db_manager.get_person_relations(person.person_id)
            created_count = len([r for r in relations if r.relation_type == 'creator'])
            modified_count = len([r for r in relations if r.relation_type == 'modifier'])
            mentioned_count = len([r for r in relations if r.relation_type == 'mentioned'])
            
            user_info = {
                "person_id": person.person_id,
                "name": person.name,
                "email": person.email,
                "department": person.department,
                "role": person.role,
                "created_pages": created_count,
                "modified_pages": modified_count,
                "mentioned_pages": mentioned_count,
                "total_relations": len(relations),
                "mentioned_count": person.mentioned_count
            }
            users.append(user_info)
        
        # 전체 관련도 순으로 정렬
        users.sort(key=lambda x: x['total_relations'], reverse=True)
        return {"users": users}
        
    except Exception as e:
        logger.error(f"사용자 목록 조회 오류: {str(e)}")
        raise HTTPException(status_code=500, detail="사용자 목록 조회 중 오류가 발생했습니다.")

@app.get("/api/users/{user_name}/stats")
async def get_user_stats(user_name: str):
    """특정 사용자의 통계 정보 조회"""
    try:
        person = db_manager.get_person_by_name(user_name)
        if not person:
            raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")
        
        relations = db_manager.get_person_relations(person.person_id)
        created_pages = [r for r in relations if r.relation_type == 'creator']
        modified_pages = [r for r in relations if r.relation_type == 'modifier']
        mentioned_pages = [r for r in relations if r.relation_type == 'mentioned']
        
        return {
            "name": person.name,
            "email": person.email,
            "department": person.department,
            "role": person.role,
            "created_pages": len(created_pages),
            "modified_pages": len(modified_pages),
            "mentioned_pages": len(mentioned_pages),
            "total_relations": len(relations),
            "mentioned_count": person.mentioned_count,
            "relations_detail": {
                "created": [{"page_id": r.page_id, "confidence": r.confidence_score} for r in created_pages],
                "modified": [{"page_id": r.page_id, "confidence": r.confidence_score} for r in modified_pages],
                "mentioned": [{"page_id": r.page_id, "confidence": r.confidence_score, "context": r.mentioned_context} for r in mentioned_pages]
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"사용자 통계 조회 오류: {str(e)}")
        raise HTTPException(status_code=500, detail="사용자 통계 조회 중 오류가 발생했습니다.")

@app.get("/mindmap/user/{user_name}")
async def get_user_mindmap(user_name: str, relation_type: str = "all"):
    """사용자 중심 마인드맵 데이터 생성 - 사용자와 연관된 문서들과 키워드들의 관계"""
    try:
        person = db_manager.get_person_by_name(user_name)
        if not person:
            raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")
        
        # 관계 유형 필터링
        valid_types = ["creator", "modifier", "mentioned", "all"]
        if relation_type not in valid_types:
            raise HTTPException(status_code=400, detail=f"관계 유형은 {valid_types} 중 하나여야 합니다.")
        
        relations = db_manager.get_person_relations(person.person_id)
        
        # 관계 유형별 필터링
        if relation_type != "all":
            relations = [r for r in relations if r.relation_type == relation_type]
        
        if not relations:
            return {
                "center_user": user_name,
                "relation_types": [relation_type] if relation_type != "all" else ["creator", "modifier", "mentioned"],
                "nodes": [],
                "links": []
            }
        
        # 페이지 정보 수집
        page_ids = [r.page_id for r in relations]
        pages = [db_manager.get_page(page_id) for page_id in page_ids]
        pages = [p for p in pages if p]  # None 제거
        
        # 노드 생성: 사용자 중심 노드 + 문서 노드 + 키워드 노드
        nodes = []
        links = []
        
        # 1. 중심 사용자 노드
        user_node = {
            "id": f"user_{person.person_id}",
            "title": user_name,
            "type": "user",
            "department": person.department or "",
            "role": person.role or "",
            "email": person.email or "",
            "size": 40,  # 중심 노드는 크게
            "color": "#2c3e50"
        }
        nodes.append(user_node)
        
        # 2. 사용자와 관련된 모든 키워드 수집 및 빈도 계산
        all_keywords = []
        keyword_contexts = {}  # 키워드별 관련 문맥 저장
        
        for page in pages:
            if page.keywords_list:
                for keyword in page.keywords_list:
                    all_keywords.append(keyword)
                    if keyword not in keyword_contexts:
                        keyword_contexts[keyword] = []
                    
                    # 해당 페이지에서 이 사용자와의 관계 찾기
                    page_relations = [r for r in relations if r.page_id == page.page_id]
                    for rel in page_relations:
                        context_info = {
                            "page_title": page.title,
                            "relation_type": rel.relation_type,
                            "context": rel.mentioned_context
                        }
                        keyword_contexts[keyword].append(context_info)
        
        # 키워드 빈도 계산
        from collections import Counter
        keyword_freq = Counter(all_keywords)
        
        # 3. 문서 노드들 생성
        for page in pages:
            page_relations = [r for r in relations if r.page_id == page.page_id]
            relation_types = [r.relation_type for r in page_relations]
            
            # 주 관계 유형 결정
            primary_relation = "mentioned"
            if "creator" in relation_types:
                primary_relation = "creator"
            elif "modifier" in relation_types:
                primary_relation = "modifier"
            
            # 관계별 색상 결정
            color_map = {
                "creator": "#e74c3c",
                "modifier": "#f39c12", 
                "mentioned": "#3498db"
            }
            
            # 사용자 컨텍스트 생성
            contexts = [r.mentioned_context for r in page_relations if r.mentioned_context]
            user_context = "; ".join(contexts) if contexts else f"{primary_relation}"
            
            page_node = {
                "id": page.page_id,
                "title": page.title,
                "type": "document",
                "relation_to_user": primary_relation,
                "user_context": user_context,
                "keywords": page.keywords_list if page.keywords_list else [],
                "url": page.url or "",
                "summary": page.summary or "",
                "size": 25 + len(page_relations) * 5,  # 관계 수에 따른 크기 조정
                "color": color_map[primary_relation]
            }
            nodes.append(page_node)
            
            # 사용자 -> 문서 링크
            user_to_doc_link = {
                "source": f"user_{person.person_id}",
                "target": page.page_id,
                "type": "user_document",
                "relation_type": primary_relation,
                "weight": len(page_relations),
                "context": user_context
            }
            links.append(user_to_doc_link)
        
        # 4. 주요 키워드 노드들 생성 (빈도 상위 키워드만)
        top_keywords = keyword_freq.most_common(15)  # 상위 15개 키워드만
        
        for keyword, freq in top_keywords:
            if freq >= 2:  # 최소 2번 이상 언급된 키워드만
                keyword_node = {
                    "id": f"keyword_{keyword}",
                    "title": keyword,
                    "type": "keyword",
                    "frequency": freq,
                    "size": 15 + freq * 3,  # 빈도에 따른 크기
                    "color": "#27ae60",
                    "contexts": keyword_contexts[keyword]
                }
                nodes.append(keyword_node)
                
                # 사용자 -> 키워드 링크
                user_to_keyword_link = {
                    "source": f"user_{person.person_id}",
                    "target": f"keyword_{keyword}",
                    "type": "user_keyword",
                    "weight": freq,
                    "frequency": freq
                }
                links.append(user_to_keyword_link)
                
                # 키워드 -> 문서 링크들
                for page in pages:
                    if page.keywords_list and keyword in page.keywords_list:
                        keyword_to_doc_link = {
                            "source": f"keyword_{keyword}",
                            "target": page.page_id,
                            "type": "keyword_document",
                            "weight": 0.5
                        }
                        links.append(keyword_to_doc_link)
        
        # 5. 문서 간 유사도 링크 (키워드 기반)
        for i, page1 in enumerate(pages):
            for j, page2 in enumerate(pages[i+1:], i+1):
                if page1.keywords_list and page2.keywords_list:
                    common_keywords = list(set(page1.keywords_list) & set(page2.keywords_list))
                    if len(common_keywords) >= 2:  # 공통 키워드 2개 이상
                        similarity = len(common_keywords) / len(set(page1.keywords_list + page2.keywords_list))
                        if similarity > 0.15:  # 유사도 임계값
                            doc_to_doc_link = {
                                "source": page1.page_id,
                                "target": page2.page_id,
                                "type": "document_similarity",
                                "weight": similarity,
                                "common_keywords": common_keywords
                            }
                            links.append(doc_to_doc_link)
        
        return {
            "center_user": user_name,
            "user_info": {
                "name": person.name,
                "department": person.department,
                "role": person.role,
                "email": person.email
            },
            "relation_types": [relation_type] if relation_type != "all" else list(set([r.relation_type for r in relations])),
            "nodes": nodes,
            "links": links,
            "keyword_analysis": {
                "total_keywords": len(keyword_freq),
                "unique_keywords": len(keyword_freq.keys()),
                "top_keywords": [{"keyword": k, "frequency": f} for k, f in top_keywords[:10]]
            },
            "stats": {
                "total_pages": len(pages),
                "total_relations": len(relations),
                "relation_breakdown": {
                    "creator": len([r for r in relations if r.relation_type == "creator"]),
                    "modifier": len([r for r in relations if r.relation_type == "modifier"]),
                    "mentioned": len([r for r in relations if r.relation_type == "mentioned"])
                }
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"사용자 마인드맵 생성 오류: {str(e)}")
        raise HTTPException(status_code=500, detail="사용자 마인드맵 생성 중 오류가 발생했습니다.")

@app.get("/health")
async def health_check():
    """헬스 체크"""
    llm_status = "none"
    llm_type = "none"
    
    if llm_service:
        from llm_service import OllamaService, OpenAIService, FallbackService
        if isinstance(llm_service, OllamaService):
            llm_type = "ollama"
            llm_status = "available" if llm_service.available else "unavailable"
        elif isinstance(llm_service, OpenAIService):
            llm_type = "openai"
            llm_status = "available"
        elif isinstance(llm_service, FallbackService):
            llm_type = "fallback"
            llm_status = "available"
        else:
            llm_status = "unknown"
    
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "llm_service": {
            "available": llm_service is not None,
            "type": llm_type,
            "status": llm_status
        },
        "rag_chunking": {
            "enabled": config.RAG_ENABLED,
            "chunk_size": config.RAG_CHUNK_SIZE,
            "max_chunk_size": config.RAG_MAX_CHUNK_SIZE,
            "overlap_tokens": config.RAG_OVERLAP_TOKENS
        },
        "database": "sqlite",
        "version": "1.0.0"
    }

# Space 관련 API 엔드포인트들
@app.get("/api/spaces")
async def get_all_spaces():
    """모든 Space 목록 조회"""
    try:
        spaces = db_manager.get_all_spaces()
        return {"spaces": spaces}
    except Exception as e:
        logger.error(f"Space 목록 조회 오류: {str(e)}")
        raise HTTPException(status_code=500, detail="Space 목록 조회 중 오류가 발생했습니다.")

@app.get("/api/spaces/{space_key}/stats")
async def get_space_stats(space_key: str):
    """특정 Space의 통계 정보 조회"""
    try:
        stats = db_manager.get_space_stats(space_key)
        return stats
    except Exception as e:
        logger.error(f"Space 통계 조회 오류: {str(e)}")
        raise HTTPException(status_code=500, detail="Space 통계 조회 중 오류가 발생했습니다.")

@app.get("/api/spaces/{space_key}/pages")
async def get_space_pages(
    space_key: str,
    page: int = 1,
    per_page: int = 20
):
    """특정 Space의 페이지들 조회"""
    try:
        result = db_manager.get_pages_by_space(space_key, page, per_page)
        return result
    except Exception as e:
        logger.error(f"Space 페이지 조회 오류: {str(e)}")
        raise HTTPException(status_code=500, detail="Space 페이지 조회 중 오류가 발생했습니다.")

@app.get("/mindmap/space/{space_key}")
async def get_space_mindmap(
    space_key: str,
    threshold: float = 0.3,
    limit: int = 100
):
    """Space별 마인드맵 데이터 조회"""
    try:
        mindmap_data = mindmap_service.generate_space_mindmap(space_key, threshold, limit)
        return mindmap_data
    except Exception as e:
        logger.error(f"Space 마인드맵 생성 오류: {str(e)}")
        raise HTTPException(status_code=500, detail="Space 마인드맵 생성 중 오류가 발생했습니다.")


if __name__ == "__main__":
    import uvicorn
    
    # 시작 시 시스템 상태 로깅
    logger.info("=== Confluence Auto-Summarization System 시작 ===")
    logger.info(f"LLM 서비스 상태: {llm_service.__class__.__name__ if llm_service else 'None'}")
    
    if llm_service:
        from llm_service import OllamaService, OpenAIService, FallbackService
        if isinstance(llm_service, FallbackService):
            logger.warning("폴백 서비스 사용 중 - 기본적인 요약/키워드 추출만 가능")
        elif isinstance(llm_service, OllamaService):
            logger.info(f"Ollama 서비스 사용: {config.OLLAMA_URL}, 모델: {config.OLLAMA_MODEL}")
        elif isinstance(llm_service, OpenAIService):
            logger.info(f"OpenAI 서비스 사용: 모델 {config.OPENAI_MODEL}")
    
    logger.info("서버 시작: http://localhost:8003")
    logger.info("===========================================")
    
    uvicorn.run(app, host="0.0.0.0", port=8003, log_level="info")