"""
Hospital-Location-Backend 통합 검색 서비스
XML 파싱부터 하이브리드 검색까지 전체 검색 플로우 관리
"""

import time
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

from app.models.requests import SearchRequest
from app.models.responses import SearchResponse, HospitalInfo
from app.models.diagnosis import DiagnosisInfo
from app.services.xml_parser import DiagnosisXMLParser, XMLParsingError
from app.services.hybrid_search import HybridSearchEngine, get_hybrid_search_engine, HybridSearchError
from app.core.config import settings

logger = logging.getLogger(__name__)


class SearchServiceError(Exception):
    """검색 서비스 오류"""
    pass


class SearchService:
    """통합 검색 서비스"""
    
    def __init__(self, hybrid_search_engine: Optional[HybridSearchEngine] = None):
        """검색 서비스 초기화"""
        self.xml_parser = DiagnosisXMLParser()
        self.hybrid_search_engine = hybrid_search_engine or get_hybrid_search_engine()
        
        logger.info("🔧 검색 서비스 초기화 완료")
    
    async def initialize(self):
        """검색 서비스 초기화 (비동기)"""
        try:
            await self.hybrid_search_engine.initialize()
            logger.info("✅ 검색 서비스 준비 완료")
        except Exception as e:
            logger.error(f"❌ 검색 서비스 초기화 실패: {e}")
            raise SearchServiceError(f"초기화 실패: {e}")
    
    async def search_hospitals_from_xml(self,
                                      xml_data: str,
                                      top_k: int = None,
                                      final_k: int = None,
                                      rerank_mode: str = "ce") -> SearchResponse:
        """
        XML 진단 데이터로부터 병원 검색
        
        Args:
            xml_data: AI 분석 백엔드에서 전송된 XML 데이터
            top_k: 초기 후보 수
            final_k: 최종 결과 수
            rerank_mode: 리랭킹 모드 (현재는 미사용)
            
        Returns:
            SearchResponse: 검색 결과
            
        Raises:
            SearchServiceError: 검색 실패 시
        """
        start_time = time.time()
        
        try:
            logger.info("🏥 병원 검색 요청 처리 시작")
            
            # 기본값 설정
            if top_k is None:
                top_k = settings.DEFAULT_TOP_K
            if final_k is None:
                final_k = settings.DEFAULT_FINAL_K
            
            # 1. XML 파싱
            logger.debug("1️⃣ XML 파싱 단계")
            logger.info(f"📄 받은 XML 내용: {xml_data[:200]}...")  # 첫 200글자만 로깅
            diagnosis_info = self._parse_xml_safe(xml_data)
            
            # 2. 하이브리드 검색 수행
            logger.debug("2️⃣ 하이브리드 검색 단계")
            search_results = await self.hybrid_search_engine.search(
                diagnosis_info=diagnosis_info,
                top_k=top_k,
                final_k=final_k
            )
            
            # 3. 응답 형식 변환
            logger.debug("3️⃣ 응답 형식 변환 단계")
            hospital_list = self._convert_to_hospital_info_list(search_results)
            
            # 4. 검색 시간 계산
            search_time_ms = (time.time() - start_time) * 1000
            
            # 5. 응답 생성
            response = SearchResponse(
                results=hospital_list,
                meta={
                    "embedding_model": settings.EMBEDDING_MODEL,
                    "search_strategy": "hybrid_cosine_bm25",
                    "cosine_weight": settings.COSINE_WEIGHT,
                    "bm25_weight": settings.BM25_WEIGHT,
                    "rerank_mode": rerank_mode
                },
                query_info={
                    "diagnosis": diagnosis_info.primary_diagnosis,
                    "summary": diagnosis_info.summary,
                    "similar_conditions": [label.name for label in diagnosis_info.similar_labels],
                    "primary_score": diagnosis_info.primary_score
                },
                total_count=len(hospital_list),
                search_time_ms=search_time_ms,
                timestamp=datetime.now()
            )
            
            logger.info(f"✅ 병원 검색 완료: {len(hospital_list)}개 병원, {search_time_ms:.1f}ms")
            
            return response
            
        except XMLParsingError as e:
            logger.error(f"❌ XML 파싱 오류: {e}")
            raise SearchServiceError(f"XML 파싱 실패: {e}")
            
        except HybridSearchError as e:
            logger.error(f"❌ 하이브리드 검색 오류: {e}")
            raise SearchServiceError(f"검색 실패: {e}")
            
        except Exception as e:
            logger.error(f"❌ 예상치 못한 오류: {e}")
            raise SearchServiceError(f"검색 중 오류 발생: {e}")
    
    def _parse_xml_safe(self, xml_data: str) -> DiagnosisInfo:
        """안전한 XML 파싱 (오류 처리 포함)"""
        try:
            return self.xml_parser.parse_xml(xml_data)
        except XMLParsingError:
            raise  # XML 파싱 오류는 그대로 전파
        except Exception as e:
            logger.error(f"❌ XML 파싱 중 예상치 못한 오류: {e}")
            raise XMLParsingError(f"XML 파싱 중 오류: {e}")
    
    def _convert_to_hospital_info_list(self, 
                                     search_results: List[Dict[str, Any]]) -> List[HospitalInfo]:
        """
        검색 결과를 HospitalInfo 리스트로 변환
        프론트엔드에서 요구하는 형식: name, tell, addr, url
        """
        hospital_list = []
        
        for result in search_results:
            try:
                # Parent와 Child 정보 추출
                parent_data = result.get('parent', {})
                child_data = result.get('child', {})
                scores = result.get('scores', {})
                
                # 실제 Qdrant 원시 데이터 로깅
                logger.debug(f"🔍 Parent 데이터: {parent_data}")
                logger.debug(f"🔍 Child 데이터: {child_data}")
                
                # 병원명 추출 (실제 데이터 구조에 맞게 수정)
                name = (
                    parent_data.get('name') or 
                    (child_data.get('snippet', {}).get('title')) or
                    child_data.get('title') or 
                    child_data.get('name') or 
                    '병원명 없음'
                )
                
                # 연락처 추출
                tell = self._extract_contact_info(parent_data, child_data)
                
                # 주소 추출
                addr = self._extract_address_info(parent_data, child_data)
                
                # URL 추출
                url = self._extract_url_info(parent_data, child_data)
                
                # 전문 분야/질환 추출
                specialties = self._extract_specialties_info(parent_data, child_data)
                
                # 실제 추출된 정보 로깅
                logger.info(f"🏥 추출된 병원 정보:")
                logger.info(f"   Name: {name}")
                logger.info(f"   Tell: {tell}")
                logger.info(f"   Addr: {addr}")
                logger.info(f"   URL: {url}")
                logger.info(f"   Specialties: {specialties}")
                logger.info(f"   Score: {scores.get('hybrid', 0.0)}")
                
                # HospitalInfo 객체 생성
                hospital_info = HospitalInfo(
                    name=name,
                    tell=tell,
                    addr=addr,
                    url=url,
                    specialties=specialties,
                    score=scores.get('hybrid', 0.0)
                )
                
                hospital_list.append(hospital_info)
                
            except Exception as e:
                logger.warning(f"병원 정보 변환 실패: {e}")
                continue
        
        logger.info(f"📊 최종 변환된 병원 수: {len(hospital_list)}")
        return hospital_list
    
    def _extract_contact_info(self, parent_data: Dict, child_data: Dict) -> Optional[str]:
        """연락처 정보 추출 (실제 데이터 구조에 맞게 수정)"""
        # contacts 객체에서 먼저 시도 (실제 데이터는 여기에 있음)
        contacts = parent_data.get('contacts', {})
        if isinstance(contacts, dict):
            # 실제 데이터에서 사용되는 필드명
            contact_fields = ['tel', 'tell', 'phone', 'contact', 'telephone']
            for field in contact_fields:
                value = contacts.get(field)
                if value and str(value).strip():
                    return str(value).strip()
        
        # Parent 데이터에서 직접 시도 (백업)
        contact_fields = ['tell', 'tel', 'phone', 'contact', 'telephone']
        for field in contact_fields:
            value = parent_data.get(field)
            if value and str(value).strip():
                return str(value).strip()
        
        # Child 데이터에서 시도 (백업)
        for field in contact_fields:
            value = child_data.get(field)
            if value and str(value).strip():
                return str(value).strip()
        
        return None
    
    def _extract_address_info(self, parent_data: Dict, child_data: Dict) -> Optional[str]:
        """주소 정보 추출 (실제 데이터 구조에 맞게 수정)"""
        # contacts 객체에서 먼저 시도 (실제 데이터는 여기에 있음)
        contacts = parent_data.get('contacts', {})
        if isinstance(contacts, dict):
            address_fields = ['addr', 'address', 'location', 'place']
            for field in address_fields:
                value = contacts.get(field)
                if value and str(value).strip():
                    return str(value).strip()
        
        # Parent 데이터에서 직접 시도 (백업)
        address_fields = ['addr', 'address', 'location', 'place']
        for field in address_fields:
            value = parent_data.get(field)
            if value and str(value).strip():
                return str(value).strip()
        
        # Child 데이터에서 시도 (백업)
        for field in address_fields:
            value = child_data.get(field)
            if value and str(value).strip():
                return str(value).strip()
        
        return None
    
    def _extract_url_info(self, parent_data: Dict, child_data: Dict) -> Optional[str]:
        """URL 정보 추출 (실제 데이터 구조에 맞게 수정)"""
        # contacts 객체에서 먼저 시도 (실제 데이터는 여기에 있음)
        contacts = parent_data.get('contacts', {})
        if isinstance(contacts, dict):
            url_fields = ['url', 'website', 'homepage', 'link']
            for field in url_fields:
                value = contacts.get(field)
                if value and str(value).strip():
                    url_str = str(value).strip()
                    # HTTP 프로토콜 확인
                    if url_str.startswith(('http://', 'https://')):
                        return url_str
                    elif url_str.startswith('www.'):
                        return f"https://{url_str}"
                    elif '.' in url_str:  # 도메인으로 보이는 경우
                        return f"https://{url_str}"
        
        # Parent 데이터에서 직접 시도 (백업)
        url_fields = ['url', 'website', 'homepage', 'link']
        for field in url_fields:
            value = parent_data.get(field)
            if value and str(value).strip():
                url_str = str(value).strip()
                if url_str.startswith(('http://', 'https://')):
                    return url_str
                elif url_str.startswith('www.'):
                    return f"https://{url_str}"
                elif '.' in url_str:
                    return f"https://{url_str}"
        
        # Child 데이터에서 시도 (백업)
        for field in url_fields:
            value = child_data.get(field)
            if value and str(value).strip():
                url_str = str(value).strip()
                if url_str.startswith(('http://', 'https://')):
                    return url_str
                elif url_str.startswith('www.'):
                    return f"https://{url_str}"
                elif '.' in url_str:
                    return f"https://{url_str}"
        
        return None
    
    def _extract_specialties_info(self, parent_data: Dict, child_data: Dict) -> Optional[List[str]]:
        """진단/치료하는 구체적인 질환명 추출 (진료과목 제외)"""
        diseases = []
        
        # Child 데이터에서 질환 정보 추출 (가장 중요)
        # topic에서 질환명 추출
        child_topic = child_data.get('topic', {})
        if isinstance(child_topic, dict):
            disease_name = child_topic.get('name')
            if disease_name and self._is_disease_name(disease_name):
                diseases.append(disease_name)
            
            # aliases도 추가 (영문명 등)
            aliases = child_topic.get('aliases', [])
            if isinstance(aliases, list):
                for alias in aliases:
                    if alias and self._is_disease_name(alias):
                        diseases.append(alias)
        
        # filters에서 disease 정보 추출
        filters = child_data.get('filters', {})
        if isinstance(filters, dict):
            disease = filters.get('disease')
            if disease and self._is_disease_name(disease):
                diseases.append(disease)
        
        # snippet에서 추가 정보 추출
        snippet = child_data.get('snippet', {})
        if isinstance(snippet, dict):
            title = snippet.get('title', '')
            if title:
                # 제목에서 질환명 추출 (괄호 안의 내용)
                import re
                bracket_content = re.findall(r'\(([^)]+)\)', title)
                for content in bracket_content:
                    if self._is_disease_name(content):
                        diseases.append(content)
        
        # Parent 데이터에서 질환 관련 정보만 추출
        parent_specialties = parent_data.get('specialties', [])
        if isinstance(parent_specialties, list):
            for spec in parent_specialties:
                if spec and self._is_disease_name(spec):
                    diseases.append(spec)
        elif isinstance(parent_specialties, str) and self._is_disease_name(parent_specialties):
            diseases.append(parent_specialties)
        
        # 중복 제거 및 정리
        unique_diseases = []
        seen = set()
        for disease in diseases:
            if disease and str(disease).strip() and str(disease).strip() not in seen:
                cleaned = str(disease).strip()
                unique_diseases.append(cleaned)
                seen.add(cleaned)
        
        return unique_diseases if unique_diseases else None
    
    def _is_disease_name(self, text: str) -> bool:
        """질환명인지 판단 (진료과목 제외)"""
        if not text or not str(text).strip():
            return False
        
        text_lower = str(text).strip().lower()
        
        # 진료과목 제외
        department_keywords = [
            '과', '센터', 'center', 'clinic', 'department', 
            '피부과', '성형외과', '외과', '내과', '소아과',
            'dermatology', 'surgery', 'plastic', 'medical'
        ]
        
        for keyword in department_keywords:
            if keyword in text_lower:
                return False
        
        # 너무 짧은 단어 제외
        if len(str(text).strip()) < 2:
            return False
            
        return True


# 글로벌 검색 서비스 인스턴스
_search_service: Optional[SearchService] = None


def get_search_service() -> SearchService:
    """검색 서비스 싱글톤 인스턴스 반환"""
    global _search_service
    if _search_service is None:
        _search_service = SearchService()
    return _search_service
