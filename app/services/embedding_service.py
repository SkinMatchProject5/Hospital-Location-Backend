"""
Hospital-Location-Backend 임베딩 서비스
OpenAI text-embedding-3-small을 사용한 텍스트 임베딩 생성
"""

import asyncio
import logging
from typing import List, Optional, Dict, Any
from openai import AsyncOpenAI
import numpy as np

from app.core.config import settings

logger = logging.getLogger(__name__)


class EmbeddingServiceError(Exception):
    """임베딩 서비스 오류"""
    pass


class EmbeddingService:
    """OpenAI 임베딩 서비스"""
    
    def __init__(self):
        """임베딩 서비스 초기화"""
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = settings.EMBEDDING_MODEL
        self.dimension = settings.EMBEDDING_DIMENSION
        
        logger.info(f"🔧 임베딩 서비스 초기화: {self.model} (차원: {self.dimension})")
    
    async def embed_text(self, text: str) -> List[float]:
        """
        단일 텍스트를 임베딩으로 변환
        
        Args:
            text: 임베딩할 텍스트
            
        Returns:
            List[float]: 임베딩 벡터
            
        Raises:
            EmbeddingServiceError: 임베딩 생성 실패 시
        """
        if not text or not text.strip():
            raise EmbeddingServiceError("빈 텍스트는 임베딩할 수 없습니다")
        
        try:
            logger.debug(f"텍스트 임베딩 요청: {text[:50]}...")
            
            response = await self.client.embeddings.create(
                model=self.model,
                input=text.strip(),
                encoding_format="float"
            )
            
            embedding = response.data[0].embedding
            
            # 차원 검증
            if len(embedding) != self.dimension:
                logger.warning(f"예상 차원({self.dimension})과 다름: {len(embedding)}")
            
            logger.debug(f"✅ 임베딩 생성 완료: {len(embedding)}차원")
            return embedding
            
        except Exception as e:
            logger.error(f"❌ 임베딩 생성 실패: {e}")
            raise EmbeddingServiceError(f"임베딩 생성 실패: {e}")
    
    async def embed_batch(self, texts: List[str], batch_size: int = 100) -> List[List[float]]:
        """
        여러 텍스트를 배치로 임베딩 생성
        
        Args:
            texts: 임베딩할 텍스트 목록
            batch_size: 배치 크기
            
        Returns:
            List[List[float]]: 임베딩 벡터 목록
        """
        if not texts:
            return []
        
        # 빈 텍스트 필터링
        valid_texts = [text.strip() for text in texts if text and text.strip()]
        if not valid_texts:
            raise EmbeddingServiceError("유효한 텍스트가 없습니다")
        
        logger.info(f"🔄 배치 임베딩 시작: {len(valid_texts)}개 텍스트")
        
        embeddings = []
        
        # 배치 단위로 처리
        for i in range(0, len(valid_texts), batch_size):
            batch = valid_texts[i:i + batch_size]
            
            try:
                logger.debug(f"배치 {i//batch_size + 1} 처리 중: {len(batch)}개")
                
                response = await self.client.embeddings.create(
                    model=self.model,
                    input=batch,
                    encoding_format="float"
                )
                
                batch_embeddings = [data.embedding for data in response.data]
                embeddings.extend(batch_embeddings)
                
                logger.debug(f"✅ 배치 {i//batch_size + 1} 완료")
                
                # API 레이트 제한 방지를 위한 짧은 대기
                if i + batch_size < len(valid_texts):
                    await asyncio.sleep(0.1)
                
            except Exception as e:
                logger.error(f"❌ 배치 {i//batch_size + 1} 실패: {e}")
                raise EmbeddingServiceError(f"배치 임베딩 실패: {e}")
        
        logger.info(f"✅ 배치 임베딩 완료: {len(embeddings)}개")
        return embeddings
    
    def cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """
        두 벡터 간의 코사인 유사도 계산
        
        Args:
            vec1, vec2: 비교할 벡터들
            
        Returns:
            float: 코사인 유사도 (-1 ~ 1)
        """
        try:
            # numpy 배열로 변환
            a = np.array(vec1)
            b = np.array(vec2)
            
            # 코사인 유사도 계산
            dot_product = np.dot(a, b)
            norm_a = np.linalg.norm(a)
            norm_b = np.linalg.norm(b)
            
            if norm_a == 0 or norm_b == 0:
                return 0.0
            
            similarity = dot_product / (norm_a * norm_b)
            
            # -1 ~ 1 범위로 클리핑
            return float(np.clip(similarity, -1.0, 1.0))
            
        except Exception as e:
            logger.error(f"❌ 코사인 유사도 계산 실패: {e}")
            return 0.0
    
    async def get_embedding_stats(self, embeddings: List[List[float]]) -> Dict[str, Any]:
        """임베딩 통계 정보 반환"""
        if not embeddings:
            return {"count": 0}
        
        embeddings_array = np.array(embeddings)
        
        return {
            "count": len(embeddings),
            "dimension": embeddings_array.shape[1] if embeddings_array.ndim > 1 else 0,
            "mean_norm": float(np.mean(np.linalg.norm(embeddings_array, axis=1))),
            "std_norm": float(np.std(np.linalg.norm(embeddings_array, axis=1))),
            "model": self.model
        }


# 글로벌 임베딩 서비스 인스턴스
_embedding_service: Optional[EmbeddingService] = None


def get_embedding_service() -> EmbeddingService:
    """임베딩 서비스 싱글톤 인스턴스 반환"""
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service


# 편의 함수들
async def embed_text(text: str) -> List[float]:
    """텍스트 임베딩 편의 함수"""
    service = get_embedding_service()
    return await service.embed_text(text)


async def embed_diagnosis(diagnosis_text: str, summary: Optional[str] = None) -> List[float]:
    """진단 정보를 임베딩으로 변환하는 편의 함수"""
    # 진단명과 요약을 결합
    combined_text = diagnosis_text
    if summary and summary.strip():
        combined_text += f" {summary.strip()}"
    
    return await embed_text(combined_text)
