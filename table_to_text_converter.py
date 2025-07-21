"""
고도화된 Table to Text 변환기
Beautiful Soup을 활용하여 HTML 테이블을 의미론적으로 풍부한 텍스트로 변환
RAG 데이터 생성 시 테이블 정보를 더 잘 보존하고 검색 가능하게 만듦
"""

import re
import html
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

try:
    from bs4 import BeautifulSoup, Tag, NavigableString
    BS4_AVAILABLE = True
except ImportError:
    BS4_AVAILABLE = False

from logging_config import get_logger

logger = get_logger("table_converter")


class TableType(Enum):
    """테이블 타입 분류"""
    KEY_VALUE = "key_value"          # 간단한 키-값 쌍 테이블
    DATA_TABLE = "data_table"        # 데이터 행렬 테이블
    LAYOUT_TABLE = "layout_table"    # 레이아웃용 테이블
    COMPLEX_TABLE = "complex_table"  # 복잡한 구조 테이블


@dataclass
class TableCell:
    """테이블 셀 정보"""
    text: str
    is_header: bool
    rowspan: int
    colspan: int
    row_index: int
    col_index: int


@dataclass
class TableStructure:
    """테이블 구조 정보"""
    cells: List[List[Optional[TableCell]]]
    headers: List[str]
    table_type: TableType
    row_count: int
    col_count: int
    has_complex_structure: bool
    caption: Optional[str] = None


class TableToTextConverter:
    """테이블을 텍스트로 변환하는 고도화된 변환기"""
    
    def __init__(self):
        self.max_cell_length = 200  # 셀 내용 최대 길이
        self.max_table_cells = 100  # 처리할 최대 셀 개수
        
    def convert_table_to_text(self, table_html: str) -> str:
        """HTML 테이블을 의미론적으로 풍부한 텍스트로 변환"""
        if not BS4_AVAILABLE:
            logger.warning("Beautiful Soup이 설치되지 않음, 기본 HTML 정리 방식 사용")
            return self._fallback_table_conversion(table_html)
        
        try:
            # Beautiful Soup으로 테이블 파싱
            soup = BeautifulSoup(table_html, 'html.parser')
            table = soup.find('table')
            
            if not table:
                logger.warning("테이블 태그를 찾을 수 없음")
                return self._fallback_table_conversion(table_html)
            
            # 테이블 구조 분석
            structure = self._analyze_table_structure(table)
            
            if not structure:
                logger.warning("테이블 구조 분석 실패")
                return self._fallback_table_conversion(table_html)
            
            # 타입별 변환 전략 적용
            text_result = self._convert_by_type(structure)
            
            logger.debug(
                "테이블 변환 완료",
                extra_data={
                    "table_type": structure.table_type.value,
                    "row_count": structure.row_count,
                    "col_count": structure.col_count,
                    "output_length": len(text_result)
                }
            )
            
            return text_result
            
        except Exception as e:
            logger.error(
                "테이블 변환 중 오류 발생",
                extra_data={"error": str(e)}
            )
            return self._fallback_table_conversion(table_html)
    
    def _analyze_table_structure(self, table: Tag) -> Optional[TableStructure]:
        """테이블 구조 분석"""
        try:
            # 캡션 추출
            caption_tag = table.find('caption')
            caption = caption_tag.get_text(strip=True) if caption_tag else None
            
            # 모든 행 수집
            rows = table.find_all('tr')
            if not rows:
                return None
            
            # 셀 매트릭스 생성
            cells_matrix = []
            headers = []
            max_cols = 0
            has_complex_structure = False
            
            for row_idx, row in enumerate(rows):
                cells = row.find_all(['td', 'th'])
                row_cells = []
                
                col_idx = 0
                for cell in cells:
                    # 병합된 셀로 인해 건너뛰어야 할 열 찾기
                    while (col_idx < len(cells_matrix) and 
                           row_idx < len(cells_matrix[col_idx]) and 
                           cells_matrix[col_idx][row_idx] is not None):
                        col_idx += 1
                    
                    # 셀 정보 추출
                    cell_text = self._extract_cell_text(cell)
                    is_header = cell.name == 'th' or row_idx == 0
                    rowspan = int(cell.get('rowspan', 1))
                    colspan = int(cell.get('colspan', 1))
                    
                    if rowspan > 1 or colspan > 1:
                        has_complex_structure = True
                    
                    # TableCell 객체 생성
                    table_cell = TableCell(
                        text=cell_text,
                        is_header=is_header,
                        rowspan=rowspan,
                        colspan=colspan,
                        row_index=row_idx,
                        col_index=col_idx
                    )
                    
                    # 병합된 셀 처리
                    for r in range(rowspan):
                        for c in range(colspan):
                            target_col = col_idx + c
                            target_row = row_idx + r
                            
                            # 매트릭스 확장
                            while len(cells_matrix) <= target_col:
                                cells_matrix.append([])
                            while len(cells_matrix[target_col]) <= target_row:
                                cells_matrix[target_col].append(None)
                            
                            cells_matrix[target_col][target_row] = table_cell if r == 0 and c == 0 else table_cell
                    
                    # 헤더 정보 수집
                    if is_header and cell_text.strip():
                        headers.append(cell_text.strip())
                    
                    col_idx += colspan
                
                max_cols = max(max_cols, col_idx)
            
            # 매트릭스 정규화 (모든 열이 같은 길이가 되도록)
            row_count = len(rows)
            col_count = max_cols
            
            normalized_matrix = []
            for col_idx in range(col_count):
                if col_idx < len(cells_matrix):
                    col = cells_matrix[col_idx]
                    while len(col) < row_count:
                        col.append(None)
                    normalized_matrix.append(col)
                else:
                    normalized_matrix.append([None] * row_count)
            
            # 테이블 타입 결정
            table_type = self._determine_table_type(normalized_matrix, headers, has_complex_structure)
            
            return TableStructure(
                cells=normalized_matrix,
                headers=headers,
                table_type=table_type,
                row_count=row_count,
                col_count=col_count,
                has_complex_structure=has_complex_structure,
                caption=caption
            )
            
        except Exception as e:
            logger.error(
                "테이블 구조 분석 오류",
                extra_data={"error": str(e)}
            )
            return None
    
    def _extract_cell_text(self, cell: Tag) -> str:
        """셀에서 텍스트 추출 및 정리"""
        try:
            # 중첩된 HTML 태그의 텍스트 추출
            text_parts = []
            
            for element in cell.descendants:
                if isinstance(element, NavigableString):
                    text = str(element).strip()
                    if text:
                        text_parts.append(text)
                elif element.name == 'br':
                    text_parts.append('\n')
            
            cell_text = ' '.join(text_parts)
            
            # HTML 엔티티 디코딩
            cell_text = html.unescape(cell_text)
            
            # 공백 정리
            cell_text = re.sub(r'\s+', ' ', cell_text).strip()
            
            # 길이 제한
            if len(cell_text) > self.max_cell_length:
                cell_text = cell_text[:self.max_cell_length - 3] + "..."
            
            return cell_text
            
        except Exception as e:
            logger.warning(
                "셀 텍스트 추출 실패",
                extra_data={"error": str(e)}
            )
            return ""
    
    def _determine_table_type(self, cells_matrix: List[List[Optional[TableCell]]], 
                            headers: List[str], has_complex_structure: bool) -> TableType:
        """테이블 타입 결정"""
        if has_complex_structure:
            return TableType.COMPLEX_TABLE
        
        row_count = len(cells_matrix[0]) if cells_matrix else 0
        col_count = len(cells_matrix)
        
        # 작은 테이블이고 2열인 경우 키-값 쌍으로 간주
        if col_count == 2 and row_count <= 10:
            return TableType.KEY_VALUE
        
        # 헤더가 있고 데이터 행이 많은 경우 데이터 테이블
        if headers and row_count > 2:
            return TableType.DATA_TABLE
        
        # 빈 셀이 많으면 레이아웃 테이블 가능성
        total_cells = row_count * col_count
        empty_cells = 0
        
        for col in cells_matrix:
            for cell in col:
                if not cell or not cell.text.strip():
                    empty_cells += 1
        
        if empty_cells / total_cells > 0.3:
            return TableType.LAYOUT_TABLE
        
        return TableType.DATA_TABLE
    
    def _convert_by_type(self, structure: TableStructure) -> str:
        """테이블 타입별 변환 전략 적용"""
        result_parts = []
        
        # 캡션 추가
        if structure.caption:
            result_parts.append(f"표 제목: {structure.caption}")
        
        # 타입별 변환
        if structure.table_type == TableType.KEY_VALUE:
            content = self._convert_key_value_table(structure)
        elif structure.table_type == TableType.DATA_TABLE:
            content = self._convert_data_table(structure)
        elif structure.table_type == TableType.LAYOUT_TABLE:
            content = self._convert_layout_table(structure)
        else:  # COMPLEX_TABLE
            content = self._convert_complex_table(structure)
        
        if content:
            result_parts.append(content)
        
        # 테이블 정보 요약 추가
        summary = f"[표 정보: {structure.row_count}행 {structure.col_count}열]"
        result_parts.append(summary)
        
        return "\n\n".join(result_parts)
    
    def _convert_key_value_table(self, structure: TableStructure) -> str:
        """키-값 쌍 테이블 변환"""
        result_parts = []
        
        if len(structure.cells) >= 2:
            for row_idx in range(structure.row_count):
                key_cell = structure.cells[0][row_idx]
                value_cell = structure.cells[1][row_idx]
                
                if key_cell and value_cell and key_cell.text.strip():
                    key = key_cell.text.strip()
                    value = value_cell.text.strip() or "정보 없음"
                    result_parts.append(f"- {key}: {value}")
        
        return "\n".join(result_parts) if result_parts else "테이블 내용 없음"
    
    def _convert_data_table(self, structure: TableStructure) -> str:
        """데이터 테이블 변환"""
        result_parts = []
        
        # 헤더 정보
        if structure.headers:
            result_parts.append(f"컬럼: {', '.join(structure.headers)}")
        
        # 데이터 행들 (처리량 제한)
        max_rows_to_process = min(20, structure.row_count)
        start_row = 1 if structure.headers else 0  # 헤더 행 건너뛰기
        
        for row_idx in range(start_row, min(start_row + max_rows_to_process, structure.row_count)):
            row_data = []
            for col_idx in range(structure.col_count):
                cell = structure.cells[col_idx][row_idx] if col_idx < len(structure.cells) else None
                cell_text = cell.text.strip() if cell and cell.text else ""
                if cell_text:
                    row_data.append(cell_text)
            
            if row_data:
                row_text = " | ".join(row_data)
                result_parts.append(f"행 {row_idx}: {row_text}")
        
        # 너무 많은 행이 있으면 요약 정보 추가
        if structure.row_count > max_rows_to_process + start_row:
            remaining = structure.row_count - max_rows_to_process - start_row
            result_parts.append(f"... ({remaining}개 행 더 있음)")
        
        return "\n".join(result_parts) if result_parts else "테이블 데이터 없음"
    
    def _convert_layout_table(self, structure: TableStructure) -> str:
        """레이아웃 테이블 변환 (의미 있는 텍스트만 추출)"""
        text_contents = []
        
        for col_idx in range(structure.col_count):
            for row_idx in range(structure.row_count):
                if col_idx < len(structure.cells):
                    cell = structure.cells[col_idx][row_idx]
                    if cell and cell.text.strip():
                        text_contents.append(cell.text.strip())
        
        # 중복 제거하면서 순서 유지
        unique_contents = []
        seen = set()
        for content in text_contents:
            if content not in seen and len(content) > 2:  # 너무 짧은 텍스트 제외
                seen.add(content)
                unique_contents.append(content)
        
        if unique_contents:
            return "레이아웃 테이블 내용: " + " / ".join(unique_contents)
        else:
            return "레이아웃 테이블 (내용 없음)"
    
    def _convert_complex_table(self, structure: TableStructure) -> str:
        """복잡한 테이블 변환 (구조적 정보 보존)"""
        result_parts = []
        
        # 병합된 셀 정보 포함하여 변환
        processed_positions = set()
        
        for row_idx in range(structure.row_count):
            row_parts = []
            for col_idx in range(structure.col_count):
                if (row_idx, col_idx) in processed_positions:
                    continue
                
                if col_idx < len(structure.cells):
                    cell = structure.cells[col_idx][row_idx]
                    if cell and cell.text.strip():
                        cell_text = cell.text.strip()
                        
                        # 병합 정보 추가
                        if cell.rowspan > 1 or cell.colspan > 1:
                            merge_info = f"({cell.rowspan}x{cell.colspan} 병합)"
                            cell_text = f"{cell_text} {merge_info}"
                            
                            # 병합된 위치들을 처리됨으로 표시
                            for r in range(cell.rowspan):
                                for c in range(cell.colspan):
                                    processed_positions.add((row_idx + r, col_idx + c))
                        
                        row_parts.append(cell_text)
            
            if row_parts:
                result_parts.append(f"행 {row_idx + 1}: {' | '.join(row_parts)}")
        
        return "\n".join(result_parts) if result_parts else "복잡한 테이블 (내용 없음)"
    
    def _fallback_table_conversion(self, table_html: str) -> str:
        """Beautiful Soup 없이 기본적인 테이블 변환"""
        try:
            # 기본 HTML 태그 제거
            text = re.sub(r'<br\s*/?>', '\n', table_html, flags=re.IGNORECASE)
            text = re.sub(r'<td[^>]*>', ' | ', text, flags=re.IGNORECASE)
            text = re.sub(r'<th[^>]*>', ' | ', text, flags=re.IGNORECASE)
            text = re.sub(r'<tr[^>]*>', '\n행: ', text, flags=re.IGNORECASE)
            text = re.sub(r'<[^>]+>', '', text)
            
            # HTML 엔티티 디코딩
            text = html.unescape(text)
            
            # 공백 정리
            text = re.sub(r'\n\s*\n', '\n', text)
            text = re.sub(r'[ \t]+', ' ', text)
            
            return text.strip()
            
        except Exception as e:
            logger.error(
                "폴백 테이블 변환 실패",
                extra_data={"error": str(e)}
            )
            return "[테이블 변환 실패]"


# 전역 변환기 인스턴스
table_converter = TableToTextConverter()


def convert_table_html_to_text(table_html: str) -> str:
    """HTML 테이블을 텍스트로 변환하는 편의 함수"""
    return table_converter.convert_table_to_text(table_html)