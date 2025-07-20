"""
커스텀 예외 클래스들과 에러 처리 유틸리티
"""
from typing import Optional, Dict, Any
from fastapi import HTTPException, status


class ConfluenceAutoBaseException(Exception):
    """Confluence Auto 시스템의 기본 예외 클래스"""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class ConfluenceConnectionError(ConfluenceAutoBaseException):
    """Confluence 연결 관련 예외"""
    pass


class ConfluenceAPIError(ConfluenceAutoBaseException):
    """Confluence API 호출 관련 예외"""
    pass


class LLMServiceError(ConfluenceAutoBaseException):
    """LLM 서비스 관련 예외"""
    pass


class DatabaseError(ConfluenceAutoBaseException):
    """데이터베이스 관련 예외"""
    pass


class PageProcessingError(ConfluenceAutoBaseException):
    """페이지 처리 관련 예외"""
    pass


class MindmapGenerationError(ConfluenceAutoBaseException):
    """마인드맵 생성 관련 예외"""
    pass


class ContentAnalysisError(ConfluenceAutoBaseException):
    """콘텐츠 분석 관련 예외"""
    pass


# HTTP 예외 팩토리 함수들
def raise_confluence_connection_error(message: str, details: Optional[Dict[str, Any]] = None):
    """Confluence 연결 에러 발생"""
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail={
            "error_type": "ConfluenceConnectionError",
            "message": message,
            "details": details or {}
        }
    )


def raise_confluence_api_error(message: str, details: Optional[Dict[str, Any]] = None):
    """Confluence API 에러 발생"""
    raise HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail={
            "error_type": "ConfluenceAPIError", 
            "message": message,
            "details": details or {}
        }
    )


def raise_llm_service_error(message: str, details: Optional[Dict[str, Any]] = None):
    """LLM 서비스 에러 발생"""
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail={
            "error_type": "LLMServiceError",
            "message": message,
            "details": details or {}
        }
    )


def raise_database_error(message: str, details: Optional[Dict[str, Any]] = None):
    """데이터베이스 에러 발생"""
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail={
            "error_type": "DatabaseError",
            "message": message,
            "details": details or {}
        }
    )


def raise_page_processing_error(message: str, details: Optional[Dict[str, Any]] = None):
    """페이지 처리 에러 발생"""
    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail={
            "error_type": "PageProcessingError",
            "message": message,
            "details": details or {}
        }
    )


def raise_mindmap_generation_error(message: str, details: Optional[Dict[str, Any]] = None):
    """마인드맵 생성 에러 발생"""
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail={
            "error_type": "MindmapGenerationError",
            "message": message,
            "details": details or {}
        }
    )


def raise_content_analysis_error(message: str, details: Optional[Dict[str, Any]] = None):
    """콘텐츠 분석 에러 발생"""
    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail={
            "error_type": "ContentAnalysisError",
            "message": message,
            "details": details or {}
        }
    )


def raise_validation_error(message: str, field: str, value: Any = None):
    """입력 검증 에러 발생"""
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail={
            "error_type": "ValidationError",
            "message": message,
            "field": field,
            "value": value
        }
    )


def raise_not_found_error(resource: str, identifier: str):
    """리소스 찾기 실패 에러 발생"""
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={
            "error_type": "NotFoundError", 
            "message": f"{resource}을(를) 찾을 수 없습니다",
            "resource": resource,
            "identifier": identifier
        }
    )


def raise_unauthorized_error(message: str = "인증이 필요합니다"):
    """인증 에러 발생"""
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={
            "error_type": "UnauthorizedError",
            "message": message
        },
        headers={"WWW-Authenticate": "Bearer"}
    )


def raise_forbidden_error(message: str = "접근 권한이 없습니다"):
    """권한 에러 발생"""
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail={
            "error_type": "ForbiddenError",
            "message": message
        }
    )