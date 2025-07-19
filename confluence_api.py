import requests
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)

class ConfluenceClient:
    def __init__(self, base_url: str, username: str, password: str):
        self.base_url = base_url.rstrip('/')
        self.username = username
        self.password = password
        self.session = requests.Session()
        self.session.auth = (username, password)
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
    
    def test_connection(self) -> Dict[str, any]:
        """Confluence 서버 연결 테스트"""
        try:
            # 현재 사용자 정보 조회로 연결 테스트
            response = self.session.get(f"{self.base_url}/rest/api/user/current")
            
            if response.status_code == 200:
                user_info = response.json()
                return {
                    "status": "success",
                    "message": f"연결 성공: {user_info.get('displayName', 'Unknown User')}",
                    "user_info": user_info
                }
            elif response.status_code == 401:
                return {
                    "status": "failed",
                    "message": "인증 실패: 사용자 ID 또는 비밀번호를 확인해주세요."
                }
            else:
                return {
                    "status": "failed",
                    "message": f"연결 실패: HTTP {response.status_code}"
                }
        except requests.exceptions.ConnectionError:
            return {
                "status": "failed",
                "message": "서버 연결 실패: URL을 확인해주세요."
            }
        except Exception as e:
            return {
                "status": "failed",
                "message": f"연결 오류: {str(e)}"
            }
    
    def get_page_content(self, page_id: str) -> Optional[Dict]:
        """페이지 상세 정보 조회 (전체 BODY 내용 포함)"""
        try:
            url = f"{self.base_url}/rest/api/content/{page_id}"
            params = {
                'expand': 'body.storage,body.view,body.export_view,version,history,space,metadata,children.page'
            }
            
            response = self.session.get(url, params=params)
            
            if response.status_code == 200:
                page_data = response.json()
                logger.debug(f"페이지 데이터 키: {list(page_data.keys())}")
                if 'body' in page_data:
                    logger.debug(f"Body 키: {list(page_data['body'].keys())}")
                return page_data
            else:
                logger.error(f"페이지 조회 실패: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            logger.error(f"페이지 조회 오류: {str(e)}")
            return None
    
    def get_page_children(self, page_id: str, limit: int = 50) -> List[Dict]:
        """페이지 하위 페이지 목록 조회 (전체 BODY 내용 포함)"""
        try:
            url = f"{self.base_url}/rest/api/content/{page_id}/child/page"
            params = {
                'limit': limit,
                'expand': 'body.storage,body.view,body.export_view,version,history,space'
            }
            
            response = self.session.get(url, params=params)
            
            if response.status_code == 200:
                results = response.json().get('results', [])
                logger.info(f"하위 페이지 조회 성공: {len(results)}개")
                return results
            else:
                logger.error(f"하위 페이지 조회 실패: {response.status_code}")
                return []
        except Exception as e:
            logger.error(f"하위 페이지 조회 오류: {str(e)}")
            return []
    
    def get_all_descendants(self, page_id: str) -> List[Dict]:
        """페이지의 모든 하위 페이지를 재귀적으로 조회"""
        all_pages = []
        
        def get_descendants_recursive(pid: str):
            children = self.get_page_children(pid)
            for child in children:
                all_pages.append(child)
                # 재귀적으로 하위 페이지 조회
                get_descendants_recursive(child['id'])
        
        get_descendants_recursive(page_id)
        return all_pages
    
    def get_page_history(self, page_id: str) -> Optional[Dict]:
        """페이지 수정 이력 조회"""
        try:
            url = f"{self.base_url}/rest/api/content/{page_id}/history"
            response = self.session.get(url)
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"페이지 히스토리 조회 실패: {response.status_code}")
                return None
        except Exception as e:
            logger.error(f"페이지 히스토리 조회 오류: {str(e)}")
            return None
    
    def extract_text_from_content(self, content_body: Dict) -> str:
        """Confluence 페이지 본문에서 전체 텍스트 추출 (모든 BODY 내용 포함)"""
        try:
            import re
            
            text_content = ""
            extracted_formats = []
            
            # 1. storage 형식에서 추출 (우선순위: 가장 완전한 형식)
            if content_body and 'storage' in content_body and content_body['storage'].get('value'):
                html_content = content_body['storage']['value']
                logger.debug(f"Storage HTML 콘텐츠 길이: {len(html_content)}")
                
                # HTML 태그 제거하되 내용은 보존
                # 먼저 일부 태그를 공백으로 변환하여 구조 유지
                html_content = re.sub(r'</(p|div|h[1-6]|li|td|th|section|article)>', ' ', html_content)
                html_content = re.sub(r'<(br|hr)\s*/?>', ' ', html_content)
                
                # 모든 HTML 태그 제거
                text_content = re.sub(r'<[^>]+>', '', html_content)
                
                # HTML 엔티티 디코딩
                text_content = text_content.replace('&nbsp;', ' ')
                text_content = text_content.replace('&amp;', '&')
                text_content = text_content.replace('&lt;', '<')
                text_content = text_content.replace('&gt;', '>')
                text_content = text_content.replace('&quot;', '"')
                text_content = text_content.replace('&#39;', "'")
                text_content = text_content.replace('&apos;', "'")
                
                # 연속된 공백, 탭, 개행 문자 정리
                text_content = re.sub(r'[\s\t\n\r]+', ' ', text_content)
                text_content = text_content.strip()
                extracted_formats.append("storage")
            
            # 2. export_view 형식에서 추가 추출 (렌더링된 내용)
            if content_body and 'export_view' in content_body and content_body['export_view'].get('value'):
                export_html = content_body['export_view']['value']
                logger.debug(f"Export view HTML 콘텐츠 길이: {len(export_html)}")
                
                export_text = re.sub(r'<[^>]+>', '', export_html)
                export_text = re.sub(r'\s+', ' ', export_text).strip()
                
                # storage 내용과 병합 (중복 제거)
                if export_text and export_text not in text_content:
                    if text_content:
                        text_content = text_content + " " + export_text
                    else:
                        text_content = export_text
                extracted_formats.append("export_view")
            
            # 3. view 형식에서 추가 추출 (폴백)
            if content_body and 'view' in content_body and content_body['view'].get('value'):
                view_html = content_body['view']['value']
                logger.debug(f"View HTML 콘텐츠 길이: {len(view_html)}")
                
                view_text = re.sub(r'<[^>]+>', '', view_html)
                view_text = re.sub(r'\s+', ' ', view_text).strip()
                
                # 기존 내용과 병합 (중복 제거)
                if view_text and view_text not in text_content:
                    if text_content:
                        text_content = text_content + " " + view_text
                    else:
                        text_content = view_text
                extracted_formats.append("view")
            
            # 최종 텍스트 정리
            if text_content:
                # 중복된 공백 제거
                text_content = re.sub(r'\s+', ' ', text_content).strip()
                
                logger.info(f"텍스트 추출 완료: {len(text_content)}자 (형식: {', '.join(extracted_formats)})")
                return text_content
            else:
                logger.warning("추출된 텍스트가 없습니다.")
                return ""
            
        except Exception as e:
            logger.error(f"텍스트 추출 오류: {str(e)}")
            return ""
    
    def get_page_url(self, page_id: str, space_key: str = None) -> str:
        """페이지 URL 생성"""
        if space_key:
            return f"{self.base_url}/spaces/{space_key}/pages/{page_id}"
        else:
            return f"{self.base_url}/pages/viewpage.action?pageId={page_id}"