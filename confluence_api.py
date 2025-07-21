"""
=============================================================================
파일명: confluence_api.py
목적: Confluence 서버와 통신하여 페이지 데이터를 가져오는 API 클라이언트

주요 역할:
1. Confluence 서버 연결 및 인증 관리
2. 페이지 내용 조회 (HTML 포맷)
3. 페이지 하위 목록 조회
4. 첨부파일 목록 조회 및 다운로드
5. HTML에서 텍스트 추출

사용 예시:
- client = ConfluenceClient('http://localhost:8090', 'username', 'password')
- page_data = client.get_page_content('페이지ID')
- attachment = client.download_attachment('페이지ID', '파일명.png')

주의사항:
- HTTP Basic 인증 사용 (사용자명/비밀번호)
- REST API v2 사용
- 첨부파일 다운로드는 10MB 제한
=============================================================================
"""

# =============================================================================
# 필요한 라이브러리들을 가져오기
# =============================================================================

import requests  # HTTP 요청을 보내기 위한 라이브러리
from typing import List, Dict, Optional  # 타입 힌트 (코드의 가독성 향상)
import logging  # 로깅 기능 (프로그램 실행 과정 기록)

# 이 파일 전용 로거 생성
logger = logging.getLogger(__name__)

# =============================================================================
# Confluence API 클라이언트 메인 클래스
# =============================================================================

class ConfluenceClient:
    """
    Confluence 서버와 통신하는 클라이언트 클래스
    
    이 클래스는 Confluence REST API를 사용하여 페이지 데이터를 조회하고
    첨부파일을 다운로드하는 기능을 제공합니다.
    """
    
    def __init__(self, base_url: str, username: str, password: str):
        """
        ConfluenceClient를 초기화합니다.
        
        매개변수:
            base_url (str): Confluence 서버의 기본 URL (예: 'http://localhost:8090')
            username (str): 로그인할 사용자명
            password (str): 사용자 비밀번호
        """
        # URL 끝의 슬래시(/) 제거 (URL 정규화)
        self.base_url = base_url.rstrip('/')
        
        # 로그인 정보 저장
        self.username = username
        self.password = password
        
        # HTTP 세션 생성 (연결 재사용으로 성능 향상)
        self.session = requests.Session()
        
        # 세션에 인증 정보 설정 (HTTP Basic Auth)
        self.session.auth = (username, password)
        
        # 모든 요청에 공통으로 사용할 HTTP 헤더 설정
        self.session.headers.update({
            'Content-Type': 'application/json',  # 요청 데이터 형식
            'Accept': 'application/json'         # 응답 데이터 형식
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
                'expand': 'body.storage,body.view,body.export_view,version,history.createdBy,history.lastUpdated,space,metadata,children.page'
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
                'expand': 'body.storage,body.view,body.export_view,version,history.createdBy,history.lastUpdated,space'
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
    
    def get_page_attachments(self, page_id: str) -> List[Dict]:
        """페이지의 첨부파일 목록 조회"""
        try:
            url = f"{self.base_url}/rest/api/content/{page_id}/child/attachment"
            response = self.session.get(url)
            
            if response.status_code == 200:
                result = response.json()
                return result.get('results', [])
            else:
                logger.error(f"첨부파일 목록 조회 실패: {response.status_code}")
                return []
        except Exception as e:
            logger.error(f"첨부파일 목록 조회 오류: {str(e)}")
            return []
    
    def download_attachment(self, page_id: str, filename: str) -> Optional[bytes]:
        """페이지의 첨부파일 다운로드"""
        try:
            # URL 인코딩을 위한 파일명 처리
            import urllib.parse
            encoded_filename = urllib.parse.quote(filename)
            
            # Confluence 표준 다운로드 URL 사용 
            download_url = f"{self.base_url}/download/attachments/{page_id}/{encoded_filename}"
            
            # 다운로드를 위한 별도 세션 (Content-Type 헤더 제거)
            download_session = requests.Session()
            download_session.auth = (self.username, self.password)
            
            logger.debug(f"첨부파일 다운로드 시도: {download_url}")
            
            response = download_session.get(download_url, stream=True, timeout=30)
            
            if response.status_code == 200:
                # 파일 크기 제한 (10MB)
                max_size = 10 * 1024 * 1024
                content = b""
                
                for chunk in response.iter_content(chunk_size=8192):
                    content += chunk
                    if len(content) > max_size:
                        logger.warning(f"첨부파일 크기가 너무 큼: {filename}")
                        return None
                
                logger.info(f"첨부파일 다운로드 완료: {filename} ({len(content)} bytes)")
                return content
                
            else:
                logger.error(f"첨부파일 다운로드 실패: {response.status_code} - {response.text[:200]}")
                return None
                
        except Exception as e:
            logger.error(f"첨부파일 다운로드 오류: {str(e)}")
            return None
    
    def get_attachment_info(self, page_id: str, filename: str) -> Optional[Dict]:
        """첨부파일 정보 조회"""
        try:
            attachments = self.get_page_attachments(page_id)
            
            for attachment in attachments:
                if attachment.get('title') == filename:
                    return {
                        'id': attachment.get('id'),
                        'title': attachment.get('title'),
                        'mediaType': attachment.get('extensions', {}).get('mediaType'),
                        'fileSize': attachment.get('extensions', {}).get('fileSize'),
                        'download_url': f"{self.base_url}/rest/api/content/{attachment.get('id')}/download"
                    }
            
            return None
            
        except Exception as e:
            logger.error(f"첨부파일 정보 조회 오류: {str(e)}")
            return None