"""
글로벌 예외 핸들러들
"""
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.exception_handlers import (
    http_exception_handler,
    request_validation_exception_handler,
)
from starlette.exceptions import HTTPException as StarletteHTTPException
import traceback
from typing import Union

from logging_config import get_logger
from exceptions import ConfluenceAutoBaseException

# 로거 인스턴스
logger = get_logger("exception_handlers")


async def confluence_auto_exception_handler(
    request: Request, 
    exc: ConfluenceAutoBaseException
) -> JSONResponse:
    """Confluence Auto 커스텀 예외 핸들러"""
    logger.error(
        f"커스텀 예외 발생: {exc.__class__.__name__}",
        extra_data={
            "exception_type": exc.__class__.__name__,
            "message": exc.message,
            "details": exc.details,
            "request_url": str(request.url),
            "request_method": request.method
        }
    )
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error_type": exc.__class__.__name__,
            "message": exc.message,
            "details": exc.details,
            "timestamp": logger.context.get("timestamp", ""),
        }
    )


async def custom_http_exception_handler(
    request: Request, 
    exc: Union[HTTPException, StarletteHTTPException]
) -> JSONResponse:
    """커스텀 HTTP 예외 핸들러"""
    # 요청 정보 로깅
    request_info = {
        "url": str(request.url),
        "method": request.method,
        "headers": dict(request.headers),
        "status_code": exc.status_code
    }
    
    # 에러 레벨에 따른 로깅
    if exc.status_code >= 500:
        logger.error(
            f"서버 에러 발생: {exc.status_code}",
            extra_data={
                "status_code": exc.status_code,
                "detail": exc.detail,
                "request_info": request_info
            }
        )
    elif exc.status_code >= 400:
        logger.warning(
            f"클라이언트 에러 발생: {exc.status_code}",
            extra_data={
                "status_code": exc.status_code,
                "detail": exc.detail,
                "request_info": request_info
            }
        )
    
    # 기본 HTTP 예외 핸들러 호출
    return await http_exception_handler(request, exc)


async def custom_validation_exception_handler(
    request: Request, 
    exc: RequestValidationError
) -> JSONResponse:
    """커스텀 입력 검증 예외 핸들러"""
    # 요청 본문 읽기 시도
    body = None
    try:
        body = await request.body()
        if body:
            body = body.decode('utf-8')
    except Exception:
        body = None
    
    # 검증 에러 상세 로깅
    logger.warning(
        "입력 검증 실패",
        extra_data={
            "validation_errors": exc.errors(),
            "request_body": body,
            "request_url": str(request.url),
            "request_method": request.method,
            "content_type": request.headers.get("content-type")
        }
    )
    
    # 기본 검증 예외 핸들러 호출하되, 추가 정보 포함
    response = await request_validation_exception_handler(request, exc)
    
    # 응답 내용 수정
    if hasattr(response, 'body'):
        import json
        try:
            content = json.loads(response.body.decode())
            content['timestamp'] = logger.context.get("timestamp", "")
            content['request_id'] = getattr(request.state, 'request_id', None)
            
            return JSONResponse(
                status_code=response.status_code,
                content=content
            )
        except Exception:
            pass
    
    return response


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """일반적인 예외에 대한 핸들러"""
    # 예외 정보 상세 로깅
    logger.exception(
        f"예상치 못한 예외 발생: {exc.__class__.__name__}",
        extra_data={
            "exception_type": exc.__class__.__name__,
            "exception_message": str(exc),
            "request_url": str(request.url),
            "request_method": request.method,
            "traceback": traceback.format_exc()
        }
    )
    
    # 프로덕션 환경에서는 내부 에러 정보를 숨김
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error_type": "InternalServerError",
            "message": "내부 서버 오류가 발생했습니다. 잠시 후 다시 시도해주세요.",
            "timestamp": logger.context.get("timestamp", ""),
            "request_id": getattr(request.state, 'request_id', None)
        }
    )


async def method_not_allowed_handler(request: Request, exc: Exception) -> JSONResponse:
    """허용되지 않은 HTTP 메서드 핸들러"""
    logger.warning(
        f"허용되지 않은 메서드 호출: {request.method}",
        extra_data={
            "method": request.method,
            "url": str(request.url),
            "allowed_methods": getattr(exc, 'allowed_methods', [])
        }
    )
    
    return JSONResponse(
        status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
        content={
            "error_type": "MethodNotAllowed",
            "message": f"HTTP 메서드 '{request.method}'는 이 엔드포인트에서 허용되지 않습니다.",
            "allowed_methods": getattr(exc, 'allowed_methods', [])
        }
    )


async def not_found_handler(request: Request, exc: Exception) -> JSONResponse:
    """404 Not Found 핸들러"""
    logger.info(
        f"존재하지 않는 경로 접근: {request.url.path}",
        extra_data={
            "path": request.url.path,
            "method": request.method,
            "query_params": dict(request.query_params)
        }
    )
    
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={
            "error_type": "NotFound",
            "message": f"경로 '{request.url.path}'를 찾을 수 없습니다.",
            "path": request.url.path
        }
    )