#!/usr/bin/env python3
"""
병원 검색 백엔드 스모크 테스트
BACKEND_PLAN.md 사양에 따른 기본 동작 확인
"""

import sys
import json
import requests
import time
from typing import Dict, Any

def test_health_endpoint(base_url: str) -> bool:
    """헬스체크 엔드포인트 테스트"""
    try:
        response = requests.get(f"{base_url}/health", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Health Check: {data.get('status')}")
            print(f"   Qdrant: {data.get('qdrant_status')}")
            print(f"   Reranker: {data.get('reranker_status')}")
            print(f"   Uptime: {data.get('uptime_seconds', 0):.1f}s")
            return data.get('status') == 'healthy'
        else:
            print(f"❌ Health Check 실패: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Health Check 오류: {e}")
        return False

def test_search_ft_xml_endpoint(base_url: str) -> bool:
    """FT XML 검색 엔드포인트 테스트"""
    try:
        # 테스트용 XML (실제 FT 모델 출력 형식)
        test_xml = """
        <root>
            <label>악성흑색종</label>
            <summary>환자가 피부에 검은 점이 생기고 크기가 변한다고 호소</summary>
            <similar>멜라노마, 흑색종, melanoma</similar>
        </root>
        """
        
        payload = {
            "xml": test_xml.strip(),
            "rerank_mode": "ce",
            "top_k": 24,
            "group_size": 8,
            "final_k": 2
        }
        
        print("🔄 FT XML 검색 테스트 중...")
        start_time = time.time()
        
        response = requests.post(
            f"{base_url}/search-ft-xml",
            json=payload,
            timeout=30  # 충분한 타임아웃
        )
        
        elapsed = time.time() - start_time
        
        if response.status_code == 200:
            data = response.json()
            results = data.get('results', [])
            meta = data.get('meta', {})
            
            print(f"✅ FT XML 검색 성공")
            print(f"   결과 수: {len(results)}")
            print(f"   응답 시간: {elapsed:.2f}s ({meta.get('elapsed_ms', 0)}ms)")
            print(f"   후보 수: {meta.get('candidates', 0)}")
            print(f"   리랭크 모드: {meta.get('rerank_mode')}")
            
            # 결과 샘플 출력
            for i, result in enumerate(results[:2]):
                parent = result.get('parent', {})
                child = result.get('child', {})
                scores = result.get('scores', {})
                
                print(f"   [{i+1}] {parent.get('name', '알 수 없는 병원')}")
                print(f"       지역: {parent.get('region', '')}")
                print(f"       치료: {child.get('title', '')}")
                print(f"       점수: {scores.get('combined', 0):.3f}")
            
            return len(results) > 0
            
        else:
            print(f"❌ FT XML 검색 실패: {response.status_code}")
            try:
                error_data = response.json()
                print(f"   오류: {error_data}")
            except:
                print(f"   오류: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ FT XML 검색 오류: {e}")
        return False

def test_agent_query_endpoint(base_url: str) -> bool:
    """에이전트 쿼리 엔드포인트 테스트"""
    try:
        payload = {
            "message": "악성흑색종 치료 병원 추천해주세요",
            "k": 3
        }
        
        print("🔄 에이전트 쿼리 테스트 중...")
        start_time = time.time()
        
        response = requests.post(
            f"{base_url}/agent-query",
            json=payload,
            timeout=30
        )
        
        elapsed = time.time() - start_time
        
        if response.status_code == 200:
            data = response.json()
            answer = data.get('answer', '')
            sources = data.get('sources', [])
            meta = data.get('meta', {})
            
            print(f"✅ 에이전트 쿼리 성공")
            print(f"   응답: {answer}")
            print(f"   소스 수: {len(sources)}")
            print(f"   응답 시간: {elapsed:.2f}s ({meta.get('elapsed_ms', 0)}ms)")
            
            for i, source in enumerate(sources[:2]):
                print(f"   [{i+1}] {source.get('source', '')}")
                print(f"       {source.get('snippet', '')}")
            
            return len(sources) > 0
            
        else:
            print(f"❌ 에이전트 쿼리 실패: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ 에이전트 쿼리 오류: {e}")
        return False

def main():
    """메인 테스트 실행"""
    base_url = "http://localhost:8002"
    
    if len(sys.argv) > 1:
        base_url = sys.argv[1]
    
    print(f"🧪 병원 검색 백엔드 스모크 테스트")
    print(f"📍 대상 서버: {base_url}")
    print(f"⏰ 테스트 시작: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # 테스트 실행
    tests = [
        ("Health Check", lambda: test_health_endpoint(base_url)),
        ("FT XML Search", lambda: test_search_ft_xml_endpoint(base_url)),
        ("Agent Query", lambda: test_agent_query_endpoint(base_url))
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"🔍 {test_name} 테스트...")
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"❌ {test_name} 예외 발생: {e}")
            results.append((test_name, False))
        print()
    
    # 결과 요약
    print("📊 테스트 결과 요약:")
    passed = 0
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"   {test_name}: {status}")
        if success:
            passed += 1
    
    print(f"\n🎯 총 {passed}/{len(results)} 개 테스트 통과")
    
    if passed == len(results):
        print("✅ 모든 스모크 테스트 통과!")
        sys.exit(0)
    else:
        print("❌ 일부 테스트 실패!")
        sys.exit(1)

if __name__ == "__main__":
    main()