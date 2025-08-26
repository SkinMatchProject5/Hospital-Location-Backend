"""
Hospital-Location-Backend 데이터 모델
Pydantic 모델 정의
"""

from app.models.requests import SearchRequest
from app.models.responses import SearchResponse, HospitalInfo
from app.models.diagnosis import DiagnosisInfo

__all__ = [
    "SearchRequest",
    "SearchResponse", 
    "HospitalInfo",
    "DiagnosisInfo"
]
