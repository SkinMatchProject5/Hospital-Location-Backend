"""Reranking component for the hospital RAG pipeline.

Supports LLM-only reranking and custom scorer injection for testing.
"""

from typing import Any, Callable, Dict, List, Optional


class LangChainReranker:
    def __init__(
        self,
        model_type: str = "llm",
        llm: Optional[Any] = None,
        scorer: Optional[Callable[[str, str], float]] = None,
    ):
        """Initialize reranker.

        - model_type: kept for compatibility ("llm").
        - llm: an optional LangChain LLM instance (or OpenAI client wrapped) for runtime scoring.
        - scorer: optional callable(query, text)->float used for testing or custom ranking.
        """
        self.model_type = model_type
        self.llm = llm
        self.scorer = scorer

    def rerank_candidates(self, query: str, candidates: List[Dict[str, Any]], top_k: int = 2) -> List[Dict[str, Any]]:
        if not candidates:
            return []

        # Score each candidate
        scored = []
        for c in candidates:
            text = self._candidate_text(c)
            score = self._score(query, text)
            c_with_score = dict(c)
            c_with_score["rerank_score"] = score
            scored.append(c_with_score)

        # Sort by rerank_score desc
        scored.sort(key=lambda x: x.get("rerank_score", 0.0), reverse=True)
        return scored[:top_k]

    def _candidate_text(self, c: Dict[str, Any]) -> str:
        # Prefer fields likely available in search results; fallback to string casting
        for key in ("snippet", "title", "text", "embedding_text"):
            v = c.get(key)
            if isinstance(v, str) and v.strip():
                return v
            if isinstance(v, dict):
                # allow nested snippet structure
                t = v.get("embedding_text") or v.get("title") or v.get("summary")
                if isinstance(t, str):
                    return t
        return str(c)

    def _score(self, query: str, candidate_text: str) -> float:
        # 1) custom scorer if provided (for tests)
        if self.scorer is not None:
            try:
                return float(self.scorer(query, candidate_text))
            except Exception:
                return 0.0

        # 2) LLM-only mode (if llm is available)
        if self.llm is not None:
            prompt = self._build_prompt(query, candidate_text)
            try:
                # Expect a numeric score 0..100 in the first number found
                resp = self.llm.invoke(prompt) if hasattr(self.llm, "invoke") else self.llm(prompt)
                text = getattr(resp, "content", None) or getattr(resp, "text", None) or str(resp)
                import re

                m = re.search(r"(\d{1,3}(?:\.\d+)?)", text)
                if m:
                    val = float(m.group(1))
                    return max(0.0, min(1.0, val / 100.0))
            except Exception:
                return 0.0

        # 3) fallback heuristic
        return 0.0

    def _build_prompt(self, query: str, candidate_text: str) -> str:
        return (
            "당신은 피부과 질환 특화 병원 추천을 위한 평가자입니다.\n"
            "입력된 질의와 후보 텍스트의 관련성을 0~100 점수로만 답하세요.\n"
            "- 질의: "
            f"{query}\n"
            "- 후보: "
            f"{candidate_text}\n"
            "정답 형식: 정수 점수만 출력 (예: 78)"
        )
