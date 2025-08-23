#!/usr/bin/env python3
"""
병원 검색 백엔드 API 서버
FastAPI + Qdrant + Rerank + Agent 기반 한국 피부과 전문병원 검색 시스템

BACKEND_PLAN.md 사양:
- 입력: FT XML(label/summary/similar)만 수신  
- 처리: Dense TopK=24 → (선택)BM25 결합 → Parent 그룹(8-12)
  - 파이프라인 모드: CrossEncoder/LLM-only 리랭크 → 최종 Parent 2개
  - 에이전트 모드: LangChain+LangGraph ReAct Agent → 최종 2개 요약
- 출력: 병원 2개(병원명/지역/연락처/특화 + 대표 child 제목/핵심문구, 내부 점수/지연)
"""

import os
import time
import logging
import traceback
from datetime import datetime
from typing import Dict, List, Any, Optional
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# 로컬 모듈 import
try:
    from utils.pipeline_factory import create_pipeline_from_config
    from pipeline.rag_pipeline import HospitalRAGPipeline
    from utils.ft_output_parser import parse_ft_xml_to_model_output
    from utils.logger import (
        jsonl_logger, performance_monitor, create_performance_timer,
        JSONLLogger, PerformanceTimer
    )
except ImportError as e:
    logging.error(f"필수 모듈 import 실패: {e}")
    raise

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('hospital_search_backend.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

# 글로벌 상태
app_state = {
    "pipeline": None,
    "startup_time": None,
    "qdrant_status": "unknown",
    "reranker_status": "unknown"
}

# Pydantic 모델들
class HealthResponse(BaseModel):
    status: str = Field(description="서비스 상태")
    startup_time: Optional[str] = Field(description="시작 시간")
    qdrant_status: str = Field(description="Qdrant 연결 상태")
    reranker_status: str = Field(description="리랭커 로딩 상태")
    uptime_seconds: Optional[float] = Field(description="업타임(초)")

class SearchFTXMLRequest(BaseModel):
    xml: str = Field(description="FT XML 입력 (<root>...</root>)")
    rerank_mode: str = Field(default="ce", description="리랭킹 모드: llm|ce|off")
    top_k: int = Field(default=24, description="초기 후보 수")
    group_size: int = Field(default=10, description="Parent 그룹 크기")
    final_k: int = Field(default=2, description="최종 결과 수")

class SearchFTXMLResponse(BaseModel):
    results: List[Dict[str, Any]] = Field(description="검색 결과")
    meta: Dict[str, Any] = Field(description="메타 정보")

class AgentQueryRequest(BaseModel):
    message: str = Field(description="자연어 쿼리")
    k: int = Field(default=5, description="검색할 문서 수")

class AgentQueryResponse(BaseModel):
    answer: str = Field(description="에이전트 응답")
    sources: List[Dict[str, Any]] = Field(description="참조 소스")
    meta: Dict[str, Any] = Field(description="메타 정보")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI 라이프사이클 관리"""
    # 시작 시 초기화
    logger.info("🚀 병원 검색 백엔드 초기화 시작...")
    app_state["startup_time"] = datetime.now().isoformat()
    
    try:
        # 파이프라인 초기화
        logger.info("📦 RAG 파이프라인 생성 중...")
        pipeline = create_pipeline_from_config(
            rerank_model_type="ce"  # CrossEncoder 기본값
        )
        app_state["pipeline"] = pipeline
        app_state["qdrant_status"] = "connected"
        app_state["reranker_status"] = "loaded"
        
        logger.info("✅ 백엔드 초기화 완료!")
        
    except Exception as e:
        logger.error(f"❌ 초기화 실패: {e}")
        logger.error(traceback.format_exc())
        app_state["qdrant_status"] = "error"
        app_state["reranker_status"] = "error"
    
    yield
    
    # 종료 시 정리
    logger.info("🛑 백엔드 종료 중...")

# FastAPI 앱 생성
app = FastAPI(
    title="병원 검색 백엔드",
    description="한국 피부과 전문병원 검색을 위한 RAG 파이프라인 API",
    version="1.0.0",
    lifespan=lifespan
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 프로덕션에서는 특정 도메인만 허용
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """
    서비스 헬스체크
    - Qdrant 연결 상태
    - 리랭커 로딩 상태  
    - 업타임 정보 반환
    - 성능 통계 포함
    """
    startup_time = app_state.get("startup_time")
    uptime = None
    
    if startup_time:
        startup_dt = datetime.fromisoformat(startup_time)
        uptime = (datetime.now() - startup_dt).total_seconds()
    
    # 성능 통계 추가
    performance_stats = performance_monitor.get_performance_stats()
    performance_alerts = performance_monitor.check_performance_alerts()
    
    health_status = "healthy"
    if app_state["pipeline"] is None:
        health_status = "unhealthy"
    elif performance_alerts:
        health_status = "degraded"
    
    response = HealthResponse(
        status=health_status,
        startup_time=startup_time,
        qdrant_status=app_state["qdrant_status"],
        reranker_status=app_state["reranker_status"],
        uptime_seconds=uptime
    )
    
    # 성능 정보를 추가 필드로 포함
    response_dict = response.dict()
    response_dict["performance"] = performance_stats
    if performance_alerts:
        response_dict["alerts"] = performance_alerts
    
    return response_dict

@app.post("/search-ft-xml", response_model=SearchFTXMLResponse)
async def search_ft_xml(request: SearchFTXMLRequest):
    """
    FT XML 기반 병원 검색 (파이프라인 모드)
    
    처리 단계:
    1. XML → 구조화된 쿼리 파싱
    2. Dense TopK=24 → BM25 결합 → Parent 그룹
    3. CrossEncoder/LLM 리랭킹 → 최종 2개 병원
    """
    # 성능 측정 시작
    timer = create_performance_timer()
    timer.start_total()
    
    request_id = f"req_{int(time.time() * 1000)}"
    
    logger.info(f"[{request_id}] FT XML 검색 요청: rerank_mode={request.rerank_mode}")
    
    if app_state["pipeline"] is None:
        raise HTTPException(status_code=503, detail="파이프라인이 초기화되지 않았습니다")
    
    results = []
    response_meta = {}
    success = False
    error_msg = ""
    
    try:
        # 1. XML 파싱
        with timer.time_step("embed"):
            logger.info(f"[{request_id}] XML 파싱 시작...")
            parsed_output = parse_ft_xml_to_model_output(request.xml)
            
            if not parsed_output:
                raise HTTPException(status_code=400, detail="XML 파싱에 실패했습니다")
        
        # 2. 파이프라인 실행 - 각 단계별 시간 측정
        pipeline: HospitalRAGPipeline = app_state["pipeline"]
        
        with timer.time_step("search"):
            logger.info(f"[{request_id}] 파이프라인 실행 시작...")
            
            # FT XML 파싱
            parsed_output = parse_ft_xml_to_model_output(request.xml)
            diagnosis = parsed_output.get("diagnosis") or parsed_output.get("disease") or ""
            description = parsed_output.get("description") or parsed_output.get("notes")
            similar = parsed_output.get("similar_diseases") or parsed_output.get("aliases") or []
            
            # 동적 리랭킹을 적용한 검색
            results_data = pipeline.search_with_dynamic_reranking(
                diagnosis=diagnosis,
                description=description,
                similar_diseases=similar,
                candidate_limit=request.top_k,
                rerank_mode=request.rerank_mode,
                final_top_k=request.final_k
            )
        
        # 전체 시간 측정 완료
        total_elapsed = timer.finish_total()
        
        # 결과 처리
        results = results_data.get("results", [])
        response_meta = results_data.get("meta", {})
        success = True
        
        # 성능 모니터링에 기록
        elapsed_ms = timer.get_timings().get("total_ms", 0)
        performance_monitor.record_response_time(elapsed_ms)
        
        # 3. 응답 구성
        response_meta.update({
            "request_id": request_id,
            "elapsed_ms": elapsed_ms,
            "rerank_mode": request.rerank_mode,
            "parameters": {
                "top_k": request.top_k,
                "group_size": request.group_size, 
                "final_k": request.final_k
            },
            "timing_breakdown": timer.get_timings()
        })
        
        # JSONL 로깅
        input_data = {
            "diagnosis": parsed_output.get("diagnosis", ""),
            "rerank_mode": request.rerank_mode,
            "top_k": request.top_k,
            "group_size": request.group_size,
            "final_k": request.final_k
        }
        
        jsonl_logger.log_search_request(
            request_id=request_id,
            request_type="ft_xml",
            input_data=input_data,
            timing_data=timer.get_timings(),
            results=results,
            meta={**response_meta, "success": success}
        )
        
        logger.info(f"[{request_id}] 검색 완료: {len(results)}개 결과, {total_elapsed:.2f}s")
        
        return SearchFTXMLResponse(
            results=results,
            meta=response_meta
        )
        
    except Exception as e:
        total_elapsed = timer.finish_total()
        elapsed_ms = timer.get_timings().get("total_ms", 0)
        error_msg = str(e)
        
        logger.error(f"[{request_id}] 검색 오류: {e}")
        logger.error(traceback.format_exc())
        
        # 실패 로그도 기록
        jsonl_logger.log_search_request(
            request_id=request_id,
            request_type="ft_xml",
            input_data={"rerank_mode": request.rerank_mode, "error": error_msg},
            timing_data=timer.get_timings(),
            results=[],
            meta={"success": False, "error": error_msg}
        )
        
        raise HTTPException(
            status_code=500, 
            detail={
                "error": error_msg,
                "request_id": request_id,
                "elapsed_ms": elapsed_ms
            }
        )

@app.post("/agent-query", response_model=AgentQueryResponse) 
async def agent_query(request: AgentQueryRequest):
    """
    에이전트 모드 자연어 쿼리 처리
    
    향후 LangGraph ReAct Agent 구현 예정
    현재는 기본 검색으로 처리
    """
    start_time = time.time()
    request_id = f"agent_{int(start_time * 1000)}"
    
    logger.info(f"[{request_id}] 에이전트 쿼리: {request.message[:50]}...")
    
    if app_state["pipeline"] is None:
        raise HTTPException(status_code=503, detail="파이프라인이 초기화되지 않았습니다")
    
    try:
        # TODO: LangGraph ReAct Agent 구현
        # 현재는 기본 파이프라인으로 처리
        pipeline: HospitalRAGPipeline = app_state["pipeline"]
        
        # 임시로 메시지를 진단명으로 처리
        results = pipeline.search_hospitals(
            diagnosis=request.message,
            final_top_k=min(request.k, 5)
        )
        
        elapsed = time.time() - start_time
        
        # 에이전트 스타일 응답 생성
        answer = f"{request.message}에 대한 추천 병원을 찾았습니다."
        sources = [
            {
                "source": result.get("parent", {}).get("name", "알 수 없는 병원"),
                "snippet": result.get("child", {}).get("title", "")
            }
            for result in results.get("results", [])
        ]
        
        logger.info(f"[{request_id}] 에이전트 응답 완료: {elapsed:.2f}s")
        
        return AgentQueryResponse(
            answer=answer,
            sources=sources,
            meta={
                "request_id": request_id,
                "elapsed_ms": round(elapsed * 1000, 2),
                "k": request.k
            }
        )
        
    except Exception as e:
        elapsed = time.time() - start_time
        logger.error(f"[{request_id}] 에이전트 쿼리 오류: {e}")
        
        raise HTTPException(
            status_code=500,
            detail={
                "error": str(e),
                "request_id": request_id,
                "elapsed_ms": round(elapsed * 1000, 2)
            }
        )

@app.get("/")
async def root():
    """루트 엔드포인트"""
    return {
        "service": "병원 검색 백엔드",
        "version": "1.0.0",
        "endpoints": [
            "GET /health - 헬스체크",
            "POST /search-ft-xml - FT XML 기반 검색",
            "POST /agent-query - 에이전트 자연어 쿼리"
        ],
        "docs": "/docs"
    }

if __name__ == "__main__":
    # 설정 로드
    port = int(os.getenv("PORT", 8002))
    host = os.getenv("HOST", "0.0.0.0")
    
    logger.info(f"🌐 병원 검색 백엔드 시작: http://{host}:{port}")
    
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=False,  # 프로덕션에서는 False
        log_level="info"
    )
