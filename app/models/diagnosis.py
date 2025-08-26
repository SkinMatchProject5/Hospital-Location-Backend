"""
Hospital-Location-Backend 진단 정보 모델
XML 파싱된 진단 데이터 구조
"""

from pydantic import BaseModel, Field
from typing import List, Optional


class SimilarLabel(BaseModel):
    """유사 진단명 정보"""
    
    id_code: str = Field(..., description="진단 코드")
    score: float = Field(..., description="유사도 점수")
    name: str = Field(..., description="진단명")


class DiagnosisInfo(BaseModel):
    """파싱된 진단 정보"""
    
    primary_diagnosis: str = Field(
        ...,
        description="주 진단명",
        min_length=1
    )
    
    primary_score: float = Field(
        ...,
        description="주 진단 신뢰도 점수",
        ge=0.0,
        le=100.0
    )
    
    summary: Optional[str] = Field(
        default=None,
        description="진단 요약/소견"
    )
    
    similar_labels: List[SimilarLabel] = Field(
        default_factory=list,
        description="유사 진단명 목록"
    )
    
    def get_all_diagnoses(self) -> List[str]:
        """주 진단명과 유사 진단명을 모두 반환"""
        diagnoses = [self.primary_diagnosis]
        diagnoses.extend([label.name for label in self.similar_labels])
        return diagnoses
    
    def get_search_text(self) -> str:
        """검색용 텍스트 생성 (진단명만 사용)"""
        text_parts = [self.primary_diagnosis]
        
        # summary는 제외 - 매번 달라져서 일관성 문제 발생
        # if self.summary:
        #     text_parts.append(self.summary)
            
        # 상위 유사 진단명 추가 (점수 기준)
        sorted_similar = sorted(self.similar_labels, key=lambda x: x.score, reverse=True)
        for label in sorted_similar[:3]:  # 상위 3개만
            text_parts.append(label.name)
        
        return " ".join(text_parts)
    
    class Config:
        json_schema_extra = {
            "example": {
                "primary_diagnosis": "광선각화증",
                "primary_score": 85.0,
                "summary": "자외선 노출이 많은 부위인 얼굴에 붉은색의 각질성 반점이 관찰됩니다.",
                "similar_labels": [
                    {
                        "id_code": "1",
                        "score": 30.0,
                        "name": "보웬병"
                    },
                    {
                        "id_code": "2", 
                        "score": 25.0,
                        "name": "기저세포암"
                    }
                ]
            }
        }
