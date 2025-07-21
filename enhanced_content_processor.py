"""
=============================================================================
파일명: enhanced_content_processor.py
목적: HTML 콘텐츠를 AI가 이해하기 쉬운 텍스트로 변환하는 고급 처리기

주요 역할:
1. HTML 테이블을 구조화된 텍스트로 변환
2. HTML 이미지를 AI가 분석한 텍스트 설명으로 변환
3. 전체 콘텐츠를 RAG(검색 증강 생성) 시스템에 최적화
4. LLM(대형 언어 모델) 처리에 적합한 형태로 데이터 가공
5. 처리 통계 및 상태 관리

사용 예시:
- result = process_page_content(html_content, page_title)
- enhanced_text = get_enhanced_content_for_summary(content)

주요 장점:
- 테이블 데이터를 텍스트로 변환하여 검색 가능하게 만듦
- 이미지 내용을 텍스트로 설명하여 AI가 이해할 수 있게 함
- 원본 HTML 구조를 유지하면서 내용을 풍부하게 만듦

기술적 특징:
- 멀티미디어 콘텐츠의 자동 텍스트 변환
- 오류 처리 및 폴백 메커니즘 제공
- 처리 통계 수집 및 성능 모니터링
=============================================================================
"""

# =============================================================================
# 필요한 라이브러리들을 가져오기
# =============================================================================

import re  # 정규표현식 - HTML 태그 찾기 및 텍스트 처리에 사용
from typing import List, Dict, Any, Optional, Tuple  # 타입 힌트
from dataclasses import dataclass  # 데이터 클래스

# 프로젝트 내 다른 모듈들 가져오기
from content_utils import analyze_page_content, ContentAnalysisResult  # 콘텐츠 분석 기능
from table_to_text_converter import convert_table_html_to_text  # 테이블을 텍스트로 변환
from image_to_text_converter import extract_images_from_html, ImageData  # 이미지 추출 및 데이터 구조
from llm_service import initialize_llm_service, LLMService  # AI 언어 모델 서비스
from logging_config import get_logger  # 로깅 설정

# 이 파일 전용 로거 생성
logger = get_logger("enhanced_content_processor")


# =============================================================================
# 데이터 구조 정의
# =============================================================================

@dataclass
class EnhancedContentResult:
    """
    향상된 콘텐츠 처리 결과를 담는 데이터 클래스
    
    이 클래스는 콘텐츠 처리 작업의 모든 결과를 정리해서 저장합니다.
    """
    original_content: str          # 원본 HTML 콘텐츠
    enhanced_content: str          # 처리된(향상된) 텍스트 콘텐츠
    extracted_images: List[ImageData]  # 추출된 이미지 데이터들
    image_descriptions: List[str]  # AI가 생성한 이미지 설명들
    table_count: int              # 변환된 테이블 개수
    image_count: int              # 처리된 이미지 개수
    processing_notes: List[str]   # 처리 과정에서 발생한 노트들


# =============================================================================
# 메인 콘텐츠 처리 클래스
# =============================================================================

class EnhancedContentProcessor:
    """
    HTML 콘텐츠를 AI가 이해하기 쉬운 형태로 변환하는 메인 클래스
    
    이 클래스는 다음과 같은 작업을 수행합니다:
    1. HTML 테이블을 읽기 쉬운 텍스트로 변환
    2. 이미지를 AI가 분석한 텍스트 설명으로 변환
    3. 전체 콘텐츠를 RAG 시스템에 최적화
    """
    
    def __init__(self, llm_service: Optional[LLMService] = None):
        """
        EnhancedContentProcessor를 초기화합니다.
        
        매개변수:
            llm_service: 사용할 AI 언어 모델 서비스 (없으면 기본값 사용)
        """
        # AI 언어 모델 서비스 설정 (이미지 분석에 사용)
        self.llm_service = llm_service or initialize_llm_service()
        
        # 처리 통계를 추적하기 위한 딕셔너리
        self.processing_stats = {
            'processed_pages': 0,      # 처리한 페이지 수
            'extracted_tables': 0,     # 추출한 테이블 수
            'extracted_images': 0,     # 추출한 이미지 수
            'failed_image_analysis': 0 # 이미지 분석 실패 수
        }
    
    def process_content(self, content: str, page_title: str = "", 
                       base_url: str = "http://localhost:8090", page_id: str = None) -> EnhancedContentResult:
        """콘텐츠를 분석하고 테이블/이미지를 텍스트로 변환"""
        try:
            logger.info(f"콘텐츠 처리 시작: {page_title}")
            
            # 기본 콘텐츠 분석
            analysis = analyze_page_content(content, page_title)
            
            enhanced_content = content
            extracted_images = []
            image_descriptions = []
            processing_notes = []
            table_count = 0
            
            # 테이블 처리
            if analysis.content_type == 'table' or '<table' in content:
                enhanced_content, table_count = self._process_tables(enhanced_content)
                processing_notes.append(f"테이블 {table_count}개를 텍스트로 변환")
            
            # 이미지 처리  
            if analysis.has_images:
                enhanced_content, extracted_images, image_descriptions = self._process_images(
                    enhanced_content, base_url, page_title, page_id
                )
                processing_notes.append(f"이미지 {len(extracted_images)}개를 분석하고 텍스트로 변환")
            
            # 통계 업데이트
            self.processing_stats['processed_pages'] += 1
            self.processing_stats['extracted_tables'] += table_count
            self.processing_stats['extracted_images'] += len(extracted_images)
            
            result = EnhancedContentResult(
                original_content=content,
                enhanced_content=enhanced_content,
                extracted_images=extracted_images,
                image_descriptions=image_descriptions,
                table_count=table_count,
                image_count=len(extracted_images),
                processing_notes=processing_notes
            )
            
            logger.info(
                f"콘텐츠 처리 완료: {page_title} "
                f"(테이블: {table_count}, 이미지: {len(extracted_images)})"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"콘텐츠 처리 중 오류 발생: {e}")
            return EnhancedContentResult(
                original_content=content,
                enhanced_content=content,
                extracted_images=[],
                image_descriptions=[],
                table_count=0,
                image_count=0,
                processing_notes=[f"처리 오류: {str(e)}"]
            )
    
    def _process_tables(self, content: str) -> Tuple[str, int]:
        """HTML 콘텐츠에서 테이블을 찾아서 텍스트로 변환"""
        try:
            # 테이블 패턴 찾기
            table_pattern = r'<table[^>]*>.*?</table>'
            tables = re.findall(table_pattern, content, re.DOTALL | re.IGNORECASE)
            
            if not tables:
                return content, 0
            
            enhanced_content = content
            processed_count = 0
            
            for table_html in tables:
                try:
                    # 테이블을 텍스트로 변환
                    table_text = convert_table_html_to_text(table_html)
                    
                    # 원본 테이블을 변환된 텍스트로 교체
                    enhanced_content = enhanced_content.replace(
                        table_html, 
                        f"\n\n[변환된 테이블]\n{table_text}\n[/변환된 테이블]\n\n",
                        1
                    )
                    processed_count += 1
                    
                except Exception as e:
                    logger.warning(f"테이블 변환 실패: {e}")
                    # 실패한 경우 원본 유지
            
            logger.debug(f"{processed_count}개 테이블이 텍스트로 변환됨")
            return enhanced_content, processed_count
            
        except Exception as e:
            logger.error(f"테이블 처리 중 오류: {e}")
            return content, 0
    
    def _process_images(self, content: str, base_url: str, page_title: str, page_id: str = None) -> Tuple[str, List[ImageData], List[str]]:
        """HTML 콘텐츠에서 이미지를 찾아서 분석하고 텍스트로 변환"""
        try:
            # HTML에서 이미지 추출
            extracted_images = extract_images_from_html(content, base_url, page_id)
            
            if not extracted_images:
                return content, [], []
            
            enhanced_content = content
            image_descriptions = []
            
            for i, image_data in enumerate(extracted_images):
                try:
                    # LLM을 사용하여 이미지 분석
                    prompt = f"이 이미지를 자세히 분석하고 설명해주세요. 이 이미지는 '{page_title}' 문서에 포함된 이미지입니다."
                    
                    image_description = self.llm_service.extract_image_text(image_data, prompt)
                    image_descriptions.append(image_description)
                    
                    # 이미지 태그를 설명으로 교체 (가능한 경우)
                    if image_data.source_url:
                        # 특정 이미지 URL을 찾아서 교체
                        img_pattern = f'<img[^>]*src[^>]*{re.escape(image_data.source_url)}[^>]*>'
                        enhanced_content = re.sub(
                            img_pattern,
                            f'\n\n[이미지 분석 결과]\n{image_description}\n[/이미지 분석 결과]\n\n',
                            enhanced_content,
                            count=1,
                            flags=re.IGNORECASE
                        )
                    elif image_data.alt_text:
                        # alt 텍스트로 찾아서 교체
                        alt_pattern = f'<img[^>]*alt[^>]*{re.escape(image_data.alt_text)}[^>]*>'
                        enhanced_content = re.sub(
                            alt_pattern,
                            f'\n\n[이미지 분석 결과]\n{image_description}\n[/이미지 분석 결과]\n\n',
                            enhanced_content,
                            count=1,
                            flags=re.IGNORECASE
                        )
                    else:
                        # 첫 번째 img 태그 교체
                        enhanced_content = re.sub(
                            r'<img[^>]*>',
                            f'\n\n[이미지 분석 결과]\n{image_description}\n[/이미지 분석 결과]\n\n',
                            enhanced_content,
                            count=1,
                            flags=re.IGNORECASE
                        )
                    
                    logger.debug(f"이미지 {i+1} 분석 완료: {len(image_description)} 문자")
                    
                except Exception as e:
                    logger.error(f"이미지 {i+1} 분석 실패: {e}")
                    self.processing_stats['failed_image_analysis'] += 1
                    
                    # 실패한 경우 기본 설명 사용
                    fallback_description = f"이미지 파일 ({image_data.format.value.upper()})"
                    if image_data.alt_text:
                        fallback_description += f": {image_data.alt_text}"
                    
                    image_descriptions.append(fallback_description)
            
            logger.debug(f"{len(extracted_images)}개 이미지 처리 완료")
            return enhanced_content, extracted_images, image_descriptions
            
        except Exception as e:
            logger.error(f"이미지 처리 중 오류: {e}")
            return content, [], []
    
    def get_processing_stats(self) -> Dict[str, Any]:
        """처리 통계 반환"""
        return self.processing_stats.copy()
    
    def reset_stats(self):
        """통계 초기화"""
        self.processing_stats = {
            'processed_pages': 0,
            'extracted_tables': 0,
            'extracted_images': 0,
            'failed_image_analysis': 0
        }
    
    def process_content_for_summary(self, content: str, page_title: str = "") -> str:
        """요약 생성을 위한 콘텐츠 처리 (간단 버전)"""
        try:
            result = self.process_content(content, page_title)
            return result.enhanced_content
        except Exception as e:
            logger.error(f"요약용 콘텐츠 처리 실패: {e}")
            return content
    
    def process_content_for_keywords(self, content: str, page_title: str = "") -> str:
        """키워드 추출을 위한 콘텐츠 처리 (간단 버전)"""
        try:
            result = self.process_content(content, page_title)
            
            # 키워드 추출을 위해 이미지 설명들을 추가
            if result.image_descriptions:
                image_context = "\n\n포함된 이미지들:\n" + "\n".join(
                    f"- {desc[:100]}..." if len(desc) > 100 else f"- {desc}"
                    for desc in result.image_descriptions
                )
                return result.enhanced_content + image_context
            
            return result.enhanced_content
            
        except Exception as e:
            logger.error(f"키워드용 콘텐츠 처리 실패: {e}")
            return content


# 전역 프로세서 인스턴스
enhanced_processor = EnhancedContentProcessor()


def process_page_content(content: str, page_title: str = "", base_url: str = "http://localhost:8090", page_id: str = None) -> EnhancedContentResult:
    """페이지 콘텐츠 처리 편의 함수"""
    return enhanced_processor.process_content(content, page_title, base_url, page_id)


def get_enhanced_content_for_summary(content: str, page_title: str = "") -> str:
    """요약용 향상된 콘텐츠 반환"""
    return enhanced_processor.process_content_for_summary(content, page_title)


def get_enhanced_content_for_keywords(content: str, page_title: str = "") -> str:
    """키워드용 향상된 콘텐츠 반환"""
    return enhanced_processor.process_content_for_keywords(content, page_title)