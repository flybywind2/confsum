from abc import ABC, abstractmethod
from typing import List, Optional, Dict
import logging
import json
import re
from config import config
from rag_chunking import RAGChunkingService, RAGChunk
from models import PersonExtractionResult, ExtractedPerson

logger = logging.getLogger(__name__)

class LLMService(ABC):
    @abstractmethod
    def summarize(self, content: str) -> str:
        pass
    
    @abstractmethod
    def extract_keywords(self, content: str) -> List[str]:
        pass
    
    @abstractmethod
    def extract_persons(self, content: str, page_title: str = "") -> PersonExtractionResult:
        """Confluence 문서에서 인물 정보 추출"""
        pass
    
    def chunk_based_summarize(self, content: str, page_title: str = "", use_chunking: bool = None) -> str:
        """RAG 최적화된 chunking 기반 요약 생성"""
        if use_chunking is None:
            use_chunking = config.RAG_ENABLED
        
        if not use_chunking or len(content) <= config.RAG_CHUNK_SIZE:
            # 짧은 콘텐츠거나 chunking 비활성화시 기본 요약 사용
            return self.summarize(content)
        
        # 원본 청크 사용 설정이 활성화되어 있으면 새로운 방식 사용
        if config.RAG_USE_RAW_CHUNKS:
            return self.chunk_based_analyze_raw(content, page_title, use_chunking, config.RAG_MAX_CHUNKS)
        
        try:
            # RAGChunkingService 초기화
            chunking_service = RAGChunkingService()
            
            # 콘텐츠를 최적화된 chunk로 분할
            chunks = chunking_service.chunk_content(content, page_title or "unknown")
            
            if not chunks:
                logger.warning("Chunking 결과가 비어있음, 기본 요약 사용")
                return self.summarize(content)
            
            logger.info(f"RAG chunking 완료: {len(chunks)}개 chunk 생성")
            
            # 각 chunk를 개별 요약 후 전체 요약 생성
            chunk_summaries = []
            for i, chunk in enumerate(chunks[:5]):  # 최대 5개 chunk만 처리 (토큰 제한)
                try:
                    chunk_summary = self.summarize(chunk.content)
                    if chunk_summary and len(chunk_summary.strip()) > 10:
                        chunk_summaries.append(f"[{chunk.chunk_type.value}] {chunk_summary}")
                except Exception as e:
                    logger.warning(f"Chunk {i} 요약 실패: {str(e)}")
                    continue
            
            if not chunk_summaries:
                logger.warning("모든 chunk 요약 실패, 기본 요약 사용")
                return self.summarize(content)
            
            # chunk 요약들을 종합하여 최종 요약 생성
            combined_summary = " ".join(chunk_summaries)
            
            if len(combined_summary) > 1000:
                # 너무 길면 다시 요약
                final_prompt = f"다음 내용들을 종합하여 간결한 요약을 생성해주세요:\n\n{combined_summary}"
                final_summary = self.summarize(final_prompt)
                return final_summary if final_summary else combined_summary[:500] + "..."
            
            return combined_summary
            
        except Exception as e:
            logger.error(f"RAG chunking 요약 실패, 기본 요약 사용: {str(e)}")
            return self.summarize(content)
    
    def chunk_based_analyze_raw(self, content: str, page_title: str = "", use_chunking: bool = None, max_chunks: int = 3) -> str:
        """RAG 청킹을 사용하여 요약 없이 원본 청크들을 분석하여 답변 생성"""
        if use_chunking is None:
            use_chunking = config.RAG_ENABLED
        
        if not use_chunking or len(content) <= config.RAG_CHUNK_SIZE:
            # 짧은 콘텐츠거나 chunking 비활성화시 기본 요약 사용
            return self.summarize(content)
        
        try:
            # RAGChunkingService 초기화
            chunking_service = RAGChunkingService()
            
            # 콘텐츠를 최적화된 chunk로 분할
            chunks = chunking_service.chunk_content(content, page_title or "unknown")
            
            if not chunks:
                logger.warning("Chunking 결과가 비어있음, 기본 요약 사용")
                return self.summarize(content)
            
            logger.info(f"RAG chunking 완료: {len(chunks)}개 청크 생성")
            
            # 품질 점수가 높은 상위 청크들 선택 (품질점수와 길이를 모두 고려)
            def get_chunk_priority(chunk):
                quality = chunk.metadata.get('quality_score', 0.0)
                length_bonus = min(len(chunk.content) / 1000, 0.2)  # 길이에 따른 보너스 (최대 0.2)
                return quality + length_bonus
            
            sorted_chunks = sorted(chunks, key=get_chunk_priority, reverse=True)
            selected_chunks = sorted_chunks[:max_chunks]
            
            logger.info(f"선택된 청크들의 품질 점수: {[round(get_chunk_priority(chunk), 2) for chunk in selected_chunks]}")
            
            # 선택된 청크들의 원본 내용을 결합
            combined_content = "\n\n".join([
                f"[청크 {i+1} - {chunk.chunk_type.value}]\n{chunk.content}" 
                for i, chunk in enumerate(selected_chunks)
            ])
            
            # 토큰 제한 확인 (매우 긴 경우에만)
            if len(combined_content) > 8000:
                # 너무 길면 각 청크를 적당히 자름
                truncated_chunks = []
                for i, chunk in enumerate(selected_chunks):
                    chunk_content = chunk.content[:2400] + "..." if len(chunk.content) > 2400 else chunk.content
                    truncated_chunks.append(f"[청크 {i+1} - {chunk.chunk_type.value}]\n{chunk_content}")
                combined_content = "\n\n".join(truncated_chunks)
            
            # 종합 분석 프롬프트 생성  
            analysis_prompt = f"""다음은 문서 "{page_title}"에서 추출된 주요 청크들입니다. 각 청크의 정보를 손실 없이 보존하면서 체계적으로 정리해주세요.

{combined_content}

위 청크들의 내용을 기반으로:
1. 각 청크의 핵심 정보를 빠뜨리지 말고 모두 포함하세요
2. 구체적인 데이터, 숫자, 절차, 인명 등은 정확히 유지하세요  
3. 청크들 간의 관계와 전체적인 맥락을 설명하세요
4. 중요한 세부사항을 생략하지 말고 체계적으로 구성하세요

정보 손실 없이 포괄적으로 정리해주세요."""

            return self.summarize(analysis_prompt)
            
        except Exception as e:
            logger.error(f"RAG 원본 청크 분석 실패, 기본 요약 사용: {str(e)}")
            return self.summarize(content)
    
    def chunk_based_extract_keywords(self, content: str, page_title: str = "", use_chunking: bool = None) -> List[str]:
        """RAG 최적화된 chunking 기반 키워드 추출"""
        if use_chunking is None:
            use_chunking = config.RAG_ENABLED
        
        if not use_chunking or len(content) <= config.RAG_CHUNK_SIZE:
            # 짧은 콘텐츠거나 chunking 비활성화시 기본 키워드 추출
            return self.extract_keywords(content)
        
        try:
            # RAGChunkingService 초기화
            chunking_service = RAGChunkingService()
            
            # 콘텐츠를 최적화된 chunk로 분할
            chunks = chunking_service.chunk_content(content, page_title or "unknown")
            
            if not chunks:
                logger.warning("Chunking 결과가 비어있음, 기본 키워드 추출 사용")
                return self.extract_keywords(content)
            
            # 각 chunk에서 키워드 추출
            all_keywords = []
            for chunk in chunks[:3]:  # 최대 3개 chunk만 처리
                try:
                    chunk_keywords = self.extract_keywords(chunk.content)
                    all_keywords.extend(chunk_keywords)
                except Exception as e:
                    logger.warning(f"Chunk 키워드 추출 실패: {str(e)}")
                    continue
            
            if not all_keywords:
                logger.warning("모든 chunk 키워드 추출 실패, 기본 키워드 추출 사용")
                return self.extract_keywords(content)
            
            # 중복 제거 및 빈도순 정렬
            from collections import Counter
            keyword_freq = Counter(all_keywords)
            unique_keywords = [kw for kw, freq in keyword_freq.most_common(20)]
            
            return unique_keywords[:10]  # 최대 10개 반환
            
        except Exception as e:
            logger.error(f"RAG chunking 키워드 추출 실패, 기본 키워드 추출 사용: {str(e)}")
            return self.extract_keywords(content)

class OllamaService(LLMService):
    def __init__(self, base_url: str = None, model_name: str = None):
        self.base_url = base_url or config.OLLAMA_URL
        self.model_name = model_name or config.OLLAMA_MODEL
        self.client = None
        self.available = False
        
        try:
            import ollama
            self.client = ollama.Client(host=self.base_url)
            # 연결 테스트
            self._test_connection()
            self.available = True
            logger.info(f"Ollama 서비스 초기화 성공: {self.base_url}, 모델: {self.model_name}")
        except ImportError:
            logger.error("ollama 패키지가 설치되지 않았습니다.")
            raise ImportError("ollama 패키지를 설치해주세요: pip install ollama")
        except Exception as e:
            logger.warning(f"Ollama 서비스 초기화 실패: {str(e)}")
            raise e
    
    def _test_connection(self):
        """Ollama 연결 테스트"""
        try:
            # 간단한 테스트 메시지로 연결 확인
            response = self.client.chat(
                model=self.model_name,
                messages=[{'role': 'user', 'content': 'test'}],
                options={'num_predict': 10}  # 짧은 응답
            )
            return True
        except Exception as e:
            logger.error(f"Ollama 연결 테스트 실패: {str(e)}")
            raise e
    
    def _call_ollama(self, prompt: str) -> str:
        """Ollama API 호출"""
        if not self.available or not self.client:
            raise Exception("Ollama 서비스가 사용 불가능합니다.")
        
        try:
            response = self.client.chat(
                model=self.model_name,
                messages=[
                    {'role': 'user', 'content': prompt}
                ],
                options={
                    'temperature': 0.7
                }
            )
            return response['message']['content']
        except Exception as e:
            logger.error(f"Ollama API 호출 오류: {str(e)}")
            raise e
    
    def summarize(self, content: str) -> str:
        """페이지 내용 요약 생성"""
        try:
            prompt = config.SUMMARY_PROMPT.format(content=content)
            return self._call_ollama(prompt)
        except Exception as e:
            logger.error(f"요약 생성 오류: {str(e)}")
            return "요약 생성 중 오류가 발생했습니다."
    
    def extract_keywords(self, content: str) -> List[str]:
        """키워드 추출"""
        try:
            prompt = config.KEYWORDS_PROMPT.format(content=content)
            response = self._call_ollama(prompt)
            
            # 응답에서 키워드 추출 (쉼표로 구분)
            keywords = [keyword.strip() for keyword in response.split(',')]
            keywords = [k for k in keywords if k]  # 빈 문자열 제거
            
            return keywords[:10]  # 최대 10개로 제한
        except Exception as e:
            logger.error(f"키워드 추출 오류: {str(e)}")
            return []
    
    def extract_persons(self, content: str, page_title: str = "") -> PersonExtractionResult:
        """Confluence 문서에서 인물 정보 추출"""
        try:
            # 정규표현식으로 후보 이름 패턴 찾기
            potential_names = self._extract_name_candidates(content)
            
            # LLM으로 인물 정보 추출 및 검증
            person_prompt = self._create_person_extraction_prompt(content, page_title, potential_names)
            response = self._call_ollama(person_prompt)
            
            # JSON 응답 파싱
            try:
                # 응답에서 JSON 부분만 추출 (```json으로 감싸진 경우 처리)
                json_response = self._extract_json_from_response(response)
                parsed_data = json.loads(json_response)
                persons = []
                
                for person_data in parsed_data.get('persons', []):
                    person = ExtractedPerson(
                        name=person_data.get('name', ''),
                        department=person_data.get('department'),
                        role=person_data.get('role'),
                        email=person_data.get('email'),
                        mentioned_context=person_data.get('mentioned_context'),
                        confidence=person_data.get('confidence', 0.0)
                    )
                    if person.name and person.confidence > 0.3:  # 최소 신뢰도 필터
                        persons.append(person)
                
                return PersonExtractionResult(persons=persons)
                
            except (json.JSONDecodeError, ValueError) as e:
                logger.warning(f"LLM 응답 JSON 파싱 실패: {str(e)[:100]}...")
                return PersonExtractionResult(persons=[])
                
        except Exception as e:
            logger.error(f"인물 정보 추출 오류: {str(e)}")
            return PersonExtractionResult(persons=[])
    
    def _extract_name_candidates(self, content: str) -> List[str]:
        """정규표현식으로 후보 이름 패턴 추출"""
        candidates = set()
        
        # 한글 이름 패턴 (2-4글자 또는 님으로 끝나는 것)
        korean_name_pattern = r'[가-힣]{2,4}(?=\s|님|씨|[,.]|$)'
        korean_names = re.findall(korean_name_pattern, content)
        
        # '님'으로 끝나는 한글 이름 패턴 (3-5글자: 이름2-4글자 + 님)
        korean_name_nim_pattern = r'[가-힣]{2,4}님(?=\s|[,.]|$)'
        korean_names_nim = re.findall(korean_name_nim_pattern, content)
        
        candidates.update(korean_names)
        candidates.update(korean_names_nim)
        
        # 이메일에서 한글 이름만 추출 (한글이 포함된 경우만)
        email_pattern = r'([가-힣]{2,4})@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        email_matches = re.findall(email_pattern, content)
        candidates.update(email_matches)
        
        # 영문 이름은 제외 (한글 이름만 허용)
        
        # 일반적이지 않은 단어들 필터링 및 이름 정리
        filtered_candidates = set()
        excluded_words = {
            '개발', '관리', '프로젝트', '문서', '페이지', '시스템', '회사', '부서', 
            '팀장', '대리', '과장', '부장', '이사', '사장', '대표', '차장', '주임',
            '센터', '사업부', '본부', '그룹', '계획', '업무', '담당', '책임'
        }
        
        for candidate in candidates:
            # '님' 제거 처리
            clean_name = candidate.rstrip('님') if candidate.endswith('님') else candidate
            
            # 한글 2-4자 이름만 허용
            if (re.match(r'^[가-힣]{2,4}$', clean_name) and 
                clean_name not in excluded_words and
                not clean_name.isdigit()):
                filtered_candidates.add(clean_name)
        
        filtered_candidates = list(filtered_candidates)
        
        return filtered_candidates[:20]  # 최대 20개로 제한
    
    def _create_person_extraction_prompt(self, content: str, page_title: str, candidates: List[str]) -> str:
        """인물 추출용 프롬프트 생성"""
        prompt = f"""다음 Confluence 문서에서 언급된 실제 인물들의 정보를 JSON 형식으로 추출해주세요.

문서 제목: {page_title}

문서 내용:
{content}

후보 인물명: {', '.join(candidates)}

다음 조건을 만족하는 실제 인물만 추출해주세요:
1. 실명으로 언급된 사람 (가명이나 역할명 제외)
2. 구체적인 맥락이 있는 경우
3. 조직 내 구성원으로 보이는 경우

추출할 정보:
- name: 인물 이름 (필수)
- department: 부서/팀 정보 (있는 경우)
- role: 역할/직책 (있는 경우)
- email: 이메일 주소 (있는 경우)
- mentioned_context: 언급된 구체적 문맥 (50자 이내)
- confidence: 신뢰도 (0.0-1.0, 확실한 경우 0.8 이상)

JSON 형식으로만 응답해주세요:
{{
  "persons": [
    {{
      "name": "홍길동",
      "department": "개발팀",
      "role": "팀장",
      "email": "hong@company.com",
      "mentioned_context": "프로젝트 승인 담당",
      "confidence": 0.95
    }}
  ]
}}"""
        return prompt

    def _extract_json_from_response(self, response: str) -> str:
        """응답에서 JSON 부분만 추출"""
        # ```json으로 감싸진 경우 처리
        if '```json' in response:
            start = response.find('```json') + 7
            end = response.find('```', start)
            if end != -1:
                return response[start:end].strip()
        
        # JSON 객체 부분만 추출 시도
        response = response.strip()
        start = response.find('{')
        if start != -1:
            # 마지막 }까지 찾기
            brace_count = 0
            for i, char in enumerate(response[start:], start):
                if char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        return response[start:i+1]
        
        return response

class OpenAIService(LLMService):
    def __init__(self, api_key: str = None, model_name: str = None):
        self.api_key = api_key or config.OPENAI_API_KEY
        self.model_name = model_name or config.OPENAI_MODEL
        
        if not self.api_key:
            raise ValueError("OpenAI API 키가 설정되지 않았습니다.")
        
        try:
            from langchain_openai import ChatOpenAI
            self.client = ChatOpenAI(
                api_key=self.api_key,
                model_name=self.model_name
            )
        except ImportError:
            logger.error("langchain-openai 패키지가 설치되지 않았습니다.")
            raise ImportError("langchain-openai 패키지를 설치해주세요: pip install langchain-openai")
    
    def summarize(self, content: str) -> str:
        """페이지 내용 요약 생성"""
        try:
            prompt = config.SUMMARY_PROMPT.format(content=content)
            response = self.client.invoke(prompt)
            return response.content
        except Exception as e:
            logger.error(f"OpenAI 요약 생성 오류: {str(e)}")
            return "요약 생성 중 오류가 발생했습니다."
    
    def extract_keywords(self, content: str) -> List[str]:
        """키워드 추출"""
        try:
            prompt = config.KEYWORDS_PROMPT.format(content=content)
            response = self.client.invoke(prompt)
            
            # 응답에서 키워드 추출 (쉼표로 구분)
            keywords = [keyword.strip() for keyword in response.content.split(',')]
            keywords = [k for k in keywords if k]  # 빈 문자열 제거
            
            return keywords[:10]  # 최대 10개로 제한
        except Exception as e:
            logger.error(f"OpenAI 키워드 추출 오류: {str(e)}")
            return []
    
    def extract_persons(self, content: str, page_title: str = "") -> PersonExtractionResult:
        """Confluence 문서에서 인물 정보 추출"""
        try:
            # 정규표현식으로 후보 이름 패턴 찾기  
            potential_names = self._extract_name_candidates(content)
            
            # LLM으로 인물 정보 추출 및 검증
            person_prompt = self._create_person_extraction_prompt(content, page_title, potential_names)
            response = self.client.invoke(person_prompt)
            
            # JSON 응답 파싱
            try:
                # 응답에서 JSON 부분만 추출 (```json으로 감싸진 경우 처리)
                json_response = self._extract_json_from_response(response.content)
                parsed_data = json.loads(json_response)
                persons = []
                
                for person_data in parsed_data.get('persons', []):
                    person = ExtractedPerson(
                        name=person_data.get('name', ''),
                        department=person_data.get('department'),
                        role=person_data.get('role'),
                        email=person_data.get('email'),
                        mentioned_context=person_data.get('mentioned_context'),
                        confidence=person_data.get('confidence', 0.0)
                    )
                    if person.name and person.confidence > 0.3:  # 최소 신뢰도 필터
                        persons.append(person)
                
                return PersonExtractionResult(persons=persons)
                
            except (json.JSONDecodeError, ValueError) as e:
                logger.warning(f"LLM 응답 JSON 파싱 실패: {str(e)[:100]}...")
                return PersonExtractionResult(persons=[])
                
        except Exception as e:
            logger.error(f"인물 정보 추출 오류: {str(e)}")
            return PersonExtractionResult(persons=[])
    
    def _extract_name_candidates(self, content: str) -> List[str]:
        """정규표현식으로 후보 이름 패턴 추출"""
        candidates = set()
        
        # 한글 이름 패턴 (2-4글자 또는 님으로 끝나는 것)
        korean_name_pattern = r'[가-힣]{2,4}(?=\s|님|씨|[,.]|$)'
        korean_names = re.findall(korean_name_pattern, content)
        
        # '님'으로 끝나는 한글 이름 패턴 (3-5글자: 이름2-4글자 + 님)
        korean_name_nim_pattern = r'[가-힣]{2,4}님(?=\s|[,.]|$)'
        korean_names_nim = re.findall(korean_name_nim_pattern, content)
        
        candidates.update(korean_names)
        candidates.update(korean_names_nim)
        
        # 이메일에서 한글 이름만 추출 (한글이 포함된 경우만)
        email_pattern = r'([가-힣]{2,4})@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        email_matches = re.findall(email_pattern, content)
        candidates.update(email_matches)
        
        # 영문 이름은 제외 (한글 이름만 허용)
        
        # 일반적이지 않은 단어들 필터링 및 이름 정리
        filtered_candidates = set()
        excluded_words = {
            '개발', '관리', '프로젝트', '문서', '페이지', '시스템', '회사', '부서', 
            '팀장', '대리', '과장', '부장', '이사', '사장', '대표', '차장', '주임',
            '센터', '사업부', '본부', '그룹', '계획', '업무', '담당', '책임'
        }
        
        for candidate in candidates:
            # '님' 제거 처리
            clean_name = candidate.rstrip('님') if candidate.endswith('님') else candidate
            
            # 한글 2-4자 이름만 허용
            if (re.match(r'^[가-힣]{2,4}$', clean_name) and 
                clean_name not in excluded_words and
                not clean_name.isdigit()):
                filtered_candidates.add(clean_name)
        
        filtered_candidates = list(filtered_candidates)
        
        return filtered_candidates[:20]  # 최대 20개로 제한
    
    def _create_person_extraction_prompt(self, content: str, page_title: str, candidates: List[str]) -> str:
        """인물 추출용 프롬프트 생성"""
        prompt = f"""다음 Confluence 문서에서 언급된 실제 인물들의 정보를 JSON 형식으로 추출해주세요.

문서 제목: {page_title}

문서 내용:
{content}

후보 인물명: {', '.join(candidates)}

다음 조건을 만족하는 실제 인물만 추출해주세요:
1. 실명으로 언급된 사람 (가명이나 역할명 제외)
2. 구체적인 맥락이 있는 경우
3. 조직 내 구성원으로 보이는 경우

추출할 정보:
- name: 인물 이름 (필수)
- department: 부서/팀 정보 (있는 경우)
- role: 역할/직책 (있는 경우)
- email: 이메일 주소 (있는 경우)
- mentioned_context: 언급된 구체적 문맥 (50자 이내)
- confidence: 신뢰도 (0.0-1.0, 확실한 경우 0.8 이상)

JSON 형식으로만 응답해주세요:
{{
  "persons": [
    {{
      "name": "홍길동",
      "department": "개발팀",
      "role": "팀장",
      "email": "hong@company.com",
      "mentioned_context": "프로젝트 승인 담당",
      "confidence": 0.95
    }}
  ]
}}"""
        return prompt
    
    def _extract_json_from_response(self, response: str) -> str:
        """응답에서 JSON 부분만 추출"""
        # ```json으로 감싸진 경우 처리
        if '```json' in response:
            start = response.find('```json') + 7
            end = response.find('```', start)
            if end != -1:
                return response[start:end].strip()
        
        # JSON 객체 부분만 추출 시도
        response = response.strip()
        start = response.find('{')
        if start != -1:
            # 마지막 }까지 찾기
            brace_count = 0
            for i, char in enumerate(response[start:], start):
                if char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        return response[start:i+1]
        
        return response

class LLMServiceFactory:
    @staticmethod
    def create_service(service_type: str = "ollama") -> LLMService:
        """LLM 서비스 생성 팩토리"""
        if service_type.lower() == "ollama":
            try:
                return OllamaService()
            except Exception as e:
                logger.warning(f"Ollama 서비스 생성 실패: {str(e)}")
                if config.OPENAI_API_KEY:
                    logger.info("OpenAI 서비스로 대체합니다.")
                    return OpenAIService()
                else:
                    raise Exception("Ollama와 OpenAI 모두 사용할 수 없습니다.")
        
        elif service_type.lower() == "openai":
            return OpenAIService()
        
        else:
            raise ValueError(f"지원하지 않는 서비스 타입: {service_type}")

# 키워드 유사도 계산 함수
def calculate_keyword_similarity(keywords1: List[str], keywords2: List[str]) -> float:
    """키워드 간 유사도 계산 (Jaccard 유사도)"""
    if not keywords1 or not keywords2:
        return 0.0
    
    set1 = set(keywords1)
    set2 = set(keywords2)
    
    intersection = len(set1.intersection(set2))
    union = len(set1.union(set2))
    
    return intersection / union if union > 0 else 0.0

def get_common_keywords(keywords1: List[str], keywords2: List[str]) -> List[str]:
    """공통 키워드 추출"""
    set1 = set(keywords1)
    set2 = set(keywords2)
    
    return list(set1.intersection(set2))

class FallbackService(LLMService):
    """LLM 서비스가 사용 불가능할 때 사용하는 폴백 서비스"""
    
    def summarize(self, content: str) -> str:
        """간단한 텍스트 요약"""
        if not content or len(content.strip()) < 10:
            return "내용이 없습니다."
        
        content = content.strip()
        
        # 문장으로 나누기 (한글과 영문 고려)
        import re
        sentences = re.split(r'[.!?。]\s*', content)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        if not sentences:
            # 문장 구분이 안 되면 길이로 자르기
            if len(content) <= 200:
                return content
            else:
                return content[:200] + "..."
        
        # 첫 2-3문장으로 요약
        summary_sentences = sentences[:min(3, len(sentences))]
        summary = '. '.join(summary_sentences)
        
        # 너무 짧으면 더 추가
        if len(summary) < 100 and len(sentences) > 3:
            summary_sentences = sentences[:min(5, len(sentences))]
            summary = '. '.join(summary_sentences)
        
        # 너무 길면 자르기
        if len(summary) > 500:
            summary = summary[:500] + "..."
        
        return summary if summary else content[:200]
    
    def extract_keywords(self, content: str) -> List[str]:
        """간단한 키워드 추출 (빈도 기반)"""
        if not content:
            return []
            
        import re
        from collections import Counter
        
        # 단어 추출 (한글, 영문, 숫자)
        # 한글은 2자 이상, 영문은 3자 이상
        korean_words = re.findall(r'[가-힣]{2,}', content)
        english_words = re.findall(r'[a-zA-Z]{3,}', content.lower())
        
        all_words = korean_words + english_words
        
        # 불용어 제거
        stop_words = {
            '의', '가', '이', '은', '는', '을', '를', '에', '와', '과', '로', '으로', '에서', '부터', '까지',
            '하고', '하는', '하기', '해서', '하여', '있습니다', '있는', '있었습니다', '때문에', '그리고', '또한',
            'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'the', 'a', 'an',
            'this', 'that', 'these', 'those', 'is', 'are', 'was', 'were', 'be', 'been', 'have', 'has', 'had'
        }
        
        # 불용어 및 너무 짧은 단어 제거
        filtered_words = []
        for word in all_words:
            word_clean = word.strip().lower()
            if word_clean not in stop_words and len(word_clean) > 1:
                filtered_words.append(word_clean)
        
        if not filtered_words:
            return []
        
        # 빈도수 계산 및 상위 키워드 반환
        word_freq = Counter(filtered_words)
        keywords = [word for word, freq in word_freq.most_common(15) if freq > 1]
        
        # 빈도가 1인 것도 포함 (최대 10개까지)
        if len(keywords) < 10:
            additional = [word for word, freq in word_freq.most_common(20) if freq == 1]
            keywords.extend(additional[:10-len(keywords)])
        
        return keywords[:10]

# 기본 LLM 서비스 인스턴스
def initialize_llm_service():
    """LLM 서비스 초기화"""
    try:
        # Ollama 먼저 시도
        service = LLMServiceFactory.create_service("ollama")
        logger.info("Ollama LLM 서비스 초기화 완료")
        return service
    except Exception as e:
        logger.warning(f"Ollama 서비스 초기화 실패: {str(e)}")
        
        try:
            # OpenAI 시도
            if config.OPENAI_API_KEY:
                service = LLMServiceFactory.create_service("openai")
                logger.info("OpenAI LLM 서비스 초기화 완료")
                return service
        except Exception as e:
            logger.warning(f"OpenAI 서비스 초기화 실패: {str(e)}")
        
        # 모든 LLM 서비스 실패 시 폴백 서비스 사용
        logger.warning("모든 LLM 서비스 실패, 폴백 서비스 사용")
        return FallbackService()

llm_service = initialize_llm_service()