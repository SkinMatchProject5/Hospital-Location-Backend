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
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"🔍 Query Builder 입력: diagnosis='{diagnosis}', description='{description}', similar='{similar_diseases}'")
        
        # 병원 검색에는 주진단명만 사용 (가장 정확한 매칭을 위해)
        expanded = self._expand_diagnosis(diagnosis)
        logger.info(f"📝 진단명 확장: {expanded}")
        
        # 설명과 유사질환은 병원 검색에서 제외 (노이즈 방지)
        if description:
            logger.info(f"📝 설명 제외됨 (병원 검색 단순화): '{description}'")
        if similar_diseases:
            logger.info(f"📝 유사질환 제외됨 (병원 검색 단순화): {list(similar_diseases)}")
        
        # 진단명과 동의어만으로 쿼리 구성
        final_query = "\n".join(expanded)
        logger.info(f"✅ 최종 쿼리 구성 (진단명만): '{final_query}'")
        return final_query

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
