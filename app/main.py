"""
Hospital-Location-Backend 메인 애플리케이션
AI 진단 결과 기반 병원 검색 시스템
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from app.core.config import settings
from app.core.logging import setup_logging
from app.api import search_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """애플리케이션 생명주기 관리"""
    # 시작 시 초기화
    setup_logging()
    logger = logging.getLogger(__name__)
    logger.info("🏥 Hospital-Location-Backend 시작")
    logger.info(f"   포트: {settings.PORT}")
    logger.info(f"   벡터DB: {settings.QDRANT_URL}")
    logger.info(f"   임베딩 모델: {settings.EMBEDDING_MODEL}")
    
    # 검색 서비스 초기화
    try:
        from app.services import get_search_service
        search_service = get_search_service()
        await search_service.initialize()
        logger.info("✅ 검색 서비스 초기화 완료")
    except Exception as e:
        logger.error(f"❌ 검색 서비스 초기화 실패: {e}")
        # 초기화 실패해도 서버는 시작 (연결 문제일 수 있음)
    
    yield
    
    # 종료 시 정리
    logger.info("🏥 Hospital-Location-Backend 종료")


# FastAPI 애플리케이션 생성
app = FastAPI(
    title="Hospital-Location-Backend",
    description="AI 진단 결과 기반 병원 검색 시스템",
    version="1.0.0",
    lifespan=lifespan
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 프로덕션에서는 구체적인 도메인 지정
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(search_router, prefix="/api/v1")


@app.get("/")
async def root():
    """루트 엔드포인트"""
    return {
        "service": "Hospital-Location-Backend",
        "version": "1.0.0",
        "status": "running",
        "description": "AI 진단 결과 기반 병원 검색 시스템"
    }


@app.get("/health")
async def health_check():
    """헬스 체크 엔드포인트"""
    return {
        "status": "healthy",
        "service": "Hospital-Location-Backend",
        "timestamp": "2024-01-01T00:00:00Z"
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    )
