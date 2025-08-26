"""
Hospital-Location-Backend API 모듈
RESTful API 엔드포인트 정의
"""

from app.api.search import router as search_router

__all__ = ["search_router"]
