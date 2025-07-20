"""
RAG 최적화를 위한 스마트 텍스트 청킹 시스템

LangChain의 best practices와 Confluence 페이지 특성을 고려한 
계층적 chunking 전략을 구현합니다.
"""

import re
import html
import json
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from abc import ABC, abstractmethod
from enum import Enum

from content_utils import ContentAnalysisResult, content_analyzer
from config import config
from logging_config import get_logger

logger = get_logger("rag_chunking")


class ChunkType(Enum):
    """청크 타입 열거형"""
    HEADER = "header"
    PARAGRAPH = "paragraph"
    CODE = "code"
    TABLE = "table"
    LIST = "list"
    MIXED = "mixed"


@dataclass
class RAGChunk:
    """RAG에 최적화된 텍스트 청크"""
    content: str                    # 청크 내용
    chunk_id: str                   # 고유 ID
    source_page_id: str            # 원본 페이지 ID
    chunk_index: int               # 페이지 내 순서
    chunk_type: ChunkType          # 청크 타입
    token_count: int               # 토큰 수
    char_count: int                # 문자 수
    metadata: Dict[str, Any]       # 메타데이터
    overlap_start: int = 0         # 이전 청크와 겹치는 시작 위치
    overlap_end: int = 0           # 다음 청크와 겹치는 끝 위치
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        result = asdict(self)
        result['chunk_type'] = self.chunk_type.value
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RAGChunk':
        """딕셔너리에서 생성"""
        data['chunk_type'] = ChunkType(data['chunk_type'])
        return cls(**data)


class TokenCounter:
    """토큰 카운팅 유틸리티"""
    
    @staticmethod
    def count_tokens(text: str) -> int:
        """텍스트의 토큰 수 추정 (한글/영문 고려)"""
        if not text:
            return 0
        
        # 한글: 글자당 ~1.5 토큰, 영문: 단어당 ~1.3 토큰
        korean_chars = len(re.findall(r'[가-힣]', text))
        english_words = len(re.findall(r'[a-zA-Z]+', text))
        other_chars = len(text) - korean_chars - sum(len(word) for word in re.findall(r'[a-zA-Z]+', text))
        
        estimated_tokens = int(korean_chars * 1.5 + english_words * 1.3 + other_chars * 0.5)
        return max(1, estimated_tokens)


class ChunkStrategy(ABC):
    """청킹 전략 추상 클래스"""
    
    @abstractmethod
    def chunk(self, content: str, page_id: str, analysis: ContentAnalysisResult) -> List[RAGChunk]:
        """콘텐츠를 청크로 분할"""
        pass


class HierarchicalChunker(ChunkStrategy):
    """계층적 청킹 전략 - HTML 구조 기반"""
    
    def __init__(self, 
                 target_chunk_size: int = 512,
                 max_chunk_size: int = 1024,
                 overlap_tokens: int = 50,
                 preserve_structure: bool = True):
        self.target_chunk_size = target_chunk_size
        self.max_chunk_size = max_chunk_size
        self.overlap_tokens = overlap_tokens
        self.preserve_structure = preserve_structure
    
    def chunk(self, content: str, page_id: str, analysis: ContentAnalysisResult) -> List[RAGChunk]:
        """계층적 청킹 실행"""
        logger.info(f"계층적 청킹 시작: page_id={page_id}, target_size={self.target_chunk_size}")
        
        chunks = []
        
        if analysis.is_html:
            chunks = self._chunk_html_content(content, page_id)
        else:
            chunks = self._chunk_plain_text(content, page_id)
        
        # 오버랩 적용
        chunks = self._apply_overlap(chunks)
        
        logger.info(f"청킹 완료: {len(chunks)}개 청크 생성")
        return chunks
    
    def _chunk_html_content(self, content: str, page_id: str) -> List[RAGChunk]:
        """HTML 콘텐츠 청킹"""
        chunks = []
        
        # HTML 태그 기반 섹션 분리
        sections = self._extract_html_sections(content)
        
        chunk_index = 0
        for section_type, section_content in sections:
            if not section_content.strip():
                continue
            
            section_chunks = self._process_section(
                section_content, section_type, page_id, chunk_index
            )
            chunks.extend(section_chunks)
            chunk_index += len(section_chunks)
        
        return chunks
    
    def _extract_html_sections(self, content: str) -> List[Tuple[ChunkType, str]]:
        """HTML에서 의미 있는 섹션 추출"""
        sections = []
        
        # 코드 블록 우선 처리 (분리하지 않음)
        code_pattern = r'<(?:pre|code)[^>]*>.*?</(?:pre|code)>'
        code_blocks = re.findall(code_pattern, content, re.DOTALL | re.IGNORECASE)
        
        remaining_content = content
        for code_block in code_blocks:
            sections.append((ChunkType.CODE, self._clean_html(code_block)))
            remaining_content = remaining_content.replace(code_block, '', 1)
        
        # 테이블 처리
        table_pattern = r'<table[^>]*>.*?</table>'
        table_blocks = re.findall(table_pattern, remaining_content, re.DOTALL | re.IGNORECASE)
        
        for table_block in table_blocks:
            sections.append((ChunkType.TABLE, self._clean_html(table_block)))
            remaining_content = remaining_content.replace(table_block, '', 1)
        
        # 헤더 기반 섹션 분리
        header_pattern = r'<h[1-6][^>]*>.*?</h[1-6]>'
        headers = re.findall(header_pattern, remaining_content, re.IGNORECASE)
        
        if headers:
            # 헤더로 콘텐츠 분할
            parts = re.split(r'<h[1-6][^>]*>.*?</h[1-6]>', remaining_content, flags=re.IGNORECASE)
            
            for i, header in enumerate(headers):
                sections.append((ChunkType.HEADER, self._clean_html(header)))
                if i < len(parts) - 1 and parts[i + 1].strip():
                    sections.append((ChunkType.PARAGRAPH, self._clean_html(parts[i + 1])))
        else:
            # 헤더가 없으면 단락으로 처리
            if remaining_content.strip():
                sections.append((ChunkType.PARAGRAPH, self._clean_html(remaining_content)))
        
        return sections
    
    def _clean_html(self, html_content: str) -> str:
        """HTML 태그 제거하면서 구조 정보 보존"""
        if not html_content:
            return ""
        
        # 특수 태그 처리
        html_content = re.sub(r'<br\s*/?>', '\n', html_content, flags=re.IGNORECASE)
        html_content = re.sub(r'<p[^>]*>', '\n\n', html_content, flags=re.IGNORECASE)
        html_content = re.sub(r'</p>', '', html_content, flags=re.IGNORECASE)
        
        # 리스트 처리
        html_content = re.sub(r'<li[^>]*>', '\n• ', html_content, flags=re.IGNORECASE)
        html_content = re.sub(r'</li>', '', html_content, flags=re.IGNORECASE)
        
        # 모든 HTML 태그 제거
        html_content = re.sub(r'<[^>]+>', '', html_content)
        
        # HTML 엔티티 디코딩
        html_content = html.unescape(html_content)
        
        # 공백 정리
        html_content = re.sub(r'\n\s*\n', '\n\n', html_content)
        html_content = re.sub(r'[ \t]+', ' ', html_content)
        
        return html_content.strip()
    
    def _chunk_plain_text(self, content: str, page_id: str) -> List[RAGChunk]:
        """일반 텍스트 청킹"""
        chunks = []
        
        # 단락 기반 분할
        paragraphs = self._split_into_paragraphs(content)
        
        current_chunk = ""
        chunk_index = 0
        
        for paragraph in paragraphs:
            paragraph_tokens = TokenCounter.count_tokens(paragraph)
            current_tokens = TokenCounter.count_tokens(current_chunk)
            
            if current_tokens + paragraph_tokens <= self.target_chunk_size:
                current_chunk += "\n\n" + paragraph if current_chunk else paragraph
            else:
                # 현재 청크 저장
                if current_chunk:
                    chunks.append(self._create_chunk(
                        current_chunk, page_id, chunk_index, ChunkType.PARAGRAPH
                    ))
                    chunk_index += 1
                
                # 새 청크 시작
                if paragraph_tokens <= self.max_chunk_size:
                    current_chunk = paragraph
                else:
                    # 너무 긴 단락은 문장 단위로 분할
                    sentence_chunks = self._split_long_paragraph(paragraph, page_id, chunk_index)
                    chunks.extend(sentence_chunks)
                    chunk_index += len(sentence_chunks)
                    current_chunk = ""
        
        # 마지막 청크 저장
        if current_chunk:
            chunks.append(self._create_chunk(
                current_chunk, page_id, chunk_index, ChunkType.PARAGRAPH
            ))
        
        return chunks
    
    def _split_into_paragraphs(self, content: str) -> List[str]:
        """텍스트를 단락으로 분할"""
        paragraphs = re.split(r'\n\s*\n', content)
        return [p.strip() for p in paragraphs if p.strip()]
    
    def _split_long_paragraph(self, paragraph: str, page_id: str, start_index: int) -> List[RAGChunk]:
        """긴 단락을 문장 단위로 분할"""
        chunks = []
        sentences = self._split_into_sentences(paragraph)
        
        current_chunk = ""
        chunk_index = start_index
        
        for sentence in sentences:
            sentence_tokens = TokenCounter.count_tokens(sentence)
            current_tokens = TokenCounter.count_tokens(current_chunk)
            
            if current_tokens + sentence_tokens <= self.target_chunk_size:
                current_chunk += " " + sentence if current_chunk else sentence
            else:
                if current_chunk:
                    chunks.append(self._create_chunk(
                        current_chunk, page_id, chunk_index, ChunkType.PARAGRAPH
                    ))
                    chunk_index += 1
                
                if sentence_tokens <= self.max_chunk_size:
                    current_chunk = sentence
                else:
                    # 극도로 긴 문장은 고정 크기로 분할
                    fixed_chunks = self._split_by_fixed_size(sentence, page_id, chunk_index)
                    chunks.extend(fixed_chunks)
                    chunk_index += len(fixed_chunks)
                    current_chunk = ""
        
        if current_chunk:
            chunks.append(self._create_chunk(
                current_chunk, page_id, chunk_index, ChunkType.PARAGRAPH
            ))
        
        return chunks
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """텍스트를 문장으로 분할"""
        # 한글/영문 문장 구분 개선
        sentence_endings = r'[.!?。！？]\s*'
        sentences = re.split(sentence_endings, text)
        
        # 빈 문장 제거 및 정리
        sentences = [s.strip() for s in sentences if s.strip()]
        return sentences
    
    def _split_by_fixed_size(self, text: str, page_id: str, start_index: int) -> List[RAGChunk]:
        """고정 크기로 텍스트 분할 (최후 수단)"""
        chunks = []
        words = text.split()
        
        current_chunk = ""
        chunk_index = start_index
        
        for word in words:
            test_chunk = current_chunk + " " + word if current_chunk else word
            if TokenCounter.count_tokens(test_chunk) <= self.target_chunk_size:
                current_chunk = test_chunk
            else:
                if current_chunk:
                    chunks.append(self._create_chunk(
                        current_chunk, page_id, chunk_index, ChunkType.MIXED
                    ))
                    chunk_index += 1
                current_chunk = word
        
        if current_chunk:
            chunks.append(self._create_chunk(
                current_chunk, page_id, chunk_index, ChunkType.MIXED
            ))
        
        return chunks
    
    def _process_section(self, content: str, section_type: ChunkType, 
                        page_id: str, start_index: int) -> List[RAGChunk]:
        """섹션 처리"""
        token_count = TokenCounter.count_tokens(content)
        
        if token_count <= self.target_chunk_size:
            # 작은 섹션은 그대로 유지
            return [self._create_chunk(content, page_id, start_index, section_type)]
        elif token_count <= self.max_chunk_size:
            # 중간 크기는 그대로 유지하되 주의 표시
            chunk = self._create_chunk(content, page_id, start_index, section_type)
            chunk.metadata['oversized'] = True
            return [chunk]
        else:
            # 큰 섹션은 분할
            if section_type in [ChunkType.CODE, ChunkType.TABLE]:
                # 코드/테이블은 의미 단위 유지
                chunk = self._create_chunk(content, page_id, start_index, section_type)
                chunk.metadata['large_block'] = True
                return [chunk]
            else:
                # 일반 텍스트는 재귀 분할
                return self._split_long_paragraph(content, page_id, start_index)
    
    def _create_chunk(self, content: str, page_id: str, index: int, 
                     chunk_type: ChunkType) -> RAGChunk:
        """RAGChunk 객체 생성"""
        chunk_id = f"{page_id}_chunk_{index:03d}"
        token_count = TokenCounter.count_tokens(content)
        char_count = len(content)
        
        metadata = {
            'created_at': None,  # 추후 설정
            'chunk_strategy': 'hierarchical',
            'quality_score': self._calculate_quality_score(content, chunk_type),
            'has_complete_sentences': self._has_complete_sentences(content),
        }
        
        return RAGChunk(
            content=content,
            chunk_id=chunk_id,
            source_page_id=page_id,
            chunk_index=index,
            chunk_type=chunk_type,
            token_count=token_count,
            char_count=char_count,
            metadata=metadata
        )
    
    def _calculate_quality_score(self, content: str, chunk_type: ChunkType) -> float:
        """청크 품질 점수 계산 (0.0 ~ 1.0)"""
        score = 0.5  # 기본 점수
        
        # 완전한 문장 여부
        if self._has_complete_sentences(content):
            score += 0.2
        
        # 적절한 길이
        token_count = TokenCounter.count_tokens(content)
        if self.target_chunk_size * 0.7 <= token_count <= self.target_chunk_size * 1.2:
            score += 0.2
        
        # 타입별 보너스
        if chunk_type in [ChunkType.HEADER, ChunkType.PARAGRAPH]:
            score += 0.1
        
        # 구조적 완성도
        if chunk_type == ChunkType.CODE and content.count('\n') > 0:
            score += 0.1
        
        return min(1.0, score)
    
    def _has_complete_sentences(self, content: str) -> bool:
        """완전한 문장 포함 여부 확인"""
        sentence_endings = r'[.!?。！？]'
        return bool(re.search(sentence_endings, content))
    
    def _apply_overlap(self, chunks: List[RAGChunk]) -> List[RAGChunk]:
        """청크 간 오버랩 적용"""
        if len(chunks) <= 1 or self.overlap_tokens <= 0:
            return chunks
        
        overlapped_chunks = []
        
        for i, chunk in enumerate(chunks):
            new_content = chunk.content
            overlap_start = 0
            overlap_end = 0
            
            # 이전 청크와 오버랩
            if i > 0:
                prev_chunk = chunks[i - 1]
                overlap_text = self._get_overlap_text(prev_chunk.content, True)
                if overlap_text:
                    new_content = overlap_text + "\n\n" + new_content
                    overlap_start = TokenCounter.count_tokens(overlap_text)
            
            # 다음 청크와 오버랩
            if i < len(chunks) - 1:
                next_chunk = chunks[i + 1]
                overlap_text = self._get_overlap_text(next_chunk.content, False)
                if overlap_text:
                    new_content = new_content + "\n\n" + overlap_text
                    overlap_end = TokenCounter.count_tokens(overlap_text)
            
            # 새 청크 생성
            new_chunk = RAGChunk(
                content=new_content,
                chunk_id=chunk.chunk_id,
                source_page_id=chunk.source_page_id,
                chunk_index=chunk.chunk_index,
                chunk_type=chunk.chunk_type,
                token_count=TokenCounter.count_tokens(new_content),
                char_count=len(new_content),
                metadata=chunk.metadata.copy(),
                overlap_start=overlap_start,
                overlap_end=overlap_end
            )
            
            new_chunk.metadata['has_overlap'] = overlap_start > 0 or overlap_end > 0
            overlapped_chunks.append(new_chunk)
        
        return overlapped_chunks
    
    def _get_overlap_text(self, content: str, from_end: bool) -> str:
        """오버랩용 텍스트 추출"""
        words = content.split()
        target_tokens = min(self.overlap_tokens, len(words) // 2)
        
        if target_tokens <= 0:
            return ""
        
        if from_end:
            overlap_words = words[-target_tokens:]
        else:
            overlap_words = words[:target_tokens]
        
        return " ".join(overlap_words)


class RAGChunkingService:
    """RAG 청킹 서비스"""
    
    def __init__(self):
        self.chunkers = {
            'hierarchical': HierarchicalChunker(
                target_chunk_size=getattr(config, 'RAG_CHUNK_SIZE', 512),
                max_chunk_size=getattr(config, 'RAG_MAX_CHUNK_SIZE', 1024),
                overlap_tokens=getattr(config, 'RAG_OVERLAP_TOKENS', 50)
            )
        }
        self.default_strategy = getattr(config, 'RAG_DEFAULT_STRATEGY', 'hierarchical')
    
    def chunk_content(self, content: str, page_id: str, 
                     strategy: str = None) -> List[RAGChunk]:
        """콘텐츠를 RAG 청크로 분할"""
        strategy = strategy or self.default_strategy
        
        if strategy not in self.chunkers:
            logger.warning(f"알 수 없는 청킹 전략: {strategy}, 기본값 사용")
            strategy = self.default_strategy
        
        # 콘텐츠 분석
        analysis = content_analyzer.analyze_content(content)
        
        # 청킹 실행
        chunker = self.chunkers[strategy]
        chunks = chunker.chunk(content, page_id, analysis)
        
        # 청크 메타데이터 보강
        for chunk in chunks:
            chunk.metadata.update({
                'content_type': analysis.content_type,
                'is_html': analysis.is_html,
                'has_images': analysis.has_images,
                'has_attachments': analysis.has_attachments,
                'source_word_count': analysis.word_count,
                'source_length': analysis.content_length
            })
        
        logger.info(f"청킹 완료: {len(chunks)}개 청크, 전략={strategy}")
        return chunks
    
    def get_chunk_summary(self, chunks: List[RAGChunk]) -> Dict[str, Any]:
        """청크 요약 정보"""
        if not chunks:
            return {}
        
        total_tokens = sum(chunk.token_count for chunk in chunks)
        avg_tokens = total_tokens / len(chunks)
        
        type_counts = {}
        for chunk in chunks:
            chunk_type = chunk.chunk_type.value
            type_counts[chunk_type] = type_counts.get(chunk_type, 0) + 1
        
        quality_scores = [chunk.metadata.get('quality_score', 0.0) for chunk in chunks]
        avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0.0
        
        return {
            'total_chunks': len(chunks),
            'total_tokens': total_tokens,
            'avg_tokens_per_chunk': round(avg_tokens, 1),
            'chunk_types': type_counts,
            'avg_quality_score': round(avg_quality, 2),
            'has_overlaps': any(chunk.metadata.get('has_overlap', False) for chunk in chunks)
        }


# 전역 서비스 인스턴스
rag_chunking_service = RAGChunkingService()