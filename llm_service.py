from abc import ABC, abstractmethod
from typing import List, Optional
import logging
import json
import re
from config import config

logger = logging.getLogger(__name__)

class LLMService(ABC):
    @abstractmethod
    def summarize(self, content: str) -> str:
        pass
    
    @abstractmethod
    def extract_keywords(self, content: str) -> List[str]:
        pass

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
                    'temperature': 0.7,
                    'num_predict': 200  # 응답 길이 제한
                }
            )
            return response['message']['content']
        except Exception as e:
            logger.error(f"Ollama API 호출 오류: {str(e)}")
            raise e
    
    def summarize(self, content: str) -> str:
        """페이지 내용 요약 생성"""
        try:
            prompt = config.SUMMARY_PROMPT.format(content=content[:4000])  # 토큰 제한
            return self._call_ollama(prompt)
        except Exception as e:
            logger.error(f"요약 생성 오류: {str(e)}")
            return "요약 생성 중 오류가 발생했습니다."
    
    def extract_keywords(self, content: str) -> List[str]:
        """키워드 추출"""
        try:
            prompt = config.KEYWORDS_PROMPT.format(content=content[:4000])
            response = self._call_ollama(prompt)
            
            # 응답에서 키워드 추출 (쉼표로 구분)
            keywords = [keyword.strip() for keyword in response.split(',')]
            keywords = [k for k in keywords if k]  # 빈 문자열 제거
            
            return keywords[:10]  # 최대 10개로 제한
        except Exception as e:
            logger.error(f"키워드 추출 오류: {str(e)}")
            return []

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
            prompt = config.SUMMARY_PROMPT.format(content=content[:4000])
            response = self.client.invoke(prompt)
            return response.content
        except Exception as e:
            logger.error(f"OpenAI 요약 생성 오류: {str(e)}")
            return "요약 생성 중 오류가 발생했습니다."
    
    def extract_keywords(self, content: str) -> List[str]:
        """키워드 추출"""
        try:
            prompt = config.KEYWORDS_PROMPT.format(content=content[:4000])
            response = self.client.invoke(prompt)
            
            # 응답에서 키워드 추출 (쉼표로 구분)
            keywords = [keyword.strip() for keyword in response.content.split(',')]
            keywords = [k for k in keywords if k]  # 빈 문자열 제거
            
            return keywords[:10]  # 최대 10개로 제한
        except Exception as e:
            logger.error(f"OpenAI 키워드 추출 오류: {str(e)}")
            return []

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