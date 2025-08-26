"""
Hospital-Location-Backend 하이브리드 검색 엔진
코사인 유사도 + BM25를 결합한 병원 검색 시스템
"""

import logging
import asyncio
from typing import List, Dict, Any, Optional, Tuple
from collections import defaultdict, Counter
import math
import re

from app.core.config import settings
from app.models.diagnosis import DiagnosisInfo
from app.services.embedding_service import EmbeddingService, get_embedding_service
from app.services.qdrant_service import QdrantService, get_qdrant_service

logger = logging.getLogger(__name__)


class HybridSearchError(Exception):
    """하이브리드 검색 오류"""
    pass


class BM25Scorer:
    """BM25 스코어링 엔진"""
    
    def __init__(self, k1: float = 1.2, b: float = 0.75):
        """
        BM25 스코어링 초기화
        
        Args:
            k1: 용어 빈도 포화도 파라미터
            b: 문서 길이 정규화 파라미터
        """
        self.k1 = k1
        self.b = b
        self.documents: List[str] = []
        self.doc_frequencies: Dict[str, int] = {}
        self.doc_lengths: List[int] = []
        self.avg_doc_length = 0.0
        self.total_docs = 0
        
    def build_index(self, documents: List[str]):
        """BM25 인덱스 구축"""
        self.documents = documents
        self.total_docs = len(documents)
        
        # 문서별 토큰화 및 길이 계산
        tokenized_docs = []
        doc_word_counts = []
        
        for doc in documents:
            tokens = self._tokenize(doc)
            tokenized_docs.append(tokens)
            self.doc_lengths.append(len(tokens))
            
            # 단어 빈도 계산
            word_count = Counter(tokens)
            doc_word_counts.append(word_count)
            
            # 전체 문서 빈도 업데이트
            for word in set(tokens):
                self.doc_frequencies[word] = self.doc_frequencies.get(word, 0) + 1
        
        # 평균 문서 길이 계산
        self.avg_doc_length = sum(self.doc_lengths) / len(self.doc_lengths) if self.doc_lengths else 0
        
        # 문서별 단어 빈도 저장
        self.doc_word_counts = doc_word_counts
        
        logger.info(f"🔧 BM25 인덱스 구축 완료: {self.total_docs}개 문서, 평균 길이 {self.avg_doc_length:.1f}")
    
    def _tokenize(self, text: str) -> List[str]:
        """텍스트 토큰화"""
        if not text:
            return []
        
        # 한글, 영문, 숫자만 추출하고 소문자로 변환
        text = re.sub(r'[^\w가-힣\s]', ' ', text.lower())
        tokens = text.split()
        
        # 길이 1 이상인 토큰만 유지
        return [token for token in tokens if len(token) > 0]
    
    def score(self, query: str, doc_idx: int) -> float:
        """BM25 스코어 계산"""
        if doc_idx >= len(self.doc_word_counts):
            return 0.0
        
        query_tokens = self._tokenize(query)
        doc_word_count = self.doc_word_counts[doc_idx]
        doc_length = self.doc_lengths[doc_idx]
        
        score = 0.0
        
        for token in query_tokens:
            if token in doc_word_count:
                # TF (Term Frequency)
                tf = doc_word_count[token]
                
                # IDF (Inverse Document Frequency)
                df = self.doc_frequencies.get(token, 0)
                if df == 0:
                    continue
                
                idf = math.log((self.total_docs - df + 0.5) / (df + 0.5) + 1.0)
                
                # BM25 공식
                tf_component = (tf * (self.k1 + 1)) / (
                    tf + self.k1 * (1 - self.b + self.b * (doc_length / self.avg_doc_length))
                )
                
                score += idf * tf_component
        
        return score
    
    def search(self, query: str, top_k: int = 10) -> List[Tuple[int, float]]:
        """BM25 검색 수행"""
        if not self.documents:
            return []
        
        scores = []
        for doc_idx in range(len(self.documents)):
            score = self.score(query, doc_idx)
            if score > 0:
                scores.append((doc_idx, score))
        
        # 점수 기준 정렬
        scores.sort(key=lambda x: x[1], reverse=True)
        
        return scores[:top_k]


class HybridSearchEngine:
    """하이브리드 검색 엔진 (코사인 + BM25)"""
    
    def __init__(self, 
                 embedding_service: Optional[EmbeddingService] = None,
                 qdrant_service: Optional[QdrantService] = None):
        """하이브리드 검색 엔진 초기화"""
        self.embedding_service = embedding_service or get_embedding_service()
        self.qdrant_service = qdrant_service or get_qdrant_service()
        
        self.cosine_weight = settings.COSINE_WEIGHT
        self.bm25_weight = settings.BM25_WEIGHT
        
        # BM25 인덱스 (문서별로 구축)
        self.bm25_scorer: Optional[BM25Scorer] = None
        self.indexed_documents: List[Dict[str, Any]] = []
        
        logger.info(f"🔧 하이브리드 검색 엔진 초기화")
        logger.info(f"   코사인 가중치: {self.cosine_weight}")
        logger.info(f"   BM25 가중치: {self.bm25_weight}")
    
    async def initialize(self):
        """검색 엔진 초기화 (벡터DB 연결 확인)"""
        try:
            # Qdrant 연결 확인
            if not await self.qdrant_service.check_connection():
                raise HybridSearchError("Qdrant 연결 실패")
            
            # 필요한 컬렉션 생성
            await self.qdrant_service.ensure_collections_exist()
            
            logger.info("✅ 하이브리드 검색 엔진 초기화 완료")
            
        except Exception as e:
            logger.error(f"❌ 하이브리드 검색 엔진 초기화 실패: {e}")
            raise HybridSearchError(f"초기화 실패: {e}")
    
    async def search(self, 
                    diagnosis_info: DiagnosisInfo,
                    top_k: int = 24,
                    final_k: int = 2) -> List[Dict[str, Any]]:
        """
        하이브리드 검색 수행
        
        Args:
            diagnosis_info: 파싱된 진단 정보
            top_k: 초기 후보 수
            final_k: 최종 결과 수
            
        Returns:
            List[Dict]: 검색된 병원 정보 목록
        """
        try:
            logger.info(f"🔍 하이브리드 검색 시작: {diagnosis_info.primary_diagnosis}")
            
            # 1. 쿼리 텍스트 생성
            query_text = diagnosis_info.get_search_text()
            logger.debug(f"검색 쿼리: {query_text}")
            
            # 2. 벡터 검색 (코사인 유사도)
            cosine_results = await self._cosine_search(query_text, top_k)
            logger.debug(f"코사인 검색 결과: {len(cosine_results)}개")
            
            # 3. BM25 검색 (키워드 매칭)
            bm25_results = await self._bm25_search(query_text, cosine_results, top_k)
            logger.debug(f"BM25 검색 결과: {len(bm25_results)}개")
            
            # 4. 하이브리드 스코어 계산 및 결합
            hybrid_results = self._combine_scores(cosine_results, bm25_results)
            
            # 5. Parent 그룹핑 (같은 Parent의 Child들 중 최고 점수만 유지)
            grouped_results = self._group_by_parent(hybrid_results)
            
            # 6. 상위 결과 선택 후 Parent 정보와 결합
            top_results = grouped_results[:final_k]
            final_results = await self._enrich_with_parent_info(top_results)
            
            logger.info(f"✅ 하이브리드 검색 완료: {len(final_results)}개 병원 (중복 제거 후)")
            
            return final_results
            
        except Exception as e:
            logger.error(f"❌ 하이브리드 검색 실패: {e}")
            raise HybridSearchError(f"검색 실패: {e}")
    
    async def _cosine_search(self, query_text: str, top_k: int) -> List[Dict[str, Any]]:
        """벡터 유사도 검색 (코사인)"""
        try:
            # 쿼리 임베딩 생성
            query_embedding = await self.embedding_service.embed_text(query_text)
            
            # Qdrant 벡터 검색
            results = await self.qdrant_service.search_hospital_children(
                query_vector=query_embedding,
                top_k=top_k,
                score_threshold=0.1  # 최소 유사도 임계값
            )
            
            return results
            
        except Exception as e:
            logger.error(f"❌ 코사인 검색 실패: {e}")
            return []
    
    async def _bm25_search(self, 
                          query_text: str, 
                          cosine_results: List[Dict[str, Any]], 
                          top_k: int) -> Dict[str, float]:
        """BM25 키워드 검색"""
        try:
            if not cosine_results:
                return {}
            
            # 문서 텍스트 추출
            documents = []
            doc_id_map = {}
            
            for i, result in enumerate(cosine_results):
                payload = result.get('payload', {})
                
                # 검색 가능한 텍스트 결합
                text_parts = []
                
                # 제목/이름
                if 'title' in payload:
                    text_parts.append(str(payload['title']))
                if 'name' in payload:
                    text_parts.append(str(payload['name']))
                
                # 설명/내용
                if 'embedding_text' in payload:
                    text_parts.append(str(payload['embedding_text']))
                if 'description' in payload:
                    text_parts.append(str(payload['description']))
                
                # 태그/키워드
                if 'tags' in payload:
                    tags = payload['tags']
                    if isinstance(tags, list):
                        text_parts.extend([str(tag) for tag in tags])
                    else:
                        text_parts.append(str(tags))
                
                doc_text = ' '.join(text_parts)
                documents.append(doc_text)
                doc_id_map[i] = result.get('id')
            
            # BM25 인덱스 구축
            bm25_scorer = BM25Scorer()
            bm25_scorer.build_index(documents)
            
            # BM25 검색 수행
            bm25_results = bm25_scorer.search(query_text, top_k)
            
            # 결과를 ID별 점수 딕셔너리로 변환
            bm25_scores = {}
            for doc_idx, score in bm25_results:
                doc_id = doc_id_map.get(doc_idx)
                if doc_id:
                    bm25_scores[str(doc_id)] = score
            
            return bm25_scores
            
        except Exception as e:
            logger.error(f"❌ BM25 검색 실패: {e}")
            return {}
    
    def _combine_scores(self, 
                       cosine_results: List[Dict[str, Any]], 
                       bm25_scores: Dict[str, float]) -> List[Dict[str, Any]]:
        """코사인과 BM25 점수를 결합"""
        try:
            # 코사인 점수 정규화 (0-1 범위)
            cosine_scores = [r.get('score', 0.0) for r in cosine_results]
            max_cosine = max(cosine_scores) if cosine_scores else 1.0
            min_cosine = min(cosine_scores) if cosine_scores else 0.0
            cosine_range = max_cosine - min_cosine if max_cosine > min_cosine else 1.0
            
            # BM25 점수 정규화 (0-1 범위)
            bm25_values = list(bm25_scores.values())
            max_bm25 = max(bm25_values) if bm25_values else 1.0
            min_bm25 = min(bm25_values) if bm25_values else 0.0
            bm25_range = max_bm25 - min_bm25 if max_bm25 > min_bm25 else 1.0
            
            combined_results = []
            
            for result in cosine_results:
                result_id = str(result.get('id'))
                cosine_score = result.get('score', 0.0)
                bm25_score = bm25_scores.get(result_id, 0.0)
                
                # 정규화
                normalized_cosine = (cosine_score - min_cosine) / cosine_range
                normalized_bm25 = (bm25_score - min_bm25) / bm25_range if bm25_range > 0 else 0.0
                
                # 하이브리드 점수 계산
                hybrid_score = (
                    self.cosine_weight * normalized_cosine + 
                    self.bm25_weight * normalized_bm25
                )
                
                # 결과에 점수 정보 추가
                enhanced_result = result.copy()
                enhanced_result.update({
                    'hybrid_score': hybrid_score,
                    'cosine_score': normalized_cosine,
                    'bm25_score': normalized_bm25,
                    'original_cosine_score': cosine_score
                })
                
                combined_results.append(enhanced_result)
            
            # 하이브리드 점수로 정렬
            combined_results.sort(key=lambda x: x.get('hybrid_score', 0.0), reverse=True)
            
            return combined_results
            
        except Exception as e:
            logger.error(f"❌ 점수 결합 실패: {e}")
            return cosine_results  # 실패 시 코사인 결과만 반환
    
    async def _enrich_with_parent_info(self, 
                                     search_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """검색 결과에 Parent 병원 정보 추가"""
        try:
            # Parent ID 추출
            parent_ids = []
            for result in search_results:
                payload = result.get('payload', {})
                parent_id = payload.get('parent_id')
                if parent_id:
                    parent_ids.append(str(parent_id))
            
            if not parent_ids:
                logger.warning("Parent ID가 없는 검색 결과")
                return search_results
            
            # Parent 정보 조회
            parent_info_list = await self.qdrant_service.get_hospital_parents(parent_ids)
            
            # Parent original_id를 키로 하는 딕셔너리 생성
            parent_info_dict = {}
            for parent_info in parent_info_list:
                parent_payload = parent_info.get('payload', {})
                original_id = parent_payload.get('original_id')
                if original_id:
                    parent_info_dict[original_id] = parent_payload
            
            # 검색 결과와 Parent 정보 결합
            enriched_results = []
            for result in search_results:
                payload = result.get('payload', {})
                parent_id = payload.get('parent_id', '')
                
                parent_data = parent_info_dict.get(parent_id, {})
                
                # 결합된 데이터 생성
                enriched_result = {
                    'child': payload,
                    'parent': parent_data,
                    'scores': {
                        'hybrid': result.get('score', 0.0),  # 실제 하이브리드 점수
                        'cosine': result.get('cosine_score', 0.0),
                        'bm25': result.get('bm25_score', 0.0)
                    }
                }
                
                enriched_results.append(enriched_result)
            
            return enriched_results
            
        except Exception as e:
            logger.error(f"❌ Parent 정보 결합 실패: {e}")
            return search_results
    
    def _group_by_parent(self, search_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Parent ID별로 그룹핑하여 각 Parent당 최고 점수 Child만 유지"""
        try:
            parent_groups = {}
            
            for result in search_results:
                parent_id = result.get('payload', {}).get('parent_id', '')
                score = result.get('score', 0.0)
                
                if parent_id:
                    # 같은 Parent ID면 더 높은 점수만 유지
                    if parent_id not in parent_groups or score > parent_groups[parent_id]['score']:
                        parent_groups[parent_id] = result
                        logger.debug(f"✅ Parent 그룹 업데이트: {parent_id} (점수: {score})")
                    else:
                        logger.debug(f"🔄 낮은 점수 Child 제거: {parent_id} (점수: {score})")
                else:
                    # parent_id가 없는 경우도 포함
                    logger.debug(f"⚠️ Parent ID 없는 결과: {result.get('id', 'unknown')}")
            
            grouped_results = list(parent_groups.values())
            # 점수 순으로 정렬 (동점일 경우 parent_id로 2차 정렬하여 일관성 보장)
            grouped_results.sort(key=lambda x: (x.get('score', 0.0), x.get('payload', {}).get('parent_id', '')), reverse=True)
            
            logger.info(f"👥 Parent 그룹핑: {len(search_results)}개 → {len(grouped_results)}개 (고유 Parent)")
            
            # 그룹핑된 Parent들 로깅
            for i, result in enumerate(grouped_results[:5], 1):
                parent_id = result.get('payload', {}).get('parent_id', 'unknown')
                score = result.get('score', 0.0)
                logger.info(f"   {i}위: {parent_id} (점수: {score:.6f})")
            return grouped_results
            
        except Exception as e:
            logger.error(f"❌ Parent 그룹핑 실패: {e}")
            return search_results


# 글로벌 하이브리드 검색 엔진 인스턴스
_hybrid_search_engine: Optional[HybridSearchEngine] = None


def get_hybrid_search_engine() -> HybridSearchEngine:
    """하이브리드 검색 엔진 싱글톤 인스턴스 반환"""
    global _hybrid_search_engine
    if _hybrid_search_engine is None:
        _hybrid_search_engine = HybridSearchEngine()
    return _hybrid_search_engine
