"""
구조화된 로깅 설정 및 유틸리티
"""
import logging
import logging.config
import json
import sys
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path


class StructuredFormatter(logging.Formatter):
    """구조화된 JSON 로그 포매터"""
    
    def format(self, record: logging.LogRecord) -> str:
        # 기본 로그 정보
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        
        # 예외 정보 추가
        if record.exc_info:
            log_entry["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "traceback": self.formatException(record.exc_info)
            }
        
        # 추가 컨텍스트 정보
        if hasattr(record, 'extra_data'):
            log_entry["extra"] = record.extra_data
            
        # 특정 로그 레코드 속성들 추가
        context_fields = [
            'request_id', 'user_id', 'session_id', 'page_id', 'task_id',
            'confluence_url', 'operation', 'duration', 'status_code'
        ]
        
        for field in context_fields:
            if hasattr(record, field):
                log_entry[field] = getattr(record, field)
        
        return json.dumps(log_entry, ensure_ascii=False, default=str)


class ContextualLogger:
    """컨텍스트 정보를 포함하는 로거 래퍼"""
    
    def __init__(self, name: str, context: Optional[Dict[str, Any]] = None):
        self.logger = logging.getLogger(name)
        self.context = context or {}
    
    def _log_with_context(self, level: int, message: str, extra_data: Optional[Dict[str, Any]] = None, **kwargs):
        """컨텍스트 정보와 함께 로그 출력"""
        # 컨텍스트와 추가 데이터 병합
        merged_context = {**self.context}
        if extra_data:
            merged_context.update(extra_data)
        
        # 로그 레코드에 컨텍스트 추가
        extra = {**kwargs}
        for key, value in merged_context.items():
            extra[key] = value
        
        if merged_context:
            extra['extra_data'] = merged_context
            
        self.logger.log(level, message, extra=extra)
    
    def debug(self, message: str, extra_data: Optional[Dict[str, Any]] = None, **kwargs):
        self._log_with_context(logging.DEBUG, message, extra_data, **kwargs)
    
    def info(self, message: str, extra_data: Optional[Dict[str, Any]] = None, **kwargs):
        self._log_with_context(logging.INFO, message, extra_data, **kwargs)
    
    def warning(self, message: str, extra_data: Optional[Dict[str, Any]] = None, **kwargs):
        self._log_with_context(logging.WARNING, message, extra_data, **kwargs)
    
    def error(self, message: str, extra_data: Optional[Dict[str, Any]] = None, **kwargs):
        self._log_with_context(logging.ERROR, message, extra_data, **kwargs)
    
    def critical(self, message: str, extra_data: Optional[Dict[str, Any]] = None, **kwargs):
        self._log_with_context(logging.CRITICAL, message, extra_data, **kwargs)
    
    def exception(self, message: str, extra_data: Optional[Dict[str, Any]] = None, **kwargs):
        """예외 정보와 함께 에러 로그 출력"""
        kwargs['exc_info'] = True
        self._log_with_context(logging.ERROR, message, extra_data, **kwargs)
    
    def with_context(self, **context) -> 'ContextualLogger':
        """새로운 컨텍스트로 로거 복사"""
        new_context = {**self.context, **context}
        return ContextualLogger(self.logger.name, new_context)


# 로깅 설정
LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "structured": {
            "()": StructuredFormatter,
        },
        "simple": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "level": "INFO",
            "formatter": "structured",
            "stream": sys.stdout
        },
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "level": "DEBUG", 
            "formatter": "structured",
            "filename": "logs/app.log",
            "maxBytes": 10485760,  # 10MB
            "backupCount": 5,
            "encoding": "utf-8"
        },
        "error_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "level": "ERROR",
            "formatter": "structured", 
            "filename": "logs/error.log",
            "maxBytes": 10485760,  # 10MB
            "backupCount": 5,
            "encoding": "utf-8"
        }
    },
    "loggers": {
        "confluence_auto": {
            "level": "DEBUG",
            "handlers": ["console", "file", "error_file"],
            "propagate": False
        },
        "uvicorn": {
            "level": "INFO",
            "handlers": ["console", "file"],
            "propagate": False
        },
        "fastapi": {
            "level": "INFO", 
            "handlers": ["console", "file"],
            "propagate": False
        }
    },
    "root": {
        "level": "INFO",
        "handlers": ["console", "file"]
    }
}


def setup_logging(log_level: str = "INFO", log_dir: str = "logs"):
    """로깅 시스템 초기화"""
    # 로그 디렉토리 생성
    Path(log_dir).mkdir(exist_ok=True)
    
    # 로그 레벨 설정
    if log_level.upper() in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
        LOGGING_CONFIG["handlers"]["console"]["level"] = log_level.upper()
        LOGGING_CONFIG["loggers"]["confluence_auto"]["level"] = log_level.upper()
    
    # 로깅 설정 적용
    logging.config.dictConfig(LOGGING_CONFIG)


def get_logger(name: str, context: Optional[Dict[str, Any]] = None) -> ContextualLogger:
    """컨텍스트 로거 인스턴스 생성"""
    full_name = f"confluence_auto.{name}" if not name.startswith("confluence_auto") else name
    return ContextualLogger(full_name, context)


# 성능 로깅을 위한 데코레이터
import functools
import time
from typing import Callable


def log_execution_time(logger: ContextualLogger):
    """함수 실행 시간을 로깅하는 데코레이터"""
    def decorator(func: Callable):
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start_time
                logger.info(
                    f"함수 '{func.__name__}' 실행 완료",
                    extra_data={
                        "function": func.__name__,
                        "duration": round(duration, 3),
                        "status": "success"
                    }
                )
                return result
            except Exception as e:
                duration = time.time() - start_time
                logger.error(
                    f"함수 '{func.__name__}' 실행 실패",
                    extra_data={
                        "function": func.__name__, 
                        "duration": round(duration, 3),
                        "status": "error",
                        "error": str(e)
                    }
                )
                raise
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                logger.info(
                    f"함수 '{func.__name__}' 실행 완료",
                    extra_data={
                        "function": func.__name__,
                        "duration": round(duration, 3),
                        "status": "success"
                    }
                )
                return result
            except Exception as e:
                duration = time.time() - start_time
                logger.error(
                    f"함수 '{func.__name__}' 실행 실패",
                    extra_data={
                        "function": func.__name__,
                        "duration": round(duration, 3), 
                        "status": "error",
                        "error": str(e)
                    }
                )
                raise
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    return decorator


import asyncio