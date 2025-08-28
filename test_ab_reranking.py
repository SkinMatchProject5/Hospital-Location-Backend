#!/usr/bin/env python3
"""
A/B 리랭킹 테스트 스크립트 (BACKEND_PLAN.md)

테스트 모드:
- 기준선(리랭크 off) vs LLM-only vs CrossEncoder  
- 지표: Top-1/Top-2 정확도, 교체율, p95 지연
- 15개 질병 × 3개 모드 = 45개 테스트 케이스

정답지: children.jsonl 기반으로 각 질병마다 2개 병원
"""

import os
import sys
import json
import time
import statistics
import requests
from datetime import datetime
from typing import Dict, List, Any, Tuple
from collections import defaultdict

# 현재 디렉토리를 파이썬 경로에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def load_ground_truth() -> Dict[str, Dict[str, Any]]:
    """최신 정답지 로드"""
    eval_dir = "eval_data"
    if not os.path.exists(eval_dir):
        print(f"❌ {eval_dir} 디렉토리를 찾을 수 없습니다.")
        return {}
    
    # 최신 정답지 파일 찾기
    gt_files = [f for f in os.listdir(eval_dir) if f.startswith("evaluation_queries_")]
    if not gt_files:
        print("❌ 정답지 파일을 찾을 수 없습니다.")
        return {}
    
    latest_file = sorted(gt_files)[-1]
    gt_path = os.path.join(eval_dir, latest_file)
    
    with open(gt_path, 'r', encoding='utf-8') as f:
        queries = json.load(f)
    
    # 질병명을 키로 하는 딕셔너리로 변환
    ground_truth = {q['disease']: q for q in queries}
    print(f"✅ 정답지 로드 완료: {len(ground_truth)}개 질병")
    
    return ground_truth

def test_rerank_mode(base_url: str, disease: str, rerank_mode: str, timeout: int = 30) -> Dict[str, Any]:
    """특정 리랭킹 모드로 검색 테스트"""
    # FT XML 형식으로 요청 구성
    test_xml = f"""
    <root>
        <label>{disease}</label>
        <summary>{disease} 치료가 필요한 환자</summary>
        <similar>{disease}</similar>
    </root>
    """
    
    payload = {
        "xml": test_xml.strip(),
        "rerank_mode": rerank_mode,
        "top_k": 24,
        "group_size": 10,
        "final_k": 2  # 최종 2개 병원
    }
    
    start_time = time.time()
    
    try:
        response = requests.post(
            f"{base_url}/search-ft-xml",
            json=payload,
            timeout=timeout
        )
        
        elapsed_ms = (time.time() - start_time) * 1000
        
        if response.status_code == 200:
            data = response.json()
            results = data.get('results', [])
            meta = data.get('meta', {})
            
            return {
                "success": True,
                "results": results,
                "meta": meta,
                "response_time_ms": elapsed_ms,
                "api_response_time_ms": meta.get('elapsed_ms', elapsed_ms)
            }
        else:
            return {
                "success": False,
                "error": f"HTTP {response.status_code}",
                "response_time_ms": elapsed_ms
            }
            
    except requests.Timeout:
        return {
            "success": False,
            "error": "Timeout",
            "response_time_ms": timeout * 1000
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "response_time_ms": (time.time() - start_time) * 1000
        }

def evaluate_accuracy(results: List[Dict], expected_hospitals: List[str], expected_parent_ids: List[str]) -> Dict[str, float]:
    """정확도 평가"""
    if not results or not expected_hospitals:
        return {"top1_accuracy": 0.0, "top2_accuracy": 0.0, "recall": 0.0}
    
    # 결과에서 병원명과 parent_id 추출
    result_hospitals = []
    result_parent_ids = []
    
    for r in results[:2]:  # Top-2만 평가
        parent = r.get('parent', {})
        result_hospitals.append(parent.get('name', ''))
        result_parent_ids.append(r.get('parent_id', parent.get('id', '')))
    
    # Top-1 정확도: 첫 번째 결과가 정답에 포함되는가
    top1_match = False
    if result_parent_ids and result_parent_ids[0] in expected_parent_ids:
        top1_match = True
    
    # Top-2 정확도: 상위 2개 결과 중 정답이 포함되는가
    top2_matches = 0
    for pid in result_parent_ids[:2]:
        if pid in expected_parent_ids:
            top2_matches += 1
    
    top2_accuracy = top2_matches / min(len(expected_parent_ids), 2)
    recall = top2_matches / len(expected_parent_ids)
    
    return {
        "top1_accuracy": 1.0 if top1_match else 0.0,
        "top2_accuracy": top2_accuracy,
        "recall": recall,
        "matched_hospitals": top2_matches
    }

def run_ab_test(base_url: str = "http://localhost:8002") -> Dict[str, Any]:
    """A/B 리랭킹 테스트 실행"""
    print(f"🧪 A/B 리랭킹 테스트 시작")
    print(f"📍 대상 서버: {base_url}")
    print(f"⏰ 시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # 정답지 로드
    ground_truth = load_ground_truth()
    if not ground_truth:
        print("❌ 정답지 로드 실패")
        return {}
    
    # 테스트 모드
    rerank_modes = ["off", "llm", "ce"]  # BACKEND_PLAN.md 사양
    diseases = list(ground_truth.keys())
    
    print(f"🔬 테스트 설정:")
    print(f"   - 리랭킹 모드: {rerank_modes}")
    print(f"   - 테스트 질병: {len(diseases)}개")
    print(f"   - 총 테스트 케이스: {len(diseases) * len(rerank_modes)}개")
    print()
    
    # 결과 저장용
    all_results = []
    mode_stats = {mode: {"response_times": [], "accuracies": []} for mode in rerank_modes}
    
    # 각 질병에 대해 3개 모드 테스트
    for i, disease in enumerate(diseases):
        expected = ground_truth[disease]
        expected_hospitals = expected.get('expected_top_k', expected.get('expected_hospitals', []))
        expected_parent_ids = expected.get('expected_parent_ids', [])
        
        print(f"[{i+1}/{len(diseases)}] 🦠 {disease} 테스트...")
        print(f"   정답 병원: {', '.join(expected_hospitals)}")
        
        disease_results = []
        
        for mode in rerank_modes:
            print(f"   🔄 {mode.upper()} 모드 테스트 중...")
            
            test_result = test_rerank_mode(base_url, disease, mode)
            
            if test_result['success']:
                accuracy = evaluate_accuracy(
                    test_result['results'], 
                    expected_hospitals, 
                    expected_parent_ids
                )
                
                result_entry = {
                    "disease": disease,
                    "rerank_mode": mode,
                    "accuracy": accuracy,
                    "response_time_ms": test_result['response_time_ms'],
                    "api_response_time_ms": test_result['api_response_time_ms'],
                    "results": test_result['results'][:2],  # Top-2만 저장
                    "expected": expected
                }
                
                disease_results.append(result_entry)
                all_results.append(result_entry)
                
                # 통계 업데이트
                mode_stats[mode]["response_times"].append(test_result['api_response_time_ms'])
                mode_stats[mode]["accuracies"].append(accuracy)
                
                print(f"      ✅ Top-1: {accuracy['top1_accuracy']:.1%}, Top-2: {accuracy['top2_accuracy']:.1%}, {test_result['api_response_time_ms']:.0f}ms")
                
            else:
                print(f"      ❌ 실패: {test_result['error']}")
        
        print()
    
    # 통계 계산
    final_stats = {}
    for mode in rerank_modes:
        times = mode_stats[mode]["response_times"]
        accuracies = mode_stats[mode]["accuracies"]
        
        if times and accuracies:
            avg_top1 = statistics.mean([acc['top1_accuracy'] for acc in accuracies])
            avg_top2 = statistics.mean([acc['top2_accuracy'] for acc in accuracies])
            avg_time = statistics.mean(times)
            p95_time = statistics.quantiles(times, n=20)[18] if len(times) >= 5 else max(times)
            
            final_stats[mode] = {
                "avg_top1_accuracy": avg_top1,
                "avg_top2_accuracy": avg_top2,
                "avg_response_time_ms": avg_time,
                "p95_response_time_ms": p95_time,
                "test_count": len(times)
            }
        else:
            final_stats[mode] = {
                "avg_top1_accuracy": 0.0,
                "avg_top2_accuracy": 0.0,
                "avg_response_time_ms": 0.0,
                "p95_response_time_ms": 0.0,
                "test_count": 0
            }
    
    return {
        "test_summary": {
            "total_diseases": len(diseases),
            "total_tests": len(all_results),
            "rerank_modes": rerank_modes,
            "timestamp": datetime.now().isoformat()
        },
        "mode_comparison": final_stats,
        "detailed_results": all_results
    }

def print_results(results: Dict[str, Any]):
    """결과 출력"""
    print("📊 A/B 리랭킹 테스트 결과:")
    print("=" * 80)
    
    mode_stats = results["mode_comparison"]
    
    # 성능 비교표
    print("🏆 모드별 성능 비교:")
    print(f"{'모드':<12} {'Top-1 정확도':<12} {'Top-2 정확도':<12} {'평균응답시간':<12} {'P95 응답시간':<12}")
    print("-" * 65)
    
    for mode, stats in mode_stats.items():
        print(f"{mode.upper():<12} "
              f"{stats['avg_top1_accuracy']:<12.1%} "
              f"{stats['avg_top2_accuracy']:<12.1%} "
              f"{stats['avg_response_time_ms']:<12.0f}ms "
              f"{stats['p95_response_time_ms']:<12.0f}ms")
    
    print()
    
    # 성능 목표 대비 평가 (BACKEND_PLAN.md)
    print("🎯 성능 목표 달성도 (BACKEND_PLAN.md):")
    for mode, stats in mode_stats.items():
        avg_ok = "✅" if stats['avg_response_time_ms'] <= 900 else "❌"
        p95_ok = "✅" if stats['p95_response_time_ms'] <= 1200 else "❌"
        
        print(f"  {mode.upper()}: 평균 {avg_ok} (목표 ≤900ms), P95 {p95_ok} (목표 ≤1200ms)")
    
    print()
    
    # 정확도 개선 분석
    if "off" in mode_stats:
        baseline = mode_stats["off"]
        print("📈 리랭킹 효과 분석 (vs 기준선):")
        
        for mode in ["llm", "ce"]:
            if mode in mode_stats:
                stats = mode_stats[mode]
                top1_improvement = stats['avg_top1_accuracy'] - baseline['avg_top1_accuracy']
                top2_improvement = stats['avg_top2_accuracy'] - baseline['avg_top2_accuracy']
                
                print(f"  {mode.upper()}: Top-1 {top1_improvement:+.1%}, Top-2 {top2_improvement:+.1%}")

def save_results(results: Dict[str, Any], output_dir: str = "ab_test_results"):
    """결과 저장"""
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    output_file = os.path.join(output_dir, f"ab_rerank_test_{timestamp}.json")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"💾 결과 저장: {output_file}")
    return output_file

def main():
    """메인 실행"""
    base_url = "http://localhost:8002"
    
    if len(sys.argv) > 1:
        base_url = sys.argv[1]
    
    try:
        results = run_ab_test(base_url)
        
        if results:
            print_results(results)
            save_results(results)
            print("\n✅ A/B 리랭킹 테스트 완료!")
        else:
            print("❌ 테스트 실행 실패")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n⏹️ 사용자에 의해 중단됨")
        sys.exit(1)
    except Exception as e:
        print(f"❌ 테스트 실행 중 오류: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()