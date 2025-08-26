"""
Hospital-Location-Backend XML 파싱 서비스
AI 분석 백엔드에서 전송된 XML 진단명 파싱
"""

import xml.etree.ElementTree as ET
from typing import Optional, List, Tuple
import logging
from bs4 import BeautifulSoup

from app.models.diagnosis import DiagnosisInfo, SimilarLabel

logger = logging.getLogger(__name__)


class XMLParsingError(Exception):
    """XML 파싱 오류"""
    pass


class DiagnosisXMLParser:
    """XML 진단 데이터 파싱 클래스"""
    
    @staticmethod
    def parse_xml(xml_data: str) -> DiagnosisInfo:
        """
        AI 분석 백엔드에서 전송된 XML을 DiagnosisInfo로 파싱
        
        예상 XML 형식:
        <root>
            <label id_code="0" score="85.0">광선각화증</label>
            <summary>자외선 노출이 많은 부위인 얼굴에 붉은색의 각질성 반점이 관찰됩니다.</summary>
            <similar_labels>
                <similar_label id_code="1" score="30.0">보웬병</similar_label>
                <similar_label id_code="2" score="25.0">기저세포암</similar_label>
            </similar_labels>
        </root>
        
        Args:
            xml_data: XML 문자열
            
        Returns:
            DiagnosisInfo: 파싱된 진단 정보
            
        Raises:
            XMLParsingError: XML 파싱 실패 시
        """
        try:
            # XML 데이터 정리
            xml_data = xml_data.strip()
            if not xml_data:
                raise XMLParsingError("빈 XML 데이터")
            
            logger.debug(f"XML 파싱 시작: {xml_data[:100]}...")
            
            # BeautifulSoup을 사용한 더 관대한 XML 파싱
            soup = BeautifulSoup(xml_data, 'xml')
            root = soup.find('root')
            
            if not root:
                # root 태그가 없으면 전체를 root로 간주
                soup = BeautifulSoup(f"<root>{xml_data}</root>", 'xml')
                root = soup.find('root')
            
            if not root:
                raise XMLParsingError("root 요소를 찾을 수 없습니다")
            
            # 주 진단명 추출
            primary_diagnosis, primary_score = DiagnosisXMLParser._extract_primary_diagnosis(root)
            
            # 요약/소견 추출
            summary = DiagnosisXMLParser._extract_summary(root)
            
            # 유사 진단명 목록 추출
            similar_labels = DiagnosisXMLParser._extract_similar_labels(root)
            
            diagnosis_info = DiagnosisInfo(
                primary_diagnosis=primary_diagnosis,
                primary_score=primary_score,
                summary=summary,
                similar_labels=similar_labels
            )
            
            logger.info(f"✅ XML 파싱 완료: {primary_diagnosis} (신뢰도: {primary_score})")
            logger.debug(f"유사 진단명 {len(similar_labels)}개: {[s.name for s in similar_labels]}")
            
            return diagnosis_info
            
        except Exception as e:
            logger.error(f"❌ XML 파싱 실패: {e}")
            logger.debug(f"실패한 XML: {xml_data}")
            raise XMLParsingError(f"XML 파싱 실패: {e}")
    
    @staticmethod
    def _extract_primary_diagnosis(root) -> Tuple[str, float]:
        """주 진단명과 점수 추출"""
        # <label> 태그에서 주 진단명 추출
        label = root.find('label')
        if not label:
            # label 태그가 없으면 diagnosis 태그 시도
            label = root.find('diagnosis')
        
        if not label:
            raise XMLParsingError("주 진단명(label/diagnosis)을 찾을 수 없습니다")
        
        diagnosis = label.get_text(strip=True) if label else ""
        if not diagnosis:
            raise XMLParsingError("진단명이 비어있습니다")
        
        # 점수 추출
        score_str = label.get('score', '0.0')
        try:
            score = float(score_str)
        except (ValueError, TypeError):
            logger.warning(f"잘못된 점수 형식: {score_str}, 기본값 0.0 사용")
            score = 0.0
        
        return diagnosis, score
    
    @staticmethod
    def _extract_summary(root) -> Optional[str]:
        """요약/소견 추출"""
        summary_element = root.find('summary')
        if not summary_element:
            # description 태그도 시도
            summary_element = root.find('description')
        
        if summary_element:
            summary = summary_element.get_text(strip=True)
            return summary if summary else None
        
        return None
    
    @staticmethod
    def _extract_similar_labels(root) -> List[SimilarLabel]:
        """유사 진단명 목록 추출"""
        similar_labels = []
        
        # <similar_labels> 컨테이너 찾기
        similar_container = root.find('similar_labels')
        if not similar_container:
            # similar_conditions도 시도
            similar_container = root.find('similar_conditions')
        
        if similar_container:
            # <similar_label> 태그들 찾기
            similar_elements = similar_container.find_all('similar_label')
            if not similar_elements:
                # similar_condition도 시도
                similar_elements = similar_container.find_all('similar_condition')
            
            for element in similar_elements:
                try:
                    name = element.get_text(strip=True)
                    if not name:
                        continue
                    
                    id_code = element.get('id_code', 'unknown')
                    score_str = element.get('score', '0.0')
                    
                    try:
                        score = float(score_str)
                    except (ValueError, TypeError):
                        logger.warning(f"잘못된 유사질병 점수: {score_str}")
                        score = 0.0
                    
                    similar_label = SimilarLabel(
                        id_code=id_code,
                        score=score,
                        name=name
                    )
                    similar_labels.append(similar_label)
                    
                except Exception as e:
                    logger.warning(f"유사 진단명 파싱 실패: {e}")
                    continue
        
        # 점수 기준으로 정렬 (높은 점수부터)
        similar_labels.sort(key=lambda x: x.score, reverse=True)
        
        return similar_labels


# 편의 함수
def parse_diagnosis_xml(xml_data: str) -> DiagnosisInfo:
    """XML 진단 데이터 파싱 편의 함수"""
    parser = DiagnosisXMLParser()
    return parser.parse_xml(xml_data)
