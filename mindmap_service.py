from typing import List, Dict, Tuple
from models import MindmapData, MindmapNode, MindmapLink, Page
from database import optimized_db_manager as db_manager
from llm_service import calculate_keyword_similarity, get_common_keywords
from config import config
import logging

logger = logging.getLogger(__name__)

class MindmapService:
    def __init__(self):
        self.threshold = config.MINDMAP_THRESHOLD
        self.max_depth = config.MINDMAP_MAX_DEPTH
    
    def generate_mindmap_data(self, parent_page_id: str, threshold: float = None, max_depth: int = None) -> MindmapData:
        """마인드맵 데이터 생성"""
        threshold = threshold or self.threshold
        max_depth = max_depth or self.max_depth
        
        logger.info(f"마인드맵 생성 시작: parent_id={parent_page_id}, threshold={threshold}")
        
        # 부모 페이지 조회
        parent_page = db_manager.get_page(parent_page_id)
        if not parent_page:
            raise ValueError(f"부모 페이지를 찾을 수 없습니다: {parent_page_id}")
        
        logger.info(f"부모 페이지 찾음: {parent_page.title} (키워드: {len(parent_page.keywords_list)}개)")
        
        # 모든 관련 페이지 조회
        related_pages = db_manager.get_pages_by_parent(parent_page_id)
        logger.info(f"관련 페이지 조회 완료: {len(related_pages)}개")
        
        # 부모 페이지도 포함
        all_pages = related_pages.copy()
        if parent_page not in all_pages:
            all_pages.append(parent_page)
            
        logger.info(f"최종 페이지 수: {len(all_pages)}개 (부모 페이지 포함)")
        
        # 노드 생성
        nodes = self._create_nodes(all_pages)
        
        # 링크 생성
        links = self._create_links(all_pages, threshold)
        
        # 중심성 계산 및 노드 크기 조정
        self._calculate_centrality(nodes, links)
        
        return MindmapData(
            nodes=nodes,
            links=links,
            center_node=parent_page_id
        )
    
    def _create_nodes(self, pages: List[Page]) -> List[MindmapNode]:
        """페이지를 노드로 변환"""
        nodes = []
        
        for page in pages:
            node = MindmapNode(
                id=page.page_id,
                title=page.title,
                keywords=page.keywords_list,
                url=page.url or "",
                summary=page.summary or "",
                size=10  # 기본 크기, 나중에 중심성으로 조정
            )
            nodes.append(node)
        
        return nodes
    
    def _create_links(self, pages: List[Page], threshold: float) -> List[MindmapLink]:
        """페이지 간 링크 생성"""
        links = []
        
        for i, page1 in enumerate(pages):
            for j, page2 in enumerate(pages):
                if i >= j:  # 중복 방지
                    continue
                
                # 키워드 유사도 계산
                similarity = calculate_keyword_similarity(
                    page1.keywords_list, 
                    page2.keywords_list
                )
                
                # 임계값 이상인 경우 링크 생성
                if similarity >= threshold:
                    common_keywords = get_common_keywords(
                        page1.keywords_list, 
                        page2.keywords_list
                    )
                    
                    link = MindmapLink(
                        source=page1.page_id,
                        target=page2.page_id,
                        weight=similarity,
                        common_keywords=common_keywords
                    )
                    links.append(link)
                    
                    # 데이터베이스에 관계 저장
                    try:
                        db_manager.create_relationship(
                            page1.page_id,
                            page2.page_id,
                            similarity,
                            common_keywords
                        )
                    except Exception as e:
                        logger.warning(f"관계 저장 실패: {str(e)}")
        
        return links
    
    def _calculate_centrality(self, nodes: List[MindmapNode], links: List[MindmapLink]):
        """노드 중심성 계산 (간단한 degree centrality)"""
        if not links:
            return
        
        # 각 노드의 연결 수 계산
        node_degrees = {}
        for node in nodes:
            node_degrees[node.id] = 0
        
        for link in links:
            if link.source in node_degrees:
                node_degrees[link.source] += 1
            if link.target in node_degrees:
                node_degrees[link.target] += 1
        
        # 최대 연결 수 찾기
        max_degree = max(node_degrees.values()) if node_degrees else 1
        
        # 노드 크기 조정 (10~50 범위)
        for node in nodes:
            degree = node_degrees.get(node.id, 0)
            normalized_degree = degree / max_degree if max_degree > 0 else 0
            node.size = int(10 + normalized_degree * 40)
    
    def get_page_connections(self, page_id: str) -> List[Dict]:
        """특정 페이지의 연결 정보 조회"""
        relationships = db_manager.get_relationships(page_id)
        connections = []
        
        for rel in relationships:
            connected_page_id = rel.target_page_id if rel.source_page_id == page_id else rel.source_page_id
            connected_page = db_manager.get_page(connected_page_id)
            
            if connected_page:
                connections.append({
                    'page_id': connected_page.page_id,
                    'title': connected_page.title,
                    'weight': rel.weight,
                    'common_keywords': rel.common_keywords_list
                })
        
        return connections
    
    def update_relationships(self, pages: List[Page]):
        """페이지 관계 업데이트"""
        logger.info(f"관계 업데이트 시작: {len(pages)} 페이지")
        
        # 기존 관계 삭제 (선택적)
        # 여기서는 중복 생성을 방지하기 위해 체크
        
        for i, page1 in enumerate(pages):
            for j, page2 in enumerate(pages):
                if i >= j:
                    continue
                
                similarity = calculate_keyword_similarity(
                    page1.keywords_list, 
                    page2.keywords_list
                )
                
                if similarity >= self.threshold:
                    common_keywords = get_common_keywords(
                        page1.keywords_list, 
                        page2.keywords_list
                    )
                    
                    try:
                        db_manager.create_relationship(
                            page1.page_id,
                            page2.page_id,
                            similarity,
                            common_keywords
                        )
                    except Exception as e:
                        logger.warning(f"관계 생성 실패: {str(e)}")
        
        logger.info("관계 업데이트 완료")
    
    def generate_all_pages_mindmap(self, threshold: float = None, limit: int = 100) -> MindmapData:
        """모든 페이지의 마인드맵 데이터 생성"""
        threshold = threshold or self.threshold
        
        # 모든 페이지 조회 (제한)
        all_pages = db_manager.get_all_pages(limit=limit)
        
        if not all_pages:
            # 빈 마인드맵 반환
            return MindmapData(
                nodes=[],
                links=[],
                center_node=""
            )
        
        # 가장 많은 키워드를 가진 페이지를 중심 노드로 설정
        center_page = max(all_pages, key=lambda p: len(p.keywords_list))
        
        # 노드 생성
        nodes = self._create_nodes(all_pages)
        
        # 링크 생성
        links = self._create_links(all_pages, threshold)
        
        # 중심성 계산 및 노드 크기 조정
        self._calculate_centrality(nodes, links)
        
        logger.info(f"전체 마인드맵 생성 완료: {len(nodes)}개 노드, {len(links)}개 링크")
        
        return MindmapData(
            nodes=nodes,
            links=links,
            center_node=center_page.page_id
        )
    
    def generate_keyword_mindmap(self, keyword: str, threshold: float = None, limit: int = 100) -> MindmapData:
        """특정 키워드 기반 마인드맵 데이터 생성 (키워드 노드 기반)"""
        threshold = threshold or self.threshold
        
        # 키워드를 포함한 페이지 조회
        keyword_pages = db_manager.get_pages_by_keyword(keyword, limit=limit)
        
        if not keyword_pages:
            # 빈 마인드맵 반환
            return MindmapData(
                nodes=[],
                links=[],
                center_node=""
            )
        
        # 모든 키워드 수집 및 빈도 계산
        keyword_count = {}
        keyword_pages_map = {}  # 키워드별 페이지 리스트
        
        for page in keyword_pages:
            for kw in page.keywords_list:
                kw_lower = kw.lower()
                keyword_count[kw_lower] = keyword_count.get(kw_lower, 0) + 1
                
                if kw_lower not in keyword_pages_map:
                    keyword_pages_map[kw_lower] = []
                keyword_pages_map[kw_lower].append(page)
        
        # 빈도가 높은 키워드들을 노드로 생성 (최소 2번 이상 등장)
        frequent_keywords = [(kw, count) for kw, count in keyword_count.items() if count >= 2]
        frequent_keywords.sort(key=lambda x: x[1], reverse=True)
        
        # 최대 20개 키워드로 제한
        frequent_keywords = frequent_keywords[:20]
        
        if not frequent_keywords:
            # 빈도가 낮으면 모든 키워드 사용
            frequent_keywords = [(kw, count) for kw, count in keyword_count.items()][:20]
        
        # 키워드 노드 생성
        nodes = []
        for kw, count in frequent_keywords:
            # 원래 대소문자 혼합 키워드 찾기
            original_keyword = kw
            for page in keyword_pages:
                for original_kw in page.keywords_list:
                    if original_kw.lower() == kw:
                        original_keyword = original_kw
                        break
                if original_keyword != kw:
                    break
            
            # 키워드가 포함된 페이지들의 URL (첫 번째 페이지)
            related_pages = keyword_pages_map[kw]
            sample_page = related_pages[0] if related_pages else None
            
            # 노드 크기는 키워드 빈도에 비례
            size = min(20 + (count * 5), 50)
            
            # 중심 키워드인지 확인
            is_center = kw == keyword.lower()
            if is_center:
                size += 10  # 중심 키워드 크기 증가
            
            # 해당 키워드를 포함하는 페이지들의 정보를 summary에 JSON으로 저장
            page_info_list = []
            for page in related_pages:
                page_info_list.append({
                    'page_id': page.page_id,
                    'title': page.title,
                    'summary': page.summary or "",
                    'url': page.url or "",
                    'keywords': page.keywords_list
                })
            
            import json
            pages_json = json.dumps(page_info_list, ensure_ascii=False)
            
            node = MindmapNode(
                id=f"keyword_{kw}",  # 키워드 ID
                title=original_keyword,  # 키워드를 제목으로 사용
                keywords=[original_keyword],
                url=sample_page.url if sample_page else "",
                summary=pages_json,  # 페이지 정보를 JSON으로 저장
                size=size
            )
            nodes.append(node)
        
        # 키워드 간 링크 생성 (공통 페이지를 가진 키워드들)
        links = []
        keyword_list = [kw for kw, _ in frequent_keywords]
        
        for i, kw1 in enumerate(keyword_list):
            for j, kw2 in enumerate(keyword_list):
                if i >= j:
                    continue
                
                # 두 키워드를 공통으로 가진 페이지 찾기
                pages1 = set(p.page_id for p in keyword_pages_map[kw1])
                pages2 = set(p.page_id for p in keyword_pages_map[kw2])
                common_pages = pages1 & pages2
                
                if len(common_pages) > 0:
                    # 공통 페이지 수에 기반한 가중치
                    weight = len(common_pages) / max(len(pages1), len(pages2))
                    
                    if weight >= threshold:
                        link = MindmapLink(
                            source=f"keyword_{kw1}",
                            target=f"keyword_{kw2}",
                            weight=weight,
                            common_keywords=list(common_pages)
                        )
                        links.append(link)
        
        # 중심 노드 설정
        center_keyword = keyword.lower()
        center_node_id = f"keyword_{center_keyword}"
        
        logger.info(f"키워드 '{keyword}' 마인드맵 생성 완료: {len(nodes)}개 키워드 노드, {len(links)}개 링크")
        
        return MindmapData(
            nodes=nodes,
            links=links,
            center_node=center_node_id
        )
    
    def generate_all_keywords_mindmap(self, threshold: float = None, limit: int = 200) -> MindmapData:
        """전체 키워드 네트워크 마인드맵 생성"""
        threshold = threshold or self.threshold
        
        # 모든 페이지 조회
        all_pages = db_manager.get_all_pages(limit=limit)
        
        if not all_pages:
            return MindmapData(nodes=[], links=[], center_node="")
        
        # 모든 키워드 수집 및 빈도 계산
        keyword_count = {}
        keyword_pages_map = {}
        keyword_cooccurrence = {}  # 키워드 동시 출현 빈도
        
        for page in all_pages:
            page_keywords = [kw.lower() for kw in page.keywords_list]
            
            # 키워드 빈도 계산
            for kw in page_keywords:
                keyword_count[kw] = keyword_count.get(kw, 0) + 1
                if kw not in keyword_pages_map:
                    keyword_pages_map[kw] = []
                keyword_pages_map[kw].append(page)
            
            # 키워드 간 동시 출현 관계 계산
            for i, kw1 in enumerate(page_keywords):
                for kw2 in page_keywords[i+1:]:
                    if kw1 != kw2:
                        pair = tuple(sorted([kw1, kw2]))
                        keyword_cooccurrence[pair] = keyword_cooccurrence.get(pair, 0) + 1
        
        # 빈도가 높은 키워드들만 선택 (최소 2번 이상 등장)
        frequent_keywords = [(kw, count) for kw, count in keyword_count.items() if count >= 2]
        frequent_keywords.sort(key=lambda x: x[1], reverse=True)
        
        # 상위 50개 키워드만 선택
        top_keywords = frequent_keywords[:50]
        selected_keywords = {kw for kw, _ in top_keywords}
        
        # 노드 생성 (키워드별)
        nodes = []
        max_count = max([count for _, count in top_keywords]) if top_keywords else 1
        
        for keyword, count in top_keywords:
            # 키워드 빈도에 따라 노드 크기 결정
            size = int((count / max_count) * 50) + 10
            
            # 키워드를 포함하는 페이지들의 정보를 JSON으로 저장
            page_info_list = []
            for page in keyword_pages_map[keyword]:
                page_info_list.append({
                    'page_id': page.page_id,
                    'title': page.title,
                    'summary': page.summary or "",
                    'url': page.url or "",
                    'keywords': page.keywords_list,
                    'modified_date': page.modified_date,
                    'created_date': page.created_date
                })
            
            import json
            pages_json = json.dumps(page_info_list, ensure_ascii=False)
            
            node = MindmapNode(
                id=f"keyword_{keyword}",
                title=keyword,
                keywords=[keyword],
                url="",  # 키워드 노드는 URL 없음
                summary=pages_json,  # JSON 형태로 페이지 정보 저장
                size=size
            )
            nodes.append(node)
        
        # 링크 생성 (키워드 간 동시 출현 관계)
        links = []
        for (kw1, kw2), cooccur_count in keyword_cooccurrence.items():
            if (kw1 in selected_keywords and kw2 in selected_keywords and 
                cooccur_count >= 2):  # 최소 2번 이상 함께 등장
                
                # 동시 출현 빈도에 따라 링크 가중치 결정
                weight = min(cooccur_count / 10.0, 1.0)  # 0.1 ~ 1.0 범위
                
                link = MindmapLink(
                    source=f"keyword_{kw1}",
                    target=f"keyword_{kw2}",
                    weight=weight,
                    common_keywords=[kw1, kw2]
                )
                links.append(link)
        
        # 가장 빈도가 높은 키워드를 중심 노드로 선택
        center_node = f"keyword_{top_keywords[0][0]}" if top_keywords else ""
        
        logger.info(f"전체 키워드 마인드맵 생성 완료: 노드 {len(nodes)}개, 링크 {len(links)}개")
        
        return MindmapData(
            nodes=nodes,
            links=links,
            center_node=center_node
        )

# 싱글톤 인스턴스
mindmap_service = MindmapService()