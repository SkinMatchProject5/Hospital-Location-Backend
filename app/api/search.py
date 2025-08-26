"""
Hospital-Location-Backend 검색 API
AI 진단 결과 기반 병원 검색 엔드포인트
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any, Optional
import logging

from app.models.requests import SearchRequest
from app.models.responses import SearchResponse
from app.services.search_service import SearchService, get_search_service

router = APIRouter(prefix="/search", tags=["search"])
logger = logging.getLogger(__name__)


@router.post("/search-ft-xml", response_model=SearchResponse)
async def search_hospitals_by_xml(
    request: SearchRequest,
    search_service: SearchService = Depends(get_search_service)
) -> SearchResponse:
    """
    AI 분석 백엔드에서 전송된 XML 진단명을 기반으로 병원 검색
    
    Args:
        request: XML 진단명이 포함된 검색 요청
        search_service: 검색 서비스 의존성
    
    Returns:
        SearchResponse: 검색된 병원 목록 (name, tell, addr, url)
    """
    try:
        logger.info(f"🔍 병원 검색 요청 수신")
        logger.debug(f"XML 데이터: {request.xml[:200]}...")  # 처음 200자만 로깅
        
        # XML 파싱 및 병원 검색 수행
        search_result = await search_service.search_hospitals_from_xml(
            xml_data=request.xml,
            top_k=request.top_k,
            final_k=request.final_k,
            rerank_mode=request.rerank_mode
        )
        
        logger.info(f"✅ 병원 검색 완료: {len(search_result.results)}개 병원")
        
        return search_result
        
    except ValueError as e:
        logger.error(f"❌ XML 파싱 오류: {e}")
        raise HTTPException(status_code=400, detail=f"XML 파싱 실패: {e}")
        
    except Exception as e:
        logger.error(f"❌ 병원 검색 실패: {e}")
        raise HTTPException(status_code=500, detail=f"병원 검색 중 오류 발생: {e}")


@router.get("/health")
async def search_health_check():
    """검색 서비스 헬스 체크"""
    return {
        "status": "healthy",
        "service": "hospital-search",
        "timestamp": "2024-01-01T00:00:00Z"
    }
