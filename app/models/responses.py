"""
Hospital-Location-Backend 응답 모델
API 응답 데이터 구조 정의
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime


class HospitalInfo(BaseModel):
    """병원 정보 모델 (프론트엔드 요구 형식)"""
    
    name: str = Field(
        ...,
        description="병원명",
        min_length=1
    )
    
    tell: Optional[str] = Field(
        default=None,
        description="병원 전화번호"
    )
    
    addr: Optional[str] = Field(
        default=None,
        description="병원 주소"
    )
    
    url: Optional[str] = Field(
        default=None,
        description="병원 웹사이트 URL"
    )
    
    # 검색 관련 메타데이터 (선택사항)
    score: Optional[float] = Field(
        default=None,
        description="검색 유사도 점수"
    )
    
    distance: Optional[str] = Field(
        default=None,
        description="거리 정보"
    )
    
    specialties: Optional[List[str]] = Field(
        default=None,
        description="병원 전문 진료 분야 및 다루는 질환"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "서울대학교병원 피부과",
                "tell": "02-2072-2114",
                "addr": "서울특별시 종로구 대학로 101",
                "url": "https://www.snuh.org",
                "score": 0.89,
                "distance": "2.3km"
            }
        }


class SearchResponse(BaseModel):
    """병원 검색 응답 모델"""
    
    results: List[HospitalInfo] = Field(
        ...,
        description="검색된 병원 목록"
    )
    
    meta: Dict[str, Any] = Field(
        default_factory=dict,
        description="검색 메타데이터"
    )
    
    query_info: Optional[Dict[str, Any]] = Field(
        default=None,
        description="쿼리 정보"
    )
    
    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="응답 생성 시간"
    )
    
    total_count: int = Field(
        default=0,
        description="총 검색 결과 수"
    )
    
    search_time_ms: Optional[float] = Field(
        default=None,
        description="검색 소요 시간 (밀리초)"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "results": [
                    {
                        "name": "서울대학교병원 피부과",
                        "tell": "02-2072-2114", 
                        "addr": "서울특별시 종로구 대학로 101",
                        "url": "https://www.snuh.org",
                        "score": 0.89
                    },
                    {
                        "name": "연세대학교 세브란스병원 피부과",
                        "tell": "02-2228-5114",
                        "addr": "서울특별시 서대문구 연세로 50-1", 
                        "url": "https://www.severance.healthcare",
                        "score": 0.82
                    }
                ],
                "meta": {
                    "embedding_model": "text-embedding-3-small",
                    "search_strategy": "hybrid_cosine_bm25"
                },
                "query_info": {
                    "diagnosis": "광선각화증",
                    "similar_conditions": ["보웬병", "기저세포암"]
                },
                "total_count": 2,
                "search_time_ms": 245.6
            }
        }
