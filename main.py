from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi import Request
import asyncio
import uuid
import logging
from datetime import datetime
from typing import Dict, Any, List

# 로컬 모듈 imports
from models import (
    ConfluenceConnection, ConnectionTestResult, ProcessRequest, 
    ProcessResponse, ProcessStatus, PageSummary, MindmapData,
    PageListResponse, PageSearchRequest
)
from confluence_api import ConfluenceClient
from llm_service import llm_service
from database import db_manager
from mindmap_service import mindmap_service
from config import config

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# FastAPI 애플리케이션 초기화
app = FastAPI(
    title="Confluence Auto-Summarization System",
    description="Confluence 페이지 자동 요약 및 키워드 추출 시스템",
    version="1.0.0"
)

# 정적 파일 및 템플릿 설정
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# 백그라운드 태스크 상태 관리
task_status: Dict[str, Dict[str, Any]] = {}

@app.get("/", response_class=HTMLResponse)
async def main_page(request: Request):
    """메인 제어 화면"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/test-connection", response_model=ConnectionTestResult)
async def test_connection(connection: ConfluenceConnection):
    """Confluence 연결 테스트"""
    try:
        client = ConfluenceClient(
            connection.url,
            connection.username,
            connection.password
        )
        
        result = client.test_connection()
        
        return ConnectionTestResult(
            status=result["status"],
            message=result["message"],
            user_info=result.get("user_info")
        )
    except Exception as e:
        logger.error(f"연결 테스트 오류: {str(e)}")
        return ConnectionTestResult(
            status="failed",
            message=f"연결 테스트 중 오류 발생: {str(e)}"
        )

@app.post("/process-pages/{parent_page_id}", response_model=ProcessResponse)
async def process_pages(
    parent_page_id: str, 
    request: ProcessRequest,
    background_tasks: BackgroundTasks
):
    """페이지 처리 시작"""
    task_id = str(uuid.uuid4())
    
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
        request.confluence_url,
        request.username,
        request.password
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
                
                # 콘텐츠가 없는 경우 대체 처리
                if not content or len(content.strip()) < 10:
                    logger.warning(f"콘텐츠가 부족합니다 ({title}): {len(content) if content else 0}자")
                    # 페이지 제목을 기본 요약으로 사용
                    summary = f"페이지 제목: {title}"
                    keywords = [title] if title else []
                    
                    # 데이터베이스에 최소한의 정보라도 저장
                    content = summary
                
                # LLM 처리
                elif llm_service:
                    try:
                        logger.info(f"LLM 처리 시작: {title} ({len(content)}자)")
                        
                        # 콘텐츠가 짧으면 간단 처리
                        if len(content.strip()) < 100:
                            summary = content.strip()
                            # 간단한 키워드 추출
                            import re
                            words = re.findall(r'[가-힣a-zA-Z0-9]+', content)
                            keywords = list(set([w for w in words if len(w) > 2]))[:5]
                        else:
                            # LLM으로 처리
                            summary = llm_service.summarize(content)
                            raw_keywords = llm_service.extract_keywords(content)
                            
                            # 키워드 결과 검증 및 정리
                            keywords = []
                            if isinstance(raw_keywords, list):
                                for keyword in raw_keywords:
                                    if isinstance(keyword, str):
                                        cleaned_keyword = keyword.strip()
                                        
                                        # LLM 응답 메시지 필터링
                                        skip_phrases = [
                                            "이 페이지", "내용이", "매우", "짧고", "의미", "없는", "내용이므로",
                                            "키워드를", "추출하기", "어렵습니다", "제공된", "내용만으로는",
                                            "다음과", "같은", "추출할", "수", "있습니다"
                                        ]
                                        
                                        skip_phrases_en = [
                                            "content", "keywords", "extract", "difficult", "short",
                                            "meaningful", "following", "provide", "limited", "based"
                                        ]
                                        
                                        # 유효하지 않은 키워드 필터링
                                        if (len(cleaned_keyword) > 20 or 
                                            any(phrase in cleaned_keyword for phrase in skip_phrases) or
                                            any(phrase in cleaned_keyword.lower() for phrase in skip_phrases_en) or
                                            "." in cleaned_keyword):
                                            continue
                                            
                                        if len(cleaned_keyword) >= 2:
                                            keywords.append(cleaned_keyword)
                            
                            # 키워드가 부족하면 폴백 처리
                            if len(keywords) < 2:
                                import re
                                words = re.findall(r'[가-힣a-zA-Z0-9]+', content)
                                fallback_keywords = list(set([w for w in words if len(w) > 2 and len(w) < 15]))[:8]
                                keywords.extend(fallback_keywords)
                            
                            keywords = keywords[:10]  # 최대 10개로 제한
                        
                        logger.info(f"LLM 처리 완료: {title}, 요약 길이: {len(summary)}, 키워드 수: {len(keywords)}")
                        
                    except Exception as e:
                        logger.warning(f"LLM 처리 실패 ({title}): {str(e)}")
                        # 폴백: 간단한 요약
                        sentences = content.split('.')[:3]
                        summary = '. '.join(sentences).strip()
                        if not summary:
                            summary = content[:200] + "..." if len(content) > 200 else content
                        
                        # 간단한 키워드 추출
                        import re
                        words = re.findall(r'[가-힣a-zA-Z0-9]+', content)
                        keywords = list(set([w for w in words if len(w) > 2 and len(w) < 15]))[:10]
                
                else:
                    logger.warning(f"LLM 서비스가 없습니다. 기본 처리: {title}")
                    # LLM 없이 기본 처리
                    sentences = content.split('.')[:3]
                    summary = '. '.join(sentences).strip()
                    if not summary:
                        summary = content[:300] + "..." if len(content) > 300 else content
                    
                    # 기본 키워드 추출
                    import re
                    words = re.findall(r'[가-힣a-zA-Z0-9]+', content)
                    keywords = list(set([w for w in words if len(w) > 2 and len(w) < 15]))[:10]
                
                # 페이지 URL 생성
                space_key = page_data.get('space', {}).get('key', '')
                page_url = client.get_page_url(page_id, space_key)
                
                # 데이터베이스에 저장 (전체 BODY 내용 포함)
                page_db_data = {
                    'page_id': page_id,
                    'title': title,
                    'content': content,  # 전체 BODY 내용 저장
                    'summary': summary,
                    'url': page_url,
                    'modified_date': current_modified,
                    'created_date': page_data.get('history', {}).get('createdDate', '')
                }
                
                logger.info(f"DB 저장 예정 콘텐츠 길이: {len(content) if content else 0}자")
                
                if db_manager.page_exists(page_id):
                    db_manager.update_page(page_id, page_db_data)
                else:
                    # 키워드 리스트를 JSON 문자열로 변환
                    page_obj = db_manager.create_page(page_db_data)
                    page_obj.keywords_list = keywords
                    db_manager.update_page(page_id, {'keywords': page_obj.keywords})
                
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

@app.get("/data", response_class=HTMLResponse)
async def data_page(request: Request):
    """데이터 조회 화면"""
    return templates.TemplateResponse("data.html", {"request": request})

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
        "keywords": page.keywords_list,
        "url": page.url or "",
        "modified_date": page.modified_date,
        "created_date": page.created_date
    }

@app.post("/pages/{page_id}/regenerate")
async def regenerate_page_summary(page_id: str):
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
        
        # LLM으로 요약 및 키워드 재생성
        try:
            new_summary = llm_service.summarize(page.content)
            raw_keywords = llm_service.extract_keywords(page.content)
            
            # 키워드 결과 검증 및 정리
            new_keywords = []
            if isinstance(raw_keywords, list):
                for keyword in raw_keywords:
                    if isinstance(keyword, str):
                        # 키워드 정리: 불필요한 문구 제거
                        cleaned_keyword = keyword.strip()
                        
                        # LLM 응답 메시지인지 확인 (한국어)
                        skip_phrases = [
                            "이 페이지", "내용이", "매우", "짧고", "의미", "없는", "내용이므로",
                            "키워드를", "추출하기", "어렵습니다", "제공된", "내용만으로는",
                            "다음과", "같은", "추출할", "수", "있습니다", "어려운", "상황"
                        ]
                        
                        # 영어 응답 메시지 확인
                        skip_phrases_en = [
                            "content", "keywords", "extract", "difficult", "short",
                            "meaningful", "following", "provide", "limited", "based"
                        ]
                        
                        # 너무 긴 키워드나 의미없는 응답 필터링
                        if (len(cleaned_keyword) > 20 or 
                            any(phrase in cleaned_keyword for phrase in skip_phrases) or
                            any(phrase in cleaned_keyword.lower() for phrase in skip_phrases_en) or
                            "." in cleaned_keyword):
                            continue
                            
                        # 유효한 키워드만 추가
                        if len(cleaned_keyword) >= 2:
                            new_keywords.append(cleaned_keyword)
            
            # 키워드가 비어있거나 너무 적으면 폴백 처리
            if len(new_keywords) < 2:
                logger.warning("LLM 키워드 추출 결과가 부적절함, 폴백 처리")
                import re
                words = re.findall(r'[가-힣a-zA-Z0-9]+', page.content)
                fallback_keywords = list(set([w for w in words if len(w) > 2 and len(w) < 15]))[:8]
                new_keywords.extend(fallback_keywords)
            
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
            
            # 간단한 키워드 추출
            import re
            words = re.findall(r'[가-힣a-zA-Z0-9]+', page.content)
            new_keywords = list(set([w for w in words if len(w) > 2 and len(w) < 15]))[:10]
        
        # 데이터베이스 업데이트
        update_data = {
            'summary': new_summary,
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
            "keywords": new_keywords
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"페이지 재생성 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=f"재생성 중 오류 발생: {str(e)}")

@app.delete("/pages/{page_id}")
async def delete_page(page_id: str):
    """페이지 삭제"""
    success = db_manager.delete_page(page_id)
    if success:
        return {"message": "페이지가 삭제되었습니다.", "page_id": page_id}
    else:
        raise HTTPException(status_code=404, detail="페이지를 찾을 수 없습니다.")

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
        "database": "sqlite",
        "version": "1.0.0"
    }

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
    
    logger.info("서버 시작: http://localhost:8001")
    logger.info("===========================================")
    
    uvicorn.run(app, host="0.0.0.0", port=8001, log_level="info")