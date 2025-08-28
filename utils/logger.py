#!/usr/bin/env python3
"""
BACKEND_PLAN.md 사양에 따른 JSONL 로깅 시스템

로그 형식:
- 요청 ID, diagnosis/message, 후보 수
- 단계별 지연(embed/search/combine/group/rerank/join)
- 최종 2개 및 근거 텍스트, rerank_mode
"""

import json
import time
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
from contextlib import contextmanager

class JSONLLogger:
    """BACKEND_PLAN.md 사양에 맞는 JSONL 로거"""
    
    def __init__(self, log_dir: str = "logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        
        # 로그 파일 경로
        today = datetime.now().strftime("%Y%m%d")
        self.search_log_path = self.log_dir / f"search_requests_{today}.jsonl"
        self.performance_log_path = self.log_dir / f"performance_{today}.jsonl"
        
        # 표준 로거 설정
        self.logger = logging.getLogger("hospital_search_backend")
    
    def log_search_request(
        self,
        request_id: str,
        request_type: str,  # "ft_xml" or "agent"
        input_data: Dict[str, Any],
        timing_data: Dict[str, float],
        results: List[Dict[str, Any]],
        meta: Dict[str, Any]
    ):
        """검색 요청 로그 기록"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "request_id": request_id,
            "request_type": request_type,
            "input": {
                "diagnosis": input_data.get("diagnosis", ""),
                "message": input_data.get("message", ""),
                "rerank_mode": input_data.get("rerank_mode", ""),
                "parameters": {
                    "top_k": input_data.get("top_k", 0),
                    "group_size": input_data.get("group_size", 0),
                    "final_k": input_data.get("final_k", 0)
                }
            },
            "timing": {
                "total_ms": timing_data.get("total_ms", 0),
                "embed_ms": timing_data.get("embed_ms", 0),
                "search_ms": timing_data.get("search_ms", 0),
                "combine_ms": timing_data.get("combine_ms", 0),
                "group_ms": timing_data.get("group_ms", 0),
                "rerank_ms": timing_data.get("rerank_ms", 0),
                "join_ms": timing_data.get("join_ms", 0)
            },
            "results": {
                "count": len(results),
                "candidates": meta.get("candidates", 0),
                "grouped": meta.get("grouped", 0),
                "final_hospitals": [
                    {
                        "hospital_name": r.get("parent", {}).get("name", ""),
                        "region": r.get("parent", {}).get("region", ""),
                        "treatment": r.get("child", {}).get("title", ""),
                        "scores": r.get("scores", {}),
                        "rationale": r.get("child", {}).get("embedding_text", "")[:200] + "..."
                    }
                    for r in results[:2]  # 최종 2개
                ]
            },
            "meta": {
                "rerank_mode": meta.get("rerank_mode", ""),
                "success": meta.get("success", True),
                "error": meta.get("error", "")
            }
        }
        
        # JSONL 파일에 기록
        with open(self.search_log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
    
    def log_performance_metrics(
        self,
        request_id: str,
        metrics: Dict[str, Any]
    ):
        """성능 메트릭 로그 기록"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "request_id": request_id,
            "metrics": metrics
        }
        
        with open(self.performance_log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")

class PerformanceTimer:
    """성능 측정 타이머"""
    
    def __init__(self):
        self.timings: Dict[str, float] = {}
        self.start_time: Optional[float] = None
    
    @contextmanager
    def time_step(self, step_name: str):
        """특정 단계 시간 측정 컨텍스트 매니저"""
        step_start = time.time()
        try:
            yield
        finally:
            step_end = time.time()
            self.timings[f"{step_name}_ms"] = round((step_end - step_start) * 1000, 2)
    
    def start_total(self):
        """전체 시간 측정 시작"""
        self.start_time = time.time()
    
    def finish_total(self) -> float:
        """전체 시간 측정 완료"""
        if self.start_time is None:
            return 0.0
        
        total_elapsed = time.time() - self.start_time
        self.timings["total_ms"] = round(total_elapsed * 1000, 2)
        return total_elapsed
    
    def get_timings(self) -> Dict[str, float]:
        """시간 측정 결과 반환"""
        return self.timings.copy()

class PerformanceMonitor:
    """성능 모니터링 및 알람"""
    
    def __init__(self, p95_threshold_ms: int = 1200, avg_threshold_ms: int = 900):
        self.p95_threshold = p95_threshold_ms
        self.avg_threshold = avg_threshold_ms
        self.recent_response_times: List[float] = []
        self.max_history = 100  # 최근 100개 요청만 추적
    
    def record_response_time(self, response_time_ms: float):
        """응답 시간 기록"""
        self.recent_response_times.append(response_time_ms)
        
        # 히스토리 크기 제한
        if len(self.recent_response_times) > self.max_history:
            self.recent_response_times = self.recent_response_times[-self.max_history:]
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """현재 성능 통계 반환"""
        if not self.recent_response_times:
            return {"status": "no_data"}
        
        sorted_times = sorted(self.recent_response_times)
        count = len(sorted_times)
        
        avg_time = sum(sorted_times) / count
        p95_index = int(count * 0.95)
        p95_time = sorted_times[min(p95_index, count - 1)]
        
        return {
            "status": "healthy",
            "request_count": count,
            "avg_response_ms": round(avg_time, 2),
            "p95_response_ms": round(p95_time, 2),
            "min_response_ms": round(sorted_times[0], 2),
            "max_response_ms": round(sorted_times[-1], 2),
            "performance_alerts": {
                "avg_exceeds_target": avg_time > self.avg_threshold,
                "p95_exceeds_target": p95_time > self.p95_threshold
            }
        }
    
    def check_performance_alerts(self) -> List[str]:
        """성능 알람 확인"""
        stats = self.get_performance_stats()
        alerts = []
        
        if stats.get("performance_alerts", {}).get("avg_exceeds_target"):
            alerts.append(f"평균 응답시간이 목표({self.avg_threshold}ms)를 초과: {stats['avg_response_ms']}ms")
        
        if stats.get("performance_alerts", {}).get("p95_exceeds_target"):
            alerts.append(f"P95 응답시간이 목표({self.p95_threshold}ms)를 초과: {stats['p95_response_ms']}ms")
        
        return alerts

# 글로벌 인스턴스
jsonl_logger = JSONLLogger()
performance_monitor = PerformanceMonitor()

def create_performance_timer() -> PerformanceTimer:
    """새 성능 타이머 생성"""
    return PerformanceTimer()