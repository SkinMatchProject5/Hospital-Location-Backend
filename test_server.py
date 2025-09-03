#!/usr/bin/env python3
"""병원 백엔드 서버 상태 테스트"""

import requests
import json

def test_server_health():
    """서버 헬스 체크"""
    try:
        response = requests.get("http://localhost:8002/health", timeout=5)
        print(f"🏥 서버 상태: {response.status_code}")
        if response.status_code == 200:
            print("✅ 서버 정상 작동")
            print(f"응답: {response.json()}")
            return True
        else:
            print(f"⚠️ 서버 응답 이상: {response.text}")
            return False
    except Exception as e:
        print(f"❌ 서버 연결 실패: {e}")
        return False

def test_search_endpoint():
    """검색 엔드포인트 테스트"""
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
    
    try:
        response = requests.post(
            "http://localhost:8002/api/v1/search/search-ft-xml",
            json={"xml": test_xml},
            timeout=30
        )
        print(f"🔍 검색 테스트: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print("✅ 검색 성공")
            print(f"병원 수: {result.get('total_count', 0)}")
            hospitals = result.get('results', [])
            if hospitals:
                print("🏥 첫 번째 병원:")
                first_hospital = hospitals[0]
                print(f"   이름: {first_hospital.get('name', 'N/A')}")
                print(f"   전화: {first_hospital.get('tell', 'N/A')}")
                print(f"   주소: {first_hospital.get('addr', 'N/A')}")
            return True
        else:
            print(f"❌ 검색 실패: {response.text}")
            return False
    except Exception as e:
        print(f"❌ 검색 요청 실패: {e}")
        return False

if __name__ == "__main__":
    print("🚀 병원 백엔드 테스트 시작\n")
    
    # 1. 헬스 체크
    health_ok = test_server_health()
    print()
    
    # 2. 검색 테스트 (서버가 살아있을 때만)
    if health_ok:
        search_ok = test_search_endpoint()
        print()
        
        if search_ok:
            print("🎉 모든 테스트 통과!")
        else:
            print("💥 검색 테스트 실패")
    else:
        print("💥 서버가 실행되지 않았습니다")
