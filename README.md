# Hospital Search Backend

Korean dermatology hospital search system with FastAPI + RAG pipeline, following BACKEND_PLAN.md specifications.

## 🎯 주요 기능

- **FT XML 검색**: Fine-tuned 모델 XML 출력을 받아 병원 검색
- **하이브리드 검색**: Dense embedding + BM25 sparse search 
- **멀티 리랭킹**: CrossEncoder(BGE) / LLM 기반 리랭킹
- **성능 모니터링**: JSONL 로깅, 실시간 성능 통계
- **A/B 테스트**: 리랭킹 알고리즘 성능 비교

## 📋 시스템 사양 (BACKEND_PLAN.md)

- **입력**: FT XML (`<label>`, `<summary>`, `<similar>`)
- **처리**: Dense TopK=24 → BM25 결합 → Parent 그룹(8-12) → 리랭킹 → 최종 2개
- **출력**: 병원 2개 (병원명/지역/연락처 + 치료정보 + 점수/지연시간)
- **성능 목표**: p95 ≤ 1200ms, 평균 ≤ 900ms

## 🚀 빠른 시작

### 1. 환경 설정

```bash
# Python 가상환경 생성
python3 -m venv venv
source venv/bin/activate

# 의존성 설치
pip install -r requirements.txt
```

### 2. 설정 파일

API 키를 설정합니다 (`config.py` 또는 환경변수):

```python
# config.py (권장)
OPENAI_API_KEY = "your-openai-api-key"
QDRANT_URL = "http://localhost:6333"  # 또는 클라우드 URL
QDRANT_API_KEY = None  # 클라우드 사용시 설정
```

또는 환경변수:
```bash
export OPENAI_API_KEY="your-api-key"
export QDRANT_URL="http://localhost:6333"
export QDRANT_API_KEY="your-qdrant-key"  # optional
```

### 3. Qdrant 서버 실행

**Docker 사용 (권장):**
```bash
docker run -p 6333:6333 -p 6334:6334 --name qdrant qdrant/qdrant
```

### 4. 서버 실행

```bash
python main.py
```

서버가 `http://localhost:8002`에서 실행됩니다.

## 📡 API 엔드포인트

### 헬스체크
```bash
GET /health
```

응답 예시:
```json
{
  "status": "healthy",
  "qdrant_status": "connected", 
  "reranker_status": "loaded",
  "uptime_seconds": 3600.5,
  "performance": {
    "avg_response_ms": 850.2,
    "p95_response_ms": 1150.0
  }
}
```

### FT XML 검색 (메인 기능)
```bash
POST /search-ft-xml
Content-Type: application/json
```

요청 예시:
```json
{
  "xml": "<root><label>악성흑색종</label><summary>환자가 피부에 검은 점이 생기고 크기가 변한다고 호소</summary><similar>멜라노마,흑색종,melanoma</similar></root>",
  "rerank_mode": "ce",
  "top_k": 24,
  "group_size": 10, 
  "final_k": 2
}
```

응답 예시:
```json
{
  "results": [
    {
      "parent": {
        "name": "세브란스병원 흑색종클리닉",
        "region": "서울 서대문",
        "contacts": {
          "tel": "1599-1004",
          "addr": "서울 서대문구 연세로 50"
        },
        "specialties": ["악성흑색종", "다학제", "면역항암"]
      },
      "child": {
        "title": "흑색종 다학제(세브란스)",
        "embedding_text": "악성흑색종은 비대칭, 경계 불규칙..."
      },
      "scores": {
        "dense": 0.892,
        "sparse": 0.745, 
        "combined": 0.819,
        "rerank": 0.945
      }
    }
  ],
  "meta": {
    "request_id": "req_1692781234567",
    "elapsed_ms": 847.2,
    "rerank_mode": "ce",
    "candidates": 24,
    "grouped": 8,
    "timing_breakdown": {
      "embed_ms": 45.3,
      "search_ms": 312.1,
      "rerank_ms": 489.8
    }
  }
}
```

### 에이전트 쿼리 (향후 확장)
```bash
POST /agent-query
```

요청 예시:
```json
{
  "message": "악성흑색종 치료 병원 추천해주세요",
  "k": 3
}
```

## 🧪 테스트 및 검증

### 스모크 테스트
```bash
python test_backend_smoke.py
```

### A/B 리랭킹 테스트
```bash
python test_ab_reranking.py
```

15개 질병 × 3개 리랭킹 모드(off/llm/ce) = 45개 테스트 케이스 실행하여 성능 비교:
- Top-1/Top-2 정확도
- 평균/P95 응답시간  
- 리랭킹 효과 분석

### 정답지 생성 (개발자용)
```bash
python ../generate_ground_truth.py
```

## 📊 성능 모니터링

### 로그 파일
- `logs/search_requests_YYYYMMDD.jsonl`: 검색 요청 상세 로그
- `logs/performance_YYYYMMDD.jsonl`: 성능 메트릭
- `hospital_search_backend.log`: 일반 서버 로그

### 성능 통계
`/health` 엔드포인트에서 실시간 성능 통계 확인:
- 평균/P95 응답시간
- 성능 목표 달성 여부
- 성능 경고 알림

## 🔧 리랭킹 모드

| 모드 | 설명 | 특징 |
|------|------|------|
| `off` | 리랭킹 없음 | 하이브리드 검색 결과만 사용 |
| `llm` | LLM 리랭킹 | GPT-4o-mini로 관련도 점수 계산 |
| `ce` | CrossEncoder | BGE 모델로 정밀한 관련도 계산 (기본값) |

## 📁 프로젝트 구조

```
병원 검색 백엔드/
├── main.py                     # FastAPI 서버
├── config.py                   # 설정 파일
├── requirements.txt            # 의존성 목록
├── test_backend_smoke.py       # 스모크 테스트
├── test_ab_reranking.py        # A/B 리랭킹 테스트
├── models/                     # RAG 파이프라인 모델
│   ├── query_builder.py        # 쿼리 확장
│   ├── hybrid_search.py        # 하이브리드 검색 + 리랭킹
│   └── reranker.py            # LangChain 리랭커
├── pipeline/                   # 파이프라인 오케스트레이션
│   └── rag_pipeline.py         # 메인 RAG 파이프라인
├── utils/                      # 유틸리티
│   ├── pipeline_factory.py     # 파이프라인 팩토리
│   ├── logger.py              # JSONL 로깅 시스템
│   └── ft_output_parser.py    # FT XML 파서
├── eval_data/                  # 정답지 및 평가 데이터
├── logs/                       # 로그 파일
├── ab_test_results/           # A/B 테스트 결과
├── children.jsonl             # 자식 문서 (검색 대상)
└── parents.jsonl              # 부모 문서 (병원 메타데이터)
```

## 🔌 다른 프로젝트에 이식하기

### 1. 독립 실행
이 디렉토리만 복사하여 다른 환경에서 독립 실행 가능합니다.

### 2. API 통합
다른 애플리케이션에서 REST API로 호출:

```python
import requests

response = requests.post(
    "http://your-server:8002/search-ft-xml",
    json={
        "xml": "<root><label>질병명</label>...</root>",
        "rerank_mode": "ce"
    }
)
hospitals = response.json()["results"]
```

### 3. 파이프라인 임베드
Python 코드에서 직접 파이프라인 사용:

```python
from utils.pipeline_factory import create_pipeline_from_config

pipeline = create_pipeline_from_config(rerank_model_type="ce")
results = pipeline.search_from_ft_xml(xml_content)
```

## ⚙️ 환경별 설정

### 개발환경
```python
QDRANT_URL = "http://localhost:6333"
DEBUG = True
LOG_LEVEL = "DEBUG"
```

### 프로덕션 환경
```python
QDRANT_URL = "https://your-qdrant-cluster.com"  
QDRANT_API_KEY = "production-api-key"
DEBUG = False
LOG_LEVEL = "INFO"
```

## 🚨 트러블슈팅

### 일반적인 문제

**Q: "파이프라인이 초기화되지 않았습니다" 에러**
- Qdrant 서버 연결 확인
- OpenAI API 키 설정 확인
- `derm_children` 컬렉션 존재 확인

**Q: 응답 시간이 목표(900ms)를 초과**
- 리랭커 모델 로딩 상태 확인
- Qdrant 서버 성능 점검
- `top_k` 파라미터 조정 (기본값: 24)

**Q: 정확도가 낮음**
- 정답지 기반 A/B 테스트로 리랭킹 모드 비교
- `ce` (CrossEncoder) 모드 사용 권장
- 쿼리 확장 로직 점검

### 성능 최적화

1. **Qdrant 최적화**: 인덱스 설정, 메모리 할당
2. **리랭커 최적화**: 배치 크기, 모델 캐싱
3. **API 최적화**: 연결 풀링, 타임아웃 설정

## 📄 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다.
