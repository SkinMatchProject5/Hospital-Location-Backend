#!/usr/bin/env python3
"""
병원 검색 API 테스트 스크립트
"""

import requests
import json

def test_search_api():
    # 사마귀 검색 테스트
    xml_data = '''<root>
    <label>사마귀</label>
    <summary>사마귀 치료가 필요한 환자</summary>
    <similar>사마귀</similar>
    </root>'''

    data = {
        'xml': xml_data,
        'rerank_mode': 'off',
        'top_k': 24,
        'group_size': 10,
        'final_k': 2
    }

    print("🔍 사마귀 검색 테스트 시작...")
    print(f"전송 데이터: {json.dumps(data, indent=2, ensure_ascii=False)}")
    
    try:
        response = requests.post('http://localhost:8002/search-ft-xml', json=data)
        print(f'응답 상태: {response.status_code}')
        
        if response.status_code == 200:
            result = response.json()
            print(f'결과 수: {len(result.get("results", []))}')
            print("\n🏥 추천된 병원들:")
            for i, r in enumerate(result.get('results', [])):
                hospital = r.get('parent', {})
                contacts = hospital.get('contacts', {})
                print(f'{i+1}. {hospital.get("name", "알수없음")}')
                print(f'   주소: {contacts.get("addr", "주소없음")}')
                print(f'   전화: {contacts.get("tel", "전화없음")}')
                print(f'   전문분야: {hospital.get("specialties", [])}')
                print(f'   점수: {r.get("scores", {})}')
                print()
        else:
            print(f'오류 응답: {response.text}')
            
    except Exception as e:
        print(f'API 호출 오류: {e}')

def test_dermatofibroma_search():
    # 피부섬유종 검색 테스트 (프론트엔드에서 나오는 엉뚱한 결과)
    xml_data = '''<root>
    <label>피부섬유종</label>
    <summary>피부섬유종 치료가 필요한 환자</summary>
    <similar>피부섬유종</similar>
    </root>'''

    data = {
        'xml': xml_data,
        'rerank_mode': 'off',
        'top_k': 24,
        'group_size': 10,
        'final_k': 2
    }

    print("\n🔍 피부섬유종 검색 테스트 시작...")
    
    try:
        response = requests.post('http://localhost:8002/search-ft-xml', json=data)
        print(f'응답 상태: {response.status_code}')
        
        if response.status_code == 200:
            result = response.json()
            print(f'결과 수: {len(result.get("results", []))}')
            print("\n🏥 추천된 병원들:")
            for i, r in enumerate(result.get('results', [])):
                hospital = r.get('parent', {})
                contacts = hospital.get('contacts', {})
                print(f'{i+1}. {hospital.get("name", "알수없음")}')
                print(f'   주소: {contacts.get("addr", "주소없음")}')
                print(f'   전화: {contacts.get("tel", "전화없음")}')
                print(f'   전문분야: {hospital.get("specialties", [])}')
                print()
        else:
            print(f'오류 응답: {response.text}')
            
    except Exception as e:
        print(f'API 호출 오류: {e}')

if __name__ == "__main__":
    test_search_api()
    test_dermatofibroma_search()
