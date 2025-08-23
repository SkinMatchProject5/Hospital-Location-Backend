"""Query builder for hospital RAG pipeline.

Constructs enriched search queries and extracts region filters.
Designed for Korean dermatology use cases with light heuristics.
"""

from typing import Iterable, Optional, Set, List


_REGIONS: Set[str] = {
    "서울",
    "경기",
    "부산",
    "대구",
    "인천",
    "광주",
    "대전",
    "울산",
    "세종",
    "강원",
    "충북",
    "충남",
    "전북",
    "전남",
    "경북",
    "경남",
    "제주",
}

_DIAG_SYNONYMS = {
    "악성흑색종": ["멜라노마", "melanoma", "흑색종"],
    "기저세포암": ["bcc", "basal cell carcinoma", "기저 세포암"],
    "편평세포암": ["scc", "squamous cell carcinoma", "편평 세포암"],
    "광선각화증": ["actinic keratosis", "ak", "광선 각화증"],
    "보웬병": ["bowen disease", "bowen's disease", "보웬 병"],
}


class QueryBuilder:
    """Query builder with diagnosis synonym expansion and region parsing."""

    def _normalize(self, text: str) -> str:
        return " ".join(text.split()).strip()

    def _expand_diagnosis(self, diagnosis: str) -> List[str]:
        base = self._normalize(diagnosis)
        syns = _DIAG_SYNONYMS.get(base, [])
        tokens = [base] + syns
        # deduplicate while keeping order
        seen = set()
        result = []
        for t in tokens:
            n = self._normalize(t)
            if n and n.lower() not in seen:
                seen.add(n.lower())
                result.append(n)
        return result

    def build_search_query(
        self,
        diagnosis: str,
        description: Optional[str] = None,
        similar_diseases: Optional[Iterable[str]] = None,
    ) -> str:
        parts: List[str] = []
        # diagnosis + synonyms
        parts.extend(self._expand_diagnosis(diagnosis))
        # optional description
        if description:
            parts.append(self._normalize(description))
        # optional similar diseases
        if similar_diseases:
            for d in similar_diseases:
                if d:
                    parts.append(self._normalize(d))
        # join with newlines to bias semantic encoders
        return "\n".join(p for p in parts if p)

    def extract_region_filter(self, user_input: str) -> Optional[str]:
        """Extract a canonical region token from user input.

        Uses substring match for Korean region names.
        Returns the first matching region for simplicity.
        """
        if not user_input:
            return None
        text = user_input
        for region in _REGIONS:
            if region in text:
                return region
        return None
