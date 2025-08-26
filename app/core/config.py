"""
Hospital-Location-Backend 설정 관리
환경변수 기반 설정 시스템
"""

import os
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """애플리케이션 설정"""
    
    # =================================================================
    # OpenAI API 설정
    # =================================================================
    OPENAI_API_KEY: str = Field(..., description="OpenAI API 키")
    
    # =================================================================
    # Qdrant 벡터 데이터베이스 설정
    # =================================================================
    QDRANT_URL: str = Field(..., description="Qdrant 서버 URL")
    QDRANT_API_KEY: Optional[str] = Field(None, description="Qdrant API 키")
    
    # =================================================================
    # 벡터 컬렉션 설정
    # =================================================================
    CHILDREN_COLLECTION: str = Field(default="derm_children", description="자식 컬렉션명")
    PARENTS_COLLECTION: str = Field(default="derm_parents", description="부모 컬렉션명")
    
    # =================================================================
    # 임베딩 모델 설정
    # =================================================================
    EMBEDDING_MODEL: str = Field(default="text-embedding-3-small", description="임베딩 모델명")
    EMBEDDING_DIMENSION: int = Field(default=1536, description="임베딩 차원")
    
    # =================================================================
    # 하이브리드 검색 파라미터
    # =================================================================
    DEFAULT_TOP_K: int = Field(default=24, description="초기 후보 검색 개수")
    DEFAULT_FINAL_K: int = Field(default=2, description="최종 결과 반환 개수")
    BM25_WEIGHT: float = Field(default=0.5, description="BM25 가중치")
    COSINE_WEIGHT: float = Field(default=0.5, description="코사인 유사도 가중치")
    
    # =================================================================
    # API 서버 설정
    # =================================================================
    HOST: str = Field(default="0.0.0.0", description="서버 호스트")
    PORT: int = Field(default=8002, description="서버 포트")
    DEBUG: bool = Field(default=False, description="디버그 모드")
    
    # =================================================================
    # 로깅 설정
    # =================================================================
    LOG_LEVEL: str = Field(default="INFO", description="로그 레벨")
    LOG_FILE: str = Field(default="logs/hospital_backend.log", description="로그 파일 경로")
    
    # =================================================================
    # 성능 최적화 설정
    # =================================================================
    REQUEST_TIMEOUT: int = Field(default=30, description="요청 타임아웃 (초)")
    MAX_CONCURRENT_REQUESTS: int = Field(default=100, description="최대 동시 요청 수")
    CACHE_TTL: int = Field(default=3600, description="캐시 TTL (초)")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        
    def __post_init__(self):
        """설정 후처리"""
        # BM25와 코사인 가중치 합이 1.0이 되도록 조정
        if self.BM25_WEIGHT + self.COSINE_WEIGHT != 1.0:
            self.COSINE_WEIGHT = 1.0 - self.BM25_WEIGHT


# 글로벌 설정 인스턴스
settings = Settings()
