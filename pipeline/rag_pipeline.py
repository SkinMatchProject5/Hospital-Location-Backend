"""Main RAG pipeline wiring (scaffold).

Connects QueryBuilder, HybridSearcher, and LangChainReranker.
Implementation details will be added in later steps.
"""

from typing import Any, Dict, Iterable, Optional

from models.query_builder import QueryBuilder
from models.hybrid_search import HybridSearcher
from models.reranker import LangChainReranker
from models.cross_encoder_reranker import CrossEncoderReranker
from utils.ft_output_parser import parse_ft_xml_to_model_output
from utils.data_access import index_parents


class HospitalRAGPipeline:
    def __init__(self, qdrant_client: Any, collection_name: str, rerank_model_type: str = "llm"):
        self.query_builder = QueryBuilder()
        self.searcher = HybridSearcher(qdrant_client=qdrant_client, collection_name=collection_name)
        
        # rerank_model_type에 따라 적절한 리랭커 초기화
        self.rerank_model_type = rerank_model_type
        if rerank_model_type == "ce":
            self.cross_encoder_reranker = CrossEncoderReranker()
            self.llm_reranker = None
        elif rerank_model_type == "llm":
            self.cross_encoder_reranker = None
            self.llm_reranker = LangChainReranker(model_type="llm")
        else:  # "off"
            self.cross_encoder_reranker = None
            self.llm_reranker = None
        
        # 기존 reranker는 호환성을 위해 유지 (팩토리에서 LLM 설정용)
        self.reranker = LangChainReranker(model_type=rerank_model_type)
        
        # Parent 병원 정보 인덱스 로드
        self.parents_index = index_parents("parents.jsonl")

    def search_hospitals(
        self,
        diagnosis: str,
        description: Optional[str] = None,
        similar_diseases: Optional[Iterable[str]] = None,
        region: Optional[str] = None,
        candidate_limit: Optional[int] = None,
        stage1_top_k: int = 12,
        stage2_top_k: int = 4,
        final_top_k: int = 2,
    ) -> Dict[str, Any]:
        query = self.query_builder.build_search_query(diagnosis, description, similar_diseases)
        region_filter = region or self.query_builder.extract_region_filter(" ".join([diagnosis or "", description or ""]))

        candidates = self.searcher.hybrid_search(
            query=query,
            top_k=candidate_limit or 10_000,
            sparse_weight=0.5,
            filters={"region": region_filter} if region_filter else None,
        )
        grouped = self.searcher.group_by_parent(candidates)
        # Three-stage reranking (LangChain strategy placeholder)
        stage1 = self.reranker.rerank_candidates(query, grouped, top_k=stage1_top_k)
        stage2 = self.reranker.rerank_candidates(query, stage1, top_k=stage2_top_k)
        reranked = self.reranker.rerank_candidates(query, stage2, top_k=final_top_k)
        
        # Parent 정보와 조인
        final_results = self._join_with_parents(reranked)

        return {
            "query": {"diagnosis": diagnosis, "description": description, "similar_diseases": list(similar_diseases or [])},
            "results": final_results,
            "meta": {"candidates": len(candidates), "grouped": len(grouped)},
        }

    def search_from_model_output(
        self,
        model_output: Dict[str, Any],
        candidate_limit: Optional[int] = None,
        stage1_top_k: int = 12,
        stage2_top_k: int = 4,
        final_top_k: int = 2,
    ) -> Dict[str, Any]:
        """Accepts fine-tuned model output and maps it to pipeline inputs.

        Expected fields (best-effort):
        - diagnosis: str (필수)
        - description: str (선택)
        - similar_diseases: list[str] (선택)
        - region: str (선택)
        """
        diagnosis = model_output.get("diagnosis") or model_output.get("disease") or ""
        description = model_output.get("description") or model_output.get("notes")
        similar = model_output.get("similar_diseases") or model_output.get("aliases") or []
        region = model_output.get("region") or model_output.get("location")

        return self.search_hospitals(
            diagnosis=diagnosis,
            description=description,
            similar_diseases=similar,
            region=region,
            candidate_limit=candidate_limit,
            stage1_top_k=stage1_top_k,
            stage2_top_k=stage2_top_k,
            final_top_k=final_top_k,
        )

    def search_from_ft_xml(
        self,
        xml_str: str,
        candidate_limit: Optional[int] = None,
        stage1_top_k: int = 12,
        stage2_top_k: int = 4,
        final_top_k: int = 2,
    ) -> Dict[str, Any]:
        """Convenience: parse FT XML string and search."""
        model_output = parse_ft_xml_to_model_output(xml_str)
        return self.search_from_model_output(
            model_output,
            candidate_limit=candidate_limit,
            stage1_top_k=stage1_top_k,
            stage2_top_k=stage2_top_k,
            final_top_k=final_top_k,
        )
    
    def _join_with_parents(self, child_results: list[Dict[str, Any]]) -> list[Dict[str, Any]]:
        """Child 검색 결과를 Parent 병원 정보와 조인"""
        joined_results = []
        
        for child in child_results:
            # Child 정보 추출
            payload = child.get("payload", {})
            parent_id = payload.get("parent_id")
            
            # Parent 정보 조회
            parent_info = {}
            if parent_id and parent_id in self.parents_index:
                parent_record = self.parents_index[parent_id]
                parent_info = parent_record.get("payload", {})
            
            # 조인된 결과 구성
            result = {
                "parent": {
                    "name": parent_info.get("name", "Unknown Hospital"),
                    "region": parent_info.get("region", "Unknown Region"), 
                    "contacts": parent_info.get("contacts", {}),
                    "specialties": parent_info.get("specialties", [])
                },
                "child": {
                    "title": payload.get("snippet", {}).get("title", ""),
                    "embedding_text": payload.get("snippet", {}).get("embedding_text", "")
                },
                "scores": {
                    "dense": child.get("dense_score", child.get("score", 0)),
                    "sparse": child.get("sparse_score", 0),
                    "combined": child.get("combined_score", child.get("score", 0)),
                    "rerank": child.get("rerank_score", 0)
                },
                "parent_id": parent_id
            }
            
            joined_results.append(result)
        
        return joined_results
    
    def search_with_dynamic_reranking(
        self,
        diagnosis: str,
        description: Optional[str] = None,
        similar_diseases: Optional[Iterable[str]] = None,
        region: Optional[str] = None,
        candidate_limit: Optional[int] = None,
        rerank_mode: str = "ce",
        final_top_k: int = 2,
    ) -> Dict[str, Any]:
        """동적 리랭킹을 적용하는 검색"""
        
        query = self.query_builder.build_search_query(diagnosis, description, similar_diseases)
        region_filter = region or self.query_builder.extract_region_filter(" ".join([diagnosis or "", description or ""]))

        # 기본 하이브리드 검색
        candidates = self.searcher.hybrid_search(
            query=query,
            top_k=candidate_limit or 24,
            sparse_weight=0.5,
            filters={"region": region_filter} if region_filter else None,
        )
        
        # Parent 그룹핑
        grouped = self.searcher.group_by_parent(candidates)
        
        # 동적 리랭킹 적용
        reranked = self._apply_reranking(query, grouped, rerank_mode, final_top_k)
        
        # Parent 정보와 조인
        final_results = self._join_with_parents(reranked)

        return {
            "query": {"diagnosis": diagnosis, "description": description, "similar_diseases": list(similar_diseases or [])},
            "results": final_results,
            "meta": {
                "candidates": len(candidates), 
                "grouped": len(grouped),
                "rerank_mode": rerank_mode,
                "rerank_applied": rerank_mode != "off"
            },
        }
    
    def _apply_reranking(self, query: str, candidates: list[Dict[str, Any]], rerank_mode: str, top_k: int = 2) -> list[Dict[str, Any]]:
        """동적 리랭킹 적용"""
        if rerank_mode == "off" or not candidates:
            print(f"🚫 리랭킹 비활성화 - 원래 순서 유지 (상위 {top_k}개)")
            return candidates[:top_k]
        
        if rerank_mode == "ce" and self.cross_encoder_reranker:
            print(f"🔄 CrossEncoder 리랭킹 적용 중...")
            try:
                return self.cross_encoder_reranker.rerank_candidates(query, candidates, top_k)
            except Exception as e:
                print(f"❌ CrossEncoder 리랭킹 실패: {e}")
                print("🔄 LLM 리랭킹으로 fallback...")
                rerank_mode = "llm"  # fallback to LLM
        
        if rerank_mode == "llm" and self.llm_reranker:
            print(f"🔄 LLM 리랭킹 적용 중...")
            try:
                return self.llm_reranker.rerank_candidates(query, candidates, top_k)
            except Exception as e:
                print(f"❌ LLM 리랭킹 실패: {e}")
                print("🚫 리랭킹 비활성화 - 원래 순서 유지")
                return candidates[:top_k]
        
        # 모든 리랭킹 실패시 원래 순서
        print(f"⚠️ 리랭킹 사용 불가 - 원래 순서 유지 (상위 {top_k}개)")
        return candidates[:top_k]
