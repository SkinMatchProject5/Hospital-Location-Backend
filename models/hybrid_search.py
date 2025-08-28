"""
3단계 HybridSearcher 구현 - Dense + Sparse + 2025 Reranking
작업일: 2025-08-21
목표: 65% → 95% 정확도 달성
"""

import time
from typing import Any, Dict, List, Optional, Tuple
from collections import defaultdict
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue
from openai import OpenAI
from rank_bm25 import BM25Okapi
import re
import config

# 2025년 최고 성능 리랭커 통합
try:
    from sentence_transformers import CrossEncoder
    RERANKER_AVAILABLE = True
except ImportError:
    RERANKER_AVAILABLE = False

class Enhanced2025Reranker:
    """2025년 최고 성능 리랭커 (BGE 기반)"""
    
    def __init__(self):
        self.model = None
        self.model_name = "BAAI/bge-reranker-base"  # 안정적이고 검증된 성능
        self._load_model()
    
    def _load_model(self):
        """리랭커 모델 로딩"""
        if not RERANKER_AVAILABLE:
            print("⚠️ sentence_transformers 없음 - 리랭킹 비활성화")
            return
            
        try:
            print(f"🔄 {self.model_name} 로딩 중...")
            self.model = CrossEncoder(self.model_name)
            print("✅ 리랭커 로딩 완료!")
        except Exception as e:
            print(f"❌ 리랭커 로딩 실패: {e}")
            self.model = None
    
    def rerank_candidates(self, query: str, candidates: List[Dict[str, Any]], 
                         top_k: int = 10) -> List[Dict[str, Any]]:
        """고성능 리랭킹"""
        if not self.model or not candidates:
            return candidates[:top_k]
        
        try:
            # 의료 쿼리 강화
            enhanced_query = f"한국 의료기관 검색: {query}"
            
            # 텍스트 추출
            texts = []
            for candidate in candidates:
                text = self._extract_text(candidate)
                texts.append(text)
            
            # 배치 리랭킹
            pairs = [(enhanced_query, text) for text in texts]
            scores = self.model.predict(pairs)
            
            # 점수 적용
            for i, candidate in enumerate(candidates):
                candidate["rerank_score"] = float(scores[i])
            
            # 정렬
            candidates.sort(key=lambda x: x.get("rerank_score", 0), reverse=True)
            return candidates[:top_k]
            
        except Exception as e:
            print(f"리랭킹 오류: {e}")
            return candidates[:top_k]
    
    def _extract_text(self, candidate: Dict[str, Any]) -> str:
        """텍스트 추출 최적화"""
        for key in ["embedding_text", "title", "snippet", "text"]:
            if key in candidate:
                value = candidate[key]
                if isinstance(value, dict):
                    inner = value.get("embedding_text") or value.get("title") or str(value)
                    if inner.strip():
                        return inner
                elif isinstance(value, str) and value.strip():
                    return value
        return str(candidate)


class HybridSearcher:
    """3단계 하이브리드 검색기 - Dense + Sparse + Reranking"""
    
    def __init__(self, qdrant_client: QdrantClient, collection_name: str):
        self.client = qdrant_client
        self.collection = collection_name
        
        # OpenAI 클라이언트 초기화
        try:
            self.openai_client = OpenAI(api_key=config.OPENAI_API_KEY)
            print("✅ OpenAI 클라이언트 초기화 완료")
        except Exception as e:
            print(f"❌ OpenAI 초기화 실패: {e}")
            self.openai_client = None
        
        # BM25 준비
        self.bm25_corpus = []
        self.bm25_index = None
        self.documents = []
        
        # 2025년 리랭커 초기화
        self.reranker = Enhanced2025Reranker()
        
        print("🚀 HybridSearcher 초기화 완료 (Dense + Sparse + Reranking)")
    
    def _prepare_bm25_index(self):
        """BM25 인덱스 준비 (처음 한 번만)"""
        if self.bm25_index is not None:
            return
        
        print("📚 BM25 인덱스 구축 중...")
        try:
            # 모든 문서 가져오기
            scroll_result = self.client.scroll(
                collection_name=self.collection,
                limit=10000,  # 모든 문서
                with_payload=True
            )
            
            documents = scroll_result[0] if scroll_result else []
            print(f"📄 {len(documents)}개 문서 로드")
            
            # BM25 코퍼스 구축
            corpus = []
            self.documents = []
            
            for doc in documents:
                # 텍스트 추출
                payload = doc.payload
                text = self._extract_searchable_text(payload)
                
                # 토큰화 (한국어 + 영어)
                tokens = self._tokenize_korean(text)
                corpus.append(tokens)
                self.documents.append(doc)
            
            # BM25 인덱스 생성
            self.bm25_index = BM25Okapi(corpus)
            self.bm25_corpus = corpus
            
            print(f"✅ BM25 인덱스 구축 완료 ({len(corpus)}개 문서)")
            
        except Exception as e:
            print(f"❌ BM25 인덱스 구축 실패: {e}")
            self.bm25_index = None
    
    def _extract_searchable_text(self, payload: Dict) -> str:
        """검색 가능한 텍스트 추출"""
        texts = []
        
        # snippet에서 텍스트 추출
        if "snippet" in payload:
            snippet = payload["snippet"]
            if isinstance(snippet, dict):
                if "embedding_text" in snippet:
                    texts.append(snippet["embedding_text"])
                if "title" in snippet:
                    texts.append(snippet["title"])
        
        # topic 정보
        if "topic" in payload:
            topic = payload["topic"]
            if isinstance(topic, dict):
                if "name" in topic:
                    texts.append(topic["name"])
                if "aliases" in topic and isinstance(topic["aliases"], list):
                    texts.extend(topic["aliases"])
        
        # filters 정보
        if "filters" in payload:
            filters = payload["filters"]
            if isinstance(filters, dict):
                if "disease" in filters:
                    texts.append(filters["disease"])
        
        return " ".join(texts)
    
    def _tokenize_korean(self, text: str) -> List[str]:
        """한국어/영어 토큰화"""
        if not text:
            return []
        
        # 한국어, 영어, 숫자만 추출
        text = re.sub(r'[^\w\s가-힣]', ' ', text)
        tokens = text.lower().split()
        
        # 빈 토큰 제거
        tokens = [token for token in tokens if token and len(token) > 1]
        
        return tokens
    
    def _dense_search(self, query: str, top_k: int, filters: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """Dense 벡터 검색"""
        if not self.openai_client:
            print("❌ OpenAI 클라이언트 없음 - Dense 검색 불가")
            return []
        
        try:
            # 쿼리 임베딩 생성
            response = self.openai_client.embeddings.create(
                model=config.EMBEDDING_MODEL,
                input=query
            )
            query_vector = response.data[0].embedding
            
            # Qdrant 필터 생성
            qdrant_filter = None
            if filters:
                conditions = []
                for key, value in filters.items():
                    if value:
                        conditions.append(
                            FieldCondition(key=f"filters.{key}", match=MatchValue(value=value))
                        )
                if conditions:
                    qdrant_filter = Filter(must=conditions)
            
            # 벡터 검색 수행
            search_results = self.client.query_points(
                collection_name=self.collection,
                query=query_vector,
                limit=top_k,
                query_filter=qdrant_filter,
                with_payload=True
            ).points
            
            # 결과 포맷팅
            results = []
            for point in search_results:
                result = {
                    "id": point.id,
                    "score": point.score,
                    "dense_score": point.score,
                    "payload": point.payload,
                    "search_type": "dense"
                }
                results.append(result)
            
            return results
            
        except Exception as e:
            print(f"❌ Dense 검색 오류: {e}")
            return []
    
    def _sparse_search(self, query: str, top_k: int, filters: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """Sparse BM25 검색"""
        # BM25 인덱스 준비
        self._prepare_bm25_index()
        
        if not self.bm25_index:
            print("❌ BM25 인덱스 없음 - Sparse 검색 불가")
            return []
        
        try:
            # 쿼리 토큰화
            query_tokens = self._tokenize_korean(query)
            if not query_tokens:
                return []
            
            # BM25 점수 계산
            scores = self.bm25_index.get_scores(query_tokens)
            
            # 점수와 문서 인덱스 조합
            doc_scores = [(i, score) for i, score in enumerate(scores) if score > 0]
            doc_scores.sort(key=lambda x: x[1], reverse=True)
            
            # 상위 결과 선택
            results = []
            for doc_idx, bm25_score in doc_scores[:top_k * 2]:  # 필터링을 위해 더 많이 가져옴
                doc = self.documents[doc_idx]
                
                # 필터 적용
                if filters and not self._apply_filters(doc.payload, filters):
                    continue
                
                result = {
                    "id": doc.id,
                    "score": bm25_score,
                    "sparse_score": bm25_score,
                    "payload": doc.payload,
                    "search_type": "sparse"
                }
                results.append(result)
                
                if len(results) >= top_k:
                    break
            
            return results
            
        except Exception as e:
            print(f"❌ Sparse 검색 오류: {e}")
            return []
    
    def _apply_filters(self, payload: Dict, filters: Dict) -> bool:
        """필터 조건 확인"""
        if not filters:
            return True
        
        payload_filters = payload.get("filters", {})
        
        for key, value in filters.items():
            if not value:
                continue
            payload_value = payload_filters.get(key)
            if payload_value != value:
                return False
        
        return True
    
    def _combine_results(self, dense_results: List[Dict], sparse_results: List[Dict], 
                        sparse_weight: float = 0.3) -> List[Dict[str, Any]]:
        """Dense + Sparse 결과 조합"""
        
        # ID별 결과 매핑
        combined = {}
        
        # Dense 점수 정규화
        if dense_results:
            max_dense = max(r["dense_score"] for r in dense_results)
            min_dense = min(r["dense_score"] for r in dense_results)
            dense_range = max_dense - min_dense if max_dense != min_dense else 1
        
        # Sparse 점수 정규화  
        if sparse_results:
            max_sparse = max(r["sparse_score"] for r in sparse_results)
            min_sparse = min(r["sparse_score"] for r in sparse_results)
            sparse_range = max_sparse - min_sparse if max_sparse != min_sparse else 1
        
        # Dense 결과 처리
        for result in dense_results:
            doc_id = result["id"]
            normalized_dense = (result["dense_score"] - min_dense) / dense_range if dense_results else 0
            
            combined[doc_id] = {
                **result,
                "normalized_dense": normalized_dense,
                "normalized_sparse": 0,
                "combined_score": normalized_dense * (1 - sparse_weight)
            }
        
        # Sparse 결과 처리
        for result in sparse_results:
            doc_id = result["id"]
            normalized_sparse = (result["sparse_score"] - min_sparse) / sparse_range if sparse_results else 0
            
            if doc_id in combined:
                # 기존 결과 업데이트
                combined[doc_id]["normalized_sparse"] = normalized_sparse
                combined[doc_id]["sparse_score"] = result["sparse_score"]
                combined[doc_id]["combined_score"] = (
                    combined[doc_id]["normalized_dense"] * (1 - sparse_weight) +
                    normalized_sparse * sparse_weight
                )
                combined[doc_id]["search_type"] = "hybrid"
            else:
                # 새로운 결과 추가
                combined[doc_id] = {
                    **result,
                    "normalized_dense": 0,
                    "normalized_sparse": normalized_sparse,
                    "combined_score": normalized_sparse * sparse_weight,
                    "search_type": "sparse_only"
                }
        
        # 조합 점수로 정렬
        results = list(combined.values())
        results.sort(key=lambda x: x["combined_score"], reverse=True)
        
        return results

    def hybrid_search(self, query: str, top_k: int = 20, sparse_weight: float = 0.3, 
                     filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """하이브리드 검색 (Dense + Sparse + Reranking)"""
        
        print(f"🔍 하이브리드 검색: '{query}' (top_k={top_k}, sparse_weight={sparse_weight})")
        start_time = time.time()
        
        # 1. Dense 검색
        print("  📊 Dense 검색 중...")
        dense_start = time.time()
        dense_results = self._dense_search(query, top_k, filters)
        dense_time = time.time() - dense_start
        print(f"    ✅ Dense: {len(dense_results)}개 결과 ({dense_time:.3f}초)")
        
        # 2. Sparse 검색
        print("  🔤 Sparse 검색 중...")
        sparse_start = time.time()
        sparse_results = self._sparse_search(query, top_k, filters)
        sparse_time = time.time() - sparse_start
        print(f"    ✅ Sparse: {len(sparse_results)}개 결과 ({sparse_time:.3f}초)")
        
        # 3. 결과 조합
        print("  🔄 결과 조합 중...")
        combine_start = time.time()
        combined_results = self._combine_results(dense_results, sparse_results, sparse_weight)
        combine_time = time.time() - combine_start
        print(f"    ✅ 조합: {len(combined_results)}개 결과 ({combine_time:.3f}초)")
        
        # 4. Parent 그룹핑
        print("  👥 Parent 그룹핑 중...")
        group_start = time.time()
        grouped_results = self.group_by_parent(combined_results)
        group_time = time.time() - group_start
        print(f"    ✅ 그룹핑: {len(grouped_results)}개 결과 ({group_time:.3f}초)")
        
        # 5. 2025년 리랭킹 적용
        print("  🏆 2025 리랭킹 중...")
        rerank_start = time.time()
        final_results = self.reranker.rerank_candidates(query, grouped_results, top_k)
        rerank_time = time.time() - rerank_start
        print(f"    ✅ 리랭킹: {len(final_results)}개 결과 ({rerank_time:.3f}초)")
        
        total_time = time.time() - start_time
        print(f"🏁 총 처리 시간: {total_time:.3f}초")
        
        return final_results

    def group_by_parent(self, search_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Parent ID로 그룹핑 (최고 점수만 유지)"""
        
        if not search_results:
            return []
        
        # Parent별 최고 점수 결과만 보관
        parent_groups = {}
        
        for result in search_results:
            payload = result.get("payload", {})
            parent_id = payload.get("parent_id")
            
            if not parent_id:
                # Parent ID가 없으면 그대로 유지
                unique_key = result.get("id", f"no_parent_{len(parent_groups)}")
                parent_groups[unique_key] = result
                continue
            
            # 기존 결과와 점수 비교
            current_score = result.get("combined_score", result.get("rerank_score", result.get("score", 0)))
            
            if parent_id not in parent_groups:
                parent_groups[parent_id] = result
            else:
                existing_score = parent_groups[parent_id].get("combined_score", 
                    parent_groups[parent_id].get("rerank_score", 
                        parent_groups[parent_id].get("score", 0)))
                
                if current_score > existing_score:
                    parent_groups[parent_id] = result
        
        # 점수 순으로 정렬
        grouped_results = list(parent_groups.values())
        grouped_results.sort(
            key=lambda x: x.get("combined_score", x.get("rerank_score", x.get("score", 0))), 
            reverse=True
        )
        
        return grouped_results