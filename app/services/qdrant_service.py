"""
Hospital-Location-Backend Qdrant 벡터 데이터베이스 서비스
병원 데이터 벡터 검색 및 관리
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue
from qdrant_client.http.exceptions import ResponseHandlingException

from app.core.config import settings

logger = logging.getLogger(__name__)


class QdrantServiceError(Exception):
    """Qdrant 서비스 오류"""
    pass


class QdrantService:
    """Qdrant 벡터 데이터베이스 서비스"""
    
    def __init__(self):
        """Qdrant 서비스 초기화"""
        self.client = AsyncQdrantClient(
            url=settings.QDRANT_URL,
            api_key=settings.QDRANT_API_KEY,
            timeout=settings.REQUEST_TIMEOUT
        )
        
        self.children_collection = settings.CHILDREN_COLLECTION
        self.parents_collection = settings.PARENTS_COLLECTION
        self.embedding_dimension = settings.EMBEDDING_DIMENSION
        
        logger.info(f"🔧 Qdrant 서비스 초기화")
        logger.info(f"   URL: {settings.QDRANT_URL}")
        logger.info(f"   Children Collection: {self.children_collection}")
        logger.info(f"   Parents Collection: {self.parents_collection}")
    
    async def check_connection(self) -> bool:
        """Qdrant 연결 상태 확인"""
        try:
            collections = await self.client.get_collections()
            logger.info(f"✅ Qdrant 연결 성공: {len(collections.collections)}개 컬렉션")
            return True
        except Exception as e:
            logger.error(f"❌ Qdrant 연결 실패: {e}")
            return False
    
    async def ensure_collections_exist(self):
        """필요한 컬렉션들이 존재하는지 확인하고 없으면 생성"""
        try:
            # 기존 컬렉션 목록 조회
            collections = await self.client.get_collections()
            existing_names = {col.name for col in collections.collections}
            
            # Children 컬렉션 확인/생성
            if self.children_collection not in existing_names:
                logger.info(f"🔧 Children 컬렉션 생성: {self.children_collection}")
                await self.client.create_collection(
                    collection_name=self.children_collection,
                    vectors_config=VectorParams(
                        size=self.embedding_dimension,
                        distance=Distance.COSINE
                    )
                )
                logger.info(f"✅ Children 컬렉션 생성 완료")
            else:
                logger.info(f"✅ Children 컬렉션 존재: {self.children_collection}")
            
            # Parents 컬렉션 확인/생성
            if self.parents_collection not in existing_names:
                logger.info(f"🔧 Parents 컬렉션 생성: {self.parents_collection}")
                await self.client.create_collection(
                    collection_name=self.parents_collection,
                    vectors_config=VectorParams(
                        size=self.embedding_dimension,
                        distance=Distance.COSINE
                    )
                )
                logger.info(f"✅ Parents 컬렉션 생성 완료")
            else:
                logger.info(f"✅ Parents 컬렉션 존재: {self.parents_collection}")
                
        except Exception as e:
            logger.error(f"❌ 컬렉션 확인/생성 실패: {e}")
            raise QdrantServiceError(f"컬렉션 설정 실패: {e}")
    
    async def vector_search(
        self,
        query_vector: List[float],
        collection_name: Optional[str] = None,
        top_k: int = 10,
        score_threshold: float = 0.0,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        벡터 유사도 검색 수행
        
        Args:
            query_vector: 쿼리 벡터
            collection_name: 검색할 컬렉션명 (None이면 children_collection)
            top_k: 반환할 결과 수
            score_threshold: 최소 유사도 점수
            filters: 추가 필터 조건
            
        Returns:
            List[Dict]: 검색 결과 목록
        """
        if collection_name is None:
            collection_name = self.children_collection
        
        try:
            logger.debug(f"🔍 벡터 검색 시작: {collection_name}, top_k={top_k}")
            
            # 필터 설정
            search_filter = None
            if filters:
                conditions = []
                for key, value in filters.items():
                    if value is not None:
                        conditions.append(
                            FieldCondition(
                                key=key,
                                match=MatchValue(value=value)
                            )
                        )
                if conditions:
                    search_filter = Filter(must=conditions)
            
            # 벡터 검색 수행
            search_result = await self.client.search(
                collection_name=collection_name,
                query_vector=query_vector,
                limit=top_k,
                score_threshold=score_threshold,
                query_filter=search_filter,
                with_payload=True
            )
            
            # 결과 변환
            results = []
            for point in search_result:
                result = {
                    "id": point.id,
                    "score": float(point.score),
                    "payload": point.payload or {}
                }
                results.append(result)
            
            logger.debug(f"✅ 벡터 검색 완료: {len(results)}개 결과")
            return results
            
        except Exception as e:
            logger.error(f"❌ 벡터 검색 실패: {e}")
            raise QdrantServiceError(f"벡터 검색 실패: {e}")
    
    async def get_points_by_ids(
        self,
        point_ids: List[str],
        collection_name: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """ID로 포인트들 조회"""
        if collection_name is None:
            collection_name = self.parents_collection
        
        try:
            logger.debug(f"📋 ID로 포인트 조회: {len(point_ids)}개")
            
            points = await self.client.retrieve(
                collection_name=collection_name,
                ids=point_ids,
                with_payload=True
            )
            
            results = []
            for point in points:
                result = {
                    "id": point.id,
                    "payload": point.payload or {}
                }
                results.append(result)
            
            logger.debug(f"✅ 포인트 조회 완료: {len(results)}개")
            return results
            
        except Exception as e:
            logger.error(f"❌ 포인트 조회 실패: {e}")
            raise QdrantServiceError(f"포인트 조회 실패: {e}")
    
    async def get_collection_info(self, collection_name: str) -> Dict[str, Any]:
        """컬렉션 정보 조회"""
        try:
            info = await self.client.get_collection(collection_name)
            
            return {
                "name": collection_name,
                "vectors_count": info.vectors_count,
                "indexed_vectors_count": info.indexed_vectors_count,
                "points_count": info.points_count,
                "segments_count": info.segments_count,
                "status": info.status.value,
                "config": {
                    "params": {
                        "vectors": {
                            "size": info.config.params.vectors.size,
                            "distance": info.config.params.vectors.distance.value
                        }
                    }
                }
            }
            
        except Exception as e:
            logger.error(f"❌ 컬렉션 정보 조회 실패: {e}")
            raise QdrantServiceError(f"컬렉션 정보 조회 실패: {e}")
    
    async def search_hospital_children(
        self,
        query_vector: List[float],
        top_k: int = 50,
        score_threshold: float = 0.3
    ) -> List[Dict[str, Any]]:
        """병원 children 데이터에서 검색"""
        return await self.vector_search(
            query_vector=query_vector,
            collection_name=self.children_collection,
            top_k=top_k,
            score_threshold=score_threshold
        )
    
    async def get_hospital_parents(self, parent_ids: List[str]) -> List[Dict[str, Any]]:
        """
        병원 parent 정보 조회
        parent_ids는 original_id이므로 스크롤로 전체 조회 후 매칭
        """
        try:
            logger.debug(f"📋 Parent 조회: {len(parent_ids)}개 original_id")
            
            # 모든 Parent 데이터 조회 (캐시 개선 가능)
            scroll_result = await self.client.scroll(
                collection_name=self.parents_collection,
                limit=1000,  # 충분히 큰 수로 모든 Parent 가져오기
                with_payload=True,
                with_vectors=False
            )
            
            all_parents = scroll_result[0]
            logger.debug(f"   전체 Parent 수: {len(all_parents)}개")
            
            # original_id로 매칭
            results = []
            parent_lookup = {}
            
            # Parent들을 original_id로 인덱싱
            for parent in all_parents:
                if parent.payload:
                    original_id = parent.payload.get('original_id')
                    if original_id:
                        parent_lookup[original_id] = {
                            "id": parent.id,
                            "payload": parent.payload
                        }
            
            # 요청된 parent_id들 찾기
            for parent_id in parent_ids:
                if parent_id in parent_lookup:
                    results.append(parent_lookup[parent_id])
                    logger.debug(f"   ✅ Parent 발견: {parent_id}")
                else:
                    logger.warning(f"   ❌ Parent 없음: {parent_id}")
            
            logger.debug(f"✅ Parent 조회 완료: {len(results)}개")
            return results
            
        except Exception as e:
            logger.error(f"❌ Parent 조회 실패: {e}")
            raise QdrantServiceError(f"Parent 조회 실패: {e}")


# 글로벌 Qdrant 서비스 인스턴스
_qdrant_service: Optional[QdrantService] = None


def get_qdrant_service() -> QdrantService:
    """Qdrant 서비스 싱글톤 인스턴스 반환"""
    global _qdrant_service
    if _qdrant_service is None:
        _qdrant_service = QdrantService()
    return _qdrant_service
