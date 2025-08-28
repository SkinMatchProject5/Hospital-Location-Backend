"""
CrossEncoder 기반 리랭커 (BGE 모델)
HybridSearcher에서 분리하여 파이프라인에서도 사용 가능하도록 함
"""

from typing import Any, Dict

# 2025년 최고 성능 리랭커 통합
try:
    from sentence_transformers import CrossEncoder
    RERANKER_AVAILABLE = True
except ImportError:
    RERANKER_AVAILABLE = False


class CrossEncoderReranker:
    """CrossEncoder(BGE) 기반 리랭커"""
    
    def __init__(self, model_name: str = "BAAI/bge-reranker-base"):
        self.model = None
        self.model_name = model_name
        self._load_model()
    
    def _load_model(self):
        """리랭커 모델 로딩"""
        if not RERANKER_AVAILABLE:
            print("⚠️ sentence_transformers 없음 - CrossEncoder 리랭킹 비활성화")
            return
            
        try:
            print(f"🔄 {self.model_name} 로딩 중...")
            self.model = CrossEncoder(self.model_name)
            print("✅ CrossEncoder 리랭커 로딩 완료!")
        except Exception as e:
            print(f"❌ CrossEncoder 리랭커 로딩 실패: {e}")
            self.model = None
    
    def rerank_candidates(self, query: str, candidates: list[Dict[str, Any]], 
                         top_k: int = 10) -> list[Dict[str, Any]]:
        """BGE CrossEncoder 리랭킹"""
        if not self.model or not candidates:
            print(f"⚠️ CrossEncoder 사용 불가 - 원래 순서 유지 (상위 {top_k}개)")
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
            
            # 점수 적용 및 정규화 (0-1 범위)
            for i, candidate in enumerate(candidates):
                raw_score = float(scores[i])
                # BGE 점수를 0-1로 정규화 (보통 -10~10 범위)
                normalized_score = max(0.0, min(1.0, (raw_score + 10) / 20))
                candidate["rerank_score"] = normalized_score
            
            # 정렬
            candidates.sort(key=lambda x: x.get("rerank_score", 0), reverse=True)
            
            print(f"✅ CrossEncoder 리랭킹 완료: {len(candidates)}개 → {top_k}개")
            return candidates[:top_k]
            
        except Exception as e:
            print(f"❌ CrossEncoder 리랭킹 오류: {e}")
            return candidates[:top_k]
    
    def _extract_text(self, candidate: Dict[str, Any]) -> str:
        """후보에서 텍스트 추출"""
        # payload 구조에서 텍스트 추출
        if "payload" in candidate:
            payload = candidate["payload"]
            snippet = payload.get("snippet", {})
            
            # embedding_text가 가장 좋은 텍스트
            if "embedding_text" in snippet:
                return snippet["embedding_text"]
            
            # title도 좋은 대안
            if "title" in snippet:
                return snippet["title"]
        
        # 다른 필드들도 시도
        for key in ["embedding_text", "title", "snippet", "text"]:
            if key in candidate:
                value = candidate[key]
                if isinstance(value, dict):
                    inner = value.get("embedding_text") or value.get("title") or str(value)
                    if inner.strip():
                        return inner
                elif isinstance(value, str) and value.strip():
                    return value
        
        return str(candidate)[:200]  # 최대 200자로 제한