"""
Hospital-Location-Backend 로깅 설정
구조화된 로깅 시스템
"""

import os
import sys
import logging
from pathlib import Path
from loguru import logger

from app.core.config import settings


def setup_logging():
    """로깅 시스템 초기화"""
    
    # 로그 디렉토리 생성
    log_dir = Path(settings.LOG_FILE).parent
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # 기본 로거 제거
    logger.remove()
    
    # 콘솔 출력 설정
    logger.add(
        sys.stdout,
        level=settings.LOG_LEVEL,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
               "<level>{level: <8}</level> | "
               "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
               "<level>{message}</level>",
        colorize=True
    )
    
    # 파일 출력 설정
    logger.add(
        settings.LOG_FILE,
        level=settings.LOG_LEVEL,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}",
        rotation="1 day",
        retention="7 days",
        compression="zip",
        encoding="utf-8"
    )
    
    # Python 기본 로깅을 loguru로 라우팅
    class InterceptHandler(logging.Handler):
        def emit(self, record):
            # Get corresponding Loguru level if it exists
            try:
                level = logger.level(record.levelname).name
            except ValueError:
                level = record.levelno
            
            # Find caller from where originated the logged message
            frame, depth = logging.currentframe(), 2
            while frame.f_code.co_filename == logging.__file__:
                frame = frame.f_back
                depth += 1
            
            logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())
    
    # Python 기본 로거 설정
    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)
    
    logger.info("🔧 로깅 시스템 초기화 완료")
    logger.info(f"   로그 레벨: {settings.LOG_LEVEL}")
    logger.info(f"   로그 파일: {settings.LOG_FILE}")


# 서비스별 로거 생성 함수
def get_logger(name: str) -> logging.Logger:
    """서비스별 로거 반환"""
    return logging.getLogger(name)
