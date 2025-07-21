"""
=============================================================================
파일명: image_to_text_converter.py
목적: 이미지를 텍스트로 변환하는 핵심 기능을 제공

주요 역할:
1. HTML 문서에서 이미지를 자동으로 찾아서 추출
2. 다양한 이미지 소스 지원 (data URL, 외부 URL, Confluence 첨부파일)
3. 이미지 데이터를 base64로 인코딩하여 OpenAI API 호환 형식으로 변환
4. Confluence 첨부파일 다운로드 기능
5. 이미지 포맷 검증 및 크기 제한 관리

사용 예시:
- HTML에서 이미지 추출: extract_images_from_html(html_content)
- base64 인코딩: encode_image_to_base64(image_data)

주의사항:
- Beautiful Soup 라이브러리가 필요함 (HTML 파싱용)
- 보안상 localhost 이미지만 다운로드 허용
- 최대 이미지 크기 10MB 제한
=============================================================================
"""

# =============================================================================
# 필요한 라이브러리들을 가져오기 (import)
# =============================================================================

import re  # 정규표현식 - 문자열 패턴을 찾기 위해 사용
import base64  # 이미지를 base64 형식으로 인코딩하기 위해 사용
import requests  # 외부 URL에서 이미지를 다운로드하기 위해 사용
from typing import List, Dict, Any, Optional, Tuple  # 타입 힌트 - 코드의 가독성을 높여줌
from dataclasses import dataclass  # 데이터 클래스 - 간단한 데이터 구조를 만들기 위해 사용
from enum import Enum  # 열거형 - 상수값들을 그룹화하기 위해 사용
import io  # 입출력 관련 기능
from pathlib import Path  # 파일 경로 처리를 위해 사용

# Beautiful Soup 라이브러리 가져오기 시도 (HTML 파싱을 위해 필요)
try:
    from bs4 import BeautifulSoup, Tag  # HTML을 파싱(분석)하기 위한 라이브러리
    BS4_AVAILABLE = True  # Beautiful Soup이 사용 가능함을 표시
except ImportError:
    # Beautiful Soup이 설치되지 않은 경우
    BS4_AVAILABLE = False  # Beautiful Soup이 사용 불가능함을 표시

# 로깅 기능 가져오기 (프로그램 실행 과정을 기록하기 위해)
from logging_config import get_logger

# 이 파일 전용 로거 생성 (디버깅과 오류 추적에 사용)
logger = get_logger("image_converter")


# =============================================================================
# 데이터 구조 정의 (클래스와 상수들)
# =============================================================================

class ImageFormat(Enum):
    """
    지원하는 이미지 포맷들을 정의하는 열거형 클래스
    
    각 이미지 포맷은 문자열 값으로 저장됩니다.
    예시: ImageFormat.PNG.value는 "png"를 반환
    """
    JPEG = "jpeg"  # JPEG 이미지 포맷
    PNG = "png"    # PNG 이미지 포맷 (투명도 지원)
    GIF = "gif"    # GIF 이미지 포맷 (애니메이션 지원)
    WEBP = "webp"  # WebP 이미지 포맷 (구글에서 개발)
    BMP = "bmp"    # BMP 이미지 포맷 (비트맵)
    SVG = "svg"    # SVG 이미지 포맷 (벡터 그래픽)


@dataclass
class ImageData:
    """
    추출된 이미지의 모든 정보를 담는 데이터 클래스
    
    @dataclass는 파이썬에서 데이터를 저장하는 클래스를 쉽게 만들어주는 기능입니다.
    """
    data: bytes  # 이미지의 실제 바이너리 데이터 (0과 1로 이루어진 파일 내용)
    format: ImageFormat  # 이미지 포맷 (위에서 정의한 ImageFormat 중 하나)
    source_url: Optional[str] = None  # 이미지의 원본 URL (있으면 문자열, 없으면 None)
    alt_text: Optional[str] = None    # 이미지의 대체 텍스트 (이미지가 로드되지 않을 때 보여줄 텍스트)
    title: Optional[str] = None       # 이미지의 제목
    width: Optional[int] = None       # 이미지 너비 (픽셀 단위)
    height: Optional[int] = None      # 이미지 높이 (픽셀 단위)


# =============================================================================
# 메인 이미지 추출 클래스
# =============================================================================

class ImageExtractor:
    """
    HTML 문서에서 이미지를 찾아서 추출하는 메인 클래스
    
    이 클래스는 다음과 같은 기능을 제공합니다:
    1. HTML에서 <img> 태그 찾기
    2. Confluence의 <ac:image> 태그 처리
    3. 이미지 다운로드 및 데이터 추출
    4. 파일 크기 및 포맷 검증
    """
    
    def __init__(self):
        """
        ImageExtractor 클래스를 초기화합니다.
        
        여기서 클래스의 기본 설정값들을 정의합니다.
        """
        # 최대 이미지 크기를 10MB로 제한 (메모리 사용량 제한을 위해)
        self.max_image_size = 10 * 1024 * 1024  # 10MB = 10 × 1024 × 1024 바이트
        
        # 지원하는 이미지 포맷들을 집합(set)으로 정의
        # 집합을 사용하면 'in' 연산자로 빠르게 포함 여부를 확인할 수 있습니다
        self.supported_formats = {
            'jpeg', 'jpg', 'png', 'gif', 'webp', 'bmp'
        }
        
    def extract_images_from_html(self, html_content: str, base_url: str = "", page_id: str = None) -> List[ImageData]:
        """
        HTML 문서에서 모든 이미지를 찾아서 추출하는 메인 메서드
        
        매개변수:
            html_content (str): 분석할 HTML 문서의 내용
            base_url (str): 상대경로 이미지 URL을 절대경로로 변환할 때 사용할 기본 URL
            page_id (str): Confluence 페이지 ID (첨부파일 다운로드용)
        
        반환값:
            List[ImageData]: 추출된 이미지 데이터들의 리스트
        """
        # Beautiful Soup 라이브러리가 설치되어 있는지 확인
        if not BS4_AVAILABLE:
            logger.warning("Beautiful Soup이 설치되지 않음, 기본 이미지 추출 방식 사용")
            # Beautiful Soup이 없으면 기본 방식으로 처리
            return self._fallback_extract_images(html_content)
        
        try:
            # HTML 문서를 파싱(분석)하여 BeautifulSoup 객체 생성
            soup = BeautifulSoup(html_content, 'html.parser')
            images = []  # 추출된 이미지들을 저장할 빈 리스트
            
            # 1단계: 일반적인 <img> 태그들 찾기
            for img_tag in soup.find_all('img'):
                # 각 img 태그에서 이미지 데이터 추출 시도
                image_data = self._extract_image_from_tag(img_tag, base_url)
                if image_data:  # 성공적으로 추출된 경우
                    images.append(image_data)  # 리스트에 추가
                    
            # 2단계: Confluence 특수 이미지 태그들 처리
            # Confluence는 <ac:image>와 <ri:attachment> 태그를 사용합니다
            for img_macro in soup.find_all(['ac:image', 'ri:attachment']):
                # Confluence 이미지 매크로에서 이미지 데이터 추출 시도
                image_data = self._extract_confluence_image(img_macro, base_url, page_id)
                if image_data:  # 성공적으로 추출된 경우
                    images.append(image_data)  # 리스트에 추가
            
            # 작업 완료 로그 기록
            logger.info(f"HTML에서 {len(images)}개의 이미지 추출 완료")
            return images
            
        except Exception as e:
            # 오류가 발생한 경우 로그에 기록하고 기본 방식으로 처리
            logger.error(f"이미지 추출 중 오류 발생: {e}")
            return self._fallback_extract_images(html_content)
    
    def _extract_image_from_tag(self, img_tag: Tag, base_url: str) -> Optional[ImageData]:
        """img 태그에서 이미지 데이터 추출"""
        try:
            src = img_tag.get('src')
            if not src:
                return None
            
            # 상대 URL을 절대 URL로 변환
            if src.startswith('/') and base_url:
                src = base_url.rstrip('/') + src
            elif not src.startswith(('http://', 'https://', 'data:')):
                if base_url:
                    src = base_url.rstrip('/') + '/' + src.lstrip('/')
            
            # data URL 처리
            if src.startswith('data:'):
                return self._process_data_url(src, img_tag)
            
            # 외부 URL에서 이미지 다운로드
            return self._download_image(src, img_tag)
            
        except Exception as e:
            logger.warning(f"이미지 태그 처리 실패: {e}")
            return None
    
    def _extract_confluence_image(self, img_macro: Tag, base_url: str, page_id: str = None) -> Optional[ImageData]:
        """Confluence 이미지 매크로에서 이미지 추출"""
        try:
            # Confluence 첨부파일 참조 처리
            attachment_ri = img_macro.find('ri:attachment')
            if attachment_ri:
                filename = attachment_ri.get('ri:filename')
                if filename and self._is_supported_image_format(filename):
                    logger.info(f"Confluence 첨부파일 이미지 감지: {filename}")
                    
                    # Confluence API를 통해 첨부파일 다운로드 시도
                    image_data = self._download_confluence_attachment(page_id, filename, base_url)
                    
                    if image_data:
                        return ImageData(
                            data=image_data,
                            format=self._get_image_format(filename),
                            alt_text=filename,
                            title=f"Confluence 첨부파일: {filename}"
                        )
                    else:
                        # 다운로드 실패 시 빈 데이터로 ImageData 생성
                        return ImageData(
                            data=b"",
                            format=self._get_image_format(filename),
                            alt_text=filename,
                            title=f"Confluence 첨부파일: {filename}"
                        )
            
            return None
            
        except Exception as e:
            logger.warning(f"Confluence 이미지 매크로 처리 실패: {e}")
            return None
    
    def _download_confluence_attachment(self, page_id: str, filename: str, base_url: str) -> Optional[bytes]:
        """Confluence 첨부파일 다운로드"""
        try:
            if not page_id:
                logger.warning("페이지 ID가 없어 첨부파일을 다운로드할 수 없음")
                return None
            
            from confluence_api import ConfluenceClient
            
            # 기본 인증 정보 사용 (실제 환경에서는 설정에서 가져와야 함)
            client = ConfluenceClient(
                base_url=base_url,
                username='',  # TODO: 설정에서 가져오기
                password=''       # TODO: 설정에서 가져오기
            )
            
            # 첨부파일 다운로드
            attachment_data = client.download_attachment(page_id, filename)
            
            if attachment_data:
                logger.info(f"Confluence 첨부파일 다운로드 성공: {filename} ({len(attachment_data)} bytes)")
                return attachment_data
            else:
                logger.warning(f"Confluence 첨부파일 다운로드 실패: {filename}")
                return None
                
        except Exception as e:
            logger.error(f"Confluence 첨부파일 다운로드 오류: {e}")
            return None
    
    def _process_data_url(self, data_url: str, img_tag: Tag) -> Optional[ImageData]:
        """data URL에서 이미지 데이터 추출"""
        try:
            # data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAA... 형식 파싱
            if not data_url.startswith('data:image/'):
                return None
            
            # MIME 타입과 데이터 분리
            header, data = data_url.split(',', 1)
            mime_type = header.split(';')[0].split(':')[1]  # image/png
            image_format = mime_type.split('/')[1]  # png
            
            if image_format.lower() not in self.supported_formats:
                logger.warning(f"지원하지 않는 이미지 포맷: {image_format}")
                return None
            
            # base64 디코딩
            if 'base64' in header:
                image_data = base64.b64decode(data)
            else:
                logger.warning("base64가 아닌 data URL은 지원하지 않음")
                return None
            
            if len(image_data) > self.max_image_size:
                logger.warning(f"이미지 크기가 너무 큼: {len(image_data)} bytes")
                return None
            
            return ImageData(
                data=image_data,
                format=ImageFormat(image_format.lower()),
                alt_text=img_tag.get('alt'),
                title=img_tag.get('title'),
                width=self._safe_int(img_tag.get('width')),
                height=self._safe_int(img_tag.get('height'))
            )
            
        except Exception as e:
            logger.error(f"data URL 처리 실패: {e}")
            return None
    
    def _download_image(self, url: str, img_tag: Tag) -> Optional[ImageData]:
        """외부 URL에서 이미지 다운로드"""
        try:
            # 보안상 로컬 서버의 이미지만 다운로드 허용
            if not url.startswith('http://localhost:') and not url.startswith('https://localhost:'):
                logger.info(f"보안상 외부 이미지 다운로드 제한: {url}")
                return None
            
            response = requests.get(url, timeout=10, stream=True)
            response.raise_for_status()
            
            # Content-Type 확인
            content_type = response.headers.get('content-type', '').lower()
            if not content_type.startswith('image/'):
                logger.warning(f"이미지가 아닌 콘텐츠: {content_type}")
                return None
            
            image_format = content_type.split('/')[1]
            if image_format not in self.supported_formats:
                logger.warning(f"지원하지 않는 이미지 포맷: {image_format}")
                return None
            
            # 이미지 데이터 읽기 (크기 제한)
            image_data = b""
            for chunk in response.iter_content(chunk_size=8192):
                image_data += chunk
                if len(image_data) > self.max_image_size:
                    logger.warning(f"이미지 크기가 너무 큼: {url}")
                    return None
            
            return ImageData(
                data=image_data,
                format=ImageFormat(image_format),
                source_url=url,
                alt_text=img_tag.get('alt'),
                title=img_tag.get('title'),
                width=self._safe_int(img_tag.get('width')),
                height=self._safe_int(img_tag.get('height'))
            )
            
        except Exception as e:
            logger.error(f"이미지 다운로드 실패 {url}: {e}")
            return None
    
    def _fallback_extract_images(self, html_content: str) -> List[ImageData]:
        """Beautiful Soup 없이 기본적인 이미지 추출"""
        images = []
        
        try:
            # data URL 패턴 찾기
            data_url_pattern = r'data:image/([a-zA-Z]+);base64,([A-Za-z0-9+/=]+)'
            matches = re.findall(data_url_pattern, html_content)
            
            for image_format, base64_data in matches:
                if image_format.lower() in self.supported_formats:
                    try:
                        image_data = base64.b64decode(base64_data)
                        if len(image_data) <= self.max_image_size:
                            images.append(ImageData(
                                data=image_data,
                                format=ImageFormat(image_format.lower()),
                                alt_text="추출된 이미지"
                            ))
                    except Exception as e:
                        logger.warning(f"base64 이미지 처리 실패: {e}")
            
            logger.info(f"폴백 방식으로 {len(images)}개 이미지 추출")
            
        except Exception as e:
            logger.error(f"폴백 이미지 추출 실패: {e}")
        
        return images
    
    def _is_supported_image_format(self, filename: str) -> bool:
        """파일명으로 지원하는 이미지 포맷인지 확인"""
        if not filename:
            return False
        
        extension = Path(filename).suffix.lower().lstrip('.')
        return extension in self.supported_formats
    
    def _get_image_format(self, filename: str) -> ImageFormat:
        """파일명에서 이미지 포맷 추출"""
        extension = Path(filename).suffix.lower().lstrip('.')
        
        # 확장자 매핑
        format_mapping = {
            'jpg': 'jpeg',
            'jpeg': 'jpeg',
            'png': 'png',
            'gif': 'gif',
            'webp': 'webp',
            'bmp': 'bmp'
        }
        
        return ImageFormat(format_mapping.get(extension, 'jpeg'))
    
    def _safe_int(self, value: str) -> Optional[int]:
        """안전한 정수 변환"""
        if not value:
            return None
        
        try:
            return int(value)
        except ValueError:
            return None


class ImageToTextConverter:
    """이미지를 텍스트로 변환하는 컨버터"""
    
    def __init__(self):
        self.extractor = ImageExtractor()
    
    def extract_images_from_content(self, html_content: str, base_url: str = "", page_id: str = None) -> List[ImageData]:
        """HTML 콘텐츠에서 이미지들을 추출"""
        return self.extractor.extract_images_from_html(html_content, base_url, page_id)
    
    def encode_image_to_base64(self, image_data: ImageData) -> str:
        """이미지 데이터를 base64로 인코딩"""
        try:
            if not image_data.data:
                return ""
            
            base64_data = base64.b64encode(image_data.data).decode('utf-8')
            mime_type = f"image/{image_data.format.value}"
            
            return f"data:{mime_type};base64,{base64_data}"
            
        except Exception as e:
            logger.error(f"이미지 base64 인코딩 실패: {e}")
            return ""
    
    def create_image_description(self, image_data: ImageData) -> str:
        """이미지에 대한 기본 설명 생성"""
        description_parts = []
        
        if image_data.alt_text:
            description_parts.append(f"대체 텍스트: {image_data.alt_text}")
        
        if image_data.title:
            description_parts.append(f"제목: {image_data.title}")
        
        if image_data.width and image_data.height:
            description_parts.append(f"크기: {image_data.width}x{image_data.height}")
        
        description_parts.append(f"포맷: {image_data.format.value.upper()}")
        
        if image_data.source_url:
            description_parts.append(f"출처: {image_data.source_url}")
        
        return " | ".join(description_parts)


# 전역 컨버터 인스턴스
image_converter = ImageToTextConverter()


def extract_images_from_html(html_content: str, base_url: str = "", page_id: str = None) -> List[ImageData]:
    """HTML에서 이미지 추출하는 편의 함수"""
    return image_converter.extract_images_from_content(html_content, base_url, page_id)


def encode_image_to_base64(image_data: ImageData) -> str:
    """이미지를 base64로 인코딩하는 편의 함수"""
    return image_converter.encode_image_to_base64(image_data)