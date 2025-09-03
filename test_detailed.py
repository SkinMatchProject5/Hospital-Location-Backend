#!/usr/bin/env python3
"""병원 백엔드 상세 테스트"""

import requests
import json

def test_embedding_service():
    """임베딩 서비스 테스트"""
    try:
        from app.services.embedding_service import get_embedding_service
        embedding_service = get_embedding_service()
        
        print(f"✅ 임베딩 서비스 인스턴스 생성 성공")
        print(f"   모델: {embedding_service.model}")
        print(f"   차원: {embedding_service.dimension}")
        return True
    except Exception as e:
        print(f"❌ 임베딩 서비스 테스트 실패: {e}")
        return False

def test_xml_parser():
    """XML 파서 테스트"""
    try:
        from app.services.xml_parser import DiagnosisXMLParser
        
        test_xml = """
        <root>
            <label id_code="0" score="85.0">광선각화증</label>
            <summary>자외선 노출이 많은 부위인 얼굴에 붉은색의 각질성 반점이 관찰됩니다.</summary>
            <similar_labels>
                <similar_label id_code="3" score="16.6">보웬병</similar_label>
                <similar_label id_code="1" score="5.7">기저세포암</similar_label>
            </similar_labels>
        </root>
        """
        
        parser = DiagnosisXMLParser()
        diagnosis_info = parser.parse_xml(test_xml)
        
        print(f"✅ XML 파서 테스트 성공:")
        print(f"   진단명: {diagnosis_info.diagnosis}")
        print(f"   신뢰도: {diagnosis_info.confidence_score}")
        print(f"   유사질병 수: {len(diagnosis_info.similar_diseases)}")
        
        return True
    except Exception as e:
        print(f"❌ XML 파서 테스트 실패: {e}")
        return False

def test_qdrant_connection():
    """Qdrant 연결 테스트"""
    try:
        from app.services.qdrant_service import get_qdrant_service
        
        qdrant_service = get_qdrant_service()
        # 연결 테스트는 비동기이므로 여기서는 인스턴스만 생성
        print(f"✅ Qdrant 서비스 인스턴스 생성 성공")
        print(f"   URL: {qdrant_service.url}")
        print(f"   Children Collection: {qdrant_service.children_collection}")
        print(f"   Parents Collection: {qdrant_service.parents_collection}")
        
        return True
    except Exception as e:
        print(f"❌ Qdrant 서비스 테스트 실패: {e}")
        return False

def test_search_service():
    """검색 서비스 테스트"""
    try:
        from app.services.search_service import get_search_service
        
        search_service = get_search_service()
        print(f"✅ 검색 서비스 인스턴스 생성 성공")
        
        return True
    except Exception as e:
        print(f"❌ 검색 서비스 테스트 실패: {e}")
        return False

def test_api_docs():
    """API 문서 확인"""
    try:
        response = requests.get("http://localhost:8002/docs", timeout=5)
        if response.status_code == 200:
            print("✅ API 문서 접근 가능: http://localhost:8002/docs")
            return True
        else:
            print(f"⚠️ API 문서 응답 이상: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ API 문서 접근 실패: {e}")
        return False

if __name__ == "__main__":
    print("🔍 병원 백엔드 상세 테스트 시작\n")
    
    # 1. 개별 서비스 테스트
    print("1️⃣ 임베딩 서비스 테스트:")
    embedding_ok = test_embedding_service()
    print()
    
    print("2️⃣ XML 파서 테스트:")
    xml_ok = test_xml_parser()
    print()
    
    print("3️⃣ Qdrant 서비스 테스트:")
    qdrant_ok = test_qdrant_connection()
    print()
    
    print("4️⃣ 검색 서비스 테스트:")
    search_ok = test_search_service()
    print()
    
    print("5️⃣ API 문서 테스트:")
    docs_ok = test_api_docs()
    print()
    
    # 결과 요약
    if embedding_ok and xml_ok and qdrant_ok and search_ok:
        print("🎉 모든 서비스 테스트 통과!")
    else:
        print("💥 일부 서비스에 문제가 있습니다.")
        if not embedding_ok:
            print("  - 임베딩 서비스 문제")
        if not xml_ok:
            print("  - XML 파서 문제")
        if not qdrant_ok:
            print("  - Qdrant 서비스 문제")
        if not search_ok:
            print("  - 검색 서비스 문제")
