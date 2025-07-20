"""
콘텐츠 분석 및 처리 유틸리티 함수들
HTML/이미지 감지 로직의 중복 코드를 해결하기 위한 모듈
"""
import re
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

from logging_config import get_logger
from exceptions import ContentAnalysisError

logger = get_logger("content_utils")


@dataclass
class ContentAnalysisResult:
    """콘텐츠 분석 결과"""
    content_type: str
    special_keywords: List[str]
    is_html: bool
    has_images: bool
    has_attachments: bool
    content_length: int
    word_count: int
    is_empty: bool


class ContentAnalyzer:
    """콘텐츠 분석기 클래스"""
    
    # HTML 패턴들
    HTML_PATTERNS = [
        r'<[^>]+>',           # HTML 태그
        r'&[a-zA-Z]+;',       # HTML 엔티티 (&amp;, &lt; 등)
        r'</[^>]+>',          # 종료 태그
        r'<!\-\-.*?\-\->',    # HTML 주석
        r'<!DOCTYPE[^>]*>',   # DOCTYPE 선언
        r'<\?xml[^>]*\?>',    # XML 선언
    ]
    
    # 이미지 관련 패턴들
    IMAGE_PATTERNS = [
        r'<img[^>]*>',                              # img 태그
        r'\.(jpg|jpeg|png|gif|bmp|svg|webp|tiff|ico)', # 이미지 파일 확장자
        r'image[s]?[:/]',                           # image: 또는 images/ 패턴
        r'attachment[s]?[:/]',                      # 첨부파일 패턴
        r'<ac:image[^>]*>',                         # Confluence 이미지 매크로
        r'ri:attachment',                           # Confluence 첨부파일 참조
        r'screenshot',                              # 스크린샷
        r'그림',                                    # 한글 그림
        r'사진',                                    # 한글 사진
        r'이미지',                                  # 한글 이미지
        r'캡처',                                    # 한글 캡처
        r'첨부파일',                               # 한글 첨부파일
    ]
    
    # 첨부파일 패턴들
    ATTACHMENT_PATTERNS = [
        r'<ac:attachment[^>]*>',                    # Confluence 첨부파일 매크로
        r'ri:attachment',                           # Confluence 첨부파일 참조
        r'attachment[s]?[:/]',                      # 첨부파일 경로
        r'\.(pdf|doc|docx|xls|xlsx|ppt|pptx|txt|zip|rar|7z)', # 첨부파일 확장자
        r'download',                                # 다운로드 관련
        r'첨부',                                    # 한글 첨부
        r'파일',                                    # 한글 파일
    ]
    
    # 특수 콘텐츠 키워드 매핑 (각 카테고리당 대표 키워드 1개)
    CONTENT_TYPE_KEYWORDS = {
        'html': 'HTML',
        'image': '이미지',
        'attachment': '첨부파일',
        'empty': '내용없음',
        'code': '코드',
        'table': '표',
        'list': '목록',
    }
    
    def __init__(self):
        """콘텐츠 분석기 초기화"""
        self.compiled_html_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.HTML_PATTERNS]
        self.compiled_image_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.IMAGE_PATTERNS]
        self.compiled_attachment_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.ATTACHMENT_PATTERNS]
    
    def analyze_content(self, content: str, title: str = "") -> ContentAnalysisResult:
        """콘텐츠 종합 분석"""
        try:
            if not content:
                content = ""
            
            # 기본 정보 분석
            content_length = len(content)
            word_count = len(re.findall(r'\S+', content))
            is_empty = content_length < 10
            
            # HTML 감지
            is_html = self._detect_html(content)
            
            # 이미지/첨부파일 감지
            has_images = self._detect_images(content)
            has_attachments = self._detect_attachments(content)
            
            # 콘텐츠 타입 결정
            content_type = self._determine_content_type(
                content, is_html, has_images, has_attachments, is_empty
            )
            
            # 특수 키워드 생성
            special_keywords = self._generate_special_keywords(
                content_type, is_html, has_images, has_attachments, is_empty
            )
            
            result = ContentAnalysisResult(
                content_type=content_type,
                special_keywords=special_keywords,
                is_html=is_html,
                has_images=has_images,
                has_attachments=has_attachments,
                content_length=content_length,
                word_count=word_count,
                is_empty=is_empty
            )
            
            logger.debug(
                "콘텐츠 분석 완료",
                extra_data={
                    "title": title,
                    "content_length": content_length,
                    "word_count": word_count,
                    "content_type": content_type,
                    "special_keywords": special_keywords,
                    "is_html": is_html,
                    "has_images": has_images,
                    "has_attachments": has_attachments
                }
            )
            
            return result
            
        except Exception as e:
            logger.error(
                "콘텐츠 분석 중 오류 발생",
                extra_data={
                    "title": title,
                    "content_length": len(content) if content else 0,
                    "error": str(e)
                }
            )
            raise ContentAnalysisError(f"콘텐츠 분석 실패: {str(e)}", {"title": title})
    
    def _detect_html(self, content: str) -> bool:
        """HTML 콘텐츠 감지"""
        if not content:
            return False
            
        for pattern in self.compiled_html_patterns:
            if pattern.search(content):
                return True
        return False
    
    def _detect_images(self, content: str) -> bool:
        """이미지 콘텐츠 감지"""
        if not content:
            return False
            
        for pattern in self.compiled_image_patterns:
            if pattern.search(content):
                return True
        return False
    
    def _detect_attachments(self, content: str) -> bool:
        """첨부파일 콘텐츠 감지"""
        if not content:
            return False
            
        for pattern in self.compiled_attachment_patterns:
            if pattern.search(content):
                return True
        return False
    
    def _determine_content_type(self, content: str, is_html: bool, has_images: bool, 
                               has_attachments: bool, is_empty: bool) -> str:
        """콘텐츠 타입 결정"""
        if is_empty:
            return "empty"
        elif is_html and has_images and has_attachments:
            return "rich_media"
        elif is_html:
            return "html"
        elif has_images:
            return "image"
        elif has_attachments:
            return "attachment"
        elif self._detect_code(content):
            return "code"
        elif self._detect_table(content):
            return "table"
        elif self._detect_list(content):
            return "list"
        else:
            return "text"
    
    def _detect_code(self, content: str) -> bool:
        """코드 콘텐츠 감지"""
        code_patterns = [
            r'```[\s\S]*?```',      # 마크다운 코드 블록
            r'`[^`]+`',             # 인라인 코드
            r'<code[^>]*>',         # HTML code 태그
            r'<pre[^>]*>',          # HTML pre 태그
            r'function\s+\w+\s*\(', # 함수 정의
            r'class\s+\w+\s*{',     # 클래스 정의
            r'def\s+\w+\s*\(',      # Python 함수
            r'#include\s*<',        # C/C++ include
            r'import\s+\w+',        # Python/Java import
            r'console\.log\s*\(',   # JavaScript console.log
        ]
        
        for pattern in code_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                return True
        return False
    
    def _detect_table(self, content: str) -> bool:
        """테이블 콘텐츠 감지"""
        table_patterns = [
            r'<table[^>]*>',        # HTML table
            r'\|.*\|.*\|',          # 마크다운 테이블
            r'<tr[^>]*>',           # HTML table row
            r'<td[^>]*>',           # HTML table cell
            r'<th[^>]*>',           # HTML table header
        ]
        
        for pattern in table_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                return True
        return False
    
    def _detect_list(self, content: str) -> bool:
        """리스트 콘텐츠 감지"""
        list_patterns = [
            r'<ul[^>]*>',           # HTML unordered list
            r'<ol[^>]*>',           # HTML ordered list
            r'<li[^>]*>',           # HTML list item
            r'^\s*[-*+]\s+',        # 마크다운 unordered list
            r'^\s*\d+\.\s+',        # 마크다운 ordered list
        ]
        
        for pattern in list_patterns:
            if re.search(pattern, content, re.MULTILINE | re.IGNORECASE):
                return True
        return False
    
    def _generate_special_keywords(self, content_type: str, is_html: bool, 
                                 has_images: bool, has_attachments: bool, is_empty: bool) -> List[str]:
        """특수 키워드 생성 (각 카테고리당 1개씩)"""
        keywords = []
        
        # 콘텐츠 타입별 키워드 추가 (1개만)
        if content_type in self.CONTENT_TYPE_KEYWORDS:
            keywords.append(self.CONTENT_TYPE_KEYWORDS[content_type])
        
        # 특성별 키워드 추가 (중복되지 않는 경우만)
        if is_html and self.CONTENT_TYPE_KEYWORDS['html'] not in keywords:
            keywords.append(self.CONTENT_TYPE_KEYWORDS['html'])
        
        if has_images and self.CONTENT_TYPE_KEYWORDS['image'] not in keywords:
            keywords.append(self.CONTENT_TYPE_KEYWORDS['image'])
        
        if has_attachments and self.CONTENT_TYPE_KEYWORDS['attachment'] not in keywords:
            keywords.append(self.CONTENT_TYPE_KEYWORDS['attachment'])
        
        if is_empty and self.CONTENT_TYPE_KEYWORDS['empty'] not in keywords:
            keywords.append(self.CONTENT_TYPE_KEYWORDS['empty'])
        
        # 중복 제거하면서 순서 유지 (이미 중복은 방지했지만 안전장치)
        return list(dict.fromkeys(keywords))
    
    def extract_keywords_from_content(self, content: str, max_keywords: int = 10) -> List[str]:
        """콘텐츠에서 키워드 추출 (폴백용)"""
        if not content:
            return []
        
        try:
            # 한글, 영문, 숫자만 추출
            words = re.findall(r'[가-힣a-zA-Z0-9]+', content)
            
            # 길이 필터링 (2자 이상 15자 이하)
            filtered_words = [w for w in words if 2 <= len(w) <= 15]
            
            # 빈도수 계산 및 정렬
            from collections import Counter
            word_counts = Counter(filtered_words)
            
            # 상위 키워드 반환
            top_keywords = [word for word, count in word_counts.most_common(max_keywords)]
            
            logger.debug(
                "폴백 키워드 추출 완료",
                extra_data={
                    "total_words": len(words),
                    "filtered_words": len(filtered_words),
                    "extracted_keywords": len(top_keywords),
                    "keywords": top_keywords
                }
            )
            
            return top_keywords
            
        except Exception as e:
            logger.error(
                "폴백 키워드 추출 실패",
                extra_data={"error": str(e)}
            )
            return []
    
    def clean_llm_keywords(self, raw_keywords: List[str]) -> List[str]:
        """LLM이 생성한 키워드 정리"""
        if not raw_keywords:
            return []
        
        cleaned_keywords = []
        
        # 제외할 구문들
        skip_phrases = [
            "이 페이지", "내용이", "매우", "짧고", "의미", "없는", "내용이므로",
            "키워드를", "추출하기", "어렵습니다", "제공된", "내용만으로는",
            "다음과", "같은", "추출할", "수", "있습니다", "어려운", "상황"
        ]
        
        skip_phrases_en = [
            "content", "keywords", "extract", "difficult", "short",
            "meaningful", "following", "provide", "limited", "based"
        ]
        
        for keyword in raw_keywords:
            if not isinstance(keyword, str):
                continue
                
            cleaned_keyword = keyword.strip()
            
            # 필터링 조건들
            if (len(cleaned_keyword) > 20 or 
                len(cleaned_keyword) < 2 or
                any(phrase in cleaned_keyword for phrase in skip_phrases) or
                any(phrase in cleaned_keyword.lower() for phrase in skip_phrases_en) or
                "." in cleaned_keyword):
                continue
            
            cleaned_keywords.append(cleaned_keyword)
        
        logger.debug(
            "LLM 키워드 정리 완료",
            extra_data={
                "raw_count": len(raw_keywords),
                "cleaned_count": len(cleaned_keywords),
                "cleaned_keywords": cleaned_keywords
            }
        )
        
        return cleaned_keywords


# 전역 콘텐츠 분석기 인스턴스
content_analyzer = ContentAnalyzer()


# 편의 함수들
def analyze_page_content(content: str, title: str = "") -> ContentAnalysisResult:
    """페이지 콘텐츠 분석"""
    return content_analyzer.analyze_content(content, title)


def extract_fallback_keywords(content: str, max_keywords: int = 10) -> List[str]:
    """폴백 키워드 추출"""
    return content_analyzer.extract_keywords_from_content(content, max_keywords)


def clean_keywords(raw_keywords: List[str]) -> List[str]:
    """키워드 정리"""
    return content_analyzer.clean_llm_keywords(raw_keywords)


def is_content_empty(content: str) -> bool:
    """콘텐츠가 비어있는지 확인"""
    return not content or len(content.strip()) < 10


def has_html_content(content: str) -> bool:
    """HTML 콘텐츠 포함 여부 확인"""
    return content_analyzer._detect_html(content)


def has_image_content(content: str) -> bool:
    """이미지 콘텐츠 포함 여부 확인"""
    return content_analyzer._detect_images(content)


def has_attachment_content(content: str) -> bool:
    """첨부파일 콘텐츠 포함 여부 확인"""
    return content_analyzer._detect_attachments(content)