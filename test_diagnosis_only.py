#!/usr/bin/env python3
"""진단명만으로 병원 검색 테스트"""

import requests
import json

def test_diagnosis_search(diagnosis_name):
    """특정 진단명으로 병원 검색 테스트"""
    test_xml = f"""<root>
    <diagnosis>{diagnosis_name}</diagnosis>
    <description>상세 설명은 검색에 사용하지 않습니다.</description>
</root>"""
    
    try:
        print(f"🔍 '{diagnosis_name}' 검색 테스트...")
        response = requests.post(
            "http://localhost:8003/api/v1/search/search-ft-xml",
            json={"xml": test_xml},
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            hospital_count = result.get('total_count', 0)
            search_time = result.get('search_time_ms', 0)
            
            print(f"✅ 검색 성공: {hospital_count}개 병원 ({search_time:.1f}ms)")
            
            hospitals = result.get('results', [])
            for i, hospital in enumerate(hospitals[:3], 1):  # 상위 3개만 표시
                name = hospital.get('name', 'N/A')
                score = hospital.get('score', 0.0)
                print(f"   {i}. {name} (점수: {score:.3f})")
            
            return hospital_count > 0
        else:
            print(f"❌ 검색 실패 ({response.status_code}): {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ 검색 요청 실패: {e}")
        return False

if __name__ == "__main__":
    print("🏥 진단명 중심 병원 검색 테스트")
    print("="*50)
    
    # 다양한 진단명으로 테스트
    test_cases = [
        "피부섬유종",
        "광선각화증", 
        "아토피",
        "건선",
        "여드름"
    ]
    
    success_count = 0
    
    for diagnosis in test_cases:
        print(f"\n📋 테스트 {len(test_cases) - test_cases.index(diagnosis)}: {diagnosis}")
        if test_diagnosis_search(diagnosis):
            success_count += 1
        print("-" * 30)
    
    print(f"\n📊 테스트 결과: {success_count}/{len(test_cases)} 성공")
    
    if success_count == len(test_cases):
        print("🎉 모든 진단명 검색 테스트 통과!")
    else:
        print("⚠️ 일부 진단명에서 병원을 찾지 못했습니다.")
