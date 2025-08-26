"""
Hospital-Location-Backend 요청 모델
API 요청 데이터 구조 정의
"""

from pydantic import BaseModel, Field
from typing import Optional


class SearchRequest(BaseModel):
    """병원 검색 요청 모델"""
    
    xml: str = Field(
        ...,
        description="AI 분석 백엔드에서 전송된 XML 진단 데이터",
        min_length=1
    )
    
    top_k: Optional[int] = Field(
        default=24,
        description="초기 후보 검색 개수",
        ge=1,
        le=100
    )
    
    final_k: Optional[int] = Field(
        default=2,
        description="최종 반환 결과 개수",
        ge=1,
        le=20
    )
    
    rerank_mode: Optional[str] = Field(
        default="ce",
        description="리랭킹 모드 (ce: CrossEncoder, llm: LLM)",
        pattern="^(ce|llm)$"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "xml": """<root>
    <label id_code="0" score="85.0">광선각화증</label>
    <summary>자외선 노출이 많은 부위인 얼굴에 붉은색의 각질성 반점이 관찰됩니다.</summary>
    <similar_labels>
        <similar_label id_code="1" score="30.0">보웬병</similar_label>
        <similar_label id_code="2" score="25.0">기저세포암</similar_label>
    </similar_labels>
</root>""",
                "top_k": 24,
                "final_k": 2,
                "rerank_mode": "ce"
            }
        }
