# 병원 검색 백엔드 설정 파일
# BACKEND_PLAN.md 사양에 따른 설정
import os
from dotenv import load_dotenv

# .env 파일 로드 (있는 경우)
load_dotenv()

# OpenAI API 설정
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "your_openai_api_key_here")

# Qdrant 설정
QDRANT_URL = os.getenv("QDRANT_URL", "your_qdrant_url_here")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY", "your_qdrant_api_key_here")

# 컬렉션 이름 (BACKEND_PLAN.md 사양)
CHILDREN_COLLECTION = "derm_children"
PARENTS_COLLECTION = "derm_parents"

# 임베딩 설정
EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSION = 1536

# RAG 파이프라인 기본 설정 (BACKEND_PLAN.md)
DEFAULT_SEARCH_CONFIG = {
    "top_k": 24,          # 초기 후보 수
    "group_size": 10,     # Parent 그룹 크기 (8-12)
    "final_k": 2,         # 최종 결과 수
    "sparse_weight": 0.5, # BM25 가중치
    "rerank_mode": "ce"   # CrossEncoder 기본값
}

# 성능 목표 (BACKEND_PLAN.md)
PERFORMANCE_TARGETS = {
    "p95_ms": 1200,      # p95 ≤ 1200ms
    "avg_ms": 900,       # 평균 ≤ 900ms
    "timeout_ms": 5000   # 요청 타임아웃
}

# 리랭킹 모델 설정
RERANKER_MODELS = {
    "ce": "BAAI/bge-reranker-base",  # CrossEncoder 기본값
    "llm": "gpt-4o-mini"             # LLM 기본값
}
